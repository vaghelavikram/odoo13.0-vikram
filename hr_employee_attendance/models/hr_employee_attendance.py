# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pyodbc
import pytz

from odoo import models, api, fields, _
import logging

_logger = logging.getLogger(__name__)

# '2019-08-22','2019-08-23 23:59:59'
class HrEmployeeAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _cron_employee_attendance(self):
        datetime_format = timedelta(hours=5, minutes=30)
        # first_row = self.env['hr.attendance'].search([])
        # param_date = False
        param_date = datetime.today().date().strftime("%Y-%m-%d 00:00:01")
        config_from_date = self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.from_date')
        config_to_date = self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.to_date')
        # if first_row:
        #     check_in = first_row[0].check_in + datetime_format
        #     check_out = first_row[0].check_out + datetime_format if first_row[0].check_out else False
        #     last_execution_time = check_out if check_out else check_in
        #     param_date = last_execution_time.strftime("%Y-%m-%d %H:%M:%S")
        conn = pyodbc.connect("Driver={ODBC Driver 17 for SQL Server};Server=172.52.60.15\SQLEXPRESS,1433;UID=sa;PWD=matrix_1;Database=CosecNew;")
        cursor = conn.cursor()
        if config_from_date or config_to_date:
            cursor.execute("{CALL dbo.USP_TeamMember_Attendance (?,?)}", config_from_date, config_to_date)
        elif param_date:
            # cursor.execute("{CALL dbo.USP_TeamMember_Attendance (?,?)}", '2019-08-19','2019-08-28 23:59:59')
            cursor.execute("{CALL dbo.USP_TeamMember_Attendance (?)}", param_date)
        else:
            cursor.execute("EXEC dbo.USP_TeamMember_Attendance")
        list_data = cursor.fetchall()
        #(sq, id, name, checkin, checkout, machine ID, machine IN, machine ID, machine OUT)
        # (923, '1899', 'Zilu Rane', datetime.datetime(2019, 9, 16, 14, 30, 17), datetime.datetime(2019, 9, 16, 14, 33, 13), Decimal('14'), 'Main 3 IN', Decimal('15'), 'Main 3 OUT')
        for rec in list_data:
            employee = self.env['hr.employee'].search([('identification_id','=',rec[1])],limit=1)
            cin = rec[3] - datetime_format
            cout = rec[4] - datetime_format if rec[4] else False
            source_check_in = rec[6] if rec[6] else ' '
            source_check_out = rec[8] if rec[8] else ' '
            if employee:
                for atten in self.env['hr.attendance'].search([('employee_id', '=', rec[1]), ('source_check_in', 'in', ['Work From Home IN', 'Update Attendance IN', 'Working From Client Location IN', 'Forgot Access Card IN'])]):
                    if atten.check_in.date() == cin.date() and (atten.check_in > cin):
                        atten.write({
                            'check_out': cin - relativedelta(minutes=1)
                        })
                    if atten.check_in.date() == cin.date() and (atten.check_in > cin):
                        atten.write({
                            'check_out': cin + relativedelta(minutes=1)
                        })
                existing_leave = self.env['hr.leave'].search([('employee_id','=',employee.id),
                    ('state','not in',['draft','refuse','cancel']),
                    ('date_from','<=',cin.date()),
                    ('date_to','>=',cin.date()),('request_unit_half','=',False)])
                if not existing_leave:
                    _logger.info("-------------Employee Match and Attendance created in hr_attendance-----------------")
                    existing = self.env['hr.attendance'].search([('ezest_id', '=', rec[1])])
                    if cin and existing and not cout:
                        # Entry with checkin but not checkout and create new row
                        # with checkin
                        atten = self.env['hr.attendance'].sudo().create({
                            'employee_id': employee.id,
                            'company_id': employee.company_id.id,
                            'ezest_id': employee.identification_id,
                            'manager_id': employee.parent_id.id,
                            'check_in': cin,
                            'source_check_in': source_check_in,
                            'source_check_out': source_check_out
                        })
                        if source_check_in == 'Server Room':
                            atten.sudo().write({'check_out': cin + timedelta(minutes=1)})
                            # atten.write({'check_out': cin + timedelta(minutes=1), 'source_check_out': "Server Room OUT"})
                            # self.env['hr.attendance'].create({
                            #     'employee_id': employee.id,
                            #     'company_id': employee.company_id.id,
                            #     'ezest_id': employee.identification_id,
                            #     'manager_id': employee.parent_id.id,
                            #     'check_in': cin + timedelta(minutes=1),
                            #     'check_out': cin + timedelta(minutes=2),
                            #     'source_check_in': 'Server Room In',
                            #     'source_check_out': 'Server Room Out'
                            # })
                            # if not existing.search([('source_check_in', '=', 'Main 3 IN'), ('check_out', '=', False)]):
                            #     self.env['hr.attendance'].create({
                            #         'employee_id': employee.id,
                            #         'company_id': employee.company_id.id,
                            #         'ezest_id': employee.identification_id,
                            #         'manager_id': employee.parent_id.id,
                            #         'check_in': cin + timedelta(minutes=3),
                            #         'source_check_in': 'Main 3 IN',
                            #     })
                        for i in existing:
                            # previous checkin and not checkout and previous checkin less than
                            # current checkin then remove previous checkin
                            if i.check_in and not i.check_out and i.check_in <= cin and not source_check_in == 'Server Room':
                            #     i.write({'check_out': cin + timedelta(minutes=1), 'source_check_out': "Main OUT before Server IN"})
                            # elif i.check_in and not i.check_out and i.check_in <= cin and not source_check_in=='Server Room':
                                i.unlink()
                            elif i.source_check_in == 'Server Room' and i.check_in == cin:
                                i.unlink()
                    elif cin and cout and existing:
                        # Entry with checkin and checkout and remove empty checkout row
                        # and create new row with first checkin and last check out
                        exist = True
                        for i in existing:
                            if i.check_in <= cin and not i.check_out:
                                i.unlink()
                            elif i.check_in == cin and i.check_out == cout and exist:
                                exist = False
                                i.unlink()

                        self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'company_id': employee.company_id.id,
                            'ezest_id': employee.identification_id,
                            'manager_id': employee.parent_id.id,
                            'check_in': cin,
                            'check_out': cout,
                            'source_check_in': source_check_in,
                            'source_check_out': source_check_out
                        })
                    elif cin and cout and not existing:
                        # exception case
                        self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'company_id': employee.company_id.id,
                            'ezest_id': employee.identification_id,
                            'manager_id': employee.parent_id.id,
                            'check_in': cin,
                            'check_out': cout,
                            'source_check_in': source_check_in,
                            'source_check_out': source_check_out
                        })
                    elif cin and not cout and not existing:
                        # First Entry with checkin Only
                        self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'company_id': employee.company_id.id,
                            'ezest_id': employee.identification_id,
                            'manager_id': employee.parent_id.id,
                            'check_in': cin,
                            'source_check_in': source_check_in,
                            'source_check_out': source_check_out
                        })

    def _cron_employee_night_shift_attendence(self):
        datetime_format = timedelta(hours=5, minutes=30)
        # first_row = self.env['hr.attendance'].search([])
        # param_date = False
        from_date = (datetime.today().date() - timedelta(1)).strftime("%Y-%m-%d")
        to_date = datetime.today().date().strftime("%Y-%m-%d 11:59:00")
        # if first_row:
        #     check_in = first_row[0].check_in + datetime_format
        #     check_out = first_row[0].check_out + datetime_format if first_row[0].check_out else False
        #     last_execution_time = check_out if check_out else check_in
        #     param_date = last_execution_time.strftime("%Y-%m-%d %H:%M:%S")
        conn = pyodbc.connect("Driver={ODBC Driver 17 for SQL Server};Server=172.52.60.15\SQLEXPRESS,1433;UID=sa;PWD=matrix_1;Database=CosecNew;")
        cursor = conn.cursor()
        if from_date:
            # cursor.execute("{CALL dbo.USP_TeamMember_Attendance (?,?)}", '2019-08-19','2019-08-28 23:59:59')
            cursor.execute("{CALL dbo.USP_TeamMember_Attendance (?,?)}", from_date,to_date)
        else:
            cursor.execute("EXEC dbo.USP_TeamMember_Attendance")
        list_data = cursor.fetchall()
        #(sq, id, name, checkin, checkout, machine ID, machine IN, machine ID, machine OUT)
        # (923, '1899', 'Zilu Rane', datetime.datetime(2019, 9, 16, 14, 30, 17), datetime.datetime(2019, 9, 16, 14, 33, 13), Decimal('14'), 'Main 3 IN', Decimal('15'), 'Main 3 OUT')
        for rec in list_data:
            employee = self.env['hr.employee'].search([('identification_id','=',rec[1])],limit=1)
            cin = rec[3] - datetime_format
            cout = rec[4] - datetime_format if rec[4] else False
            source_check_in = rec[6] if rec[6] else ' '
            source_check_out = rec[8] if rec[8] else ' '
            if employee:
                _logger.info("-------------Employee Match and Attendance created in hr_attendance-----------------")
                existing_wfh = self.env['hr.attendance'].search([
                    '&', '&', ('source_check_in', 'in', ['Work From Home IN', 'Update Attendance IN', 'Working From Client Location IN', 'Forgot Access Card IN']), ('employee_id', '=', employee.id),
                    '|', '&',('check_in', '>', cin), ('check_out', '>', cin), '&', ('check_in', '<', cin), ('check_out', '>', cin),
                ])
                existing_leave = self.env['hr.leave'].search([('employee_id','=',employee.id),
                    ('state','not in',['draft','refuse','cancel']),
                    ('request_date_from','<=',cin.date()),
                    ('request_date_to','>=',cin.date())])
                if not existing_wfh and not existing_leave:
                    existing = self.env['hr.attendance'].search([('ezest_id', '=', rec[1])])
                    if cin and existing and not cout:
                        # Entry with checkin but not checkout and create new row
                        # with checkin
                        atten = self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'company_id': employee.company_id.id,
                            'ezest_id': employee.identification_id,
                            'manager_id': employee.parent_id.id,
                            'check_in': cin,
                            'source_check_in': source_check_in,
                            'source_check_out': source_check_out
                        })
                        if source_check_in == 'Server Room':
                            atten.write({'check_out': cin + timedelta(minutes=1)})
                        for i in existing:
                            # previous checkin and not checkout and previous checkin less than
                            # current checkin then remove previous checkin
                            if i.check_in and not i.check_out and i.check_in <= cin and not source_check_in=='Server Room':
                                i.unlink()
                            elif i.source_check_in == 'Server Room' and i.check_in == cin:
                                i.unlink()
                    elif cin and cout and existing:
                        # Entry with checkin and checkout and remove empty checkout row
                        # and create new row with first checkin and last check out
                        exist = True
                        for i in existing:
                            if i.check_in <= cin and not i.check_out:
                                i.unlink()
                            elif i.check_in == cin and i.check_out == cout and exist:
                                exist = False
                                i.unlink()

                        self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'company_id': employee.company_id.id,
                            'ezest_id': employee.identification_id,
                            'manager_id': employee.parent_id.id,
                            'check_in': cin,
                            'check_out': cout,
                            'source_check_in': source_check_in,
                            'source_check_out': source_check_out

                        })
                    elif cin and cout and not existing:
                        # exception case
                        self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'company_id': employee.company_id.id,
                            'ezest_id': employee.identification_id,
                            'manager_id': employee.parent_id.id,
                            'check_in': cin,
                            'check_out': cout,
                            'source_check_in': source_check_in,
                            'source_check_out': source_check_out

                        })
                    elif cin and not cout and not existing:
                        # First Entry with checkin Only
                        self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'company_id': employee.company_id.id,
                            'ezest_id': employee.identification_id,
                            'manager_id': employee.parent_id.id,
                            'check_in': cin,
                            'source_check_in': source_check_in,
                            'source_check_out': source_check_out

                        })

    def _get_emp_absent_days(self, employee, from_date, to_date):
        admin = self.env['hr.employee'].search([('id', '=', 1)])
        tz = timezone(admin.resource_calendar_id.tz)
        date_from = tz.localize(datetime.combine(from_date, time.min))
        date_to = tz.localize(datetime.combine(to_date, time.max))
        intervals = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
        casual_leave = self.env['hr.leave.type'].search([('name','=','Casual Leave'), ('active', '=', True)])
        privelage_leave = self.env['hr.leave.type'].search([('name','=','Privilege Leave'), ('active', '=', True)])
        absent_list = []
        leave_list = []
        hdl = []
        absent = 0
        for rec in intervals:
            attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id), ('checkin', '>=', rec[0]), ('checkin', '<=', rec[0])])
            attendance_regular = self.env['attendance.regular.line'].search([('employee_id', '=', employee.id), ('state', '=', 'requested'), ('check_in', '>=', rec[0]), ('check_out', '<=', rec[0]),('state','not in',['reject','draft'])])
            if not attendance and not attendance_regular:
                absent += 1
                absent_list.append(rec[0])
        # leaves = self.env['hr.leave'].search([('employee_id','=', employee.id),('state','not in',['cancel','draft','refuse'])])
        leaves = self.env['hr.leave'].search([('employee_id','=', employee.id),('state', 'in', ['confirm', 'validate'])])
        for leave in leaves:
            leave_date = leave.date_from
            if (leave.date_to - leave.date_from).days >= 1:
                for x in range(0, int((leave.date_to - leave.date_from).days)+1):
                    leave_list.append(leave_date.date())
                    leave_date = leave_date + relativedelta(days=1)
            else:
                if leave.request_unit_half:
                    hdl.append(leave.date_from.date())
                leave_list.append(leave.date_to.date())
        emp_absent = [days.strftime("%a, %d-%b-%Y") for days in absent_list if days not in leave_list]
        hdl_list = [i for i in hdl if hdl.count(i) > 1]
        new_hdl_list = [i for i in hdl if i not in hdl_list]
        hdl = [days for days in absent_list if days in new_hdl_list]
        # emp_hd_absent = [days.strftime("%a, %d-%b-%Y") for days in absent_list if days in hdl]
        #  Leave(CL AND PL REmaining) Count
        cl_list = []
        pl_list = []
        self._cr.execute('''
                SELECT number_of_days, holiday_status_id, state, date_from, date_to
                FROM hr_leave_report
                WHERE employee_id = %s''', ([employee.id]))
        leave_report = self._cr.fetchall()
        for leaves in leave_report:
            if leaves[1] == casual_leave.id:
                if leaves[0] is not None:
                    cl_list.append(leaves[0])
            if leaves[1] == privelage_leave.id:
                if leaves[0] is not None:
                    pl_list.append(leaves[0])
        cl_list = sum(cl_list) if cl_list else 0
        pl_list = sum(pl_list) if pl_list else 0
        absent = len(emp_absent)
        hdl_absent = len(hdl)
        cl = False
        pl = False
        unpaid = False
        if absent>0:
            cl = absent if cl_list > absent else cl_list
            cl_list = cl_list - cl
            if (absent-cl):
                pl = (absent-cl) if pl_list > (absent-cl) else pl_list
                pl_list = pl_list - pl
                if (absent-cl-pl):
                    unpaid = (absent-cl-pl)
        for k in range(hdl_absent):
            if hdl_absent > 0 and cl_list >= 0.5:
                cl += 0.5
                hdl_absent = hdl_absent - 1
            elif hdl_absent > 0 and pl_list >= 0.5:
                pl += 0.5
                hdl_absent = hdl_absent - 1
            elif hdl_absent > 0:
                unpaid += 0.5
                hdl_absent = hdl_absent - 1
        emp_absent.extend([(days.strftime("%a, %d-%b-%Y") + " (Half Day)") for days in absent_list if days in new_hdl_list])
        return emp_absent,cl,pl,unpaid

    # def _get_managers_subordinate(self, managers, employees, from_date, to_date):
    #     emp_dict = {}
    #     for manager in managers:
    #         empl ={}
    #         for employee in employees:
    #             if employee.parent_id == manager:
    #                 emp_list = self._get_emp_absent_days(employee,from_date,to_date)
    #                 empl.update({employee.name:emp_list})
    #         emp_dict.update({manager:empl})
    #         template = '<p>Hello %s,<p>Here is the list of your subordinates absent days for this month\
    #                    till <b>%s</b></p><p>Either ask them to regularize there attendance or apply for leave.\
    #                    </p><b>Name & Absent Dates:</b>\
    #                    <p>%s</p><p><br></p><p>Thanks,</p><p>Team Unity</p>\
    #                    <p><br></p>' % (manager.name,to_date.strftime("%a, %d-%b-%Y"),str(empl)[1:-1])
    #         template_values = {
    #             'subject': 'Reminder for Absent Days of your Subordinates',
    #             'body_html': template,
    #             'e_from': employee.company_id.e,
    #             'e_to': manager.user_id.login,
    #             'e_cc': False,
    #             'auto_delete': False,
    #             'partner_to': False,
    #             'scheduled_date': False,
    #         }
    #         self.env['.'].create(template_values).sudo().send()
    def _get_emp_pending_request(self, employee, from_date, to_date):
        admin = self.env['hr.employee'].search([('id', '=', 1)])
        tz = timezone(admin.resource_calendar_id.tz)
        date_from = tz.localize(datetime.combine(from_date, time.min))
        date_to = tz.localize(datetime.combine(to_date, time.max))
        intervals = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
        request_list = []
        leave_list = []
        for rec in intervals:
            attendance_regular = self.env['attendance.regular.line'].search([('employee_id', '=', employee.id), ('state', '=', 'requested'), ('check_in', '>=', rec[0]), ('check_out', '<=', rec[0])])
            if attendance_regular:
                request_list.append(rec[0].strftime("%a, %d-%b-%Y"))
        leaves = self.env['hr.leave'].search([('employee_id', '=', employee.id), ('state', 'in', ['confirm'])])
        for leave in leaves:
            leave_date = leave.date_from
            if (leave.date_to - leave.date_from).days >= 1:
                for x in range(0, int((leave.date_to - leave.date_from).days)+1):
                    leave_list.append(leave_date.date().strftime("%a, %d-%b-%Y"))
                    leave_date = leave_date + relativedelta(days=1)
            else:
                leave_list.append(leave.date_to.date().strftime("%a, %d-%b-%Y"))
        leave_list = [i for i in leave_list if datetime.strptime(i, "%a, %d-%b-%Y").date() >= from_date and datetime.strptime(i, "%a, %d-%b-%Y").date() <= to_date]
        return request_list, leave_list

    def _get_managers_subordinate(self, managers, employees, from_date, to_date):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for manager in managers:
            empl_leave = {}
            empl_reg = {}
            for employee in employees:
                if employee.parent_id == manager:
                    request_list, leave_list = self._get_emp_pending_request(employee, from_date, to_date)
                    if leave_list:
                        empl_leave.update({employee.name:leave_list})
                    if request_list:
                        empl_reg.update({employee.name:request_list})
            # if empl_reg and empl_leave:
            #     # import pdb; pdb.set_trace()
            #     template = '<p>Hello %s,<p>Here is the list of your subordinates pending request for this month\
            #                till <b>%s</b></p><p>Request you to approve their regularization and leave request.\
            #                </p><b>Name & To Approve Regularization Dates:</b><p>%s</p><br/><b>Name & To Approve Leave Dates:</b>\
            #                <p>%s</p><p><br></p><p>Thanks,</p><p>Team Unity</p>\
            #                <p><br></p>' % (manager.name, to_date.strftime("%a, %d-%b-%Y"), str(empl_reg)[1:-1], str(empl_leave)[1:-1])
            #     template_values = {
            #         'subject': 'Reminder for Pending Request of your Subordinates',
            #         'body_html': template,
            #         'e_from': employee.company_id.e,
            #         'e_to': manager.user_id.login,
            #         'e_cc': False,
            #         'auto_delete': False,
            #     }
            #     self.env['.'].create(template_values).sudo().send()

            if empl_reg or empl_leave:
                message_body = 'Dear %s,'% (manager.name) + '<br/>'
                if empl_reg:
                    reg_count = 1
                    message_body += "<h5 style='color:black;''>Below list of pending regularization requests of your team members</h5>"
                    message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
                    message_body += '<tr style="text-align:center;">'\
                                        '<th>' + 'Sr. No.' + '</th>'\
                                        '<th>' + 'e-Zestian Name' + '</th>'\
                                        '<th>' + 'Regularization To Approve' + '</th>'\
                                    '</tr>'
                    for emp in empl_reg:
                        message_body += '<tr style="text-align:center;">'\
                                            '<td>' + str(reg_count) + '</td>'\
                                            '<td>' + emp + '</td>'\
                                            '<td>' + str(empl_reg[emp])[1:-1] + '</td>'\
                                        '</tr>'
                        reg_count += 1
                    message_body += '</table>' + '<br/>' + '<br/>'

                    # template = '<p>Hello %s,<p>Here is the list of your subordinates pending request for this month\
                    #            till <b>%s</b></p><p>Request you to approve their regularization and leave request.\
                    #            </p><b>Name & To Approve Regularization Dates:</b><p>%s</p><br/>\
                    #            <p>Thanks,</p><p>Team Unity</p>\
                    #            <p><br></p>' % (manager.name, to_date.strftime("%a, %d-%b-%Y"), str(empl_reg)[1:-1])
                if empl_leave:
                    leave_count = 1
                    # message_body += 'Here is the list of your subordinates pending leave request for this month till %s' % (to_date.strftime("%a, %d-%b-%Y"))
                    message_body += "<h5 style='color:black;''>Below list of pending leave requests of your team members,</h5>"
                    message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
                    message_body += '<tr style="text-align:center;">'\
                                        '<th>' + 'Sr. No.' + '</th>'\
                                        '<th>' + 'e-Zestian Name' + '</th>'\
                                        '<th>' + 'Leave To Approve' + '</th>'\
                                    '</tr>'
                    for emp in empl_leave:
                        message_body += '<tr style="text-align:center;">'\
                                            '<td>' + str(leave_count) + '</td>'\
                                            '<td>' + emp + '</td>'\
                                            '<td>' + str(empl_leave[emp])[1:-1] + '</td>'\
                                        '</tr>'
                        leave_count += 1
                    message_body += '</table>' + '<br/>'
                    # template = '<p>Hello %s,<p>Here is the list of your subordinates pending request for this month\
                    #            till <b>%s</b></p><p>Request you to approve their regularization and leave request.\
                    #            </p><b>Name & To Approve Leave Dates:</b>\
                    #            <p>%s</p><p><br></p><p>Thanks,</p><p>Team Unity</p>\
                    #            <p><br></p>' % (manager.name, to_date.strftime("%a, %d-%b-%Y"), str(empl_leave)[1:-1])
                message_body += 'Going forward system will not automatically approve any attendance regularization requests  or leave requests. Unapproved leave will be considered as absent and will result in loss of pay. Kindly approve your  team members’ pending requests to avoid inconvenience.'
                message_body += 'Click on the below link to view your pending activities'
                message_body += '<p>Please click on' \
                    '<a href="{base_url}/web#action=773&amp;cids=&amp;menu_id=95'\
                    'target="_blank" style="background-color: #875A7B; padding: 8px 16px 8px 16px;'\
                    'text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">View Details</a> to view your pending activities.</p>'.format(base_url=base_url)
                if manager.responsible_hr and manager.responsible_hr.related_hr:
                    message_body += '<br/>' + '<br/>' + 'Get in touch with your HR %s in case of any queries.' % (manager.responsible_hr.related_hr[0].name)
                    message_body += '<br/>' + '<br/>'
                else:
                    message_body += '<br/>' + '<br/>' + 'Get in touch with your HR Spoc in case of any queries.' + '<br/>' + '<br/>'
                message_body += 'Thank you' + '<br/>' + 'Unity'
                template_values = {
                    'subject': 'Pending Leave and attendance regularization requests of your team members',
                    'body_html': message_body,
                    'e_from': 'unity@e-zest.in',
                    'e_to': manager.user_id.login,
                    'e_cc': 'unity@e-zest.in,hrd@e-zest.in',
                    'auto_delete': True,
                }
                # For serialization testing commented below line
                # self.env['.'].create(template_values).sudo().send()

    def _cron_emp_absent_remainder(self):
        from_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'), '%Y-%m-%d').date()
        to_date = datetime.today().date() + relativedelta(days=-1)
        employees = self.env['hr.employee'].search([('is_ezestian', '=', True), ('employee_category','=','eZestian'),('company_id', '=', 1)])
        # skip leadership ezestian for absent 
        leadership_team = self.env['leader.team'].sudo().search([]).mapped('employee_id')
        if leadership_team:
            employees = list(set(employees) - set(leadership_team))
        for employee in employees:
            if employee.joining_date and employee.joining_date.month == from_date.month and employee.joining_date.year == from_date.year:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,employee.joining_date,to_date)
            elif employee.joining_date and employee.joining_date.month == to_date.month and employee.joining_date.year == to_date.year:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,employee.joining_date,to_date)
            else:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,from_date,to_date)
            if emp_list:
                template = '<p>Hello %s,</p>\
                            <p>Your absent days are <b>%s</b>. You have not recorded your attendance for below date / dates :</p>.\
                            <p><h3>Absent Dates:</h3></p><p>%s</p><br/>\
                            <p>Above dates are for this month till <b>%s</b></p>\
                            <p>You are requested to regularize the attendance / apply for leave as applicable at the earliest.</p>\
                            <p>If leave/ Attendance regularization requests are not applied in UNITY, it will be considered as AB which will result in loss of pay.</p>\
                            <br/><br/><br/>\
                            Thanks,\
                            <br/>\
                            Team Unity\
                            <p><br></p>' % (employee.name,len(emp_list),str(emp_list)[1:-1],to_date.strftime("%a, %d-%b-%Y"))
                # <p>If leave/ Attendance regularization requests are not applied in UNITY the same will be adjusted against existing leave balance (CL & PL).</p>\
                # <p>In case of 0 leave balance (PL and CL) same will be considered as unpaid leave i.e. loss of pay.</p>\
                # <p>These CL’s / PL’s / Unpaid days will be applied by Unity after the payroll cut off.</p>\
                template_values = {
                    'subject': 'Reminder for Absent Days',
                    'body_html': template,
                    'e_from': employee.company_id.e,
                    'e_to': employee.user_id.login or False,
                    'e_cc': 'unity@e-zest.in,hrd@e-zest.in',
                    'auto_delete': True,
                }
                # For serialization testing commented below line
                # self.env['.'].create(template_values).sudo().send()

    def _cron_contract_absent_remainder(self):
        if datetime.today().date().day > 10:
            from_date = datetime.today().date() + relativedelta(day=1)
            to_date = datetime.today().date() + relativedelta(month=1, day=10)
        else:
            from_date = datetime.today().date() - relativedelta(month=1, day=1)
            to_date = datetime.today().date() + relativedelta(day=10)
        employees = self.env['hr.employee'].search([('is_ezestian', '=', True), ('employee_category','in',['Contractor', 'Intern']),('company_id','=',1)])
        # managers = []
        for employee in employees:
            # if employee.parent_id:
            #     managers.append(employee.parent_id)
            if employee.joining_date and employee.joining_date.month == from_date.month and employee.joining_date.year == from_date.year:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,employee.joining_date,to_date)
            elif employee.joining_date and employee.joining_date.month == to_date.month and employee.joining_date.year == to_date.year:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,employee.joining_date,to_date)
            else:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,from_date,to_date)
            if emp_list:
                template = '<p>Hello %s,</p>\
                            <p>Your absent days are <b>%s</b>. You have not recorded your attendance for below date / dates :</p>.\
                            <p><h3>Absent Dates:</h3></p><p>%s</p><br/>\
                            <p>Above dates are for this month till <b>%s</b></p>\
                            <p>You are requested to regularize the attendance / apply for leave as applicable at the earliest.</p>\
                            <p>If leave/ Attendance regularization requests are not applied in UNITY, it will be considered as AB which will result in loss of pay.</p>\
                            <br/><br/><br/>\
                            Thanks,\
                            <br/>\
                            Team Unity\
                            <p><br></p>' % (employee.name,len(emp_list),str(emp_list)[1:-1],to_date.strftime("%a, %d-%b-%Y"))
                # <p>If leave/ Attendance regularization requests are not applied in UNITY the same will be adjusted against existing leave balance (CL & PL).</p>\
                # <p>In case of 0 leave balance (PL and CL) same will be considered as unpaid leave i.e. loss of pay.</p>\
                # <p>These CL’s / PL’s / Unpaid days will be applied by Unity after the payroll cut off.</p>\
                template_values = {
                    'subject': 'Reminder for Absent Days',
                    'body_html': template,
                    'e_from': employee.company_id.e,
                    'e_to': employee.user_id.login or False,
                    'e_cc': 'unity@e-zest.in,hrd@e-zest.in',
                    'auto_delete': True,
                }
                # For serialization testing commented below line
                # self.env['.'].create(template_values).sudo().send()

        #  <<<<<<<<<<<<<<<<<<For Managers>>>>>>>>>>>>>>>>>>>>>

    def _cron_manager_subordinate_absent_remainder(self):
        from_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'), '%Y-%m-%d').date()
        to_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date'), '%Y-%m-%d').date()
        # to_date = datetime.today().date() + relativedelta(days=-1)
        employees = self.env['hr.employee'].search([('is_ezestian', '=', True), ('employee_category','=','eZestian'),('company_id','=',1)])
        managers = []
        for employee in employees:
            if employee.parent_id:
                managers.append(employee.parent_id)
        managers = list(set(managers))
        self._get_managers_subordinate(managers, employees, from_date, to_date)

    def _cron_emp_leave_adjustment_remainder(self):
        from_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'), '%Y-%m-%d').date()
        to_date = datetime.today().date() + relativedelta(days=-1)
        employees = self.env['hr.employee'].search([('is_ezestian', '=', True), ('employee_category','=','eZestian'),('company_id','=',1)])
        # managers = []
        for employee in employees:
            # if employee.parent_id:
            #     managers.append(employee.parent_id)
            if employee.joining_date and employee.joining_date.month == from_date.month and employee.joining_date.year == from_date.year:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,employee.joining_date,to_date)
            elif employee.joining_date and employee.joining_date.month == to_date.month and employee.joining_date.year == to_date.year:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,employee.joining_date,to_date)
            else:
                emp_list,cl,pl,unpaid = self._get_emp_absent_days(employee,from_date,to_date)
            if cl and pl and unpaid:
                leave_str = '%s Casual Leave, %s Privilege Leave, %s Unpaid Leave'%(cl,pl,unpaid)
            elif cl and pl:
                leave_str = '%s Casual Leave, %s Privilege Leave'%(cl,pl)
            elif pl and unpaid:
                leave_str = '%s Privilege Leave, %s Unpaid Leave'%(pl,unpaid)
            elif cl and unpaid:
                leave_str = '%s Casual Leave, %s Unpaid Leave'%(cl,unpaid)
            elif cl:
                leave_str = '%s Casual Leave'%(cl)
            elif pl:
                leave_str = '%s Privilege Leave'%(pl)
            elif unpaid:
                leave_str = '%s Unpaid Leave'%(unpaid)
            if emp_list:
                template = '<p>Hello %s,<p>Your absent days are <b>%s</b>.\
                           </p><p><h3>Absent Dates:</h3></p>\
                           <p>%s</p><p><br></p>\
                           If you do not act on it then unity will deduct your <b>%s</b>.\
                           Above dates are for this month till <b>%s</b>.</p><p>Either regularize it or apply for leave.\
                           <br/><br/><p>Thanks,</p><p>Team Unity</p>\
                           <p><br></p>' % (employee.name,len(emp_list),str(emp_list)[1:-1],leave_str,to_date.strftime("%a, %d-%b-%Y"))
                template_values = {
                    'subject': 'Reminder for Absent Days',
                    'body_html': template,
                    'e_from': employee.company_id.e,
                    'e_to': employee.user_id.login,
                    'e_cc': 'unity@e-zest.in,hrd@e-zest.in',
                    'auto_delete': True,
                }
                # For serialization testing commented below line
                # self.env['.'].create(template_values).sudo().send()

    def _cron_payroll_dates(self):
        payroll_to_date = self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date')
        newdate = datetime.strptime(payroll_to_date, '%Y-%m-%d')
        if date.today() == newdate.date() + relativedelta(days=5):
            from_date = newdate + relativedelta(days=1)
            to_date = newdate + relativedelta(months=1)
            self.env['ir.config_parameter'].sudo().set_param('hr_employee_attendance.payroll_from_date', from_date.date())
            self.env['ir.config_parameter'].sudo().set_param('hr_employee_attendance.payroll_to_date', to_date.date())

    def _cron_absent_remainder__change(self):
        payroll_from_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'), "%Y-%m-%d").date()
        payroll_to_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_to_date'), "%Y-%m-%d").date()
        if payroll_from_date <= date.today() and payroll_from_date + relativedelta(days=10) >= date.today():
            self._cron_emp_absent_remainder()
        elif payroll_from_date + relativedelta(days=11) <= date.today() and payroll_to_date >= date.today():
            self._cron_emp_leave_adjustment_remainder()

    def _cron_archive_team_member(self):
        payroll_from_date = datetime.strptime(self.env['ir.config_parameter'].sudo().get_param('hr_employee_attendance.payroll_from_date'), "%Y-%m-%d").date()
        attendance = self.env['hr.attendance'].sudo().search([])
        regular = self.env['attendance.regular'].sudo().search([])
        leave = self.env['hr.leave'].sudo().search([])
        confimation = self.env['hr.probation.survey'].sudo().search([])
        for atten in attendance:
            if not atten.employee_id.active and atten.employee_id.exit_date and atten.employee_id.exit_date < payroll_from_date:
                atten.sudo().write({
                    'active': False
                })
        for reg in regular:
            if not reg.employee.active and reg.employee.exit_date and reg.employee.exit_date < payroll_from_date:
                reg.sudo().write({
                    'active': False
                })
        for lev in leave:
            if not lev.employee_id.active and lev.employee_id.exit_date and lev.employee_id.exit_date < payroll_from_date:
                lev.sudo().write({
                    'active': False
                })
        for conf in confimation:
            if not conf.employee_id.active and conf.employee_id.exit_date and conf.employee_id.exit_date < payroll_from_date:
                conf.sudo().write({
                    'active': False
                })

    @api.depends('check_in', 'check_out')
    def _get_check_in_date(self):
        for rec in self:
            rec.checkin = (rec.check_in + timedelta(hours=5, minutes=30)).date().strftime("%Y-%m-%d")
            rec.checkout = rec.check_out and rec.check_out.date().strftime("%Y-%m-%d") or False

    @api.depends('check_in', 'check_out')
    def _get_checkin_day(self):
        for rec in self:
            rec.day_check_in = (rec.check_in + timedelta(hours=5, minutes=30)).strftime("%a, %d-%b-%Y %H:%M:%S") if rec.check_in else ''
            rec.day_check_out = (rec.check_out + timedelta(hours=5, minutes=30)).strftime("%a, %d-%b-%Y %H:%M:%S") if rec.check_out else ''

    def unlink(self):
        for rec in self:
            for atten in rec.regular_id.attendance_regular_ids:
                if atten.check_in == rec.check_in and atten.check_out == rec.check_out:
                    atten.sudo().unlink()
            if not rec.regular_id.attendance_regular_ids:
                rec.regular_id.sudo().unlink()
            # rec.regular_id.sudo().unlink()
        res = super(HrEmployeeAttendance, self).unlink()
        return res

    ezest_id = fields.Char(related='employee_id.identification_id', string='e-Zest Id')
    source_check_in = fields.Char(string='Source Check In')
    source_check_out = fields.Char(string='Source Check Out')
    checkin = fields.Char(string='Checkin', compute="_get_check_in_date", store=True)
    checkout = fields.Char(string='CheckOut', compute="_get_check_in_date", store=True)
    image = fields.Binary(related="employee_id.image_1920")
    image_medium = fields.Binary(related="employee_id.image_1024")
    image_small = fields.Binary(related="employee_id.image_256")
    day_check_in = fields.Char(string="Check In", compute="_get_checkin_day")
    day_check_out = fields.Char(string="Check Out", compute="_get_checkin_day")
    manager_id = fields.Many2one('hr.employee', string='Manager', default=lambda self: self.employee_id.parent_id.id)
    regular_id = fields.Many2one('attendance.regular', string='Go to Regularization')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    active = fields.Boolean('Active', default=True, store=True, readonly=False)
