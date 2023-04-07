# -*- coding: utf-8 -*-
from pytz import timezone
import ast

from dateutil.relativedelta import relativedelta
from datetime import date, timedelta, datetime, time
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class EmployeeSummaryReportCalendar(models.Model):
    _name = 'employee.summary.report.calendar'
    _description = 'e-Zestian Summary Report'

    name = fields.Char(string="Type")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    employee_id = fields.Many2one('hr.employee', string='e-Zestian', readonly=True)
    identification_id = fields.Char(related="employee_id.identification_id", string='e-Zestian ID')
    employee_name = fields.Char(related="employee_id.name", string='e-Zestian Name')
    image_medium = fields.Binary(related="employee_id.image_1024")
    check_absent = fields.Boolean(string="Is Absent")

    def open_leave(self):
        context = {'default_request_date_from': self.from_date,
                   'default_request_date_to': self.to_date,
                   'default_date_from': self.from_date,
                   'default_date_to': self.to_date}
        return {
            'name': ('Apply Leave'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.leave',
            'view_id': self.env.ref('hr_holidays.hr_leave_view_form').id,
            'target': 'current',
            'context': context
        }

    def open_regularize(self):
        context = {
            'default_from_date': datetime.combine(self.from_date, time(3, 30)), #send time by minus 5 hours 30 minutes
            'default_to_date': datetime.combine(self.to_date, time(12, 30)),
            'default_employee': self.employee_id.id
        }
        return {
            'name': ('Apply Regularization'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'attendance.regular',
            'view_id': self.env.ref('hr_attendance_regularization.attendance_regular11').id,
            'target': 'current',
            'context': context
        }


class EmployeeAttendanceLeaveSummary(models.TransientModel):
    _name = 'employee.attendance.leave.summary'
    _description = 'Employee Attendance Leave Summary'

    @api.model
    def _get_employees_domain(self):
        if self.user_has_groups('hr.group_hr_user'):
            res = []
        else:
            res = ['|', ('user_id.id', '=', self.env.user.id), ('user_id.employee_id.parent_id.user_id.id', '=', self.env.user.id)]
        return res

    from_date = fields.Date(string='From', required=True, default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'))
    to_date = fields.Date(string='To', required=True, default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date'))
    user_id = fields.Many2one('res.users', string='e-Zestian User', default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', string="e-Zestian",  domain=lambda self: self._get_employees_domain())

    def _is_public_holiday(self, start_date):
        self._cr.execute('''
            SELECT holiday_type
            FROM hr_holidays_public_line
            WHERE date = %s''', ([start_date.strftime('%Y-%m-%d')]))
        holiday = self._cr.fetchall()
        if holiday:
            if holiday[0][0] == 'Public Holidays':
                return 'public'
            elif holiday[0][0] == 'Optional Holidays':
                return 'optional'
        else:
            return False

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

    def action_summary_report(self):
        if self.from_date and self.to_date:
            if self.from_date.year < 2020 or self.to_date.year < 2020:
                raise UserError(_('Details are available from 1 Jan 2020.'))

        employee = self.employee_id or self.env.user.employee_id
        config_from_date = self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date')
        config_to_date = self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date')
        if employee.joining_date and str(employee.joining_date) > config_from_date:
            config_from_date = str(employee.joining_date)
        from_date = self.from_date or datetime.strptime(config_from_date, '%Y-%m-%d').date()
        today = datetime.today()
        date_to = (today + relativedelta(days=-1)).date() if today.month != 12 else datetime.today()+relativedelta(year=today.year+1, month=1, days=-1)
        to_date = self.to_date or (fields.Date.today() + relativedelta(days=-1))
        if from_date > to_date:
            to_date = datetime.strptime(config_to_date, '%Y-%m-%d').date()
            # raise UserError(_("The From date must be anterior to the End date."))
        weekdays = self._get_weekday(from_date, to_date)
        admin = self.env['hr.employee'].search([('id', '=', 1)])
        tz = timezone(employee.resource_calendar_id.tz)
        date_from = tz.localize(datetime.combine(from_date, time.min))
        date_to = tz.localize(datetime.combine(to_date, time.max))
        intervals = employee.list_work_time_per_day(date_from, date_to, calendar=employee.resource_calendar_id)
        present = 0
        absent = 0
        regularize = 0
        wfh = 0
        od = 0 #out duty
        ph = 0
        ph_without_weekend = 0
        oh = 0
        hdl = 0
        wp = 0 # (to remove duplicate from attendance and regularization)
        leave_list = []
        res = []
        absent_dates = []
        date_list = []
        total_working_hours = []
        start_date = from_date
        half_day_dates = [] #(to calculate and show half day absent in summary report)
        for x in range(0, int((to_date - from_date).days)+1):
            res.append({'date': start_date})
            start_date = start_date + timedelta(days=1)
        for rec in intervals:
            attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id), ('checkin', '>=', rec[0]), ('checkin', '<=', rec[0])])
            attendance_regular = self.env['attendance.regular.line'].search([('employee_id', '=', employee.id), ('state', '=', 'requested')])
            if attendance:
                worked_hours = "%.2f" % sum([rec.worked_hours for rec in attendance])
                if attendance[0].source_check_in == 'Work From Home IN':
                    wfh += 1
                    total_working_hours.append(float(worked_hours))
                    date_list.append({'name': 'Work From Home', 'date': rec[0]})
                elif attendance[0].source_check_in == 'Out Duty IN':
                    od += 1
                    total_working_hours.append(float(worked_hours))
                    date_list.append({'name': 'Out Duty', 'date': rec[0]})
                else:
                    present += 1
                    total_working_hours.append(float(worked_hours))
                    date_list.append({'name': 'Present', 'date': rec[0]})
            elif attendance_regular:
                absent += 1
                reg_list = [reg for reg in attendance_regular if reg.check_in.date() >= rec[0] and reg.check_out.date() <= rec[0]]
                if len(reg_list) > 0:
                    regularize += 1
                    absent -= 1
                    date_list.append({'name': 'To Approve Regularize', 'date': rec[0]})
                elif rec[0] > datetime.today().date():
                    date_list.append({'name': 'NA', 'date': rec[0]})
                else:
                    absent_dates.append(rec[0])
                    date_list.append({'name': 'ABSENT', 'date': rec[0]})

                # for reg in attendance_regular:
                #     if reg.check_in.date() >= rec[0] and reg.check_out.date() <= rec[0]: 
                #         regularize += 1
                #         absent -= 1
                #         date_list.append({'name': 'To Approve Regularize', 'date': rec[0]})
                #     else:
                #         absent_dates.append(rec[0])
                #         date_list.append({'name': 'ABSENT', 'date': rec[0]})
            # elif self._is_public_holiday(rec[0]) == 'optional':
            #     oh += 1
            #     date_list.append({'name': 'Optional Holiday', 'date': rec[0]})
            elif not ((employee.joining_date and rec[0] < employee.joining_date) or (employee.exit_date and rec[0] > employee.exit_date)):
                absent += 1
                absent_dates.append(rec[0])
                date_list.append({'name': 'ABSENT', 'date': rec[0]})
        for record in res:
            if self._is_public_holiday(record['date']) == 'public':
                ph += 1
                date_list.append({'name': 'Public Holiday', 'date': record['date']})
            if record['date'].weekday() not in [5, 6]:
                if self._is_public_holiday(record['date']) == 'public':
                    ph_without_weekend += 1
        for week_day in weekdays:
            attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id), ('checkin', '>=', week_day), ('checkin', '<=', week_day)])
            attendance_regular = self.env['attendance.regular.line'].search([('employee_id', '=', employee.id), ('state', '=', 'requested')])
            if attendance:
                worked_hours = "%.2f" % sum([attendee.worked_hours for attendee in attendance])
                if attendance[0].source_check_in == 'Work From Home IN':
                    wfh += 1
                    wp += 1
                    total_working_hours.append(float(worked_hours))
                    date_list.append({'name': 'Work From Home', 'date': week_day})
                elif attendance[0].source_check_in == 'Out Duty IN':
                    od += 1
                    wp += 1 
                    total_working_hours.append(float(worked_hours))
                    date_list.append({'name': 'Out Duty', 'date': week_day})
                else:
                    wp += 1
                    present += 1
                    total_working_hours.append(float(worked_hours))
                    date_list.append({'name': 'Present', 'date': week_day})
            elif attendance_regular:
                for reg in attendance_regular:
                    if reg.check_in.date() >= week_day and reg.check_out.date() <= week_day: 
                        regularize += 1
                        date_list.append({'name': 'To Approve Regularize', 'date': rec[0]})

        self._cr.execute('''
                SELECT date_from, date_to, number_of_days, request_unit_half, leave_type.name, state
                FROM hr_leave as leave
                INNER JOIN hr_leave_type as leave_type on leave_type.id = leave.holiday_status_id
                WHERE employee_id = %s AND leave_type.active = %s''', (employee.id, 'True'))
        leaves = self._cr.fetchall()
        leave_days = 0
        upl = 0
        lc = 0
        for leave in leaves:
            date_from = leave[0].date()
            date_to = leave[1].date()
            if date_from and date_to:
                for leave_request in self._daterange(date_from, date_to):
                    if (leave_request >= from_date and leave_request <= to_date):
                        if leave[5] != 'refuse' and leave_request not in weekdays:
                            leave_list.append(leave_request)
                            absent = absent-1
                            if leave[3]:
                                hdl += 1
                                hdl_rec = self.env['account.analytic.line'].search([])
                                rec_hdl = hdl_rec.mapped('date')
                                if leave_request in rec_hdl:
                                    leaves_date = {'name': 'Half Day Leave', 'date': leave_request}
                                else:
                                    half_day_dates.append(leave_request)
                                    leaves_date = {'name': 'Half Day Leave', 'date': leave_request}
                            elif leave[4] == 'Optional Holidays':
                                oh += 1
                                leaves_date = {'name': 'Optional Leave', 'date': leave_request}
                            elif leave[4] == 'UnPaid Leave':
                                absent = absent+1
                                upl = upl+1
                                leaves_date = {'name': 'UnPaid Leave', 'date': leave_request}
                            else:
                                leaves_date = {'name': 'Leave', 'date': leave_request}
                            if leaves_date['date'] not in weekdays:
                                date_list.append(leaves_date)
                if leave[5] != 'refuse' and leave[4]!='UnPaid Leave':
                    if leave[2]:
                        leave_days += leave[2]
        self._cr.execute('''
                    SELECT number_of_days, holiday_status_id
                    FROM hr_leave_allocation as allocation
                    INNER JOIN hr_leave_type as leave_type on leave_type.id = allocation.holiday_status_id
                    WHERE employee_id = %s
                    AND state = %s AND leave_type.active = %s''', (employee.id, 'validate', 'True'))
        leave_alloc = self._cr.fetchall()
        leaves_rem = sum([rec[0] for rec in leave_alloc])
        date_list = list({v['date']:v for v in date_list}.values())
        total = (present+wfh+od-wp) if present or wfh or od or wp else 1
        working_hours = sum(total_working_hours) / total if total and total > 0 else 1
        total_working_hours = '{0:02.0f}.{1:02.0f}'.format(*divmod(working_hours * 60, 60))
        absent_list = list(set([ab for ab in absent_dates if ab not in leave_list]))
        context = {
                    'default_date_list': date_list,
                    'default_from_date': from_date,
                    'default_to_date': to_date,
                    'default_actual_present_days': present,
                    'default_optional_holiday': oh,
                    'default_leave': len(leave_list),
                    'default_half_day_leave': hdl,
                    'default_remaining_leave': leaves_rem - leave_days if leaves_rem > 0 else leaves_rem,
                    'default_work_from_home': wfh,
                    'default_out_duty': od,
                    'default_absent': len(absent_list) if len(absent_list) > 0 else False,
                    'default_absent_green': len(absent_list) if len(absent_list) == 0 else False,
                    'default_public_holiday': ph,
                    'default_total_working_days': len(res) - len(weekdays) - ph_without_weekend,
                    'default_user': self.employee_id.user_id.name or self.env.user.name,
                    'default_user_id': self.employee_id.user_id.id or self.env.user.id,
                    'default_worked_hours': total_working_hours,
                    'default_weekend': len(weekdays),
                    'default_total_days': len(res),
                    'default_to_approve_regularize': regularize,
                    'default_employee_id': employee.id,
                    'default_absent_dates': absent_list + half_day_dates
                }
        view_id = self.env.ref('hr_employee_attendance.view_employee_summary_report_form').id,
        return {
            'name': ('Summary Report'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'employee.summary.report',
            'view_id': view_id,
            'target': 'current',
            'context': context
        }


class EmployeeSummaryReport(models.Model):
    _name = 'employee.summary.report'
    _rec_name = 'user'
    _description = 'Employee Summary Report'

    def open_leave(self):
        return {
            'name': ('Apply Leave'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.leave',
            'view_id': self.env.ref('hr_holidays.hr_leave_view_form_dashboard').id,
            'target': 'current',
        }

    def open_timesheet(self):
        return {
            'name': ('Apply Timesheet'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.analytic.line',
            'view_id': self.env.ref('hr_timesheet.hr_timesheet_line_form').id,
            'target': 'current',
        }

    def open_regularize(self):
        if self.employee_id.account.name == 'Deployable - Billable' or self.employee_id.account.name == 'Enabling – Support':
            is_regularization_visible = True
        else:
            is_regularization_visible = False
        context = {
            'default_from_date': datetime.combine(self.from_date, time(3, 30)),  # send time by minus 5 hours 30 minutes
            'default_to_date': datetime.combine(self.to_date, time(12, 30)),
            'default_employee': self.employee_id.id,
            'default_is_regularization_visible': is_regularization_visible
        }
        return {
            'name': ('Apply Regularization'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'attendance.regular',
            'view_id': self.env.ref('hr_attendance_regularization.attendance_regular11').id,
            'target': 'current',
            'context': context
        }
    
    @api.model
    def _get_emp_attendance(self):
        user = self._context.get('default_user_id') if not self.user_id else self.user_id.id
        user_id = self.env['res.users'].search([('id', '=', user)])
        from_date = self._context.get('default_from_date') if not self.from_date else self.from_date
        to_date = self._context.get('default_to_date') if not self.to_date else self.to_date
        attendance_ids = self.env['hr.attendance'].search([
                 ('employee_id', '=', user_id.employee_id.id),
                 ('checkin', '>=', from_date),
                 ('checkin', '<=', to_date)
        ])
        return attendance_ids.ids

    @api.model
    def _get_employee_regularize(self):
        user = self._context.get('default_user_id') if not self.user_id else self.user_id.id
        user_id = self.env['res.users'].search([('id', '=', user)])
        from_date = self._context.get('default_from_date') if not self.from_date else self.from_date
        to_date = self._context.get('default_to_date') if not self.to_date else self.to_date
        regularize_ids = self.env['attendance.regular.line'].search([
                 ('employee_id', '=', user_id.employee_id.id),
                 ('check_in', '>=', from_date),
                 ('check_in', '<=', to_date)
        ])
        return regularize_ids.ids

    @api.model
    def _get_employee_leave(self):
        user = self._context.get('default_user_id') if not self.user_id else self.user_id.id
        user_id = self.env['res.users'].search([('id', '=', user)])
        from_date = self._context.get('default_from_date') if not self.from_date else self.from_date
        to_date = self._context.get('default_to_date') if not self.to_date else self.to_date
        leave_ids = self.env['hr.leave'].search([
                 ('employee_id', '=', user_id.employee_id.id),
                 ('date_from', '>=', from_date),
                 ('date_to', '<=', to_date)
        ])
        return leave_ids.ids

    employee_id = fields.Many2one('hr.employee', string='e-Zestian', readonly=True)
    image = fields.Binary(related="employee_id.image_1920")
    image_medium = fields.Binary(related="employee_id.image_1024")
    image_small = fields.Binary(related="employee_id.image_256")
    from_date = fields.Date(string="From Date", readonly=True)
    user_id = fields.Many2one('res.users', string='e-Zestian User', readonly=True)
    ezest_id = fields.Char(related="employee_id.identification_id", string='e-Zest ID', readonly=True)
    to_date = fields.Date(string="To Date", readonly=True)
    actual_present_days = fields.Char(string="Office Attendance", readonly=True)
    public_holiday = fields.Char(string="Public Holiday", readonly=True)
    optional_holiday = fields.Char(string="Optional Holiday", readonly=True)
    leave = fields.Char(string="Leaves Used", readonly=True)
    half_day_leave = fields.Char(string="Half Day Leaves Used", readonly=True)
    remaining_leave = fields.Char(string="Total Leave Balance", readonly=True)
    work_from_home = fields.Char(string="Work From Home", readonly=True)
    out_duty = fields.Char(string="Out Duty", readonly=True)
    absent = fields.Char(string="Absent Days", readonly=True)
    absent_green = fields.Char(string="No Absent Days", readonly=True)
    worked_hours = fields.Float(string="Avg. Worked Hours", readonly=True)
    total_working_days = fields.Char(string="Total Working Days", readonly=True)
    date_list = fields.Text(string="Dates")
    user = fields.Char(string="e-Zestian Related User")
    weekend = fields.Integer(string="Weekend", readonly=True)
    total_days = fields.Integer(string="Total Days", readonly=True)
    attendance_ids = fields.Many2many('hr.attendance', string="Attendance Details", default=_get_emp_attendance, readonly=True)
    leave_ids = fields.Many2many('hr.leave', string="Leave Details", default=_get_employee_leave, readonly=True)
    to_approve_regularize = fields.Integer(string="To Approve Regularize", readonly=True)
    regularize_ids = fields.Many2many('attendance.regular.line', string="Regularization Details", default=_get_employee_regularize, readonly=True)
    absent_dates = fields.Char(string="Absent Dates", readonly=True)
    is_regularization_visible = fields.Boolean(string="Regularize")

    def action_change_date(self):
        view_id = self.env.ref('hr_employee_attendance.view_employee_own_attendance_form').id,
        return {
            'name': ('Change Date'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'employee.attendance.leave.summary',
            'view_id': view_id,
            'target': 'new'
        }

    def action_summary_calendar_report(self):
        dates = ast.literal_eval(self.date_list)
        res_calendar = self.env['employee.summary.report.calendar']
        for i in dates:
            rec_calendar = res_calendar.search([('from_date', '=', i['date']), ('name', '=', i['name'])])
            from_date = datetime.strptime(i['date'],'%Y-%m-%d').date()
            if i['name'] == 'ABSENT':
                is_absent = True
            else:
                is_absent = False
            if rec_calendar:
                self._cr.execute('UPDATE employee_summary_report_calendar '\
                    'SET employee_id=NULL '\
                    'WHERE employee_id=%s AND from_date=%s', (self.user_id.employee_id.id,from_date))
                self._cr.execute("DELETE FROM employee_summary_report_calendar WHERE employee_id=%s AND from_date=%s", (self.user_id.employee_id.id,from_date))
                res_calendar.create({
                    'from_date': i['date'], 'to_date': i['date'], 'name': i['name'],
                    'employee_id': self.user_id.employee_id.id, 'check_absent': is_absent})
            else:
                self._cr.execute("DELETE FROM employee_summary_report_calendar WHERE employee_id=%s AND from_date=%s", (self.user_id.employee_id.id,from_date))
                res_calendar.create({
                    'from_date': i['date'], 'to_date': i['date'], 'name': i['name'],
                    'employee_id': self.user_id.employee_id.id, 'check_absent': is_absent})
        return {
            'name': ('Calendar'),
            'type': 'ir.actions.act_window',
            'view_type': 'calendar',
            'view_mode': 'calendar',
            'res_model': 'employee.summary.report.calendar',
            'view_id': self.env.ref('hr_employee_attendance.view_employee_summary_report_calendar').id,
            'target': 'current',
            'domain': [('employee_id','=',self.user_id.employee_id.id)]
        }
