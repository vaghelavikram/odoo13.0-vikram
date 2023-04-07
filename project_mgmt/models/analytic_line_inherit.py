# -*- coding: utf-8 -*-

from datetime import datetime, time, timedelta
import collections, functools, operator
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class AnalyticLineInherit(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['account.analytic.line', 'mail.thread', 'mail.activity.mixin']

    tym_task_shift = fields.Selection([('regular', 'Regular'), ('shift_1', 'Shift 1'), ('shft_2', 'Shift 2')], string="Shift", default='regular')
    is_regularize = fields.Boolean(string="Regularize Done")
    state = fields.Selection([('open', 'Draft'), ('regularize', 'Attendance Requested'), ('approved', 'Approved'), ('not_regularize', 'Already Requested'), ('reject', 'Rejected')], string="Attendance Status", default="open", tracking=True)
    regular_id = fields.Many2one('attendance.regular', string="View Attendance Request")
    payroll_pass = fields.Boolean(string="Payroll Passed")
    unit_amount = fields.Float('Duration (Hours)', default=0.0, tracking=True)
    external_timesheet = fields.Boolean(string="Ext Timesheet")
    start_datetime = fields.Datetime(string="DateTime")
    partner_id = fields.Many2one(related="project_id.partner_id", string="Customer")
    project_ids = fields.Many2many('project.project', string="Project Ids", compute="_compute_user_project")

    @api.depends('user_id', 'start_datetime', 'date')
    def _compute_user_project(self):
        for rec in self:
            allocations = self.env['project.assignment'].sudo().search([('employee_id', '=', self.user_id.employee_id.id), ('assign_status', '=', 'confirmed'), ('end_date', '>=', fields.Date.today())])
            allocations = allocations.filtered(lambda alloc: alloc.project_id.actual_end_date is False)
            projects = allocations.mapped('project_id.id')
            if projects:
                rec.project_ids = projects
            else:
                on_bench_project = self.env['project.project'].sudo().search([('name', '=', 'On Bench Internal Project'), ('active', '=', False)])
                rec.project_ids = on_bench_project.ids
                rec.project_id = on_bench_project.id

    @api.onchange('start_datetime', 'date')
    def _onchange_start_datetime(self):
        if self.start_datetime:
            from_date = self.start_datetime + timedelta(hours=5, minutes=30)
            if from_date.time().hour >= 6:
                self.date = self.start_datetime
            else:
                self.date = from_date
        elif not self.start_datetime and self.date:
            self.start_datetime = datetime.today().replace(hour=3, minute=30, second=00)
        allocations = self.env['project.assignment'].sudo().search([('employee_id', '=', self.user_id.employee_id.id), ('assign_status', '=', 'confirmed'),('end_date', '>=', self.start_datetime.strftime('%Y-%m-%d'))])
        projects = allocations.mapped('project_id.id')
        if projects:
            self.project_ids = projects
        else:
            on_bench_project = self.env['project.project'].sudo().search([('name', '=', 'On Bench Internal Project'), ('active', '=', False)])
            #self.project_ids = on_bench_project.ids
            self.project_id = on_bench_project.ids

    @api.model
    def default_get(self, vals):
        rslt = super(AnalyticLineInherit, self).default_get(vals)
        employee = self.env.user.employee_id
        allocation = employee.allocation_ids
        active_alloc = [i for i in allocation if i.end_date and i.end_date >= fields.Date.today()]
        project = self.env['project.project'].sudo().search([('name', '=', 'On Bench Internal Project'), ('active', '=', False)])
        if not project:
            project = self.env['project.project'].sudo().create({
                'name': 'On Bench Internal Project',
                'is_internal': True,
                'active': False,
            })
        if not active_alloc:
            rslt['project_id'] = project.id
        return rslt

    @api.model
    def create(self, vals):
        # import pdb;
        # pdb.set_trace()
        if vals.get('task_id'):
            task = self.env['project.task'].browse(vals.get('task_id'))
            project_id = self.env['project.project'].browse(vals.get('project_id'))
            if project_id.name != 'Internal Project':
                if not task.start_date or not task.date_deadline:
                    raise UserError("Fill Task start date and end date.")
            if project_id.name != 'Internal Project' and not(str(task.start_date) <= vals.get('date') and str(task.date_deadline) >= vals.get('date')):
                raise UserError("Fill timesheet within task duration i.e %s-%s." % (task.start_date.strftime('%d-%b-%Y'), task.date_deadline.strftime('%d-%b-%Y')))
        if not vals.get('move_id') and not vals.get('external_timesheet'):
            total_hours = [i.unit_amount for i in self.env['account.analytic.line'].search([('employee_id', '=', vals.get('employee_id')), ('state', '!=', 'reject')]) if str(i.date) == vals.get('date')]
            total_hours.append(vals.get('unit_amount'))
            payroll_from_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'), '%Y-%m-%d').date()
            payroll_to_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date'), '%Y-%m-%d').date()
            if sum(total_hours) > 24:
                raise UserError(_("You can't add timesheet for more than 24 hours for same date."))
            elif vals.get('unit_amount') > 24:
                raise UserError(_("You can't add timesheet for more than 24 hours."))
            elif vals.get('unit_amount') <= 0:
                raise UserError(_("You can't add timesheet for 0 hours."))
            res = super(AnalyticLineInherit, self.with_context(mail_create_nosubscribe=True)).create(vals)
            if res.company_id.name == 'e-Zest Solutions Ltd.' and res.user_id.employee_id.employee_category.name == 'eZestian' and res.create_date.date() > payroll_to_date + relativedelta(days=1) and res.date > payroll_from_date and res.date < payroll_to_date + relativedelta(days=1):
                res.payroll_pass = True
            elif res.company_id.name == 'e-Zest Solutions Ltd.' and res.user_id.employee_id.employee_category.name == 'eZestian' and res.date < payroll_from_date:
                res.payroll_pass = True
            else:
                self.timesheet_attendance_regularize(res)
        else:
            res = super(AnalyticLineInherit, self.with_context(mail_create_nosubscribe=True)).create(vals)
        return res

    def write(self, vals):
        for rec in self:
            if vals.get('date') and rec.task_id:
                if rec.project_id.name != 'Internal Project' and not(str(rec.task_id.start_date) <= vals.get('date') and str(rec.task_id.date_deadline) >= vals.get('date')):
                    raise UserError("Fill timesheet within task duration.")
            unit_amount = rec.unit_amount
            res = super(AnalyticLineInherit, self).write(vals)
            if vals.get('unit_amount'):
                total_hours = [i.unit_amount for i in self.env['account.analytic.line'].search([('employee_id','=',rec.employee_id.id), ('state', '!=', 'reject')]) if i.date == rec.date]
                if sum(total_hours) > 24:
                    raise UserError(_("You can't add timesheet for more than 24 hours for same date."))
                elif vals.get('unit_amount') > 24:
                    raise UserError(_("You can't add timesheet for more than 24 hours."))
            if rec.state == 'open' and vals.get('date'):
                self.timesheet_attendance_regularize(rec)
            if rec.state in ['regularize', 'not_regularize'] and rec.regular_id:
                if vals.get('unit_amount'):
                    work_hour = rec.regular_id.worked_hours + vals['unit_amount'] - unit_amount
                    # work_time = str(work_hour).split('.')
                    rec.regular_id.write({
                        'to_date': str(self.regular_id.from_date + timedelta(hours=work_hour)),
                        'worked_hours': work_hour,
                    })
                    regular_line = self.env['attendance.regular.line'].search([('from_date', '=', rec.regular_id.from_date), ('employee_id', '=', rec.employee_id.id)])
                    if regular_line:
                        regular_line.write({
                            'to_date': str(rec.regular_id.from_date + timedelta(hours=work_hour)),
                            'check_out': str(regular_line.check_in + timedelta(hours=work_hour)),
                            'worked_hours': work_hour,
                        })
            return res

    def timesheet_attendance_regularize(self, rec):

        date_list = [i.date for i in self]
        dup_date_list = [i for i in date_list if date_list.count(i) > 1]
        payroll_from_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'), '%Y-%m-%d').date()
        payroll_to_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date'), '%Y-%m-%d').date()
        timesheet = []
        if rec.project_id.name != 'Internal Project' and not rec.external_timesheet:
            if rec.company_id.name == 'e-Zest Solutions Ltd.' and rec.user_id.employee_id.employee_category.name == 'eZestian' and (rec.create_date.date() > (payroll_to_date + relativedelta(days=1)) and rec.date > payroll_from_date and rec.date < (payroll_to_date + relativedelta(days=1))):
                raise UserError("You can not create timesheet beyond payroll duration")
            rec.payroll_pass = False
            if not (rec.state == 'regularize' or rec.state == 'not_regularize'):
                regular = self.env['attendance.regular.line'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('check_in', '>=', rec.date),
                    ('check_out', '<=', rec.date),
                    ('state', '!=', 'reject')], limit=1)
                attendance = self.env['hr.attendance'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('check_in', '>=', rec.date),
                    ('check_out', '<=', rec.date)])
                leave_list, hdl = self.env['attendance.regular']._check_leave_date(rec.employee_id.id)
                [leave_list.remove(dl['date']) for dl in hdl if dl['date'] in leave_list]
                hd_from_date = False
                hd_to_date = False
                description = "Auto Work From Home from timesheet\n"
                description += "Project Name: {0} \n Task Name: {1} \n Description: {2} \n".format(rec.project_id.name, rec.task_id.name or 'N/A', rec.name)
                # if dup_date_list:
                #     for dates in list(set(dup_date_list)):
                #         data = [(i.project_id.name, i.task_id.name, i.name) for i in self if i.date == dates and dates == rec.date]
                #         for i in data:
                #             description += " Project Name: {0} \n Task Name: {1} \n Description: {2} \n _____________________\n".format(i[0], i[1], i[2])
                if not regular and [hd for hd in hdl if hd['date'] == rec.date]:
                    for d in hdl:
                        if d['date'] == rec.date:
                            if d['time'] == 'am':
                                hd_from_date = datetime.combine(rec.date, time(8, 30))
                                hd_to_date = hd_from_date + timedelta(hours=rec.unit_amount)
                            if d['time'] == 'pm':
                                hd_from_date = datetime.combine(rec.date, time(3, 30))
                                hd_to_date = hd_from_date + timedelta(hours=rec.unit_amount)
                            if dup_date_list and rec.date in dup_date_list:
                                timesheet = [k for k in self if k.date in dup_date_list and k.date == rec.date and k.employee_id.id == rec.employee_id.id]
                                # rec_hd_time = str(result[rec.date]).split('.')
                                # hd_to_date = hd_from_date + timedelta(hours=int(rec_hd_time[0]), minutes=int(rec_hd_time[1]))
                            regular_id = self.env['attendance.regular'].with_context(from_timesheet=True).create({
                                'state_select': 'requested',
                                'reg_category': self.env['reg.categories'].search([('type','=','Work From Home')], limit=1).id,
                                'reg_reason': description,
                                'employee': rec.employee_id.id,
                                'from_date': str(hd_from_date),
                                'to_date': str(hd_to_date),
                                'worked_hours': (hd_to_date - hd_from_date).total_seconds()/3600.0,
                                'divide_date': True,
                            })
                            if timesheet:
                                for t in timesheet:
                                    t.regular_id = regular_id.id
                            else:
                                rec.regular_id = regular_id.id
                    rec.state = 'regularize'
                elif not regular and rec.date not in leave_list and attendance:
                    atten_worked = sum(attendance.mapped('worked_hours'))
                    time_worked = rec.unit_amount
                    total_worked = atten_worked + time_worked
                    if total_worked > 24:
                        raise UserError("You already have attendance for %s date for %s hours. You can't work for more than 24 hours. Please reduce your input work hour." % (rec.date, atten_worked))
                    else:
                        max_atten_time = [(rec.check_out, rec) for rec in attendance]
                        max_atten_time = max(max_atten_time)
                        max_atten_time = max_atten_time[1].check_out + timedelta(minutes=1)
                        from_date = datetime.combine(rec.date, max_atten_time.time())
                        to_date = from_date + timedelta(hours=rec.unit_amount)
                        if dup_date_list and rec.date in dup_date_list:
                            timesheet = [k for k in self if k.date in dup_date_list and k.date == rec.date and k.employee_id.id == rec.employee_id.id]
                            # rec_time = str(result[rec.date]).split('.')
                            # to_date = from_date + timedelta(hours=int(rec_time[0]), minutes=int(rec_time[1]))
                        regular_id = self.env['attendance.regular'].with_context(from_timesheet=True).create({
                            'state_select': 'requested',
                            'reg_category': self.env['reg.categories'].search([('type','=','Work From Home')]).id,
                            'reg_reason': description,
                            'employee': rec.employee_id.id,
                            'from_date': str(from_date),
                            'to_date': str(to_date),
                            'worked_hours': (to_date - from_date).total_seconds()/3600.0,
                            'divide_date': False,
                        })
                        if timesheet:
                            for t in timesheet:
                                t.regular_id = regular_id.id
                        else:
                            rec.regular_id = regular_id.id
                        rec.state = 'regularize'
                elif not regular and rec.date not in leave_list:
                    if rec.start_datetime:
                        from_date = rec.start_datetime + timedelta(hours=5, minutes=30)
                        if from_date.time().hour >= 6:
                            from_date = rec.start_datetime
                    else:
                        from_date = datetime.combine(rec.date, time(3, 30))
                    # rec_time = str(rec.unit_amount).split('.')
                    to_date = from_date + timedelta(hours=rec.unit_amount)
                    if dup_date_list and rec.date in dup_date_list:
                        timesheet = [k for k in self if k.date in dup_date_list and k.date == rec.date and k.employee_id.id == rec.employee_id.id]
                        # rec_time = str(result[rec.date]).split('.')
                        # to_date = from_date + timedelta(hours=int(rec_time[0]), minutes=int(rec_time[1]))
                    regular_id = self.env['attendance.regular'].with_context(from_timesheet=True).create({
                        'state_select': 'requested',
                        'reg_category': self.env['reg.categories'].search([('type','=','Work From Home')]).id,
                        'reg_reason': description,
                        'employee': rec.employee_id.id,
                        'from_date': str(from_date),
                        'to_date': str(to_date),
                        'worked_hours': (to_date - from_date).total_seconds()/3600.0,
                        'divide_date': False,
                    })
                    if timesheet:
                        for t in timesheet:
                            t.regular_id = regular_id.id
                    else:
                        rec.regular_id = regular_id.id
                    rec.state = 'regularize'
                if regular:
                    # from_date = datetime.combine(rec.date, time(3, 30))
                    if rec.start_datetime:
                        from_date = rec.start_datetime + timedelta(hours=5, minutes=30)
                        if from_date.time().hour >= 6:
                            from_date = rec.start_datetime
                    else:
                        from_date = datetime.combine(rec.date, time(3, 30))
                    to_date = from_date + timedelta(hours=rec.unit_amount)
                    work_hour = regular.worked_hours + rec.unit_amount
                    # work_time = str(work_hour).split('.')
                    atten_regular = self.env['attendance.regular'].search([
                        ('from_date', '=', regular.from_date),
                        ('to_date', '=', regular.to_date),
                        ('state_select', 'not in', ['reject', 'approved']),
                        ('employee', '=', rec.employee_id.id)], limit=1)
                    rec.state = 'not_regularize'
                    if atten_regular and atten_regular.reg_reason and atten_regular.reg_reason.find("Auto Work From Home from timesheet") >= 0:
                        rec.regular_id = atten_regular.id
                        if atten_regular:
                            description = atten_regular.reg_reason + "_____________________\n"
                            description += " Project Name: {0} \n Task Name: {1} \n Description: {2} \n _____________________\n".format(rec.project_id.name, rec.task_id.name or 'N/A', rec.name)
                            atten_regular.with_context(from_timesheet=True).write({
                                'from_date': str(regular.from_date),
                                'to_date': str(regular.from_date + timedelta(hours=work_hour)),
                                'worked_hours': work_hour,
                                'reg_reason': description
                            })
                            regular.with_context(from_timesheet=True).write({
                                'from_date': str(regular.from_date),
                                'to_date': str(regular.from_date + timedelta(hours=work_hour)),
                                'check_out': str(regular.check_in + timedelta(hours=work_hour)),
                                'worked_hours': work_hour,
                            })
                    elif atten_regular and atten_regular.from_date.date() == rec.date and atten_regular.to_date.date() == rec.date:
                        atten_regular.sudo().unlink()
                        rec.state = 'regularize'
                        regular_id = self.env['attendance.regular'].with_context(from_timesheet=True).create({
                            'state_select': 'requested',
                            'reg_category': self.env['reg.categories'].search([('type','=','Work From Home')]).id,
                            'reg_reason': description,
                            'employee': rec.employee_id.id,
                            'from_date': str(from_date),
                            'to_date': str(to_date),
                            'worked_hours': (to_date - from_date).total_seconds()/3600.0,
                            'divide_date': False,
                        })
                        rec.regular_id = regular_id.id
                    elif regular.state != 'approved':
                        regular.sudo().unlink()
                        rec.state = 'regularize'
                        regular_id = self.env['attendance.regular'].with_context(from_timesheet=True).create({
                            'state_select': 'requested',
                            'reg_category': self.env['reg.categories'].search([('type','=','Work From Home')]).id,
                            'reg_reason': description,
                            'employee': rec.employee_id.id,
                            'from_date': str(from_date),
                            'to_date': str(to_date),
                            'worked_hours': (to_date - from_date).total_seconds()/3600.0,
                            'divide_date': False,
                        })
                        rec.regular_id = regular_id.id

    # def create_attendance_regularize(self):
    #     for rec in self:
    #         self.timesheet_attendance_regularize(rec)

    def cron_attendance_regularize(self):
        for rec in self.search([('state', 'in', ['open', 'regularize', 'not_regularize'])]):
            self.timesheet_attendance_regularize(rec)

    @api.onchange('project_id', 'date')
    def onchange_project_id(self):
        # force domain on task when project is set
        if self.project_id:
            if self.project_id != self.task_id.project_id:
                # reset task when changing project
                self.task_id = False
            if self.task_id.sale_line_id:
                return {'domain': {
                    'task_id': [('start_date', '<=', self.date), ('date_deadline', '>=', self.date), ('project_id', '=', self.project_id.id),('user_id','=',self.env.user.id),('sale_line_id.product_states', 'not in', ['accepted_by_client', 'reinvoice', 'paid'])]
                }}
            else:
                return {'domain': {
                    'task_id': [('start_date', '<=', self.date), ('date_deadline', '>=', self.date), ('project_id', '=', self.project_id.id),('user_id','=',self.env.user.id)]
                }}
        return {'domain': {
            'task_id': [('start_date', '<=', self.date), ('date_deadline', '>=', self.date), ('project_id.allow_timesheets', '=', True),('user_id','=',self.env.user.id),('sale_line_id.product_states', 'not in', ['accepted_by_client', 'reinvoice', 'paid'])]
        }}

    def action_resubmit(self):
        if self.state == 'reject' and self.regular_id and self.unit_amount > 0:
            self.state = 'regularize'
            self.regular_id.state_select = 'requested'
            description = "Auto Work From Home from timesheet\n"
            description += "Project Name: {0} \n Task Name: {1} \n Description: {2} \n".format(self.project_id.name, self.task_id.name or 'N/A', self.name)
            from_date = self.regular_id.from_date
            to_date = from_date + timedelta(hours=self.unit_amount)
            regular_line = self.env['attendance.regular.line'].sudo().create({
                'from_date': from_date,
                'to_date': to_date,
                'employee_id': self.employee_id.id,
                'state': 'requested',
                'check_in': from_date,
                'check_out': to_date,
                'worked_hours': (to_date - from_date).total_seconds()/3600.0,
            })
            self.regular_id.attendance_regular_ids = [(4, regular_line.id)]
            self.regular_id.sudo().write({
                'state_select': 'requested',
                'manager_id': self.employee_id.parent_id.id,
                'reg_reason': description,
                'reg_reason_reject': '',
                'from_date': str(from_date),
                'to_date': str(to_date),
            })
            self.regular_id.activity_update()
