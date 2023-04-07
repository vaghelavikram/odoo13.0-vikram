# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta


class Regular(models.Model):
    _name = 'attendance.regular'
    _rec_name = 'employee'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _cron_attendance_leader_team(self):
        today_date = date.today()
        teams = self.env['leader.team'].sudo().search([])
        # print("TEAMS----------->",teams)
        for t in teams:
            existing = self.env['hr.attendance'].sudo().search([('employee_id', '=', t.employee_id.id)])
            existing = existing.filtered(lambda atten: atten.check_in.date() == today_date)
            leave_list, hdl = self._check_leave_date(t.employee_id.id)
            if not existing and today_date not in leave_list:
                self.env['hr.attendance'].sudo().create({
                    'check_in': datetime.combine(today_date, time(3,30)),
                    'check_out': datetime.combine(today_date, time(12,30)),
                    'employee_id': t.employee_id.id,
                    'company_id': t.employee_id.company_id.id,
                    'manager_id': t.employee_id.parent_id.id,
                    'source_check_in': 'Update Attendace IN by Unity',
                    'source_check_out': 'Update Attendace OUT by Unity',
                })

    def _get_employee_id(self):
        employee_rec = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id

    def name_get(self):
        result = []
        for regular in self:
            name = regular.employee.name + ' (' + (regular.from_date.date()).strftime('%d-%m-%Y') + ' to ' + (regular.to_date.date()).strftime('%d-%m-%Y') + ')'
            result.append((regular.id, name))
        return result

    # @api.onchange('manager_id')
    # def _onchange_manager_id(self):
    #     if self.employee.parent_id.id != self.manager_id.id:
    #         self.employee.sudo().write({'parent_id': self.manager_id.id})

    @api.depends('employee')
    def _compute_is_manager(self):
        for rec in self:
            manager = rec.employee.parent_id.user_id if rec.employee.parent_id else rec.employee.user_id
            check_group = manager.user_has_groups('hr_attendance_regularization.group_attendance_regular_manager')
            if check_group:
                rec.is_manager = True
            else:
                rec.is_manager = False

    @api.depends('user_id')
    def _compute_is_hr(self):
        for rec in self:
            check_group = rec.user_id.user_has_groups('hr.group_hr_user')
            if check_group:
                rec.is_hr = True
            else:
                rec.is_hr = False

    def open_leave(self):
        return {
            'name': ('Apply Leave'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.leave',
            'view_id': self.env.ref('hr_holidays.hr_leave_view_form_dashboard').id,
            'target': 'new',
        }

    @api.onchange('employee')
    def _onchange_employee(self):
        if self.employee and self.employee.parent_id:
            self.manager_id = self.employee.parent_id.id
        else:
            self.manager_id = False

    def _default_manager(self):
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if employee:
            return employee.parent_id

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    reg_category = fields.Many2one('reg.categories', string='Category', required=True)
    from_date = fields.Datetime(string='From Date', required=True, tracking=True, default=(datetime.today().replace(hour=3, minute=30, second=00)))
    to_date = fields.Datetime(string='To Date', required=True, tracking=True, default=(datetime.today().replace(hour=12, minute=30, second=00)))
    reg_reason = fields.Text(string='Details', required=True)
    employee = fields.Many2one('hr.employee', string="e-Zestian", default=_get_employee_id, required=True)
    job_id = fields.Many2one(related="employee.job_id", string="Designation")
    identification_id = fields.Char(related="employee.identification_id")
    # job_title = fields.Char(related="employee.job_id")
    state_select = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('reject', 'Rejected')], default='draft', track_visibility='onchange', string='State')
    worked_hours = fields.Float(string='Total Worked hours', compute="_get_compute_worked_hours")
    manager_id = fields.Many2one('hr.employee', string='Manager', track_visibility='onchange', default=_default_manager)
    attendance_regular_ids = fields.Many2many('attendance.regular.line', string="Attendace Ids", compute="_compute_regular_attendance", search="_search_regular_attendance")
    divide_date = fields.Boolean(string="Mark for Working Days", default=True)
    is_readonly = fields.Boolean(string="Readonly From date")
    auto_approve = fields.Boolean(string="Verballly approved by Manager")
    # is_manager = fields.Boolean(string='Is Manager', compute="_compute_is_manager")
    is_manager = fields.Boolean(string='Is Manager')
    is_hr = fields.Boolean(string='Is HR', compute="_compute_is_hr", default=False)
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True,
                                 default=lambda self: self.env.user.company_id)
    skip_dates = fields.Text(string="Skip Dates")
    skip_atten = fields.Text(string="Skip Attendace")
    is_lock = fields.Boolean(string='Is Lock')
    reg_approved_employee = fields.Many2one('hr.employee', string="Approved By")
    timesheet_ids = fields.Many2many('account.analytic.line', string="Timesheet Record", compute="_get_timesheet_rec")
    active = fields.Boolean('Active', default=True, store=True, readonly=False)
    reg_reason_reject = fields.Text(string="Reject Reason")
    show_create = fields.Selection([('yes','Yes'),('no','No')], string="Show Create", compute="_compute_regular_attendance")

    def _daterange(self, date1, date2):
        for n in range(int((date2 - date1).days)+1):
            yield date1 + timedelta(n)

    def _get_weekday(self, from_date, to_date):
        weekdays = []
        for dt in self._daterange(from_date, to_date):
            # to print only the weekenddates
            if dt.weekday() in [5, 6]:
                weekdays.append(dt)
        return weekdays

    @api.depends('attendance_regular_ids.check_in', 'attendance_regular_ids.check_out', 'from_date', 'to_date')
    def _get_compute_worked_hours(self):
        for attendance in self:
            if attendance.from_date and attendance.to_date:
                regular_ids = [line.worked_hours for line in attendance.attendance_regular_ids]
                if not len(regular_ids):
                    days = (attendance.to_date - attendance.from_date).days
                    weekdays = self._get_weekday(attendance.from_date,attendance.to_date)
                    delta = ((days+1)*9)-(len(weekdays)*9) if (days+1) > 1 else (attendance.to_date - attendance.from_date)
                    attendance.worked_hours = delta.total_seconds() / 3600.0 if not (days+1) > 1 else delta
                else:
                    attendance.worked_hours = sum(regular_ids)

    def _reg_activity_schedule(self, res):
        for reg_attendace in res.filtered(lambda hol: hol.state_select == 'requested'):
            note = '<p>Dear {0}</p>\
                    <p>Your member {1} has submitted request for {2} for {3}.\
                    <br/><br/>\
                    <p>Request you to kindly approve / reject the same</p>\
                    In case of any discrepancy connect with your HR {4}\
                    <br/><br/>\
                    <p>Request you to kindly action further on Unity</p>\
                    <p>Please click on \
                    <a href="/web#id={5}&amp;model={6}&amp;view_type=form"\
                    target="_blank" style="background-color: #875A7B; padding: 8px 16px 8px 16px;\
                    text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">View Details</a> to action the same.</p>\
                    <br/><br/><br/>\
                    Thanks,\
                    <br/>\
                    Team Unity\
                    <p><br></p>'.format(reg_attendace.manager_id.name, reg_attendace.employee.name, reg_attendace.reg_category.type,
                    reg_attendace.from_date.strftime('%d-%b-%Y'), reg_attendace.employee.responsible_hr.name,
                    reg_attendace.id,reg_attendace._name)
            subject = '%s has applied for %s for date %s'% (reg_attendace.employee.name, reg_attendace.reg_category.type, reg_attendace.from_date.strftime('%d-%b-%Y')) 
            res.activity_schedule(
                'hr_attendance_regularization.mail_act_reg_attendance_approval',
                user_id=reg_attendace.employee.parent_id.user_id.id or self.env.user.id, note=note, summary=subject)

    @api.model
    def create(self, vals):
        from_date = datetime.strptime(vals.get('from_date'), "%Y-%m-%d %H:%M:%S")
        to_date = datetime.strptime(vals.get('to_date'), "%Y-%m-%d %H:%M:%S")
        weekday = self._get_weekday(from_date.date(), to_date.date())
        total_days = (to_date - from_date).days
        if total_days > 31:
            raise UserError(_("You can not regularize for more than 1 month."))
        to_date_add = to_date + timedelta(hours=5.50)
        from_date_add = from_date + timedelta(hours=5.50)
        delta = to_date - from_date
        worked_hours = delta.total_seconds() / 3600.0
        if worked_hours > 24 and not vals.get('divide_date'):
            raise UserError(_('Your worked hours can not be more than 24 hours. Check Mark for working days True.'))
        # if from_date_add.date() != to_date_add.date() and relativedelta(to_date_add, from_date_add).hours <= 12 and relativedelta(to_date_add, from_date_add).days == 0:
        vals['divide_date'] = vals.get('divide_date')
        employee = vals['employee'] if vals.get('employee') else self.env.user.employee_id.id
        skip_atten, skip_list = self.get_attendance_lines(from_date, to_date, vals['divide_date'], employee)
        date_diff = delta.days + 1
        if len(skip_atten) == date_diff:
            raise UserError("Attendance already captured for these dates %s "%(skip_atten))
        vals['is_readonly'] = vals['divide_date']
        vals['skip_dates'] = skip_list or False
        vals['skip_atten'] = skip_atten or False
        res = super(Regular, self.with_context(mail_create_nosubscribe=True)).create(vals)
        payroll_from_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'), '%Y-%m-%d').date()
        payroll_to_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date'), '%Y-%m-%d').date()
        current_user = self.env.user.employee_id
        responsible_hr = res.employee.responsible_hr
        future_create_date = res.create_date.date() + relativedelta(days=7)
        if res.employee.joining_date and res.employee.joining_date > res.from_date.date():
            raise UserError(_('You can not apply regularization before your joining date'))
        if res.employee.company_id.name == 'e-Zest Solutions Ltd.':
            if res.employee.employee_category.name == 'eZestian':
                if res.create_date.date() > payroll_from_date and res.create_date.date() < payroll_to_date:
                    if res.from_date.date() > payroll_to_date or res.to_date.date() > payroll_to_date:
                        raise UserError(_('You cannot apply regularization beyond payroll dates i.e %s' % str(payroll_to_date)))
                if res.from_date.date() < payroll_to_date and res.to_date.date() > payroll_to_date:
                    raise UserError(_('You cannot apply regularization beyond payroll dates i.e %s' % str(payroll_to_date)))
                if not (responsible_hr and current_user.id in responsible_hr.related_hr.ids):
                    if (res.from_date.date() < payroll_from_date) or (res.create_date.date() > payroll_to_date+relativedelta(days=1) and res.from_date.date() >= payroll_from_date and res.from_date.date() <= payroll_to_date):
                        raise UserError(_("You cannot apply Regularization for previous payroll duration"))
            if res.employee.employee_category.name in ['Contractor', 'Intern']:
                if datetime.today().date().day > 10:
                    next_date = datetime.today().date() + relativedelta(day=1)
                    next_from_date = datetime.today().date() + relativedelta(months=1, day=10)
                else:
                    next_date = datetime.today().date() - relativedelta(months=1, day=1)
                    next_from_date = datetime.today().date() + relativedelta(day=10)
                # next_date = fields.Date.today() + relativedelta(months=+1, day=10)
                # next_from_date = next_date - relativedelta(months=1, day=1)
                if res.from_date.date() > next_from_date and res.to_date.date() > next_date:
                    raise UserError(_('You cannot apply regularization beyond dates i.e %s' % next_date.strftime("%d-%b-%Y")))
                if (res.from_date.date() > next_from_date):
                    raise UserError(_("You cannot apply Regularization for previous duration"))
        if res.from_date.date() > future_create_date or res.to_date.date() > future_create_date:
            raise UserError(_('You cannot apply regularization beyond 1 week i.e %s' % future_create_date.strftime("%d-%b-%Y")))
        if not len(res.attendance_regular_ids) and (res.to_date - from_date).days >= 1 and (from_date+timedelta(hours=5, minutes=30)).date() in weekday:
            raise UserError(_('Apply regularization for weekends separately'))
        if res.auto_approve:
            res.sudo().write({
                'state_select': 'approved'
            })
            regular = res.attendance_regular_ids
            regular.sudo().write({
                'state': 'approved'
            })
            for rec in regular:
                self.env['hr.attendance'].sudo().create({
                    'check_in': rec.check_in,
                    'check_out': rec.check_out,
                    'employee_id': rec.employee_id.id,
                    'company_id': rec.employee_id.company_id.id,
                    'manager_id': rec.employee_id.parent_id.id,
                    'source_check_in': res.reg_category.type + ' IN',
                    'source_check_out': res.reg_category.type + ' OUT',
                    'regular_id': res.id
                })
            template = self.env.ref('hr_attendance_regularization.send_auto_approve_regularization_email')
            template_values = {
                'email_from': 'unity@e-zest.in',
                'email_to': '${object.employee_id.parent_id.user_id.login|safe}',
                'auto_delete': True,
                'partner_to': False,
                'scheduled_date': False,
            }
            # template.write(template_values)
            # For testing
            # with self.env.cr.savepoint():
            #     template.with_context(lang=res.employee.user_id.lang).sudo().send_mail(res.employee.user_id.id, force_send=True, raise_exception=False)
            note_summary = "Regularization Request approved on behalf of " + (res.manager_id.name if res.manager_id else 'Manager')
            subject = "Self Approved Regularization Request"
            res.filtered(lambda res: res.state_select == 'approved').message_post(body=note_summary, subject=subject)
        else:
            res.sudo().write({
                'state_select': 'requested'
            })
            res.attendance_regular_ids.sudo().write({
                'state': 'requested'
            })
            self._reg_activity_schedule(res)
        # if res.worked_hours > 12 and not res.divide_date:
        #     return {
        #         'name': 'Regularize Warning',
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'regularize.confirm.wizard',
        #         'view_mode': 'form',
        #         'view_type': 'form',
        #         'target': 'new',
        #     }
        if res.is_readonly:
            time_duration = (to_date - from_date).total_seconds()/3600.0
            if not time_duration > 0:
                raise ValidationError(_('Choose the date correctly. Worked hours should greater than 0'))
        else:
            if not res.worked_hours > 0:
                raise ValidationError(_('Choose the date correctly. Worked hours should greater than 0'))
        template_id = self.env.ref('hr_attendance_regularization.send_apply_regularization_email_user').id
        template = self.env['mail.template'].browse(template_id)
        template_values = {
            'email_from': 'unity@e-zest.in',
            'email_to': res.employee.user_id.login or False,
            'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
            'auto_delete': True,
            'partner_to': False,
            'scheduled_date': False,
        }
        # template.sudo().write(template_values)
        # For testing
        # with self.env.cr.savepoint():
        #     template.with_context(lang=res.employee.user_id.lang).sudo().send_mail(res.id, force_send=True, raise_exception=False)
        return res

    def write(self, vals):
        from_date = datetime.strptime(vals.get('from_date'), "%Y-%m-%d %H:%M:%S") if vals.get('from_date') else self.from_date
        to_date = datetime.strptime(vals.get('to_date'), "%Y-%m-%d %H:%M:%S") if vals.get('to_date') else self.to_date
        total_days = (to_date - from_date).days
        if self.state_select in ['approved','reject'] and (vals.get('from_date') or vals.get('to_date')):
            raise UserError(_("You can not change dates after regularization is approved or reject."))
        if total_days > 31:
            raise UserError(_("You can not regularize for more than 1 month."))
        if vals.get('divide_date') in [True, False]:
            self.get_updated_attendance_lines(from_date, to_date, self.from_date, self.to_date, vals['divide_date'], vals.get('state_select') or self.state_select)
            vals['is_readonly'] = vals['divide_date']
            if self.state_select == 'requested':
                self.update_manager_edit(vals, from_date, to_date, vals['divide_date'])
        if vals.get('from_date') or vals.get('to_date'):
            if self.employee.joining_date and self.employee.joining_date > from_date.date():
                raise UserError(_('You can not apply regularization before your joining date'))
            if not self.worked_hours >= 0:
                raise ValidationError(_('Choose the date correctly. Worked hours should greater than 0'))
            if not self.divide_date and not vals.get('divide_date'):
                self.update_manager_edit(vals, from_date, to_date, self.divide_date)
            self.get_updated_attendance_lines(from_date, to_date, self.from_date, self.to_date, self.divide_date, vals.get('state_select') or self.state_select)
        # for i in self.attendance_regular_ids:
        #     atten = self.env['attendance.regular.line'].sudo().search([('employee_id', '=', self.employee.id), ('from_date', '=', i.from_date), ('to_date', '=', i.to_date)])
        # if atten and not self.divide_date:
        #     self._cr.execute("DELETE FROM attendance_regular_line WHERE id=%s", ([atten[0].id]))
        if vals.get('attendance_regular_ids'):
            for rec in self.attendance_regular_ids:
                if len(vals['attendance_regular_ids']) >= 2:
                    if not rec.id in vals['attendance_regular_ids'][0][2]:
                        rec.sudo().unlink()
                elif len(vals['attendance_regular_ids']) == 1 and isinstance(vals['attendance_regular_ids'][0][1], int):
                    if not (rec.id == vals['attendance_regular_ids'][0][1]):
                        rec.sudo().unlink()
        res = super(Regular, self).write(vals)
        return res

    @api.model
    def _search_regular_attendance(self, operator, operand):
        """Search Nothing"""
        return


    @api.depends('employee')
    def _compute_regular_attendance(self):
        current_employee = self.env.user.employee_id
        for rec in self:
            if rec.from_date and rec.to_date and rec.employee:
                attendance_regular_ids = rec.env['attendance.regular.line'].sudo().search([
                         ('employee_id', '=', rec.employee.id),
                         ('from_date', '=', rec.from_date),
                         ('to_date', '=', rec.to_date),
                         ('state', '!=', 'reject')
                ])
                if rec.divide_date:
                    rec.attendance_regular_ids = attendance_regular_ids.ids
                else:
                    rec.attendance_regular_ids = attendance_regular_ids.sudo().filtered(lambda self: self.check_in== self.from_date and self.check_out == self.to_date)
            if current_employee.account and current_employee.account.name in ['Deployable - Billable', 'Temporarily - Deployable']:
                rec.show_create = 'no'
            else:
                rec.show_create = 'yes'

    @api.depends('employee')
    def _get_timesheet_rec(self):
        for rec in self:
            if rec.from_date and rec.to_date and rec.employee:
                timesheet_ids = rec.env['account.analytic.line'].sudo().search([
                         ('employee_id', '=', rec.employee.id),
                         ('date', '=', rec.from_date.date()),
                         ('state', '!=', 'reject')
                ])
                rec.timesheet_ids = timesheet_ids

    def get_updated_attendance_lines(self, from_date, to_date, self_from_date, self_to_date, divide_date, state):
        check_in = from_date + timedelta(hours=5, minutes=30)
        check_out = to_date + timedelta(hours=5, minutes=30)
        regular = self.env['attendance.regular.line'].sudo().search([('employee_id', '=', self.employee.id)])
        for reg in regular:
            reg_checkin = reg.check_in + timedelta(hours=5, minutes=30)
            reg_checkout = reg.check_out + timedelta(hours=5, minutes=30)
            if reg_checkin.date() >= check_in.date() and not state == 'requested':
                if reg_checkout >= check_out and reg_checkin <= check_out:
                    raise UserError(_('Already worked for this %s - %s. Select another dates.' %(reg_checkin,reg_checkout)))
                elif reg_checkout >= check_in and reg_checkin <= check_in:
                    raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
                elif reg_checkout < check_out and reg_checkin > check_in:
                    raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
                elif reg_checkout.date() < check_out.date() and reg_checkin.date() > check_in.date():
                    raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
            elif reg_checkout.date() == check_out.date() and reg_checkin.date() == check_in.date() and not state == 'requested':
                raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
        regular_line = self.env['attendance.regular.line'].sudo().search([('employee_id','=',self.employee.id),('from_date','=',self_from_date),('to_date','=',self_to_date)])
        if regular_line and divide_date:
            self._cr.execute("DELETE FROM attendance_regular_line WHERE employee_id=%s AND from_date=%s AND to_date=%s", (self.employee.id,self_from_date,self_to_date))
            self.get_attendance_lines(from_date, to_date, divide_date, self.employee.id, state)
        else:
            self.get_attendance_lines(from_date, to_date, divide_date, self.employee.id, state)

    def _check_leave_date(self, employee_id):
        leaves = self.env['hr.leave'].sudo().search([('employee_id','=',employee_id),('state','in',['confirm','validate'])])
        leave_list = []
        hd_leave_list = []
        for leave in leaves:
            if not leave.request_unit_half:
                leave_date = leave.date_from
                if (leave.date_to - leave.date_from).days >=1:
                    for x in range(0, int((leave.date_to - leave.date_from).days)+1):
                        leave_list.append(leave_date.date())
                        leave_date = leave_date + relativedelta(days=1)
                else:
                    leave_list.append(leave.date_to.date())
            if leave.request_unit_half:
                leave_list.append(leave.date_to.date())
                hd_leave_list.append({'date': leave.date_to.date(), 'time': leave.request_date_from_period})
        duplicate_lst = [i['date'] for i in hd_leave_list]
        two_hdl = list(set([hd for hd in duplicate_lst if duplicate_lst.count(hd) > 1]))
        if two_hdl:
            for k in two_hdl:
                hd_leave_list = [i for i in hd_leave_list if i['date'] != k]
        return leave_list, hd_leave_list

    def _get_holiday(self, from_date, to_date):
        holiday = self.env['hr.holidays.public.line'].search([('holiday_type', '=', 'Public Holidays')])
        return [h.date for h in holiday]

    def get_attendance_lines(self, from_date, to_date, divide_date, employee_id, state=False):
        check_in_date = from_date
        check_out_date = to_date
        check_in = from_date + timedelta(hours=5, minutes=30)
        check_out = to_date+timedelta(hours=5, minutes=30)
        skip_attendance = []
        weekday = self._get_weekday(check_in_date.date(), check_out_date.date())
        public_holiday = self._get_holiday(check_in_date.date(), check_out_date.date())
        time_duration = (to_date - from_date).total_seconds()/3600.0
        if not time_duration > 0:
            raise ValidationError(_('Choose the date correctly. Worked hours should greater than 0'))
        attendances = self.env['hr.attendance'].sudo().search([('employee_id', '=', employee_id)])
        regular_line = self.env['attendance.regular.line'].sudo().search([('employee_id', '=', employee_id),('from_date','=',from_date),('to_date','=',to_date)])
        leave_list, hdl = self._check_leave_date(employee_id)
        # regular_line_dates = [reg.check_in.date() for reg in regular_line if regular_line]
        regularization = self.env['attendance.regular.line'].sudo().search([('employee_id', '=', employee_id)])
        if regular_line and not self._context.get('from_timesheet'):
            raise UserError(_('Already worked for this %s - %s. Select another dates.' %(check_in_date.date(),check_out_date.date())))
        if (check_out.date() == check_in.date()):
            for reg in regularization:
                reg_checkin = reg.check_in + timedelta(hours=5, minutes=30)
                reg_checkout = reg.check_out + timedelta(hours=5, minutes=30)
                if reg_checkin.date() >= check_in.date() and reg.state == 'requested' and not state == 'requested':
                    if reg_checkout >= check_out and reg_checkin <= check_out:
                        raise UserError(_('Already worked for this %s - %s. Select another dates.' %(reg_checkin,reg_checkout)))
                    elif reg_checkout >= check_in and reg_checkin <= check_in:
                        raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
                    elif reg_checkout < check_out and reg_checkin > check_in:
                        raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
                    elif reg_checkout.date() < check_out.date() and reg_checkin.date() > check_in.date():
                        raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
        if divide_date:
            if (check_out.date() == check_in.date()):
                for rec in attendances:
                    atten_check_in = rec.check_in + timedelta(hours=5, minutes=30)
                    atten_check_out = rec.check_out + timedelta(hours=5, minutes=30) if rec.check_out else False
                    # if regular_line_dates:
                    #     for k in regular_line_dates:
                    #         if not atten_check_out and k:
                    #             if not((atten_check_in > k and atten_check_in > k)):
                    #                 raise UserError(_('First checkout your previous checkin %s' %(atten_check_in)))
                    #         elif atten_check_out and atten_check_out >= k and atten_check_in <= k:
                    #             raise UserError(_('Already worked for this %s - %s. Select another dates.' %(atten_check_in,atten_check_out)))
                    #         elif atten_check_out and atten_check_out >= k and atten_check_in <= k:
                    #             raise UserError(_('Already worked for this %s - %s. Select another dates' %(atten_check_in,atten_check_out)))
                    if atten_check_in.date() == check_in.date():
                        if not atten_check_out and check_in:
                            if not((atten_check_in > check_in and atten_check_in > check_out)):
                                raise UserError(_('First checkout your previous checkin %s' %(atten_check_in)))
                        elif atten_check_out and atten_check_out >= check_out and atten_check_in <= check_out:
                            raise UserError(_('Already worked for this %s - %s. Select another dates.' %(atten_check_in,atten_check_out)))
                        elif atten_check_out and atten_check_out >= check_in and atten_check_in <= check_in:
                            raise UserError(_('Already worked for this %s - %s. Select another dates' %(atten_check_in,atten_check_out)))

            if not (check_out.date() == check_in.date()) and not regular_line:
                from_date = check_in
                date_list = []
                new_date_list = []
                for x in range(0, int((check_out_date.date() - check_in_date.date()).days)):
                    if not check_out.date() == check_in.date():
                        date_list.append(from_date-timedelta(hours=5, minutes=30))
                        new_date_list.append((from_date-timedelta(hours=5, minutes=30)).date())
                    from_date = from_date + relativedelta(days=1)
                date_list.append(to_date)
                new_date_list.append(to_date.date())
                skip_attendance.extend([dt for dt in date_list for reg in regularization if reg.check_in.date() == dt.date() and reg.state in ['requested', 'approved']])
                for i in skip_attendance:
                    if i in date_list:
                        date_list.remove(i)
                # raise UserError(_('Already worked for this %s - %s. Select another dates' %(i.check_in,i.check_out)))
                for rec in date_list:
                    time_diff = (check_out_date - check_in_date)
                    diff_days, diff_seconds = time_diff.days,time_diff.seconds
                    new_hours = diff_seconds // 3600
                    new_minutes = (diff_seconds % 3600)//60
                    dic_attten = {'employee_id': employee_id, 'from_date': check_in_date, 'to_date': to_date}
                    if check_in_date == rec:
                        check_out = rec+timedelta(hours=new_hours, minutes=new_minutes) # we decuct time from db by 5.50 hours
                        dic_attten.update({
                            'state': 'requested',
                            'check_in': rec,
                            'check_out': check_out, # time will be 18'o clock
                            'worked_hours': (check_out-rec).total_seconds()/3600.0
                        })
                    elif to_date == rec:
                        check_in = rec-timedelta(hours=new_hours, minutes=new_minutes) # because in db time store as minus 5.50 hours
                        dic_attten.update({
                            'state': 'requested',
                            'check_in': check_in, # time will be 9'o clock
                            'check_out': rec,
                            'worked_hours': (rec-check_in).total_seconds()/3600.0
                        })
                    else:

                        # check_in = rec.replace(hour=3,minute=30,second=0) # in ui it shows 9'o clock but in db it shows 3:30 time that means time difference is 5 hours 30 minutes
                        check_in = rec.replace(hour=check_in_date.time().hour,minute=check_in_date.time().minute,second=check_in_date.time().second) # in ui it shows 9'o clock but in db it shows 3:30 time that means time difference is 5 hours 30 minutes
                        check_out = rec.replace(hour=check_out_date.time().hour,minute=check_out_date.time().minute,second=check_out_date.time().second)
                        dic_attten.update({
                            'state': 'requested',
                            'check_in': check_in, # time will be 9'o clock
                            'check_out': check_out, # time will be 18'o clock
                            'worked_hours': (check_out-check_in).total_seconds()/3600.0
                            # '{0:02.0f}.{1:02.0f}'.format(*divmod((check_out-check_in) * 60, 60))
                        })

                    if (check_out_date.date() - check_in_date.date()).days >= 1:
                        if self.env['hr.employee'].browse(employee_id).empl_shift and (dic_attten['check_in'] + timedelta(hours=5,minutes=30)).date() not in leave_list:
                            self.env['attendance.regular.line'].sudo().create(dic_attten)
                        elif (dic_attten['check_in'] + timedelta(hours=5,minutes=30)).date() not in weekday and (dic_attten['check_in'] + timedelta(hours=5,minutes=30)).date() not in public_holiday and (dic_attten['check_in']+timedelta(hours=5,minutes=30)).date() not in leave_list:
                            self.env['attendance.regular.line'].sudo().create(dic_attten)
                    else:
                        self.env['attendance.regular.line'].sudo().create(dic_attten)
            elif (check_out.date() == check_in.date()) and not regular_line:
                [leave_list.remove(dl['date']) for dl in hdl if dl['date'] in leave_list]
                if check_in.date() in leave_list:
                    raise UserError(_("You already had applied leave for %s" % check_in.date()))
                elif hdl:
                    hd_from_date = False
                    hd_to_date = False
                    for d in hdl:
                        if d['date'] == check_in.date():
                            if d['time'] == 'am':
                                hd_from_date = datetime.combine(check_in_date, time(8, 30))
                                # hd_to_date = hd_from_date + timedelta(hours=4, minutes=00)
                                hd_to_date = to_date
                            if d['time'] == 'pm':
                                hd_from_date = check_in_date
                                hd_to_date = hd_from_date + timedelta(hours=5, minutes=00)
                    reg_from_date = hd_from_date or check_in_date
                    reg_to_date = hd_to_date or to_date
                    worked_hours = (reg_to_date - reg_from_date).total_seconds()/3600.0
                    dic_attten = {'employee_id': employee_id, 'from_date': check_in_date, 'to_date': to_date, 'check_in': reg_from_date, 'check_out': reg_to_date, 'worked_hours': worked_hours}
                    self.env['attendance.regular.line'].sudo().create(dic_attten)
                else:
                    worked_hours = (to_date-check_in_date).total_seconds()/3600.0
                    dic_attten = {'employee_id': employee_id, 'from_date': check_in_date, 'to_date': to_date, 'check_in': check_in_date, 'check_out': to_date, 'worked_hours': worked_hours}
                    self.env['attendance.regular.line'].sudo().create(dic_attten)
        elif not len(self.attendance_regular_ids) and (check_in_date+timedelta(hours=5,minutes=30)).date() not in leave_list:
            attendance_reg = self.env['attendance.regular.line'].sudo().create({
                'state': 'requested',
                'employee_id': employee_id,
                'check_in': check_in_date,
                'check_out': to_date,
                'worked_hours': (to_date-check_in_date).total_seconds()/3600.0,
                'from_date': check_in_date,
                'to_date': to_date
            })
        elif self.attendance_regular_ids:
            for i in self.attendance_regular_ids:
                atten = self.env['attendance.regular.line'].sudo().search([('employee_id', '=', self.employee.id), ('from_date', '=', from_date), ('to_date', '=', to_date)])
                if i.from_date != check_in_date and i.to_date != to_date and not atten:
                    attendance_reg = self.env['attendance.regular.line'].sudo().create({
                        'state': 'requested',
                        'employee_id': employee_id,
                        'check_in': check_in_date,
                        'check_out': to_date,
                        'worked_hours': (to_date-check_in_date).total_seconds()/3600.0,
                        'from_date': check_in_date,
                        'to_date': to_date
                    })
        # else:
        #     if self.attendance_regular_ids:
        #         for i in self.attendance_regular_ids:
        #             self._cr.execute("DELETE FROM attendance_regular_line WHERE id=%s", ([i.id]))
                # self.attendance_regular_ids = [(5, 0, 0)]
        skip_list = list(set([i.strftime('%a, %d-%b-%Y') for i in leave_list if i >= check_in_date.date() and i <= to_date.date()]))
        skip_attendance = list(set([i.strftime('%a, %d-%b-%Y') for i in skip_attendance]))
        attendance_skip = ', '.join(i for i in skip_attendance if i)
        if self and not len(self.attendance_regular_ids):
            raise UserError("Your attendance is not captured for below dates as you have approved or requested attendance. If you still want to regularize, get your attendance refused and re-apply. %s" % attendance_skip)
        return skip_attendance, skip_list
        # if skip_list:
        #     return {
        #         'name': _('Regularize Warning'),
        #         'view_mode': 'form',
        #         'res_model': 'regularize.confirm.wizard',
        #         'view_id': self.env.ref('hr_attendance_regularization.regularize_confirm_wizard_form_skip').id,
        #         'type': 'ir.actions.act_window',
        #         'context': {'default_skip_test': skip_list},
        #         'target': 'new'
        #     }

    def update_manager_edit(self, vals, from_date, to_date, divide_date):
        check_in_date = from_date
        check_in = from_date + timedelta(hours=5, minutes=30)
        check_out = to_date+timedelta(hours=5, minutes=30)
        attendances = self.env['hr.attendance'].sudo().search([('employee_id', '=', self.employee.id)])
        regularization = self.env['attendance.regular.line'].sudo().search([('employee_id', '=', self.employee.id),('check_in','=',from_date),('check_out','=',to_date)])
        if relativedelta(check_out,check_in).hours > 24 and not divide_date:
            raise UserError(_('Your worked hours can not be more than 24 hours. Check Mark for working days True.'))
        elif relativedelta(check_out, check_in).days > 0 and not divide_date:
            raise UserError(_('Your worked hours can not be more than 24 hours. Check Mark for working days True.'))
        if self.attendance_regular_ids:
            self.attendance_regular_ids.sudo().write({
                'check_in': check_in_date,
                'check_out': to_date,
                'worked_hours': (to_date-check_in_date).total_seconds()/3600.0,
                'from_date': check_in_date,
                'to_date': to_date
            })
        if not len(self.attendance_regular_ids) and not regularization and not divide_date:
            attendance_reg = self.env['attendance.regular.line'].sudo().create({
                'state': 'requested',
                'employee_id': self.employee.id,
                'check_in': check_in_date,
                'check_out': to_date,
                'worked_hours': (to_date-check_in_date).total_seconds()/3600.0,
                'from_date': check_in_date,
                'to_date': to_date
            })

    def submit_reg(self):
        self.ensure_one()
        check_in_date = self.from_date
        check_in = self.from_date + timedelta(hours=5, minutes=30)
        check_out = self.to_date+timedelta(hours=5, minutes=30)
        weekday = self._get_weekday(check_in_date.date(), self.to_date.date())
        attendances = self.env['hr.attendance'].sudo().search([('employee_id', '=', self.employee.id)])
        regularization = self.env['attendance.regular.line'].sudo().search([('employee_id', '=', self.employee.id)])
        leave_list, hdl = self._check_leave_date(self.employee.id)
        # regular_line_dates = [reg.check_in.date() for reg in regular_line if regular_line]
        for reg in regularization:
            reg_checkin = reg.check_in + timedelta(hours=5, minutes=30)
            reg_checkout = reg.check_out + timedelta(hours=5, minutes=30)
            if reg_checkin.date() >= check_in.date() and reg.state == 'requested':
                if reg_checkout >= check_out and reg_checkin <= check_out:
                    raise UserError(_('Already worked for this %s - %s. Select another dates.' %(reg_checkin,reg_checkout)))
                elif reg_checkout >= check_in and reg_checkin <= check_in:
                    raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
                elif reg_checkout < check_out and reg_checkin > check_in:
                    raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
                elif reg_checkout.date() < check_out.date() and reg_checkin.date() > check_in.date():
                    raise UserError(_('Already worked for this %s - %s. Select another dates' %(reg_checkin,reg_checkout)))
        for rec in attendances:
            atten_check_in = rec.check_in + timedelta(hours=5, minutes=30)
            atten_check_out = rec.check_out + timedelta(hours=5, minutes=30) if rec.check_out else False
            if atten_check_in.date() == check_in.date():
                if not atten_check_out and check_in:
                    if not((atten_check_in > check_in and atten_check_in > check_out)):
                        raise UserError(_('First checkout your previous checkin %s' %(atten_check_in)))
                elif atten_check_out and atten_check_out >= check_out and atten_check_in <= check_out:
                    raise UserError(_('Already worked for this %s - %s. Select another dates.' %(atten_check_in,atten_check_out)))
                elif atten_check_out and atten_check_out >= check_in and atten_check_in <= check_in:
                    raise UserError(_('Already worked for this %s - %s. Select another dates' %(atten_check_in,atten_check_out)))
        if not len(self.attendance_regular_ids) and (self.to_date-check_in_date).days >= 1 and (check_in_date+timedelta(hours=5,minutes=30)).date() in weekday:
            raise UserError(_('Apply regularization for weekends separately'))
        elif not len(self.attendance_regular_ids) and (check_in_date+timedelta(hours=5,minutes=30)).date() not in leave_list:
            attendance_reg = self.env['attendance.regular.line'].sudo().create({
                'state': 'requested',
                'employee_id': self.employee.id,
                'check_in': check_in_date,
                'check_out': self.to_date,
                'worked_hours': (self.to_date-check_in_date).total_seconds()/3600.0,
                'from_date': check_in_date,
                'to_date': self.to_date
            })
        if self.auto_approve:
            self.sudo().write({
                'state_select': 'approved'
            })
            regular = self.attendance_regular_ids
            regular.sudo().write({
                'state': 'approved'
            })
            for rec in regular:
                self.env['hr.attendance'].sudo().create({
                    'check_in': rec.check_in,
                    'check_out': rec.check_out,
                    'employee_id': rec.employee_id.id,
                    'company_id': rec.employee_id.company_id.id,
                    'manager_id': rec.employee_id.parent_id.id,
                    'source_check_in': self.reg_category.type + ' IN',
                    'source_check_out': self.reg_category.type + ' OUT',
                    'regular_id': self.id
                })
            template = self.env.ref('hr_attendance_regularization.send_auto_approve_regularization_email')
            template_values = {
                'email_from': 'unity@e-zest.in',
                'email_to': '${object.employee_id.parent_id.user_id.login|safe}',
                'auto_delete': True,
                'partner_to': False,
                'scheduled_date': False,
            }
            # template.write(template_values)
            # For serialization testing commented below line
            # with self.env.cr.savepoint():
            #     template.with_context(lang=self.employee.user_id.lang).sudo().send_mail(self.employee.user_id.id, force_send=True, raise_exception=False)
            note_summary = "Regularization Request approved on behalf of " + (self.manager_id.name if self.manager_id else 'Manager')
            subject = "Self Approved Regularization Request"
            self.filtered(lambda hol: hol.state_select == 'approved').message_post(body=note_summary, subject=subject)
        else:
            self.sudo().write({
                'state_select': 'requested'
            })
            self.attendance_regular_ids.sudo().write({
                'state': 'requested'
            })
            self.activity_update()
        if self.worked_hours > 12 and not self.divide_date:
            return {
                'name': 'Regularize Warning',
                'type': 'ir.actions.act_window',
                'res_model': 'regularize.confirm.wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
            }
        return

    def activity_update(self):
        for reg_attendace in self.filtered(lambda hol: hol.state_select == 'requested'):
            self.activity_schedule(
                'hr_attendance_regularization.mail_act_reg_attendance_approval',
                user_id=reg_attendace.employee.parent_id.user_id.id or self.env.user.id)

    def regular_approval(self):
        for regular in self:
            check_in = regular.from_date + timedelta(hours=5, minutes=30)
            check_out = regular.to_date + timedelta(hours=5, minutes=30)
            attendances = self.env['hr.attendance'].sudo().search([('employee_id', '=', regular.employee.id)])
            # leave_list, hdl = self._check_leave_date(self.employee.id)
            for rec in attendances:
                atten_check_in = rec.check_in + timedelta(hours=5, minutes=30)
                atten_check_out = rec.check_out + timedelta(hours=5, minutes=30) if rec.check_out else False
                if atten_check_in.date() == check_in.date():
                    if not atten_check_out and check_in:
                        if not((atten_check_in > check_in and atten_check_in > check_out)):
                            raise UserError(_('First checkout your previous checkin %s-%s' % (atten_check_in, regular.employee)))
                    # elif atten_check_out and atten_check_out >= check_out and atten_check_in <= check_out:
                    #     raise UserError(_('Already Approved. Attendance for %s-%s is captured in system %s' % (atten_check_in, atten_check_out, regular.employee)))
                    # elif atten_check_out and atten_check_out >= check_in and atten_check_in <= check_in:
                    #     raise UserError(_('Already Approved. Attendance for %s-%s is captured in system %s' % (atten_check_in, atten_check_out, regular.employee)))
            # if check_in.date() in leave_list:
            #     raise UserError(_("Already Applied leave for this date %s. Refuse leave and then ask for regularization" %(check_in.date())))
            # elif check_out.date() in leave_list:
            #     raise UserError(_("Already Applied leave for this date %s. Refuse leave and then ask for regularization" %(check_out.date())))
            if self.env.user.has_group('hr_attendance_regularization.group_attendance_regular_manager'):
                current_managers = regular.employee.parent_id.user_id
                if current_managers and regular.employee.user_id == self.env.user:
                    raise UserError(_("You cannot approve your own attendance"))
            if not self.env.user.has_group('base.group_system') and not self.env.user.has_group('hr_attendance_regularization.group_attendance_regular_manager'):
                if self.env.user.id == regular.employee.user_id.id:
                    raise UserError(_("You cannot approve your own attendance"))
            regular.sudo().write({
                'state_select': 'approved',
                'reg_approved_employee': self.env.user.employee_id.id
            })
            regular.attendance_regular_ids.sudo().write({
                'state': 'approved'
            })
            for t in regular.timesheet_ids:
                t.sudo().write({
                    'state': 'approved'
                })
            self.filtered(lambda hol: hol.state_select == 'approved').activity_feedback(['hr_attendance_regularization.mail_act_reg_attendance_approval'])
            for reg_line in regular.attendance_regular_ids:
                self.env['hr.attendance'].sudo().create({
                    'check_in': reg_line.check_in,
                    'check_out': reg_line.check_out,
                    'employee_id': reg_line.employee_id.id,
                    'company_id': reg_line.employee_id.company_id.id,
                    'manager_id': reg_line.employee_id.parent_id.id,
                    'source_check_in': regular.reg_category.type + ' IN',
                    'source_check_out': regular.reg_category.type + ' OUT',
                    'regular_id': regular.id
                })
            template_id = self.env.ref('hr_attendance_regularization.send_approved_regularization_email_user').id
            template = self.env['mail.template'].browse(template_id)
            template_values = {
                'email_from': 'unity@e-zest.in',
                'email_to': regular.employee.user_id.login or False,
                'auto_delete': True,
                'partner_to': False,
                'scheduled_date': False,
            }
            # template.write(template_values)
            # For testing
            # with self.env.cr.savepoint():
            #     template.with_context(lang=regular.employee.user_id.lang).sudo().send_mail(regular.id, force_send=True, raise_exception=False)

            message = _('Successfull! Attendance is approved.')
            if message and len(self) == 1:
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': message,
                        'img_url': '/web/image/%s/%s/image_1024' % (regular.employee._name, regular.employee.id) if regular.employee.image_1024 else '/web/static/src/img/smile.svg',
                        'type': 'rainbow_man',
                    }
                }
        return True

    def regular_rejection(self):
        if self.state_select in ['requested', 'approved'] and not self.reg_reason_reject:
            raise UserError(_("Fill the Reason of Reject."))
        if self.user_has_groups('hr_attendance_regularization.group_attendance_regular_manager'):
            current_managers = self.employee.parent_id.user_id
            if current_managers and self.employee.user_id == self.env.user:
                raise UserError(_("You cannot reject your own attendance"))
        if self.is_lock is True:
            raise UserError(_("You cannot change once payroll is completed."))
        if self.state_select == "approved":
            for regular_line in self.attendance_regular_ids:
                self._cr.execute("DELETE FROM hr_attendance WHERE employee_id=%s AND check_in=%s AND check_out=%s", (regular_line.employee_id.id,regular_line.check_in,regular_line.check_out))  
        else:
            self.filtered(lambda hol: hol.state_select == 'requested').activity_unlink(['hr_attendance_regularization.mail_act_reg_attendance_approval'])
        self.sudo().write({
            'state_select': 'reject',
            'reg_approved_employee': self.env.user.employee_id.id
        })
        for i in self.attendance_regular_ids:
            self._cr.execute("DELETE FROM attendance_regular_line WHERE id=%s", ([i.id]))
        for t in self.timesheet_ids:
            t.sudo().write({
                'state': 'reject'
            })
        template_id = self.env.ref('hr_attendance_regularization.send_reject_regularization_email_user').id
        template = self.env['mail.template'].browse(template_id)
        template_values = {
            'email_from': 'unity@e-zest.in',
            'email_to': self.employee.user_id.login or False,
            'auto_delete': True,
            'partner_to': False,
            'scheduled_date': False,
        }
        # template.sudo().write(template_values)
        # For Testing
        # with self.env.cr.savepoint():
        #     template.with_context(lang=self.employee.user_id.lang).sudo().send_mail(self.id, force_send=True, raise_exception=False)

        # for regular in self:
        #     if regular.employee.user_id:
        #         regular.message_post(
        #             body=_('Dear %s, <br/> Your request for %s for %s has been rejected<br/><br/> In case of any discrepancy connect with you manager %s') % (regular.employee.name, regular.reg_category.type, regular.from_date, regular.manager_id.name),
        #             partner_ids=regular.employee.user_id.partner_id.ids)

        return

    def unlink(self):
        for rec in self:
            rec.attendance_regular_ids.unlink()
        return super(Regular, self).unlink()

