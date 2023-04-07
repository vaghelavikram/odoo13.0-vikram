# -*- coding: utf-8 -*-
from pytz import timezone
import calendar

from datetime import date, timedelta, datetime, time
from dateutil.relativedelta import relativedelta
from odoo import models, api, fields, _
from odoo.addons.hr_employee_attendance.report.report_attendance import LeaveAllocationSummaryXlsx

class NewJoineeSummaryXlsx(models.AbstractModel):
    _name = 'report.hr_employee_attendance.report_new_joinee_summary'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Report New Joinee Summary'

    def _get_new_joinee_record(self, employees, from_date, to_date, sheet_new_joinee, sheet_exit, sheet_pf, holiday_type, responsible_hr):
        count = 1
        count_e = 1
        count_pf = 2
        for employee in employees:
            employee = self.env['hr.employee'].browse(employee[0])
            if employee.is_ezestian:
                if employee and employee.responsible_hr and employee.responsible_hr.related_hr:
                    responsible_hr = employee.responsible_hr.related_hr[0].name
                else:
                    responsible_hr = False
                if employee and employee.is_hr_verified:
                    if employee.joining_date and employee.joining_date >= from_date and employee.joining_date <= to_date:
                        if employee.marital == 'married' and employee.gender == 'female':
                            name = employee.spouse_complete_name
                            relation = 'Husband'
                        else:
                            name = employee.fathers_name
                            relation = 'Father'
                        if employee.emp_emergency_contact:
                            emer_con = employee.emp_emergency_contact[0].number
                            emer_name = employee.emp_emergency_contact[0].relation
                        else:
                            emer_con = False
                            emer_name = False
                        if employee.street_c and employee.street2_c:
                            street_c = employee.street_c + ', ' + employee.street2_c
                        elif employee.street_c:
                            street_c = employee.street_c
                        elif employee.street2_c:
                            street_c = employee.street2_c
                        else:
                            street_c = False
                        if employee.street_p and employee.street2_p:
                            street_p = employee.street_p + ', ' + employee.street2_p
                        elif employee.street_p:
                            street_p = employee.street_p
                        elif employee.street2_p:
                            street_p = employee.street2_p
                        else:
                            street_p = False
                        passport_expiry_date = False
                        birthday = False
                        passport_validity_date = False
                        date_of_leaving = False
                        if employee.passport_expiry_date:
                            passport_expiry_date = employee.passport_expiry_date.strftime("%d-%m-%Y")
                        if employee.passport_validity_date:
                            passport_validity_date = employee.passport_validity_date.strftime("%d-%m-%Y")
                        if employee.date_of_leaving:
                            date_of_leaving = employee.date_of_leaving.strftime("%d-%m-%Y")
                        if employee.birthday:
                            birthday = employee.birthday.strftime("%d-%m-%Y")
                        sheet_new_joinee.write(count, 0, employee.identification_id)
                        sheet_new_joinee.write(count, 1, employee.gender)
                        sheet_new_joinee.write(count, 2, employee.name)
                        sheet_new_joinee.write(count, 3, name)
                        sheet_new_joinee.write(count, 4, relation)
                        sheet_new_joinee.write(count, 5, employee.is_technical)
                        sheet_new_joinee.write(count, 6, employee.lwf)
                        sheet_new_joinee.write(count, 7, employee.marital)
                        sheet_new_joinee.write(count, 8, (street_c))
                        sheet_new_joinee.write(count, 9, employee.city_c)
                        sheet_new_joinee.write(count, 10, employee.state_c.name)
                        sheet_new_joinee.write(count, 11, employee.zip_c)
                        sheet_new_joinee.write(count, 12, employee.mobile_phone)
                        sheet_new_joinee.write(count, 13, (street_p))
                        sheet_new_joinee.write(count, 14, employee.city_p)
                        sheet_new_joinee.write(count, 15, employee.state_p.name)
                        sheet_new_joinee.write(count, 16, employee.zip_p)
                        sheet_new_joinee.write(count, 17, employee.mobile_phone)
                        sheet_new_joinee.write(count, 18, employee.bank_account_id.sudo().bank_id.name)
                        sheet_new_joinee.write(count, 19, employee.bank_account_id.sudo().bank_id.bic)
                        sheet_new_joinee.write(count, 20, employee.bank_account_id.sudo().acc_number)
                        sheet_new_joinee.write(count, 21, employee.personal_bnk_name)
                        sheet_new_joinee.write(count, 22, employee.personal_bnk_ifsc)
                        sheet_new_joinee.write(count, 23, employee.personal_acc_no)
                        sheet_new_joinee.write(count, 24, employee.payroll_loc.name)
                        sheet_new_joinee.write(count, 25, employee.joining_date.strftime("%d-%m-%Y"))
                        sheet_new_joinee.write(count, 26, birthday)
                        sheet_new_joinee.write(count, 27, employee.job_id.name)
                        sheet_new_joinee.write(count, 28, employee.parent_id.identification_id)
                        sheet_new_joinee.write(count, 29, employee.pan_no)
                        sheet_new_joinee.write(count, 30, employee.blood_group)
                        sheet_new_joinee.write(count, 31, emer_con)
                        sheet_new_joinee.write(count, 32, emer_name)
                        sheet_new_joinee.write(count, 33, employee.work_email)
                        sheet_new_joinee.write(count, 34, employee.personal_email)
                        sheet_new_joinee.write(count, 35, employee.parent_id.name)
                        sheet_new_joinee.write(count, 36, employee.passport_id)
                        sheet_new_joinee.write(count, 37, passport_expiry_date)
                        sheet_new_joinee.write(count, 38, employee.work_phone)
                        sheet_new_joinee.write(count, 39, employee.aadhar_no)
                        sheet_new_joinee.write(count, 40, employee.pf_uan)
                        sheet_new_joinee.write(count, 41, employee.pf_acc)
                        sheet_new_joinee.write(count, 43, employee.paytm_acc)
                        sheet_new_joinee.write(count, 44, employee.paytm_amt)
                        sheet_new_joinee.write(count, 45, employee.paytm_contact)
                        sheet_new_joinee.write(count, 46, employee.ltc)
                        sheet_new_joinee.write(count, 47, employee.pf_status)
                        sheet_new_joinee.write(count, 50, responsible_hr)
                        count += 1
                        # sheet_new_joinee.write(1, 48, employee.)

                        #sheet pf summary
                        sheet_pf.write(count_pf, 0, employee.identification_id)
                        sheet_pf.write(count_pf, 2, employee.name)
                        sheet_pf.write(count_pf, 3, name)
                        sheet_pf.write(count_pf, 4, relation)
                        sheet_pf.write(count_pf, 5, birthday)
                        sheet_pf.write(count_pf, 6, employee.gender.capitalize())
                        sheet_pf.write(count_pf, 7, employee.joining_date.strftime("%d-%m-%Y"))
                        sheet_pf.write(count_pf, 8, (employee.pf_acc))
                        sheet_pf.write(count_pf, 9, (employee.pf_opt))
                        sheet_pf.write(count_pf, 11, employee.marital.capitalize())
                        sheet_pf.write(count_pf, 12, employee.country_id.name)
                        sheet_pf.write(count_pf, 13, employee.personal_acc_no)
                        sheet_pf.write(count_pf, 14, (employee.personal_bnk_ifsc))
                        sheet_pf.write(count_pf, 15, employee.personal_name)
                        sheet_pf.write(count_pf, 16, employee.pan_no)
                        sheet_pf.write(count_pf, 17, employee.name_pan_card)
                        sheet_pf.write(count_pf, 18, employee.aadhar_no)
                        sheet_pf.write(count_pf, 19, employee.name_aadhar_card)
                        sheet_pf.write(count_pf, 20, employee.passport_id)
                        sheet_pf.write(count_pf, 21, passport_expiry_date)
                        sheet_pf.write(count_pf, 22, passport_validity_date)
                        sheet_pf.write(count_pf, 23, employee.passport_country_id.name)
                        sheet_pf.write(count_pf, 24, employee.pf_uan)
                        sheet_pf.write(count_pf, 25, date_of_leaving)
                        sheet_pf.write(count_pf, 26, employee.prev_epf_no)
                        sheet_pf.write(count_pf, 27, employee.prev_pension_no)
                        sheet_pf.write(count_pf, 31, employee.prev_pf_address)
                        sheet_pf.write(count_pf, 32, employee.mobile_phone)
                        sheet_pf.write(count_pf, 33, employee.personal_email)
                        sheet_pf.write(count_pf, 34, responsible_hr)
                        count_pf += 1

                    if employee.exit_date and employee.exit_date >= from_date and employee.exit_date <= to_date:
                        joining_date = False
                        gratuity = False
                        if employee.joining_date:
                            joining_date = employee.joining_date.strftime("%d-%m-%Y")
                            emp_join = relativedelta(employee.exit_date, employee.joining_date)
                            if emp_join.years >= 5 or (emp_join.years >= 4 and emp_join.months >= 8):
                                gratuity = 'Yes'
                            else:
                                gratuity = 'No'
                        pl = []
                        upl = []
                        self._cr.execute('''
                            SELECT date_from, date_to, number_of_days, leave_type.name
                            FROM hr_leave_report as leave
                            INNER JOIN hr_leave_type as leave_type on leave_type.id = leave.holiday_status_id
                            WHERE employee_id = %s AND leave_type.active='True' ''', ([employee.id]))
                        leaves = self._cr.fetchall()
                        for leave in leaves:
                            if leave[3] == 'Privilege Leave':
                                if leave[2]:
                                    pl.append(leave[2])
                        if sum(pl) > 45:
                            pl = 45
                        else:
                            pl = sum(pl)

                        holiday_status_id = self.env['hr.leave.type'].search([('name', '=', 'UnPaid Leave')]).id
                        leaves = self.env['hr.leave.report'].search([('employee_id', '=', employee.id), ('holiday_status_id', '=', holiday_status_id)])
                        for leave in leaves:
                            if leave.date_from and leave.date_to and leave.date_from.date() >= from_date and leave.date_to.date() <= to_date:
                                if leave.number_of_days:
                                    upl.append(leave.number_of_days)
                        if employee.single_parent:
                            insurance = "Yes"
                            ins_type = "Single Parent"
                        elif employee.set_of_parent:
                            insurance = "Yes"
                            ins_type = "Set of Parent"
                        else:
                            insurance = "No"
                            ins_type = "NA"
                        self._cr.execute('''
                            SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc,responsible_hr
                            FROM hr_employee as emp
                            LEFT JOIN hr_department as dept on dept.id = emp.department_id
                            LEFT JOIN hr_job as job on job.id = emp.job_id
                            WHERE emp.id=%s''', [employee.id])
                        employees = self._cr.fetchall()
                        public_holiday_list = []
                        for rec in self.env['hr.holidays.public.line'].search([('holiday_type','=','Public Holidays')]):
                            public_holiday_list.append(rec.date)
                        start_date = from_date
                        res = []
                        present_dic = []
                        for x in range(0, int((to_date - from_date).days)+1):
                            if start_date in public_holiday_list:
                                present_dic.append({'id': '', 'date': start_date, 'present': 'PH', 'color': ''})
                            y = y + 1 if x > 0 else 11
                            res.append({'day_str': start_date.strftime('%a'), 'day': datetime.strptime(str(start_date),'%Y-%m-%d').date(), 'color': '', 'count': y, 'holiday_color': ''})
                            start_date = start_date + relativedelta(days=1)
                        so, ab, up = LeaveAllocationSummaryXlsx._get_employee_attendance(self, employees, str(from_date), str(to_date), holiday_type, public_holiday_list, res, present_dic, employee.company_id, responsible_hr, sheet=False, create_sheet=False)
                        sheet_exit.write(count_e, 0, employee.identification_id)
                        sheet_exit.write(count_e, 1, employee.name)
                        sheet_exit.write(count_e, 2, (employee.payroll_loc.name or False))
                        sheet_exit.write(count_e, 3, joining_date)
                        sheet_exit.write(count_e, 4, employee.exit_date.strftime("%d-%m-%Y"))
                        sheet_exit.write(count_e, 5, employee.relevant_exp_aftr_join)
                        sheet_exit.write(count_e, 6, pl)
                        sheet_exit.write(count_e, 7, so)
                        sheet_exit.write(count_e, 8, ab)
                        sheet_exit.write(count_e, 9, -(sum(upl)))
                        sheet_exit.write(count_e, 10, (so + ab + up))
                        sheet_exit.write(count_e, 11, gratuity)
                        sheet_exit.write(count_e, 12, employee.gender.capitalize())
                        sheet_exit.write(count_e, 13, employee.is_technical)
                        sheet_exit.write(count_e, 14, responsible_hr)
                        sheet_exit.write(count_e, 15, insurance)
                        sheet_exit.write(count_e, 16, ins_type)
                        count_e += 1

    def generate_xlsx_report(self, workbook, data, lines):
        # get data from wizard
        sheet_new_joinee = workbook.add_worksheet("New Joniee Payroll Summary")
        sheet_exit = workbook.add_worksheet("Exit Employee Summary")
        sheet_pf = workbook.add_worksheet("New Joinee PF Summary")
        bold = workbook.add_format({'bold': True, 'border': 1})
        from_date = data.get('form')['from_date']
        to_date = data.get('form')['to_date']
        from_date = fields.Date.from_string(str(from_date))
        to_date = fields.Date.from_string(str(to_date))
        mode = data.get('form')['mode']
        category = data.get('form')['emp_category']
        location = data.get('form')['emp_work_location']
        payroll_loc = data.get('form')['emp_payroll_loc']
        responsible_hr = data.get('form').get('responsible_hr')
        for_client = data.get('form').get('is_for_client')
        employee = data.get('form').get('mode_employee_id')
        company = data.get('form').get('mode_company_id')
        department = data.get('form').get('mode_department_id')
        holiday_type = data.get('form').get('holiday_type')
        if mode == 'employee' and employee:
            if category and location and payroll_loc:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.id=%s AND emp.employee_category=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', (employee[0], category[0], location[0], payroll_loc[0]))
                employees = self._cr.fetchall()
            elif category and payroll_loc:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.id=%s AND emp.employee_category=%s AND emp.payroll_loc=%s''', (employee[0], category[0], payroll_loc[0]))
                employees = self._cr.fetchall()
            elif payroll_loc and location:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.id=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', (employee[0], location[0], payroll_loc[0]))
                employees = self._cr.fetchall()
            elif category and location:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.id=%s AND emp.employee_category=%s AND emp.location_work=%s''', (employee[0], category[0], location[0]))
                employees = self._cr.fetchall()
            elif category:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.id=%s AND emp.employee_category=%s''', (employee[0], category[0]))
                employees = self._cr.fetchall()
            elif location:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.id=%s AND emp.location_work=%s''', (employee[0], location[0]))
                employees = self._cr.fetchall()
            elif payroll_loc:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.id=%s AND emp.payroll_loc=%s''', (employee[0], payroll_loc[0]))
                employees = self._cr.fetchall()
            else:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.id=%s''', ([employee[0]]))
                employees = self._cr.fetchall()
        elif mode == 'company' and company:
            if category and location and payroll_loc:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.company_id = %s AND emp.employee_category=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', ((company[0], category[0], location[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif category and payroll_loc:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.company_id = %s AND emp.employee_category=%s AND emp.payroll_loc=%s''', ((company[0], category[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif payroll_loc and location:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.company_id = %s AND emp.location_work=%s AND emp.payroll_loc=%s''', ((company[0], location[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif category and location:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.company_id = %s AND emp.employee_category=%s AND emp.location_work=%s''', ((company[0], category[0], location[0])))
                employees = self._cr.fetchall()
            elif category:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.company_id = %s AND emp.employee_category=%s''', ((company[0], category[0])))
                employees = self._cr.fetchall()
            elif location:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.company_id = %s AND emp.location_work=%s''', ((company[0], location[0])))
                employees = self._cr.fetchall()
            elif payroll_loc:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.company_id = %s AND emp.payroll_loc=%s''', ((company[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            else:
                self._cr.execute('''
                    SELECT id
                    FROM hr_employee as emp
                    WHERE emp.company_id = %s''', (([company[0]])))
                employees = self._cr.fetchall()
        elif mode == 'department'and department:
            if category and location and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc
                    FROM hr_employee as emp
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    WHERE emp.department_id = %s AND emp.employee_category=%s AND emp.location_work=%s AND emp.payroll_loc=%s''', ((department[0], category[0], location[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif category and payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc
                    FROM hr_employee as emp
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    WHERE emp.department_id = %s AND emp.employee_category=%s AND emp.payroll_loc=%s''', ((department[0], category[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif payroll_loc and location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc
                    FROM hr_employee as emp
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    WHERE emp.department_id = %s AND emp.location_work=%s AND emp.payroll_loc=%s''', ((department[0], location[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            elif category and location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc
                    FROM hr_employee as emp
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    WHERE emp.department_id = %s AND emp.employee_category=%s AND emp.location_work=%s''', ((department[0], category[0], location[0])))
                employees = self._cr.fetchall()
            elif category:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc
                    FROM hr_employee as emp
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    WHERE emp.department_id = %s AND emp.employee_category=%s''', ((department[0], category[0])))
                employees = self._cr.fetchall()
            elif location:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc
                    FROM hr_employee as emp
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    WHERE emp.department_id = %s AND emp.location_work=%s''', ((department[0], location[0])))
                employees = self._cr.fetchall()
            elif payroll_loc:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc
                    FROM hr_employee as emp
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    WHERE emp.department_id = %s AND emp.payroll_loc=%s''', ((department[0], payroll_loc[0])))
                employees = self._cr.fetchall()
            else:
                self._cr.execute('''
                    SELECT emp.id,emp.name,identification_id,job.name,dept.name,emp.parent_id,location_work,emp.active,emp.exit_date,emp.work_email,emp.joining_date,emp.payroll_loc
                    FROM hr_employee as emp
                    LEFT JOIN hr_job as job on job.id = emp.job_id
                    LEFT JOIN hr_department as dept on dept.id = emp.department_id 
                    WHERE emp.department_id = %s''', (([department[0]])))
                employees = self._cr.fetchall()

        # new joinee report summary header
        sheet_new_joinee.write(0, 0, 'Employee Number', bold)
        sheet_new_joinee.write(0, 1, 'Gender -M/F', bold)
        sheet_new_joinee.write(0, 2, 'Display Name', bold)
        sheet_new_joinee.write(0, 3, 'Fathers/Husband Name', bold)
        sheet_new_joinee.write(0, 4, 'EmpRelation', bold)
        sheet_new_joinee.write(0, 5, 'Technical/ Non technical', bold)
        sheet_new_joinee.write(0, 6, 'LWF applicability (Y/N)', bold)
        sheet_new_joinee.write(0, 7, 'Marital Status (B/S/M/W)', bold)
        sheet_new_joinee.write(0, 8, 'Present Address 1', bold)
        sheet_new_joinee.write(0, 9, 'Present City', bold)
        sheet_new_joinee.write(0, 10, 'Present State', bold)
        sheet_new_joinee.write(0, 11, 'Present Pincode', bold)
        sheet_new_joinee.write(0, 12, 'Present Phone', bold)
        sheet_new_joinee.write(0, 13, 'Permanent Address 1', bold)
        sheet_new_joinee.write(0, 14, 'Permanent City', bold)
        sheet_new_joinee.write(0, 15, 'Permanent State', bold)
        sheet_new_joinee.write(0, 16, 'Permanent Pincode', bold)
        sheet_new_joinee.write(0, 17, 'Permanent Phone', bold)
        sheet_new_joinee.write(0, 18, 'Primary Bank Code', bold)
        sheet_new_joinee.write(0, 19, 'Primary IFSC', bold)
        sheet_new_joinee.write(0, 20, 'Primary Bank A/c No', bold)
        sheet_new_joinee.write(0, 21, 'Secondary Bank Code', bold)
        sheet_new_joinee.write(0, 22, 'Secondary IFSC', bold)
        sheet_new_joinee.write(0, 23, 'Secondary Bank A/c No', bold)
        sheet_new_joinee.write(0, 24, 'Payroll Code', bold)
        sheet_new_joinee.write(0, 25, 'Date Of Joining', bold)
        sheet_new_joinee.write(0, 26, 'Date Of Birth', bold)
        sheet_new_joinee.write(0, 27, 'Designation', bold)
        sheet_new_joinee.write(0, 28, 'Leave Approver', bold)
        sheet_new_joinee.write(0, 29, 'Permanent A/c No.', bold)
        sheet_new_joinee.write(0, 30, 'Blood Group', bold)
        sheet_new_joinee.write(0, 31, 'Emergency Phone No.', bold)
        sheet_new_joinee.write(0, 32, 'Emergency Contact Person', bold)
        sheet_new_joinee.write(0, 33, 'Email ID', bold)
        sheet_new_joinee.write(0, 34, 'Personal Email ID', bold)
        sheet_new_joinee.write(0, 35, 'Reports To Emp', bold)
        sheet_new_joinee.write(0, 36, 'Passport No', bold)
        sheet_new_joinee.write(0, 37, 'Passport Validity (YYYY-MM-DD)', bold)
        sheet_new_joinee.write(0, 38, 'Mobile No', bold)
        sheet_new_joinee.write(0, 39, 'Aadhaar Card No', bold)
        sheet_new_joinee.write(0, 40, 'UAN', bold)
        sheet_new_joinee.write(0, 41, 'PF', bold)
        sheet_new_joinee.write(0, 42, 'ESIC', bold)
        sheet_new_joinee.write(0, 43, 'Paytm', bold)
        sheet_new_joinee.write(0, 44, 'Paytm Amount', bold)
        sheet_new_joinee.write(0, 45, 'Paytm Number', bold)
        sheet_new_joinee.write(0, 46, 'LTC', bold)
        sheet_new_joinee.write(0, 47, 'Transfer/Withdrawal Status', bold)
        sheet_new_joinee.write(0, 48, 'Annual CTC Fixed', bold)
        sheet_new_joinee.write(0, 49, 'Bonus Component ', bold)
        sheet_new_joinee.write(0, 50, 'Responsible HR', bold)

        #exit report header
        sheet_exit.write(0, 0, 'Employee code', bold)
        sheet_exit.write(0, 1, 'Display Name', bold)
        sheet_exit.write(0, 2, 'Payroll Code', bold)
        sheet_exit.write(0, 3, 'DOJ (YYYY-MM-DD)', bold)
        sheet_exit.write(0, 4, 'Last working date (YYYY-MM-DD)', bold)
        sheet_exit.write(0, 5, 'Total Expereince', bold)
        sheet_exit.write(0, 6, 'Remaining PL', bold)
        sheet_exit.write(0, 7, 'Sandwich WO', bold)
        sheet_exit.write(0, 8, 'Absent', bold)
        sheet_exit.write(0, 9, 'Unpaid Leave', bold)
        sheet_exit.write(0, 10, 'Non Payable Days', bold)
        sheet_exit.write(0, 11, 'Gratuity Applicable', bold)
        sheet_exit.write(0, 12, 'Gender-M/F', bold)
        sheet_exit.write(0, 13, 'Technical/Non-Technical', bold)
        sheet_exit.write(0, 14, 'Responsible HR', bold)
        sheet_exit.write(0, 15, 'Parental Insurance', bold)
        sheet_exit.write(0, 16, 'Insurance Type', bold)

        # new joinee pf summary header
        sheet_pf.write(0, 0, 'EMP ID', bold)
        sheet_pf.write(0, 1, 'UAN NUMBER ALLOTTED BY OUR ESTABLISHMENT', bold)
        sheet_pf.write(0, 2, 'DISPLAY NAME', bold)
        sheet_pf.write(0, 3, 'Fathers/Husband Name', bold)
        sheet_pf.write(0, 4, 'SPECIFY RELATIONSHIP MENTIONED COLUMN D Father/Husband (F/H)', bold)
        sheet_pf.write(0, 5, 'DOB', bold)
        sheet_pf.write(0, 6, 'Gender', bold)
        sheet_pf.write(0, 7, 'DOJ', bold)
        sheet_pf.write(0, 8, 'WHETHER EARLIER MEMBER OF PF', bold)
        sheet_pf.write(0, 9, 'IF No PF ACCOUNT, DO YOU WANT TO OPT FOR PF ACCOUNT?', bold)
        sheet_pf.write(0, 10, 'MONTHLY BASIC ( PF WAGES RATE)', bold)
        sheet_pf.write(0, 11, 'MARITAL STATUS', bold)
        sheet_pf.write(0, 12, 'NATIONALITY', bold)
        sheet_pf.write(0, 13, 'PERSONAL BANK A/C NUMBER', bold)
        sheet_pf.write(0, 14, 'IFSC CODE OF THE BANK', bold)
        sheet_pf.write(0, 15, 'NAME AS PER BANK RECORDS', bold)
        sheet_pf.write(0, 16, 'PAN NUMBER', bold)
        sheet_pf.write(0, 17, 'NAME AS PER PAN CARD', bold)
        sheet_pf.write(0, 18, 'AADHAR NUMBER', bold)
        sheet_pf.write(0, 19, 'NAME AS PER AADHAR CARD', bold)
        sheet_pf.write(0, 20, 'PASSPORT NO.', bold)
        sheet_pf.write(0, 21, 'PASSPORT ISSUE DATE', bold)
        sheet_pf.write(0, 22, 'PASSPORT VALID UPTO', bold)
        sheet_pf.write(0, 23, 'PASSPORT ISSUED COUNTRY NAME', bold)
        sheet_pf.write(0, 24, 'UAN NUMBER ALLOTED AT PREVIOUS ESTABLISHMENT', bold)
        sheet_pf.write(0, 25, 'DATE OF LEAVING OF PREVIOUS ESTABLISHMENT', bold)
        sheet_pf.write(0, 26, 'PREVIOUS EPF NUMBER', bold)
        sheet_pf.write(0, 27, 'PREVIOUS PENSION FUND NUMBER', bold)
        sheet_pf.write(0, 28, 'ADDRESS OF PF OFFICE WHERE PREVIOUS PF IS MAINTAINED', bold)
        sheet_pf.write(0, 29, 'WHETHER FIRST SERVICE IN INDIA', bold)
        sheet_pf.write(0, 30, 'FORM IS CORRECT/NOT CORRECT', bold)
        sheet_pf.write(0, 31, 'IF NOT CORRECT THEN REMARKS', bold)
        sheet_pf.write(0, 32, 'PERSONAL MOBILE NO- Mobile No. on which formal communication can be established & necessary information can be provided through SMS to the Employee by EPF Office', bold)
        sheet_pf.write(0, 33, 'PERSONAL Email ID', bold)
        sheet_pf.write(0, 34, 'Responsible HR', bold)

        sheet_pf.write(1, 1, '(MANDATORY)', bold)
        sheet_pf.write(1, 2, '(MANDATORY)', bold)
        sheet_pf.write(1, 3, '(MANDATORY)', bold)
        sheet_pf.write(1, 4, '(MANDATORY)', bold)
        sheet_pf.write(1, 5, '(MANDATORY)', bold)
        sheet_pf.write(1, 6, '(MANDATORY)', bold)
        sheet_pf.write(1, 7, '(MANDATORY)', bold)
        sheet_pf.write(1, 8, '(MANDATORY)', bold)
        sheet_pf.write(1, 9, '(MANDATORY)', bold)
        sheet_pf.write(1, 10, '(MANDATORY)', bold)
        sheet_pf.write(1, 11, '(MANDATORY)', bold)
        sheet_pf.write(1, 12, '(MANDATORY)', bold)
        sheet_pf.write(1, 13, '(MANDATORY)', bold)
        sheet_pf.write(1, 14, '(MANDATORY)', bold)
        sheet_pf.write(1, 15, '(MANDATORY)', bold)
        sheet_pf.write(1, 16, '(MANDATORY)', bold)
        sheet_pf.write(1, 17, '(MANDATORY)', bold)
        sheet_pf.write(1, 18, '(MANDATORY)', bold)
        sheet_pf.write(1, 19, '(MANDATORY IF INTERNATIONAL WORKER)', bold)
        sheet_pf.write(1, 20, '(MANDATORY IF INTERNATIONAL WORKER)', bold)
        sheet_pf.write(1, 21, '(MANDATORY IF INTERNATIONAL WORKER)', bold)
        sheet_pf.write(1, 22, '(MANDATORY IF INTERNATIONAL WORKER)', bold)
        sheet_pf.write(1, 23, '(MANDATORY IF INTERNATIONAL WORKER)', bold)
        sheet_pf.write(1, 24, '(MANDATORY IF INTERNATIONAL WORKER)', bold)
        sheet_pf.write(1, 25, '(MANDATORY IF INTERNATIONAL WORKER)', bold)
        sheet_pf.write(1, 26, '(MANDATORY IF INTERNATIONAL WORKER)', bold)

        if not for_client:
            self._get_new_joinee_record(employees, from_date, to_date, sheet_new_joinee, sheet_exit, sheet_pf, holiday_type, responsible_hr)
