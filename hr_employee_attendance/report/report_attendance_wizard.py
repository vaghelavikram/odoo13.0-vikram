# -*- coding: utf-8 -*-
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AttendanceSummaryReport(models.TransientModel):
    _name = 'hr.attendance.summary'
    _description = 'HR Attendance, Leaves Summary Report'

    # date_from = fields.Date(string='From', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    from_date = fields.Date('From Date', default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'),
                            required=True)
    to_date = fields.Date("To Date", default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date'), required=True)
    mode = fields.Selection([
        ('employee', 'By e-Zestian'),
        ('company', 'By Company'),
        ('department', 'By Department')],
        string='Allocation Mode', default='company')
    emp_category = fields.Many2one('hr.contract.type', string="e-Zestian Category", default= lambda self: self.env['hr.contract.type'].search([], limit=1).id)
    emp_work_location = fields.Many2one('hr.location.work', string="e-Zestian Work Location", default= lambda self: self.env['hr.location.work'].search([], limit=1).id)
    emp_payroll_loc = fields.Many2one('hr.payroll.location', string="e-Zestian Payroll Location", default= lambda self: self.env['hr.payroll.location'].search([], limit=1).id)
    mode_company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    mode_department_id = fields.Many2one('hr.department', string='Department')
    mode_employee_id = fields.Many2one('hr.employee', string='By Particular e-Zestian')
    employee_id = fields.Many2many('hr.employee', string='e-Zestian')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    is_for_client = fields.Boolean(string='Download For Client')
    responsible_hr = fields.Many2one('hr.employee.group', string="Responsible HR")
    holiday_type = fields.Selection([
        ('validate', 'Approved'),
        ('confirm', 'Approved & To Approve')], string='Leave Type', required=True, default='confirm')

    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        if data.get('from_date') > data.get('to_date'):
            raise UserError(_("The From date must be anterior to the End date."))
        if data.get('mode_company_id'):
            record = self.env['res.company'].browse(data['mode_company_id'])
        if data.get('mode_department_id'):
            record = self.env['hr.department'].browse(data['mode_department_id'])
        if data.get('mode_employee_id'):
            record = self.env['hr.employee'].browse(data['mode_employee_id'])
        if data.get('employee_id'):
            record = self.env['hr.employee'].browse(data['employee_id'])
        datas = {
            'ids': [],
            'model': 'hr.attendance',
            'form': data
        }
        return self.env.ref('hr_employee_attendance.report_attendance_xlsx').with_context(from_transient_model=True).report_action(record, data=datas)
        # return self.env.ref('hr_holidays.action_report_holidayssummary').with_context(from_transient_model=True).report_action(departments, data=datas)

    def print_new_joinee_report(self):
        self.ensure_one()
        [data] = self.read()
        if data.get('from_date') > data.get('to_date'):
            raise UserError(_("The From date must be anterior to the End date."))
        if data.get('mode_company_id'):
            record = self.env['res.company'].browse(data['mode_company_id'])
        if data.get('mode_department_id'):
            record = self.env['hr.department'].browse(data['mode_department_id'])
        if data.get('mode_employee_id'):
            record = self.env['hr.employee'].browse(data['mode_employee_id'])
        if data.get('employee_id'):
            record = self.env['hr.employee'].browse(data['employee_id'])
        datas = {
            'ids': [],
            'model': 'hr.attendance',
            'form': data
        }
        return self.env.ref('hr_employee_attendance.report_new_joinee_xlsx').with_context(from_transient_model=True).report_action(record, data=datas)

    def print_leave_adjust_report(self):
        self.ensure_one()
        [data] = self.read()
        if data.get('from_date') > data.get('to_date'):
            raise UserError(_("The From date must be anterior to the End date."))
        if data.get('mode_company_id'):
            record = self.env['res.company'].browse(data['mode_company_id'])
        if data.get('mode_department_id'):
            record = self.env['hr.department'].browse(data['mode_department_id'])
        if data.get('mode_employee_id'):
            record = self.env['hr.employee'].browse(data['mode_employee_id'])
        if data.get('employee_id'):
            record = self.env['hr.employee'].browse(data['employee_id'])
        datas = {
            'ids': [],
            'model': 'hr.attendance',
            'form': data
        }
        return self.env.ref('hr_employee_attendance.report_leave_adjustment_xlsx').with_context(from_transient_model=True).report_action(record, data=datas)


class AttendanceSummaryConfirm(models.TransientModel):
    _name = "attendance.summary.confirm"
    _description = "Attendance Summary"

    def _get_absent_days(self,employee,from_date,to_date):
        admin = self.env['hr.employee'].search([('id', '=', 1)])
        tz = timezone(admin.resource_calendar_id.tz)
        date_from = tz.localize(datetime.combine(from_date, time.min))
        date_to = tz.localize(datetime.combine(to_date, time.max))
        intervals = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
        casual_leave = self.env['hr.leave.type'].search([('name','=','Casual Leave'), ('active', '=', True)])
        privelage_leave = self.env['hr.leave.type'].search([('name','=','Privilege Leave'), ('active', '=', True)])
        absent_list = []
        leave_list = []
        half_day_list = []
        absent = 0
        for rec in intervals:
            attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id), ('checkin', '>=', rec[0]), ('checkin', '<=', rec[0])])
            attendance_regular = self.env['attendance.regular.line'].search([('employee_id', '=', employee.id), ('check_in', '>=', rec[0]), ('check_out', '<=', rec[0]),('state','not in',['reject','draft'])])
            if not attendance and not attendance_regular:
                absent += 1
                absent_list.append(rec[0])
        leaves = self.env['hr.leave'].search([('employee_id','=',employee.id),('state','not in',['cancel','draft','refuse'])])
        for leave in leaves:
            leave_date = leave.date_from
            if (leave.date_to - leave.date_from).days >=1:
                for x in range(0, int((leave.date_to - leave.date_from).days)+1):
                    if leave.number_of_days > 0:
                        leave_list.append(leave_date.date())
                    leave_date = leave_date + relativedelta(days=1)
            elif leave.request_unit_half and leave.date_from.date() >= from_date and leave.date_from.date() <= to_date:
                if leave.date_from.date() in half_day_list:
                    half_day_list.remove(leave.date_from.date())
                    leave_list.append(leave.date_from.date())
                else:
                    half_day_list.append(leave.date_from.date())
            else:
                if leave.number_of_days > 0:
                    leave_list.append(leave.date_to.date())
        emp_absent_list = [days.strftime("%a, %d-%b-%Y") for days in absent_list if days not in leave_list and days not in half_day_list]
        half_day_list = [day for day in half_day_list if day in absent_list]
        cl_list = []
        pl_list = []
        self._cr.execute('''
                SELECT number_of_days, holiday_status_id, state, date_from, date_to
                FROM hr_leave_report
                WHERE employee_id = %s AND state != 'refuse' ''', ([employee.id]))
        leave_report = self._cr.fetchall()
        for leaves in leave_report:
            if leaves[1] == casual_leave.id:
                if leaves[0]:
                    cl_list.append(leaves[0])
            if leaves[1] == privelage_leave.id:
                if leaves[0]:
                    pl_list.append(leaves[0])
        # import pdb; pdb.set_trace()
        cl_list = sum(cl_list) if cl_list else 0
        pl_list = sum(pl_list) if pl_list else 0
        absent = len(emp_absent_list) + (len(half_day_list) / 2)
        cl = False
        pl = False
        unpaid = False
        if absent>0:
            cl = absent if cl_list > absent else cl_list
            if (absent-cl):
                pl = (absent-cl) if pl_list > (absent-cl) else pl_list
                if (absent-cl-pl):
                    unpaid = (absent-cl-pl)
        return emp_absent_list,cl,pl,unpaid,half_day_list

    def action_approve_leave_reg(self):
        self.ensure_one()
        [data] = self.env['hr.attendance.summary'].browse(self.env.context.get('active_id')).read()
        _logger.info("%s, -------------DATA-----------------" % data)
        if data:
            if data.get('from_date') > data.get('to_date'):
                raise UserError(_("The From date must be anterior to the End date."))
            from_date = data.get('from_date')
            to_date = data.get('to_date')
            conv_from_date = fields.Date.from_string(str(from_date))
            conv_to_date = fields.Date.from_string(str(to_date))
            mode = data.get('mode')
            admin = self.env['hr.employee'].search([('id', '=', 1)])
            tz = timezone(admin.resource_calendar_id.tz)
            date_from = tz.localize(datetime.combine(conv_from_date, time.min))
            date_to = tz.localize(datetime.combine(conv_to_date, time.max))
            intervals = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
            category = data.get('emp_category')
            location = data.get('emp_work_location')
            payroll_loc = data.get('emp_payroll_loc')
            employee_ids = data.get('employee_id')
            for_client = data.get('is_for_client')
            holiday_type = data.get('holiday_type')
            employee = data.get('mode_employee_id')
            company = data.get('mode_company_id')
            department = data.get('mode_department_id')
            if mode == 'employee' and employee:
                if category and location and payroll_loc:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('location_work','=',location[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and payroll_loc:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif location and payroll_loc:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('location_work','=',location[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and location:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('location_work','=',location[0]),('employee_category','=',category[0])])
                elif category:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('employee_category','=',category[0])])
                elif location:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('location_work','=',location[0])])
                elif payroll_loc:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('payroll_loc','=',payroll_loc[0])])
                else:
                    employees = self.env['hr.employee'].search([('id','=',employee[0])])
            elif mode == 'company' and company:
                if category and location and payroll_loc:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('location_work','=',location[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and payroll_loc:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif location and payroll_loc:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('location_work','=',location[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and location:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('location_work','=',location[0]),('employee_category','=',category[0])])
                elif category:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('employee_category','=',category[0])])
                elif location:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('location_work','=',location[0])])
                elif payroll_loc:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('payroll_loc','=',payroll_loc[0])])
                else:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0])])
            elif mode == 'department'and department:
                if category and location and payroll_loc:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('location_work','=',location[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and payroll_loc:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif location and payroll_loc:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('location_work','=',location[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and location:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('location_work','=',location[0]),('employee_category','=',category[0])])
                elif category:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('employee_category','=',category[0])])
                elif location:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('location_work','=',location[0])])
                elif payroll_loc:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('payroll_loc','=',payroll_loc[0])])
                else:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0])])
            else:
                raise UserError(_("Select any one of Allocation mode."))
            for employee in employees:
                attendance_regular = self.env['attendance.regular'].search([('employee', '=', employee.id), ('state_select', '=', 'requested')])
                if attendance_regular:
                    for i in attendance_regular:
                        if (i.from_date.date() >= conv_from_date and i.to_date.date() <= conv_to_date):
                            i.write({
                                'reg_reason_reject': 'Rejected by Unity Payroll'
                            })
                            i.regular_rejection()
                            # i.sudo().write({
                            #     'state_select': 'approved'
                            # })
                            # i.attendance_regular_ids.sudo().write({
                            #     'state': 'approved'
                            # })
                            # i.filtered(lambda hol: hol.state_select == 'approved').activity_feedback(['hr_attendance_regularization.mail_act_reg_attendance_approval'])
                            # for reg in i.attendance_regular_ids:
                            #     self.env['hr.attendance'].sudo().create({
                            #         'check_in': reg.check_in,
                            #         'check_out': reg.check_out,
                            #         'employee_id': reg.employee_id.id,
                            #         'company_id': reg.employee_id.company_id.id,
                            #         'manager_id': reg.employee_id.parent_id.id,
                            #         'source_check_in': i.reg_category.type + ' IN',
                            #         'source_check_out': i.reg_category.type + ' OUT',
                            #         'regular_id': i.id
                            #     })
                leaves = self.env['hr.leave'].search([('employee_id', '=', employee.id), ('state', 'in', ['confirm'])])
                for leave in leaves:
                    if (leave.date_from.date() >= conv_from_date and leave.date_to.date() <= conv_to_date):
                        leave.sudo().write({'state': 'validate'})
                        leave.filtered(lambda hol: hol.state == 'validate').activity_feedback(['hr_holidays.mail_act_leave_approval'])

            approve_attendance_regular = self.env['attendance.regular'].search([('state_select', '=', 'approved')])
            for reg in approve_attendance_regular:
                if reg.from_date.date() >= conv_from_date and reg.to_date.date() <= conv_to_date:
                    reg.sudo().write({
                        'is_lock': True
                    })

            validate_leaves = self.env['hr.leave'].search([('state', '=', 'validate')])
            for validate_leave in validate_leaves:
                if validate_leave.date_from.date() >= conv_from_date:
                    validate_leave.sudo().write({
                        'is_lock': True
                    })
            self.env['ir.config_parameter'].sudo().set_param('allocate_pl', True)

    def action_leave_adjust(self):
        self.ensure_one()
        [data] = self.env['hr.attendance.summary'].browse(self.env.context.get('active_id')).read()
        # absent_list,cl,pl,unpaid,hdl = [],0,0,0,0
        if data:
            if data.get('from_date') > data.get('to_date'):
                raise UserError(_("The From date must be anterior to the End date."))
            from_date = data.get('from_date')
            to_date = data.get('to_date')
            conv_from_date = fields.Date.from_string(str(from_date))
            conv_to_date = fields.Date.from_string(str(to_date))
            mode = data.get('mode')
            category = data.get('emp_category')
            location = data.get('emp_work_location')
            payroll_loc = data.get('emp_payroll_loc')
            employee_ids = data.get('employee_id')
            for_client = data.get('is_for_client')
            holiday_type = data.get('holiday_type')
            employee = data.get('mode_employee_id')
            company = data.get('mode_company_id')
            department = data.get('mode_department_id')
            if mode == 'employee' and employee:
                if category and location and payroll_loc:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('location_work','=',location[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and payroll_loc:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif location and payroll_loc:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('location_work','=',location[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and location:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('location_work','=',location[0]),('employee_category','=',category[0])])
                elif category:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('employee_category','=',category[0])])
                elif location:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('location_work','=',location[0])])
                elif payroll_loc:
                    employees = self.env['hr.employee'].search([('id','=',employee[0]),('payroll_loc','=',payroll_loc[0])])
                else:
                    employees = self.env['hr.employee'].search([('id','=',employee[0])])
            elif mode == 'company' and company:
                if category and location and payroll_loc:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('location_work','=',location[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and payroll_loc:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif location and payroll_loc:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('location_work','=',location[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and location:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('location_work','=',location[0]),('employee_category','=',category[0])])
                elif category:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('employee_category','=',category[0])])
                elif location:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('location_work','=',location[0])])
                elif payroll_loc:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0]),('payroll_loc','=',payroll_loc[0])])
                else:
                    employees = self.env['hr.employee'].search([('company_id','=',company[0])])
            elif mode == 'department'and department:
                if category and location and payroll_loc:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('location_work','=',location[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and payroll_loc:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('employee_category','=',category[0]),('payroll_loc','=',payroll_loc[0])])
                elif location and payroll_loc:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('location_work','=',location[0]),('payroll_loc','=',payroll_loc[0])])
                elif category and location:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('location_work','=',location[0]),('employee_category','=',category[0])])
                elif category:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('employee_category','=',category[0])])
                elif location:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('location_work','=',location[0])])
                elif payroll_loc:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0]),('payroll_loc','=',payroll_loc[0])])
                else:
                    employees = self.env['hr.employee'].search([('department_id','=',department[0])])
            else:
                raise UserError(_("Select any one of Allocation mode."))
            for employee in employees:
                if employee.joining_date and employee.exit_date and (employee.joining_date.month == from_date.month or employee.joining_date.month == to_date.month) and (employee.joining_date.year == to_date.year or employee.joining_date.year == from_date.year) and (employee.exit_date.month == from_date.month or employee.exit_date.month == to_date.month) and (employee.exit_date.year == from_date.year or employee.exit_date.year == to_date.year):
                    if employee.exit_date <= to_date:
                        absent_list, cl, pl, unpaid, hdl = self._get_absent_days(employee,employee.joining_date,employee.exit_date)
                    elif employee.exit_date > to_date:
                        absent_list, cl, pl, unpaid, hdl = self._get_absent_days(employee,employee.joining_date,employee.to_date)
                elif employee.joining_date and (employee.joining_date.month == from_date.month or employee.joining_date.month == to_date.month) and (employee.joining_date.year == to_date.year or employee.joining_date.year == from_date.year):
                    # if employee.joining_date < to_date:
                    absent_list, cl, pl, unpaid, hdl = self._get_absent_days(employee,employee.joining_date,to_date)
                elif employee.exit_date and (employee.exit_date.month == from_date.month or employee.exit_date.month == to_date.month) and (employee.exit_date.year == from_date.year or employee.exit_date.year == to_date.year):
                    if employee.exit_date <= to_date:
                        absent_list, cl, pl, unpaid, hdl = self._get_absent_days(employee,from_date,employee.exit_date)
                    elif employee.exit_date > to_date:
                        absent_list, cl, pl, unpaid, hdl = self._get_absent_days(employee,from_date,to_date)
                else:
                    # if not employee.joining_date > to_date:
                    absent_list, cl, pl, unpaid, hdl = self._get_absent_days(employee,from_date,to_date)
                absent_list.sort()
                absent_list = [datetime.strptime(ab, "%a, %d-%b-%Y").date() for ab in absent_list]
                _logger.info("%s >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", employee.name)
                if cl and hdl:
                    for hc in range(len(hdl)):
                        if cl:
                            hd = self.env['hr.leave'].search([('employee_id', '=', employee.id), ('request_date_to', '=', hdl[0]), ('state', '!=', 'refuse')]).request_date_from_period
                            if hd == 'am':
                                leav_from = datetime.combine(hdl[0], time(8, 30))
                                leav_to = datetime.combine(hdl[0], time(12, 30))
                            if hd == 'pm':
                                leav_from = datetime.combine(hdl[0], time(3, 30))
                                leav_to = datetime.combine(hdl[0], time(7, 30))
                            casual_leave = self.env['hr.leave'].with_context(
                                mail_notify_force_send=False,
                                mail_activity_automation_skip=True
                            ).sudo().create({
                                'name': 'Leave Applied by Unity',
                                'date_from': leav_from or hdl[0],
                                'request_date_from': leav_from.date() or hdl[0],
                                'date_to': leav_to or hdl[0],
                                'request_date_to': leav_to.date() or hdl[0],
                                'number_of_days': 0.5,
                                'request_unit_half':True,
                                'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'Casual Leave')]).id,
                                'holiday_type': 'employee',
                                'employee_id': employee.id
                            })
                            casual_leave.sudo().write({'state':'validate'})
                            hdl.pop(0)
                            cl = cl - 0.5
                if cl and absent_list:
                    for c in range(int(cl)):
                        if absent_list:
                            casual_leave = self.env['hr.leave'].with_context(
                                mail_notify_force_send=False,
                                mail_activity_automation_skip=True
                            ).sudo().create({
                                'name': 'Leave Applied by Unity',
                                'date_from': datetime.combine(absent_list[0], time(3, 30)),
                                'date_to': datetime.combine(absent_list[0], time(12, 30)),
                                'request_date_from': absent_list[0],
                                'request_date_to': absent_list[0],
                                'number_of_days': 1,
                                'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'Casual Leave')]).id,
                                'holiday_type': 'employee',
                                'employee_id': employee.id
                            })
                            casual_leave.sudo().write({'state':'validate'})
                            cl -= 1
                            absent_list.pop(0)
                    if cl == 0.5 and absent_list:
                        casual_leave = self.env['hr.leave'].with_context(
                            mail_notify_force_send=False,
                            mail_activity_automation_skip=True
                        ).sudo().create({
                            'name': 'Leave Applied by Unity',
                            'date_from': datetime.combine(absent_list[0], time(3, 30)),
                            'date_to': datetime.combine(absent_list[0], time(7, 30)),
                            'request_date_from': absent_list[0],
                            'request_date_to': absent_list[0],
                            'number_of_days': 0.5,
                            'request_unit_half': True,
                            'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'Casual Leave')]).id,
                            'holiday_type': 'employee',
                            'employee_id': employee.id
                        })
                        half_cl_morning = True
                        casual_leave.sudo().write({'state':'validate'})
                        if pl > 0:
                            date_from_half = datetime.combine(absent_list[0], time(8, 30)) if half_cl_morning else datetime.combine(absent_list[0], time(3, 30))
                            date_to_half = datetime.combine(absent_list[0], time(12, 30)) if half_cl_morning else datetime.combine(absent_list[0], time(7, 30))
                            privilege_leave = self.env['hr.leave'].with_context(
                                mail_notify_force_send=False,
                                mail_activity_automation_skip=True
                            ).sudo().create({
                                'name': 'Leave Applied by Unity',
                                'date_from': date_from_half,
                                'date_to': date_to_half,
                                'request_date_from': date_from_half.date(),
                                'request_date_to': date_to_half.date(),
                                'number_of_days': 0.5,
                                'request_unit_half': True,
                                'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'Privilege Leave')]).id,
                                'holiday_type': 'employee',
                                'employee_id': employee.id
                            })
                            pl = pl - 0.5
                            privilege_leave.sudo().write({'state':'validate'})
                            half_cl_morning = False
                        else:
                            date_from_half = datetime.combine(absent_list[0], time(8, 30)) if half_cl_morning else datetime.combine(absent_list[0], time(3, 30))
                            date_to_half = datetime.combine(absent_list[0], time(12, 30)) if half_cl_morning else datetime.combine(absent_list[0], time(7, 30))
                            unpaid_leave = self.env['hr.leave'].with_context(
                                mail_notify_force_send=False,
                                mail_activity_automation_skip=True
                            ).sudo().create({
                                'name': 'Leave Applied by Unity',
                                'date_from': date_from_half,
                                'date_to': date_to_half,
                                'request_date_from': date_from_half.date(),
                                'request_date_to': date_to_half.date(),
                                'number_of_days': 0.5,
                                'request_unit_half': True,
                                'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'UnPaid Leave')]).id,
                                'holiday_type': 'employee',
                                'employee_id': employee.id
                            })
                            unpaid_leave.sudo().write({'state':'validate'})
                            half_cl_morning = False
                        absent_list.pop(0)
                    _logger.info("-------------Casual Leave Created-----------------")
                if pl and hdl:
                    for hp in range(len(hdl)):
                        if pl:
                            hdp = self.env['hr.leave'].search([('employee_id','=',employee.id),('request_date_to','=',hdl[0]), ('state', '!=', 'refuse')]).request_date_from_period
                            if hdp == 'am':
                                leav_fromp = datetime.combine(hdl[0], time(8, 30))
                                leav_top = datetime.combine(hdl[0], time(12, 30))
                            if hdp == 'pm':
                                leav_fromp = datetime.combine(hdl[0], time(3, 30))
                                leav_top = datetime.combine(hdl[0], time(7, 30))
                            privilege_leave = self.env['hr.leave'].with_context(
                                mail_notify_force_send=False,
                                mail_activity_automation_skip=True
                            ).sudo().create({
                                'name': 'Leave Applied by Unity',
                                'date_from': leav_fromp or hdl[0],
                                'date_to': leav_top or hdl[0],
                                'request_date_from': leav_fromp.date() or hdl[0],
                                'request_date_to': leav_top.date() or hdl[0],
                                'number_of_days': 0.5,
                                'request_unit_half': True,
                                'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'Privilege Leave')]).id,
                                'holiday_type': 'employee',
                                'employee_id': employee.id
                            })
                            privilege_leave.sudo().write({'state': 'validate'})
                            pl = pl - 0.5
                            hdl.pop(0)
                if pl and absent_list:
                    # import pdb; pdb.set_trace()
                    for p in range(int(pl)):
                        if absent_list:
                            privilege_leave = self.env['hr.leave'].with_context(
                                mail_notify_force_send=False,
                                mail_activity_automation_skip=True
                            ).sudo().create({
                                'name': 'Leave Applied by Unity',
                                'date_from': datetime.combine(absent_list[0], time(3, 30)),
                                'date_to': datetime.combine(absent_list[0], time(12, 30)),
                                'request_date_from': absent_list[0],
                                'request_date_to': absent_list[0],
                                'number_of_days': 1,
                                'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'Privilege Leave')]).id,
                                'holiday_type': 'employee',
                                'employee_id': employee.id
                            })
                            privilege_leave.sudo().write({'state': 'validate'})
                            pl = pl - 1
                            absent_list.pop(0)
                            _logger.info("-------------Privelege Leave Created-----------------")
                    if pl == 0.5 and absent_list:
                        privilege_leave = self.env['hr.leave'].with_context(
                            mail_notify_force_send=False,
                            mail_activity_automation_skip=True
                        ).sudo().create({
                            'name': 'Leave Applied by Unity',
                            'date_from': datetime.combine(absent_list[0], time(3, 30)),
                            'date_to': datetime.combine(absent_list[0], time(7, 30)),
                            'request_date_from': absent_list[0],
                            'request_date_to': absent_list[0],
                            'number_of_days': 0.5,
                            'request_unit_half': True,
                            'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'Privilege Leave')]).id,
                            'holiday_type': 'employee',
                            'employee_id': employee.id
                        })
                        privilege_leave.sudo().write({'state': 'validate'})
                        unpaid_leave = self.env['hr.leave'].with_context(
                            mail_notify_force_send=False,
                            mail_activity_automation_skip=True
                        ).sudo().create({
                            'name': 'Leave Applied by Unity',
                            'date_from': datetime.combine(absent_list[0], time(8, 30)),
                            'date_to': datetime.combine(absent_list[0], time(12, 30)),
                            'request_date_from': absent_list[0],
                            'request_date_to': absent_list[0],
                            'number_of_days': 0.5,
                            'request_unit_half': True,
                            'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'UnPaid Leave')]).id,
                            'holiday_type': 'employee',
                            'employee_id': employee.id
                        })
                        unpaid_leave.sudo().write({'state': 'validate'})
                        absent_list.pop(0)
                if absent_list:
                    for u in range(len(absent_list)):
                        unpaid_leave = self.env['hr.leave'].with_context(
                            mail_notify_force_send=False,
                            mail_activity_automation_skip=True
                        ).sudo().create({
                            'name': 'Leave Applied by Unity',
                            'date_from': datetime.combine(absent_list[0], time(3, 30)),
                            'date_to': datetime.combine(absent_list[0], time(12, 30)),
                            'request_date_from': absent_list[0],
                            'request_date_to': absent_list[0],
                            'number_of_days': 1,
                            'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'UnPaid Leave')]).id,
                            'holiday_type': 'employee',
                            'employee_id': employee.id
                        })
                        unpaid_leave.sudo().write({'state': 'validate'})
                        absent_list.pop(0)
                        _logger.info("-------------Unpaid Leave Created-----------------")
                if hdl:
                    for h in range(len(hdl)):
                        hdu = self.env['hr.leave'].search([('employee_id', '=', employee.id), ('request_date_to', '=', hdl[0]), ('state', '!=', 'refuse')]).request_date_from_period
                        if hdu == 'am':
                            leav_fromu = datetime.combine(hdl[0], time(8, 30))
                            leav_tou = datetime.combine(hdl[0], time(12, 30))
                        if hdu == 'pm':
                            leav_fromu = datetime.combine(hdl[0], time(3, 30))
                            leav_tou = datetime.combine(hdl[0], time(7, 30))
                        unpaid_leave = self.env['hr.leave'].with_context(
                            mail_notify_force_send=False,
                            mail_activity_automation_skip=True
                        ).sudo().create({
                            'name': 'Leave Applied by Unity',
                            'date_from': leav_fromu or hdl[0],
                            'date_to': leav_tou or hdl[0],
                            'request_date_from': leav_fromu.date() or hdl[0],
                            'request_date_to': leav_tou.date() or hdl[0],
                            'number_of_days': 0.5,
                            'holiday_status_id': self.env['hr.leave.type'].search([('name', '=', 'UnPaid Leave')]).id,
                            'holiday_type': 'employee',
                            'employee_id': employee.id
                        })
                        unpaid_leave.sudo().write({'state': 'validate'})
                        hdl.pop(0)

            validate_leaves = self.env['hr.leave'].search([('state', '=', 'validate')])
            for validate_leave in validate_leaves:
                if validate_leave.date_from.date() >= conv_from_date and validate_leave.date_to.date() <= conv_to_date:
                    validate_leave.sudo().write({
                        'is_lock': True
                    })