class AttendanceRegularLine(models.Model):
    _name = 'attendance.regular.line'
    _description = 'Attendance Regular Line'
    _rec_name = 'employee_id'

    def approve_regular_line(self):
        for rec in self:
            self.env['hr.attendance'].sudo().create({
                'check_in': rec.check_in,
                'check_out': rec.check_out,
                'employee_id': rec.employee_id.id,
                'company_id': rec.employee_id.company_id.id,
                'manager_id': rec.employee_id.parent_id.id,
                'source_check_in': rec.attendance_regular_id.reg_category.type + ' IN',
                'source_check_out': rec.attendance_regular_id.reg_category.type + ' OUT',
                'regular_id': rec.attendance_regular_id.id
            })
            rec.sudo().write({
                'state': 'approved'
            })


    def get_attendance_regular(self):

        for rec in self:
            rec.attendance_regular_id = self.env['attendance.regular'].sudo().search([
                ('from_date', '=', rec.from_date),
                ('to_date', '=', rec.to_date),
                ('state_select', '=', 'approved'),
                ('employee', '=', rec.employee_id.id)
            ], limit=1).id

    attendance_regular_id = fields.Many2one('attendance.regular', string="Attendance Summary", compute="get_attendance_regular", store=True, compute_sudo=True)
    employee_id = fields.Many2one('hr.employee', string="e-Zestian")
    check_in = fields.Datetime(string="Check In")
    check_out = fields.Datetime(string="Check Out")
    worked_hours = fields.Float(string='Worked Hours')
    from_date = fields.Datetime(string='From Date')
    to_date = fields.Datetime(string='To Date')
    state = fields.Selection([('draft', 'Draft'), ('requested', 'Requested'), ('reject', 'Rejected'),
                              ('approved', 'Approved')], string='State')
    manager_id = fields.Many2one(related='employee_id.parent_id', string="Manager")

class Category(models.Model):
    _name = 'reg.categories'
    _description = 'Regularization Categories'
    _rec_name = 'type'

    type = fields.Char(string='Category')


class HrEmployeeAttendaceInherit(models.Model):

    _inherit = 'hr.employee'

    def attendance_action_change(self):
        res = super(HrEmployeeAttendaceInherit,self).attendance_action_change()
        if res.check_in and not res.check_out:
            res.source_check_in = 'Web Check IN'
        else:
            res.source_check_out = 'Web Check OUT'
        return res

class LeadershipTeam(models.Model):

    _name = 'leader.team'
    _description = 'Leadership Team'

    employee_id = fields.Many2one('hr.employee', string='e-Zestian')
