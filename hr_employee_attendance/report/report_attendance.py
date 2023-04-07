# -*- coding: utf-8 -*-
from pytz import timezone
import calendar
import logging

from datetime import date, timedelta, datetime, time
from dateutil.relativedelta import relativedelta
from odoo import models, api, fields, _
_logger = logging.getLogger(__name__)


class LeaveAllocationSummaryXlsx(models.AbstractModel):
    _name = 'report.hr_employee_attendance.report_attendance_summary'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Report Attendance Summary'

    def _date_is_day_off(self, date):
        return date.weekday() in [5, 6]

    def _is_public_holiday(self, start_date, current_company):
        self._cr.execute('''
            SELECT holiday_type
            FROM hr_holidays_public_line
            WHERE date = %s and company_id = %s''', (start_date.strftime('%Y-%m-%d'), current_company.id))
        holiday = self._cr.fetchall()
        if holiday:
            if holiday[0][0] == 'Public Holidays':
                return 'public'
            elif holiday[0][0] == 'Optional Holidays':
                return 'optional'
        else:
            return False

    def _get_public_holiday_name(self, start_date):
        self._cr.execute('''
            SELECT holiday_type, name
            FROM hr_holidays_public_line
            WHERE date = %s''', ([start_date.strftime('%Y-%m-%d')]))
        holiday = self._cr.fetchall()
        if holiday and holiday[0][0] == 'Public Holidays':
            return holiday[0][1]

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

    def _get_employee_attendance(self, employees, from_date, to_date, holiday_type, public_holiday_list, res, present_dic, current_company, responsible_hr, sheet=False, leave_color=False, absent_color=False, public_holiday_color=False, color=False, cell_border=False, wfh_color=False, od_color=False, unpaid_color=False, create_sheet=False):
        conv_from_date = fields.Date.from_string(str(from_date))
        conv_to_date = fields.Date.from_string(str(to_date))

        def _daterange(date1, date2):
            for n in range(int((date2 - date1).days)+1):
                yield date1 + timedelta(n)

        def _get_weekday(from_date, to_date):
            weekdays = []
            for dt in _daterange(from_date, to_date):
                # to print only the weekenddates
                if dt.weekday() in [5, 6]:
                    weekdays.append(dt)
            return weekdays
        weekdays = _get_weekday(conv_from_date, conv_to_date)
        admin = self.env['hr.employee'].search([('id', '=', 1)])
        tz = timezone(admin.resource_calendar_id.tz)
        date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
        date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.max))
        intervals = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
        count_row = 1
        count_sr = 1
        if create_sheet:
            emp = [employee for employee in employees if employee[8] and not (employee[8]>=datetime.strptime(from_date,"%Y-%m-%d").date())]
            access_emp = self.env['hr.employee'].search([('is_ezestian','=',True)])
            employees = [employeee for employeee in employees if employeee not in emp and employeee[0] in access_emp.ids]
        if responsible_hr:
            employees = [emps for emps in employees if emps[12] and emps[12] == responsible_hr[0]]
        public_holidays_all = []
        for rec in self.env['hr.holidays.public.line'].search([('holiday_type','=','Public Holidays'), ('company_id', '=', current_company.id)]):
            public_holidays_all.append(rec.date)
        emp_na_count = 0
        emp_absent = 0
        emp_datas_upl = 0
        for employee in employees:
            present_list = []
            absent_list = []
            leave_list = []
            datas = []
            total_working_hours = []
            present = 0
            total_days = 0
            na_count = 0
            absent = 0
            weekday_count = 0
            weekday_count_without_ph = 0
            apresent = 0
            regular = 0
            holiday_count = 0
            manager = self.env['hr.employee'].search([('id','=',employee[5])]).name
            if employee[12]:
                employee_group = self.env['hr.employee.group'].browse(employee[12])
                responsible_hr = self.env['hr.employee'].search([('id','=',employee_group.related_hr[0].id)]).name
            else:
                responsible_hr = False
            employee_id = self.env['hr.employee'].search([('id','=',employee[0])])
            work_email = employee_id.work_email if employee_id.work_email else employee[9]
            work_location = self.env['hr.location.work'].search([('id','=',employee[6])])
            work_location = work_location.name if work_location else False
            payroll_location = self.env['hr.payroll.location'].search([('id','=',employee[11])])
            payroll_location = payroll_location.name if payroll_location else False
            pub_holiday_list = [m['date'] for m in present_dic]
            for rec in intervals:
                self._cr.execute('''
                    SELECT id, worked_hours, source_check_in
                    FROM hr_attendance
                    WHERE employee_id = %s
                    AND checkin >= %s
                    AND checkin <= %s''', (employee[0],rec[0].strftime("%Y-%m-%d"),rec[0].strftime("%Y-%m-%d")))
                attendances = self._cr.fetchall()
                regular_line = self.env['attendance.regular.line'].search([
                    ('employee_id', '=', employee[0]),
                    ('state', '=', 'requested'),
                    ('check_in', '>=', rec[0]),
                    ('check_out', '<=', rec[0])
                ])
                present_date = {'id': employee[0], 'date': rec[0]}
                if attendances:
                    worked_hours = "%.2f" % sum([rec[1] for rec in attendances])
                    if attendances[0][2]:
                        total_working_hours.append(float(worked_hours))
                        present_date['present'] = '%s/%s'%(attendances[0][2],worked_hours)
                        present_date['color'] = False
                    else:
                        total_working_hours.append(float(worked_hours))
                        present_date['present'] = 'P/%s'%(worked_hours)
                        present_date['color'] = False
                    present += 1
                    apresent += 1
                elif regular_line and holiday_type == 'confirm':
                    present_date['present'] = 'To Approve Regularization'
                    present_date['color'] = False
                    # regular += 1    comment for no need
                    present += 1
                elif (employee[10] and rec[0] < employee[10]) or (employee[8] and rec[0] > employee[8]):
                    present_date['present'] = 'NA'
                    present_date['color'] = color
                    total_days += 1
                else:
                    present_date['present'] = 'AB'
                    present_date['color'] = absent_color
                    absent += 1
                    absent_list.append(rec[0])
                present_list.append(present_date)
            for week_day in weekdays:
                self._cr.execute('''
                    SELECT id, worked_hours, source_check_in
                    FROM hr_attendance 
                    WHERE employee_id = %s 
                    AND checkin >= %s 
                    AND checkin <= %s''', (employee[0],week_day.strftime("%Y-%m-%d"),week_day.strftime("%Y-%m-%d")))
                attendances = self._cr.fetchall()
                regular_line = self.env['attendance.regular.line'].search([
                    ('employee_id', '=', employee[0]),
                    ('state', '=', 'requested'),
                    ('check_in', '>=', week_day),
                    ('check_out', '<=', week_day)
                ])
                present_week_date = {'id': employee[0], 'date': week_day}
                # present_dates = [k['date'] for k in present_list if k['present']=='AB']
                # ph_list = [s['date'] for s in present_dic if s['date'].strftime("%a")=='Mon']
                weekday_count += 1
                if week_day not in public_holiday_list:
                    weekday_count_without_ph += 1
                if attendances:
                    worked_hours = "%.2f" % sum([rec[1] for rec in attendances])
                    if attendances[0][2]:
                        total_working_hours.append(float(worked_hours))
                        present_week_date['present'] = '%s/%s'%(attendances[0][2],worked_hours)
                        present_week_date['color'] = False

                    else:
                        total_working_hours.append(float(worked_hours))
                        present_week_date['present'] = 'P/%s'%(worked_hours)
                        present_week_date['color'] = False
                elif regular_line and holiday_type == 'confirm':
                    present_week_date['present'] = 'To Approve Regularization'
                    present_week_date['color'] = False

                elif (employee[10] and week_day < employee[10]) or (employee[8] and week_day > employee[8]):
                    if week_day not in public_holiday_list:
                        total_days += 1
                    if week_day in pub_holiday_list:
                        weekday_count_without_ph += 1
                    weekday_count = weekday_count - 1
                    weekday_count_without_ph = weekday_count_without_ph - 1
                    present_week_date['present'] = 'NA'
                    present_week_date['color'] = color
                else:
                    present_week_date['present'] = 'WO'
                    present_week_date['color'] = color
                present_list.append(present_week_date)

            if present_dic:
                for k in pub_holiday_list:
                    if (employee[10] and k < employee[10]) or (employee[8] and k > employee[8]):
                        holiday_count-=1 if holiday_count else 0
                        total_days += 1
                        dict_na = {'id': employee[0], 'date': k, 'present': 'NA', 'color': color}
                        present_list.append(dict_na)
                    else:
                        holiday_count+=1
                        dict_na = {'id': employee[0], 'date': k, 'present': 'PH', 'color': public_holiday_color}
                        present_list.append(dict_na)
            self._cr.execute('''
                    SELECT date_from, date_to, number_of_days, request_unit_half, leave_type.name, state
                    FROM hr_leave as leave
                    INNER JOIN hr_leave_type as leave_type on leave_type.id = leave.holiday_status_id
                    WHERE employee_id = %s AND state != 'draft' AND leave_type.active = %s''', (employee[0], 'True'))
            leaves = self._cr.fetchall()
            leave_days = 0
            pl_used = 0
            upl = 0
            uph = 0
            hdupl = 0
            half_day_list = []
            unpaid_leave_list = []
            half_day_count = 0
            total_leaves_taken = 0 #if leave request is in to approve state then also len(leave list) will show "present" thats why when only leave request gets approved present days will be no. of approved leaves taken
            for leave in leaves:
                date_from = leave[0].date()
                date_to = leave[1].date()
                if date_from and date_to:
                    for leave_request in _daterange(date_from, date_to):
                        # exist_in_list = [j['date'] for j in present_list if j['date']==leave_request and j['present']=='NA']
                        if leave_request not in public_holidays_all:
                            if (leave_request >= conv_from_date and leave_request <= conv_to_date) and (leave[2] != None and leave[2]>0):
                                if leave[5] != 'refuse' and leave_request not in weekdays and not (holiday_type == 'validate' and leave[5] == 'confirm'):
                                    leave_list.append(leave_request)
                                if holiday_type == 'confirm' and leave[5] == 'validate':
                                    # absent = absent-1
                                    if leave[3] or leave[2] == 0.5:
                                        half_day_list.append({'date':leave_request,'type':leave[4]})
                                        half_day_count += leave[2]
                                        check_leave = [i['present'] for i in present_list if i['date']==leave_request and i['present'] != 'AB']
                                        if leave[4] == 'UnPaid Leave':
                                            hdupl += leave[2]
                                        if leave_request == half_day_list[0]['date'] and len(half_day_list)>1:
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4] +'/ '+ half_day_list[0]['type']+ ' Approved', 'color': leave_color}
                                        elif check_leave and 'HDL' not in str(check_leave):
                                            present = present-0.5 if present else 0
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4]+' HDL Approved / '+check_leave[0], 'color': leave_color}
                                        else:
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4]+' HDL Approved', 'color': leave_color}
                                    elif leave[4] == 'Optional Holidays':
                                        leaves_date = {'id': employee[0], 'date': leave_request, 'present': 'OH Approved', 'color': public_holiday_color}
                                    elif leave[4] == 'UnPaid Leave':
                                        absent = absent+1
                                        if leave_request not in weekdays:
                                            unpaid_leave_list.append(leave_request)
                                            upl = upl+1
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': 'Unpaid Leave Approved', 'color': unpaid_color}
                                    else:
                                        leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4] + ' Approved', 'color': leave_color}
                                    if leaves_date['date'] not in weekdays:
                                        present_list.append(leaves_date)
                                    total_leaves_taken +=1
                                elif holiday_type == 'validate' and leave[5] == 'validate':
                                    # absent = absent-1
                                    if leave[3] or leave[2] == 0.5:
                                        half_day_list.append({'date':leave_request,'type':leave[4]})
                                        half_day_count += leave[2]
                                        check_leave = [i['present'] for i in present_list if i['date']==leave_request and i['present'] != 'AB']
                                        if leave[4] == 'UnPaid Leave':
                                            hdupl += leave[2]
                                        if leave_request == half_day_list[0]['date'] and len(half_day_list)>1:
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4] +'/ '+ half_day_list[0]['type'], 'color': leave_color}
                                        elif check_leave and 'HDL' not in str(check_leave):
                                            present = present-0.5 if present else 0
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4]+' HDL / '+check_leave[0], 'color': leave_color}
                                        else:
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4]+' HDL', 'color': leave_color}
                                    elif leave[4] == 'Optional Holidays':
                                        leaves_date = {'id': employee[0], 'date': leave_request, 'present': 'OH', 'color': public_holiday_color}
                                    elif leave[4] == 'UnPaid Leave':
                                        absent = absent+1
                                        if leave_request not in weekdays:
                                            unpaid_leave_list.append(leave_request)
                                            upl = upl+1
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': 'Unpaid Leave', 'color': unpaid_color}
                                    else:
                                        leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4], 'color': leave_color}
                                    if leaves_date['date'] not in weekdays:
                                        present_list.append(leaves_date)
                                    total_leaves_taken +=1
                                elif holiday_type == 'confirm' and leave[5] == 'confirm':
                                    # absent = absent-1
                                    if leave[3] or leave[2] == 0.5:
                                        half_day_list.append({'date':leave_request,'type':leave[4]})
                                        half_day_count += leave[2]
                                        check_leave = [i['present'] for i in present_list if i['date']==leave_request and i['present'] != 'AB']
                                        if leave[4] == 'UnPaid Leave':
                                            hdupl += leave[2]
                                        if leave_request == half_day_list[0]['date'] and len(half_day_list)>1:
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4] +'/ '+ half_day_list[0]['type'], 'color': leave_color}
                                        elif check_leave and 'HDL' not in str(check_leave):
                                            present = present-0.5 if present else 0
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4]+' HDL / '+check_leave[0], 'color': leave_color}
                                        else:
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4]+' HDL', 'color': leave_color}
                                        # leaves_date = {'id': employee[0], 'date': leave_request, 'present': 'HDL', 'color': leave_color}
                                    elif leave[4] == 'Optional Holidays':
                                        leaves_date = {'id': employee[0], 'date': leave_request, 'present': 'OH', 'color': public_holiday_color}
                                    elif leave[4] == 'UnPaid Leave':
                                        absent = absent+1
                                        if leave_request not in weekdays:
                                            unpaid_leave_list.append(leave_request)
                                            upl = upl+1
                                            leaves_date = {'id': employee[0], 'date': leave_request, 'present': 'Unpaid Leave', 'color': unpaid_color}
                                    else:
                                        leaves_date = {'id': employee[0], 'date': leave_request, 'present': leave[4], 'color': leave_color}
                                    if leaves_date['date'] not in weekdays:
                                        present_list.append(leaves_date)
                                    total_leaves_taken +=1
                    if leave[5] != 'refuse' and leave[4] != 'UnPaid Leave':
                        if (leave[2] != None  and leave[2]>0):
                            leave_days += leave[2]
                    if leave[5] != 'refuse' and leave[4] == 'Privilege Leave':
                        if (leave[2] != None and leave[2]>0):
                            pl_used += leave[2]
            leaves_used = (len(leave_list) - len(half_day_list)) + half_day_count if len(half_day_list) else len(leave_list)
            casual_leave = self.env['hr.leave.type'].search([('name','=','Casual Leave'), ('active', '=', True)])
            unpaid_leave = self.env['hr.leave.type'].search([('name','=','UnPaid Leave'), ('active', '=', True)])
            optional_leave = self.env['hr.leave.type'].search([('name','=','Optional Holidays'), ('active', '=', True)])
            privelage_leave = self.env['hr.leave.type'].search([('name','=','Privilege Leave'), ('active', '=', True)])
            special_leave = self.env['hr.leave.type'].search([('name','=','Special Leave'), ('active', '=', True)])
            self._cr.execute('''
                    SELECT number_of_days, allocation.create_date, holiday_status_id
                    FROM hr_leave_allocation as allocation
                    INNER JOIN hr_leave_type as leave_type on leave_type.id = allocation.holiday_status_id
                    WHERE employee_id = %s
                    AND state = %s AND leave_type.active = %s''', (employee[0], 'validate', 'True'))
            leave_alloc = self._cr.fetchall()
            leaves_rem_cl_oh = sum([rec[0] for rec in leave_alloc if rec[2] in [casual_leave.id, optional_leave.id]])
            leaves_rem_other = sum([rec[0] for rec in leave_alloc if rec[2] not in [casual_leave.id, optional_leave.id]])
            leaves_rem = leaves_rem_cl_oh + leaves_rem_other
            leave_lapsed = 0
            leave_additions = False
            if (employee[10] and conv_from_date < employee[10] and conv_to_date > employee[10]):
                leave_additions = sum([rec[0] for rec in leave_alloc])
            if conv_to_date.month == 1:
                pl = sum([rec[0] for rec in leave_alloc if rec[2] == privelage_leave.id and rec[1].year == conv_from_date.year])
                if (pl-pl_used) > 45:
                    leave_lapsed = (pl-pl_used)-45
            leave_used_list = []
            cl_list = []
            pl_list = []
            oh_list = []
            spl_list = []
            self._cr.execute('''
                SELECT number_of_days, holiday_status_id, state, date_from, date_to
                FROM hr_leave_report as report
                INNER JOIN hr_leave_type as leave_type on leave_type.id = report.holiday_status_id
                WHERE employee_id = %s AND state != 'refuse' AND leave_type.active='True' ''', ([employee[0]]))
            leave_report = self._cr.fetchall()
            for leaves in leave_report:
                if leaves[0] and leaves[1] and leaves[0]<0 and leaves[1] != unpaid_leave.id:
                    leave_used_list.append(leaves[0])
                if leaves[1] == casual_leave.id:
                    if leaves[0]:
                        cl_list.append(leaves[0])
                if leaves[1] == privelage_leave.id:
                    if leaves[0]:
                        pl_list.append(leaves[0])
                if leaves[1] == optional_leave.id:
                    if leaves[0]:
                        oh_list.append(leaves[0])
                if leaves[1] == special_leave.id:
                    if leaves[0]:
                        spl_list.append(leaves[0])
            cl_list = sum(cl_list) if cl_list else 0
            pl_list = sum(pl_list) if pl_list else 0
            oh_list = sum(oh_list) if oh_list else 0
            spl_list = sum(spl_list) if spl_list else 0
            total_leaves_rem = leaves_rem + sum(leave_used_list)  #adding because leave used list is in negative
            # for absent sandwich
            unpaid_leave_list.extend(i for i in absent_list if i not in leave_list)
            for unpaid in unpaid_leave_list:
                if unpaid.strftime("%a") == 'Fri':
                    unpaid_mon = (unpaid + relativedelta(days=3))
                    if unpaid_mon in unpaid_leave_list:
                        na_count = na_count + 2
                        present_list.append({'id': employee[0], 'date': unpaid + relativedelta(days=1), 'present': 'Sandwich Off', 'color': color})
                        present_list.append({'id': employee[0], 'date': unpaid + relativedelta(days=2), 'present': 'Sandwich Off', 'color': color})

            # self._cr.execute('''
            #         SELECT number_of_days, holiday_status_id, state, date_from, date_to
            #         FROM hr_leave_report
            #         WHERE employee_id = %s''', ([employee[0]]))
            # leave_report = self._cr.fetchall()
            # for leaves in leave_report:
            #     leave_type = self.env['hr.leave.type'].search([('id', '=', leaves[1])]).name
            #     if leave_type == 'UnPaid Leave' and leaves[0] <= -15.0:
            #         for leave in self._daterange(leaves[3], leaves[4]):
            #             if leave.date() in weekdays:
            #                 na_count += 1
            #                 leaves_date = {'id': employee[0], 'date': leave.date(), 'present': 'NA', 'color': color}
            #                 present_list.append(leaves_date)
            #             elif leave.date() in pub_holiday_list:
            #                 holiday_count -= 1
            #                 uph += 1
            #                 leaves_date = {'id': employee[0], 'date': leave.date(), 'present': 'NA', 'color': color}
            #                 present_list.append(leaves_date)
            working_hours = sum(total_working_hours)
            total_working_hours = '{0:02.0f}.{1:02.0f}'.format(*divmod(working_hours * 60, 60))
            datas.append({
                    'id': employee[0],
                    'name': employee[1],
                    'present': present,
                    'upl': upl + hdupl,
                    'absent': absent,
                    'total_remaining_leaves': total_leaves_rem,
                    'total_leaves_taken': leaves_used,
                    'total_worked_days': len(leave_list) + len(intervals) - len(weekdays),
                    'total_working_hours': total_working_hours,
                    'op_leave_balance': leaves_used + total_leaves_rem,
                    'leave_lapsed': leave_lapsed,
                    'leave_additions': leave_additions
                })
            active = 'Active' if employee[7] == 1 else 'In Active'
            joining_date = employee[10] and employee[10].strftime("%Y-%m-%d") or False
            exit_date = employee[8] and employee[8].strftime("%Y-%m-%d") or False
            if create_sheet:
                sheet.write(count_row, 0, count_sr, cell_border)
                sheet.write(count_row, 1, employee[2], cell_border)
                sheet.write(count_row, 2, employee[1], cell_border)
                sheet.write(count_row, 3, work_email, cell_border)
                sheet.write(count_row, 4, joining_date, cell_border)
                sheet.write(count_row, 5, exit_date, cell_border)
                sheet.write(count_row, 6, employee[3], cell_border)
                sheet.write(count_row, 7, manager, cell_border)
                sheet.write(count_row, 8, work_location, cell_border)
                sheet.write(count_row, 9, payroll_location, cell_border)
                sheet.write(count_row, 10, responsible_hr, cell_border)
                sheet.write(count_row, 11, active, cell_border)
                sheet.write(count_row, 12, employee[4], cell_border)
            present_list.sort(key = lambda x:x['date']) 
            presents = [{'present':present['present'],'date':present['date'],'count':i['count'], 'color':present['color']} for present in present_list for i in res if present['date'] == i['day']]
            col_count = 0
            for present in presents:
                if present['color'] and create_sheet:
                    sheet.write(count_row, present['count']+1, present['present'], present['color'])
                elif create_sheet:
                    sheet.write(count_row, present['count']+1, present['present'], cell_border)
                col_count = present['count']+1
            week_off = weekday_count - na_count if weekday_count else 0
            absent_week_off = weekday_count_without_ph - na_count if weekday_count else 0
            absent = (((((((len(res)-total_days))-na_count)-datas[0]['present'])-absent_week_off)-holiday_count)-datas[0]['total_leaves_taken']) - uph - regular
            total_payable = ((((len(res)-total_days)-datas[0]['upl'])-na_count)-absent)-uph if absent==0 else (((len(res)-total_days)-datas[0]['upl'])-na_count)-absent
            if create_sheet:
                sheet.write(count_row, col_count+1, len(res)-total_days, cell_border)
                sheet.write(count_row, col_count+2, week_off, cell_border)
                sheet.write(count_row, col_count+3, holiday_count, cell_border)
                sheet.write(count_row, col_count+4, datas[0]['present'] + regular, cell_border)
                sheet.write(count_row, col_count+5, datas[0]['total_leaves_taken'], cell_border)
                sheet.write(count_row, col_count+6, na_count, cell_border)
                sheet.write(count_row, col_count+7, absent, cell_border)
                sheet.write(count_row, col_count+8, datas[0]['upl'], cell_border)
                sheet.write(count_row, col_count+9, total_payable, cell_border)
                sheet.write(count_row, col_count+10, absent + datas[0]['upl'] + na_count, cell_border)
                sheet.write(count_row, col_count+11, datas[0]['op_leave_balance'], cell_border)
                sheet.write(count_row, col_count+12, cl_list, cell_border)
                sheet.write(count_row, col_count+13, pl_list, cell_border)
                sheet.write(count_row, col_count+14, oh_list, cell_border)
                sheet.write(count_row, col_count+15, spl_list, cell_border)
                sheet.write(count_row, col_count+16, datas[0]['total_remaining_leaves'], cell_border)
                sheet.write(count_row, col_count+17, datas[0]['leave_additions'], cell_border)
                sheet.write(count_row, col_count+18, datas[0]['leave_lapsed'], cell_border)
                sheet.write(count_row, col_count+19, datas[0]['total_working_hours'], cell_border)
            count_row += 1
            count_sr += 1
            emp_na_count = na_count
            emp_absent = absent
            emp_datas_upl = datas[0]['upl']
        return emp_na_count, emp_absent, emp_datas_upl

    def _get_report_header(self, workbook, sheet, bold, from_date, conv_to_date, conv_from_date, color, public_holiday_color, current_company):
        public_holiday_list = []
        res = []
        p_dic = []
        start_date = fields.Date.from_string(from_date)
        for x in range(0, int((conv_to_date - conv_from_date).days)+1):
            color_format = '#BFBFBF' if self._date_is_day_off(start_date) else ''
            if self._is_public_holiday(start_date, current_company) == 'public':
                holiday_color = 'red'
                public_holiday_list.append(start_date)
                p_dic.append({'id':'','date': start_date, 'present': 'PH', 'color':public_holiday_color})
            elif self._is_public_holiday(start_date, current_company) == 'optional':
                holiday_color = 'red'
            else:
                holiday_color = ''
            y = y+1 if x>0 else 11
            res.append({'day_str': start_date.strftime('%a'), 'day': datetime.strptime(str(start_date),'%Y-%m-%d').date(), 'color': color_format, 'count': y, 'holiday_color': holiday_color})
            start_date = start_date + relativedelta(days=1)
        count = 12
        for days in res:
            if days['color'] != '':
                sheet.write(0, count, days['day'].strftime('%d/%b/%Y'), color)
            elif days['holiday_color'] == 'red':
                sheet.write(0, count, days['day'].strftime('%d/%b/%Y'), public_holiday_color)
            else:
                sheet.write(0, count, days['day'].strftime('%d/%b/%Y'), bold)
            count += 1

        sheet.write(0, count, 'Total Days in Month', bold)
        sheet.write(0, count+1, 'Total Week Off in Month', bold)
        sheet.write(0, count+2, 'Declared Holidays', bold)
        sheet.write(0, count+3, 'Present Days', bold)
        sheet.write(0, count+4, 'Leaves Used', bold)
        sheet.write(0, count+5, 'Sandwiched Week Off', bold)
        sheet.write(0, count+6, 'AB Days', bold)
        sheet.write(0, count+7, 'Unpaid Leaves', bold)
        sheet.write(0, count+8, 'Total Payable Days for the month', bold)
        sheet.write(0, count+9, 'Total non-payable days', bold)
        sheet.write(0, count+10, 'Opening leave balance', bold)
        sheet.write(0, count+11, 'Opening CL', bold)
        sheet.write(0, count+12, 'Opening PL', bold)
        sheet.write(0, count+13, 'Opening OH', bold)
        sheet.write(0, count+14, 'Opening SPl', bold)
        sheet.write(0, count+15, 'Leave Balance', bold)
        sheet.write(0, count+16, 'Leaves Additions', bold)
        sheet.write(0, count+17, 'Leaves Lapsed', bold)
        sheet.write(0, count+18, 'Total Working Hours', bold)
        return {'res': res, 'public_holiday_list': public_holiday_list, 'p_dic': p_dic}

    def _get_attendance_client(self, employees, from_date, to_date, sheet_for_client):
        res = []
        conv_from_date = fields.Date.from_string(str(from_date))
        conv_to_date = fields.Date.from_string(str(to_date))
        weekdays = self._get_weekday(conv_from_date, conv_to_date)
        start_date = fields.Date.from_string(from_date)
        for x in range(0, int((conv_to_date - conv_from_date).days)+1):
            if start_date not in weekdays:
                res.append({'day': datetime.strptime(str(start_date),'%Y-%m-%d').date(), 'count': x})
            start_date = start_date + relativedelta(days=1)
        count = 1
        for rec in res:
            for employee in employees:
                attendances = self.env['hr.attendance'].search([('employee_id', '=', employee[0]), ('checkin', '>=', rec['day'].strftime("%Y-%m-%d")),('checkin', '<=', rec['day'].strftime("%Y-%m-%d"))])
                if attendances:
                    time_format = timedelta(hours=5, minutes=30)
                    check_in = (attendances[-1].check_in + time_format).strftime('%Y-%m-%d %H:%M:%S')
                    check_out = (attendances[0].check_out + time_format).strftime('%Y-%m-%d %H:%M:%S') if attendances[0].check_out else ''
                    worked_sec = (((attendances[0].check_out + time_format) - (attendances[-1].check_in + time_format)).total_seconds()) if attendances[0].check_out else 0.0
                    worked_hrs = int(worked_sec / 3600)
                    worked_min = int(worked_sec / 60) % 60
                    worked_hours = '%s.%s' % (worked_hrs,worked_min)
                    if attendances[-1].source_check_in and attendances[0].source_check_out:
                        source = attendances[-1].source_check_in + '/ ' + attendances[0].source_check_out
                    else:
                        source = 'Present'
                else:
                    check_in = 'Absent'
                    check_out = 'Absent'
                    worked_hours = 0.0
                    source = 'Absent'
                sheet_for_client.write(count, 0, count, False)
                sheet_for_client.write(count, 1, rec['day'].strftime('%Y-%m-%d'), False)
                sheet_for_client.write(count, 2, employee[2], False)
                sheet_for_client.write(count, 3, employee[1], False)
                sheet_for_client.write(count, 4, employee[4], False)
                sheet_for_client.write(count, 5, check_in, False)
                sheet_for_client.write(count, 6, check_out, False)
                sheet_for_client.write(count, 7, worked_hours, False)
                sheet_for_client.write(count, 8, source, False)
                count+=1
        # for k in weekdays:

    def _get_report_header_for_client(self, workbook, sheet_for_client, from_date, conv_to_date, conv_from_date):
        sheet_for_client.write(0, 0, 'Sr No.', False)
        sheet_for_client.write(0, 1, 'Date', False)
        sheet_for_client.write(0, 2, 'e-Zestian ID', False)
        sheet_for_client.write(0, 3, 'e-Zestian Name', False)
        sheet_for_client.write(0, 4, 'Department', False)
        sheet_for_client.write(0, 5, 'Check In', False)
        sheet_for_client.write(0, 6, 'Check Out', False)
        sheet_for_client.write(0, 7, 'Total worked hours', False)
        sheet_for_client.write(0, 8, 'Status', False)

    def generate_xlsx_report(self, workbook, data, lines):
        # get data from wizard
        from_date = data.get('form')['from_date']
        to_date = data.get('form')['to_date']
        conv_from_date = fields.Date.from_string(str(from_date))
        conv_to_date = fields.Date.from_string(str(to_date))
        mode = data.get('form')['mode']
        category = data.get('form')['emp_category']
        location = data.get('form')['emp_work_location']
        payroll_loc = data.get('form')['emp_payroll_loc']
        employee_ids = data.get('form').get('employee_id')
        for_client = data.get('form').get('is_for_client')
        holiday_type = data.get('form').get('holiday_type')
        employee = data.get('form').get('mode_employee_id')
        company = data.get('form').get('mode_company_id')
        department = data.get('form').get('mode_department_id')
        responsible_hr = data.get('form').get('responsible_hr')
        if mode == 'employee' and employee:
            if category and location and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.id=%s AND emp.employee_category=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', (employee[0], category[0], location[0], payroll_loc[0]))
                employees = self._cr.fetchall()
            elif category and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.id=%s AND emp.employee_category=%s AND emp.payroll_loc=%s''', (employee[0], category[0], payroll_loc[0]))
                employees = self._cr.fetchall()
            elif location and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.id=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', (employee[0], location[0], payroll_loc[0]))
                employees = self._cr.fetchall()
            elif category and location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.id=%s AND emp.employee_category=%s AND emp.location_work=%s''', (employee[0], category[0], location[0]))
                employees = self._cr.fetchall()
            elif category:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.id=%s AND emp.employee_category=%s''', (employee[0], category[0]))
                employees = self._cr.fetchall()
            elif location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.id=%s AND emp.location_work=%s''', (employee[0], location[0]))
                employees = self._cr.fetchall()
            elif payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.id=%s AND emp.payroll_loc=%s''', (employee[0], payroll_loc[0]))
                employees = self._cr.fetchall()
            else:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.id=%s''', ([employee[0]]))
                employees = self._cr.fetchall()
        elif mode == 'company' and company:
            if category and location and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.company_id = %s AND emp.employee_category=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', ((company[0], category[0], location[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif location and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.company_id = %s AND emp.location_work=%s AND emp.payroll_loc=%s''', ((company[0], location[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif category and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.company_id = %s AND emp.employee_category=%s AND emp.payroll_loc=%s''', ((company[0], category[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif category and location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.company_id = %s AND emp.employee_category=%s AND emp.location_work=%s''', ((company[0], category[0], location[0])))
                employees = self._cr.fetchall()
            elif category:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.company_id = %s AND emp.employee_category=%s''', ((company[0], category[0])))
                employees = self._cr.fetchall()
            elif location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.company_id = %s AND emp.location_work=%s''', ((company[0], location[0])))
                employees = self._cr.fetchall()
            elif payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.company_id = %s AND emp.payroll_loc=%s''', ((company[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            else:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.company_id = %s''', ([company[0]]))
                employees = self._cr.fetchall()
        elif mode == 'department'and department:
            if category and location and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.department_id = %s AND emp.employee_category=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', ((department[0], category[0], location[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif location and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.department_id = %s AND emp.location_work=%s AND emp.payroll_loc=%s''', ((department[0], location[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif category and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.department_id = %s AND emp.employee_category=%s AND emp.payroll_loc=%s''', ((department[0], category[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif category and location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.department_id = %s AND emp.employee_category=%s AND emp.location_work=%s''', ((department[0], category[0], location[0])))
                employees = self._cr.fetchall()
            elif category:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.department_id = %s AND emp.employee_category=%s''', ((department[0], category[0])))
                employees = self._cr.fetchall()
            elif location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.department_id = %s AND emp.location_work=%s''', ((department[0], location[0])))
                employees = self._cr.fetchall()
            elif payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.department_id = %s AND emp.payroll_loc=%s''', ((department[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            else:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                    FROM hr_employee as emp
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    WHERE emp.department_id = %s''', ([department[0]]))
                employees = self._cr.fetchall()
        if employee_ids:
            if len(employee_ids)==1:
                if category and location and payroll_loc:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id=%s AND emp.employee_category=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', (employee_ids[0], category[0], location[0], payroll_loc[0]))
                    employees = self._cr.fetchall()
                elif category and payroll_loc:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id=%s AND emp.employee_category=%s AND emp.payroll_loc=%s''', (employee_ids[0], category[0], payroll_loc[0]))
                    employees = self._cr.fetchall()
                elif payroll_loc and location:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id=%s AND emp.payroll_loc=%s AND emp.location_work=%s''', (employee_ids[0], payroll_loc[0], location[0]))
                    employees = self._cr.fetchall()
                elif category and location:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id=%s AND emp.employee_category=%s AND emp.location_work=%s''', (employee_ids[0], category[0], location[0]))
                    employees = self._cr.fetchall()
                elif category:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id=%s AND emp.employee_category=%s''', (employee_ids[0], category[0]))
                    employees = self._cr.fetchall()
                elif location:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id=%s AND emp.location_work=%s''', (employee_ids[0], location[0]))
                    employees = self._cr.fetchall()
                elif payroll_loc:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id=%s AND emp.payroll_loc=%s''', (employee_ids[0], payroll_loc[0]))
                    employees = self._cr.fetchall()
                else:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id=%s''', ([employee_ids[0]]))
                    employees = self._cr.fetchall()
            else:
                if category and location and payroll_loc:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id IN {0} AND emp.employee_category={1} AND emp.location_work={2} AND emp.payroll_loc={3}'''.format(tuple(employee_ids), category[0], location[0], payroll_loc[0]))
                    employees = self._cr.fetchall()
                elif category and payroll_loc:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id IN {0} AND emp.employee_category={1} AND emp.payroll_loc={3}'''.format(tuple(employee_ids), category[0], payroll_loc[0]))
                    employees = self._cr.fetchall()
                elif payroll_loc and location:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id IN {0} AND emp.payroll_loc={3} AND emp.location_work={2}'''.format(tuple(employee_ids), location[0], payroll_loc[0]))
                    employees = self._cr.fetchall()
                elif category and location:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id IN {0} AND emp.employee_category={1} AND emp.location_work={2}'''.format(tuple(employee_ids), category[0], location[0]))
                    employees = self._cr.fetchall()
                elif category:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id IN {0} AND emp.employee_category={1}'''.format(tuple(employee_ids), category[0]))
                    employees = self._cr.fetchall()
                elif location:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id IN {0} AND emp.location_work={1}'''.format(tuple(employee_ids), location[0]))
                    employees = self._cr.fetchall()
                elif payroll_loc:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id IN {0} AND emp.payroll_loc={1}'''.format(tuple(employee_ids), payroll_loc[0]))
                    employees = self._cr.fetchall()
                else:
                    self._cr.execute('''
                        SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                        FROM hr_employee as emp
                        LEFT JOIN hr_department as dept on dept.id = emp.department_id
                        LEFT JOIN hr_job as job on job.id = emp.job_id
                        WHERE emp.id IN {0}'''.format(tuple(employee_ids)))
                    employees = self._cr.fetchall()
        # prepare sheet
        month_str = conv_from_date.strftime('%B')
        sheet = workbook.add_worksheet("Payroll Summary for %s"%month_str) 
        sheet_static = workbook.add_worksheet("Abbreviated Payroll Summary")
        sheet_for_client = workbook.add_worksheet("For Client Side Attendance Summary for %s"%month_str)
        bold = workbook.add_format({'bold': True, 'border': 1})
        cell_border = workbook.add_format({'border': 1})
        leave_color = workbook.add_format({'bg_color': '#B3A2C7', 'border':1})
        absent_color = workbook.add_format({'bg_color': '#FF0000', 'border':1})
        unpaid_color = workbook.add_format({'bg_color': '#FFF200', 'border':1})
        color = workbook.add_format({'bg_color': '#BFBFBF', 'border':1}) #weekend color
        public_holiday_color = workbook.add_format({'bg_color': '#9BBB59', 'border':1})
        wfh_color = workbook.add_format({'bg_color': '#C0504D', 'border':1})
        od_color = workbook.add_format({'bg_color': '#948A54', 'border':1})

        # for static header summary
        sheet_static.write(0, 0, 'Sr No', bold)
        sheet_static.write(0, 1, '', cell_border)
        sheet_static.write(0, 2, 'Summary', bold)
        sheet_static.write(1, 0, '1', cell_border)
        sheet_static.write(1, 1, 'P', cell_border)
        sheet_static.write(1, 2, 'Actual present days', cell_border)
        sheet_static.write(2, 0, '2', cell_border)
        sheet_static.write(2, 1, 'WO', color)
        sheet_static.write(2, 2, 'Weekly Off', cell_border)
        sheet_static.write(3, 0, '3', cell_border)
        sheet_static.write(3, 1, 'PH', public_holiday_color)
        sheet_static.write(3, 2, 'Public Holiday', cell_border)
        sheet_static.write(4, 0, '4', cell_border)
        sheet_static.write(4, 1, 'OH', public_holiday_color)
        sheet_static.write(4, 2, 'Optional Holiday', cell_border)
        sheet_static.write(5, 0, '5', cell_border)
        sheet_static.write(5, 1, 'Leave Name', leave_color)
        sheet_static.write(5, 2, 'Leave', cell_border)
        sheet_static.write(6, 0, '6', cell_border)
        sheet_static.write(6, 1, 'Leave Type Approved', leave_color)
        sheet_static.write(6, 2, 'Approved Leave', cell_border)
        sheet_static.write(7, 0, '7', cell_border)
        sheet_static.write(7, 1, 'HDL', leave_color)
        sheet_static.write(7, 2, 'Half Day Leave', cell_border)
        sheet_static.write(8, 0, '8', cell_border)
        sheet_static.write(8, 1, 'WFH', cell_border)
        sheet_static.write(8, 2, 'Work From Home', cell_border)
        sheet_static.write(9, 0, '9', cell_border)
        sheet_static.write(9, 1, 'OD', cell_border)
        sheet_static.write(9, 2, 'Out Duty', cell_border)
        sheet_static.write(10, 0, '10', cell_border)
        sheet_static.write(10, 1, 'AB', absent_color)
        sheet_static.write(10, 2, 'Absent (Missed punch/no leave balance/No regularised)', cell_border)
        sheet_static.write(11, 1, 'NA', cell_border)
        sheet_static.write(11, 2, 'Not Applicable', cell_border)
        # sheet_static.write(11, 0, '11', cell_border)
        # sheet_static.write(11, 1, 'SPL Leaves', cell_border)
        # sheet_static.write(11, 2, 'Maternity/Patrenity/Adoption leave', cell_border)

        # sheet start
        sheet.write(0, 0, 'Sr No', bold)
        sheet.write(0, 1, 'e-Zestian ID', bold)
        sheet.write(0, 2, 'e-Zestian Name', bold)
        sheet.write(0, 3, 'Email', bold)
        sheet.write(0, 4, 'Joining Date (YYYY-MM-DD)', bold)
        sheet.write(0, 5, 'Exit Date (YYYY-MM-DD)', bold)
        sheet.write(0, 6, 'Designation', bold)
        sheet.write(0, 7, 'Manager', bold)
        sheet.write(0, 8, 'Work Location', bold)
        sheet.write(0, 9, 'Payroll Location', bold)
        sheet.write(0, 10, 'Responsible HR', bold)
        sheet.write(0, 11, 'Status', bold)
        sheet.write(0, 12, 'Department', bold)
        # prepare report header
        if employee:
            employee_id = self.env['hr.employee'].browse(employee[0])
            current_company = employee_id.company_id
        elif company:
            company_id = self.env['res.company'].browse(company[0])
            current_company = company_id
        elif department:
            department_id = self.env['hr.department'].browse(department[0])
            current_company = department_id.company_id
        else:
            current_company = self.env.company
        if for_client:
            record = self._get_report_header_for_client(workbook, sheet_for_client, from_date, conv_to_date, conv_from_date)
            self._get_attendance_client(employees, from_date, to_date, sheet_for_client)
        else:
            record = self._get_report_header(workbook, sheet, bold, from_date, conv_to_date, conv_from_date, color, public_holiday_color, current_company)
            res = record['res']
            public_holiday_list = record['public_holiday_list']
            present_dic = record.get('p_dic')
            # prepare report body
            self._get_employee_attendance(employees, from_date, to_date, holiday_type, public_holiday_list, res, present_dic, current_company, responsible_hr, sheet, leave_color, absent_color, public_holiday_color, color, cell_border, wfh_color, od_color, unpaid_color, create_sheet=True)
