# -*- coding: utf-8 -*-
import logging
from pytz import timezone
from datetime import date, timedelta, datetime, time
from dateutil.relativedelta import relativedelta
from collections import OrderedDict
from odoo import models, api, fields, _
_logger = logging.getLogger(__name__)

class UtilizationReportXlsx(models.AbstractModel):
    _name = 'report.project_role.report_utilization_data_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Report Utilization Xlsx'

    def _get_report_header(self, sheet, bold):
        sheet.write(0, 0, 'e-Zestian ID', bold)
        sheet.write(0, 1, 'Name', bold)
        sheet.write(0, 2, 'e-Zestian BU', bold)
        sheet.write(0, 3, 'Group Customer', bold)
        sheet.write(0, 4, 'Customer', bold)
        sheet.write(0, 5, 'Project', bold)
        sheet.write(0, 6, 'Project Whizible ID', bold)
        sheet.write(0, 7, 'Project Unity ID', bold)
        sheet.write(0, 8, 'Project BU', bold)
        sheet.write(0, 9, 'BU Head', bold)
        sheet.write(0, 10, 'Delivery Geo', bold)
        sheet.write(0, 11, 'Effective Delivery Geo', bold)
        sheet.write(0, 12, 'Team Member Category', bold)
        sheet.write(0, 13, 'Effect Team Member Category', bold)
        sheet.write(0, 14, 'Deployability', bold)
        sheet.write(0, 15, 'Billing Geo', bold)
        sheet.write(0, 16, 'Customer Geo', bold)
        sheet.write(0, 17, 'Engagement Model', bold)
        sheet.write(0, 18, 'Effective Engagement Model', bold)
        sheet.write(0, 19, 'Onsite/Offshore', bold)
        sheet.write(0, 20, 'Effective Onsite/Offshore', bold)
        sheet.write(0, 21, 'Allocation%', bold)
        sheet.write(0, 22, 'Effective Allocation%', bold)
        sheet.write(0, 23, 'Effective Hours', bold)
        sheet.write(0, 24, 'Standard Hours', bold)
        sheet.write(0, 25, 'Billed Hours', bold)
        sheet.write(0, 26, 'Inter company HC', bold)
        sheet.write(0, 27, 'Inter company Cost USD', bold)
        sheet.write(0, 28, 'Inter Company Revenue USD', bold)
        sheet.write(0, 29, 'Effective Cost USD', bold)
        sheet.write(0, 30, 'Cost USD', bold)
        sheet.write(0, 31, 'Revenue USD', bold)
        sheet.write(0, 32, 'Accrued Revenue USD', bold)
        sheet.write(0, 33, 'Billability', bold)
        sheet.write(0, 34, 'Effective Billability', bold)
        sheet.write(0, 35, 'Line Of Services', bold)
        sheet.write(0, 36, 'Effective Lines of Services', bold)
        sheet.write(0, 37, 'Tech Areas', bold)
        sheet.write(0, 38, 'Industry', bold)
        sheet.write(0, 39, 'Sub-Industry', bold)
        sheet.write(0, 40, 'Remarks', bold)
        sheet.write(0, 41, 'Sales Person', bold)
        sheet.write(0, 42, 'Total Experience of e-Zestian', bold)
        sheet.write(0, 43, 'Date of Joining', bold)
        sheet.write(0, 44, 'Release Date', bold)
        sheet.write(0, 45, 'Start Date', bold)
        sheet.write(0, 46, 'End Date', bold)
        sheet.write(0, 47, 'Rate per person', bold)
        sheet.write(0, 48, 'Rate data', bold)
        sheet.write(0, 49, 'TCV($)', bold)

    def _get_report_header_without_alloc(self, sheet, bold):
        sheet.write(0, 0, 'Project Name', bold)
        sheet.write(0, 1, 'Whizible ID', bold)
        sheet.write(0, 2, 'Unity ID', bold)
        sheet.write(0, 3, 'Company', bold)
        sheet.write(0, 4, 'Billing Location', bold)
        sheet.write(0, 5, 'Start Date', bold)

    def _get_report_body_without_alloc(self, sheet):
        projects = self.env['project.project'].sudo().search([('state', '=', 'active')])
        projects = projects.filtered(lambda proj: not proj.assignment_ids)
        row_count = 1
        for project in projects:
            sheet.write(row_count, 0, project.name)
            sheet.write(row_count, 1, project.whizible_id)
            sheet.write(row_count, 2, project.name_seq)
            sheet.write(row_count, 3, project.company_id.name)
            sheet.write(row_count, 4, project.payroll_loc.name)
            sheet.write(row_count, 5, str(project.actual_start_date))
            row_count += 1

    def _get_effective_alloc(self, i, admin, alloc_month, from_date, to_date, tz):
        if i.start_date and i.start_date < from_date:
            date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
        else:
            date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(i.start_date)), time.min))
        if i.end_date and i.end_date > to_date:
            date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.min))
        else:
            date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(i.end_date)), time.min))
        # localize_from_date = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
        # localize_to_date = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.min))
        # standard_working_days = admin.list_work_time_per_day(localize_from_date, localize_to_date, calendar=admin.resource_calendar_id)
        if date_from == date_to and date_from.date().weekday() not in [5, 6]:
            working_days = 1
            effective_alloc_per_user = (i.allocation_percentage * (working_days * 8)) / 100
        else:
            working_days = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
            effective_alloc_per_user = (i.allocation_percentage * (len(working_days) * 8)) / 100
        return effective_alloc_per_user

    def _get_report_body(self, sheet, number_format, month, year, save_report):
        # allocation = self.env['project.assignment'].sudo().search([('assign_status', '=', 'confirmed')]).filtered(lambda alloc: alloc.end_date.month >= int(month) and alloc.end_date.year >= year.name)
        # employees = list(set([i.employee_id for i in allocation]))
        today = fields.Date.today()
        from_date = today + relativedelta(month=int(month), day=1, year=year.name)
        to_date = today + relativedelta(month=int(month), day=31, year=year.name)
        saved_utilization = new_utilization = False
        utilization_line = []
        saved_data = self.env['project.team.utilization'].search([('from_date', '=', from_date), ('to_date', '=', to_date)])
        if saved_data:
            saved_utilization = saved_data
            saved_utilization.utilization_line = [(5, 0, 0)]
        elif save_report:
            new_utilization = self.env['project.team.utilization'].create({'from_date': from_date, 'to_date': to_date})
            # new_utilization.utilization_line = [(0, 0, {})]
        allocations = self.env['project.assignment'].search([('assign_status', '=', 'confirmed')], order='project_id asc')
        allocations = allocations.filtered(lambda alloc: ((from_date <= alloc.start_date and to_date >= alloc.start_date) or (from_date <= alloc.end_date and to_date >= alloc.end_date) or (alloc.start_date <= to_date and alloc.end_date >= to_date)))
        avg_ptp_amount = 0.0
        allocation_on_ptp = allocations.filtered(lambda a: 'PTP' in a.project_id.name)
        allocation_on_ptp_list = []
        for i in allocation_on_ptp:
            duplicate_proj = [d for d in allocation_on_ptp_list if d.project_id.id == i.project_id.id]
            if duplicate_proj and i.employee_id.id in [e.employee_id.id for e in duplicate_proj]:
                pass
            else:
                allocation_on_ptp_list.append(i)
        sale_line = self.env['sale.order.line'].search([('date_target', '>=', from_date), ('date_target', '<=', to_date), ('display_type', '!=', 'line_section')])
        sale_line_fc = sale_line.filtered(lambda y: (y.order_id.group_multi_company or y.order_id.contract_sign_id.id == y.order_id.company_sign_id.id) and y.price_subtotal > 0 and y.order_id.state not in ['cancel', 'sent', 'draft'] and y.employee_id.name != 'Unity')
        sale_line = sale_line.filtered(lambda x: (x.order_id.group_multi_company or x.order_id.contract_sign_id.id == x.order_id.company_sign_id.id) and x.order_id.state not in ['draft', 'sent', 'cancel'])
        # fc_amount = []
        # for line in sale_line_fc:
        #     if not line.order_id.project_id.assignment_ids.filtered(lambda alloc: ((from_date <= alloc.start_date and to_date >= alloc.start_date) or (from_date <= alloc.end_date and to_date >= alloc.end_date) or (alloc.start_date <= to_date and alloc.end_date >= to_date))):
        #         fc_amount.append(line.amount_inr)
        # fc_amount = sum(fc_amount) if fc_amount else 0.0
        # sale_amount = [line.amount_inr for line in sale_line if line.employee_id.name == 'Unity' or line.employee_id is False]
        # if sale_amount:
        #     sale_amount = sum(sale_amount)
        #     sale_amount = sale_amount + fc_amount
        #     avg_ptp_amount = sale_amount / len(allocation_on_ptp_list) if len(allocation_on_ptp_list) else 0.0
        # else:
        #     avg_ptp_amount = fc_amount / len(allocation_on_ptp_list) if len(allocation_on_ptp_list) else 0.0
        employees = self.env['hr.employee'].sudo().search([('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']), ('joining_date', '!=', False), ('active', '=', True)])
        remain_emp = [i for i in employees if i.id not in allocations.mapped('employee_id.id') and i.joining_date <= to_date]
        admin = self.env['hr.employee'].search([('id', '=', 1)])
        tz = timezone(admin.resource_calendar_id.tz)
        total_days = to_date.day
        row_count = 1
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')])
        usd_date = [i.rate for i in usd_currency.rate_ids if i.name and i.end_date and to_date and to_date >= i.name and to_date <= i.end_date]
        usd_rate = usd_date[0] if len(usd_date) else usd_currency.rate
        non_revenue_allocation = []
        revenue_allocation = []
        duplicate_alloc = []
        for alloc in allocations:
            same_alloc = [i for i in allocations if i.employee_id.id == alloc.employee_id.id]
            # if len(same_alloc) > 1:
            if alloc.start_date and alloc.start_date < from_date:
                date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
            else:
                date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(alloc.start_date)), time.min))
            if alloc.end_date and alloc.end_date > to_date:
                date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.min))
            else:
                date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(alloc.end_date)), time.min))
            localize_from_date = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
            localize_to_date = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.min))
            standard_working_days = admin.list_work_time_per_day(localize_from_date, localize_to_date, calendar=admin.resource_calendar_id)
            if date_from == date_to and date_from.date().weekday() not in [5, 6]:
                working_days = 1
                effective_alloc_per = (alloc.allocation_percentage * (working_days * 8)) / (len(standard_working_days) * 8) if len(standard_working_days) else alloc.allocation_percentage * ((working_days) * 8)
                effective_alloc_per_month = (alloc.allocation_percentage * (working_days * 8)) / 100
            else:
                working_days = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
                effective_alloc_per = (alloc.allocation_percentage * (len(working_days) * 8)) / (len(standard_working_days) * 8)
                effective_alloc_per_month = (alloc.allocation_percentage * (len(working_days) * 8)) / 100
            # else:
            #     if alloc.employee_id.joining_date and alloc.employee_id.joining_date >= from_date:
            #         date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(alloc.employee_id.joining_date)), time.min))
            #     else:
            #         date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
            #     if alloc.employee_id.exit_date and alloc.employee_id.exit_date <= to_date:
            #         date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(alloc.employee_id.exit_date)), time.min))
            #     else:
            #         date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.min))
            #     working_days = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
            #     effective_alloc_per = alloc.allocation_percentage
            revenue_inr = 0.0
            effective_emp_wage = 0.0
            effective_working_days = 0.0
            effective_categ = ''
            effective_delivery_geo = ''
            effective_engagmnt_model = ''
            effective_onshore = ''
            effective_billability = ''
            effective_lob = ''
            if alloc.project_id.payroll_loc and alloc.project_id.payroll_loc.name in ['Austria Branch Office', 'GMBH Payroll']:
                effective_delivery_geo = 'EU'
            elif alloc.project_id.payroll_loc and alloc.project_id.payroll_loc.name == 'Inc USA':
                effective_delivery_geo = 'USA'
            elif alloc.project_id.payroll_loc and alloc.project_id.payroll_loc.name in ['KTH', 'SEZ 3', 'SEZ 6']:
                effective_delivery_geo = 'India'
            if alloc.employee_id.employee_category and alloc.employee_id.employee_category.name == 'eZestian':
                effective_categ = 'Employee'
            elif alloc.employee_id.employee_category and alloc.employee_id.employee_category.name == 'Contractor':
                effective_categ = 'Consultant'
            if alloc.project_id.sale_order_id.commercial_details and alloc.project_id.sale_order_id.commercial_details == 'fixed_cost':
                effective_engagmnt_model = 'Project - Fixed Price'
            elif alloc.project_id.sale_order_id.commercial_details and alloc.project_id.sale_order_id.commercial_details == 'tnm':
                effective_engagmnt_model = 'Project - T&M'
            if alloc.project_id.project_location and alloc.project_id.project_location.name in ['Offshore', 'India client side']:
                effective_onshore = 'Offshore'
            elif alloc.project_id.project_location and alloc.project_id.project_location.name == 'On-site':
                effective_onshore = 'On-site'
            if alloc.project_bill_status in [100, 50, 25]:
                effective_billability = 'Billable'
            elif alloc.project_bill_status in ['0_unbilled', '0_unbilled_buffer', '0_unbilled_shadow']:
                effective_billability = 'Non Billable'
            if alloc.project_id.sale_order_id.lob and alloc.project_id.sale_order_id.lob.name == 'Big Data Analytics AI':
                effective_lob = 'Data Science & AI/ML'
            elif alloc.project_id.sale_order_id.lob and alloc.project_id.sale_order_id.lob.name == 'Business Process Management':
                effective_lob = 'Application Monitoring & Support'
            elif alloc.project_id.sale_order_id.lob and alloc.project_id.sale_order_id.lob.name == 'Data Engineering':
                effective_lob = 'Data Analytics & Insights'
            elif alloc.project_id.sale_order_id.lob and alloc.project_id.sale_order_id.lob.name == 'Digital Applications ':
                effective_lob = 'Product Design & Engg'
            elif alloc.project_id.sale_order_id.lob and alloc.project_id.sale_order_id.lob.name == 'Digital Commerce':
                effective_lob = 'Digital Commerce'
            elif alloc.project_id.sale_order_id.lob and alloc.project_id.sale_order_id.lob.name == 'Managed Cloud AND DevOps':
                effective_lob = 'Cloud & Infra Modernization'
            elif alloc.project_id.sale_order_id.lob and alloc.project_id.sale_order_id.lob.name == 'Tech Modernization':
                effective_lob = 'Tech Modernization'
            elif alloc.project_id.sale_order_id.lob and alloc.project_id.sale_order_id.lob.name == 'Digital Operations':
                effective_lob = 'Application Monitoring & Support'
            if alloc.employee_id.emp_wage:
                inr_rate = [i.rate for i in alloc.employee_id.company_id.currency_id.rate_ids if i.name and i.end_date and to_date and to_date >= i.name and to_date <= i.end_date]
                inr_rate1 = alloc.employee_id.emp_wage * inr_rate[0] if alloc.employee_id.emp_wage and inr_rate else 0.0
                emp_wage = inr_rate1 / usd_rate
                effective_emp_wage = emp_wage    
                if len(same_alloc) > 1:
                    effective_emp_wage_calc = (effective_alloc_per * alloc.employee_id.emp_wage) / 100
                    effective_emp_wage_inr = effective_emp_wage_calc * inr_rate[0] if inr_rate else 0.0
                    effective_emp_wage = effective_emp_wage_inr / usd_rate
                less_join = False
                if alloc.employee_id.joining_date and alloc.employee_id.joining_date > from_date:
                    less_join = True
                    wage_date_from = alloc.employee_id.joining_date
                else:
                    wage_date_from = from_date
                if alloc.employee_id.exit_date and alloc.employee_id.exit_date < to_date:
                    less_join = True
                    wage_date_to = alloc.employee_id.exit_date
                else:
                    wage_date_to = to_date
                if less_join:
                    diff_days = wage_date_to - wage_date_from
                    diff_days = diff_days.days + 1
                    per_day_cost = alloc.employee_id.emp_wage / to_date.day
                    total_cost = per_day_cost * diff_days
                    total_cost_inr = total_cost * inr_rate[0] if inr_rate else 0.0
                    total_cost_usd = total_cost_inr / usd_rate
                    effective_emp_wage = total_cost_usd
            else:
                emp_wage = 0.0
            alloc_timesheet = self.env['account.analytic.line'].search([('employee_id', '=', alloc.employee_id.id), ('state', '!=', 'reject'), ('project_id', '=', alloc.project_id.id)]).filtered(lambda tim: tim.date >= from_date and tim.date <= to_date)
            worked_hours = sum(alloc_timesheet.mapped('unit_amount'))
            order = alloc.project_id.sale_order_id
            # if 'PTP' in alloc.project_id.name:
            #     revenue_inr = avg_ptp_amount / usd_rate
            # else:
            order_line = order.order_line.filtered(lambda ol: ol.offering_type == 'tnm' and ol.date_target and ol.start_date and ol.date_target >= from_date and ol.date_target <= to_date and ol.employee_id.id == alloc.employee_id.id)
            # if order_line and sum(order_line.mapped('invoice_amount_inr')) != 0.0:
            #     revenue_inr = sum(order_line.mapped('invoice_amount_inr')) if order_line else 0.0
            # else:
            revenue_inr = sum(order_line.mapped('amount_inr')) if order_line else 0.0
            revenue_inr = revenue_inr / usd_rate
            standard_hours = len(working_days) * 8 if isinstance(working_days, list) else (working_days * 8)
            effective_working_days = (standard_hours * effective_alloc_per) / 100
            if not order_line:
                # order_line = order.order_line.filtered(lambda ol: ol.offering_type == 'fixed_cost' and ol.date_target and ol.start_date and ((ol.start_date <= from_date and ol.date_target >= to_date) or (ol.start_date >= from_date and ol.date_target <= to_date) or (ol.date_target >= from_date and ol.date_target <= to_date)))
                order_line = order.order_line.filtered(lambda ol: ol.offering_type == 'fixed_cost' and ol.date_target and ol.start_date and ol.date_target >= from_date and ol.date_target <= to_date)
                order_line1 = order_line[0] if len(order_line) > 1 else order_line
                # revenue_inr = order_line.amount_inr if order_line else 0.0
                if order_line1.date_target and order_line1.start_date and order_line1.date_target == order_line1.start_date:
                    milestone_days = to_date.day
                elif order_line1.date_target and order_line1.date_target and order_line1.date_target >= to_date and order_line1.start_date <= from_date:
                    milestone_days = to_date.day
                elif order_line1.date_target and order_line1.date_target and order_line1.date_target < to_date and order_line1.start_date <= from_date:
                    milestone_days = order_line1.date_target.day
                elif order_line1.date_target and order_line1.date_target and order_line1.date_target > to_date and order_line1.start_date > from_date:
                    milestone_days = (to_date - order_line1.start_date).days + 1
                elif order_line1.date_target and order_line1.date_target and order_line1.date_target < to_date and order_line1.start_date > from_date:
                    milestone_days = (order_line1.date_target - order_line1.start_date).days + 1
                else:
                    milestone_days = to_date.day
                # if order_line.invoice_amount_inr != 0.0:
                #     milestone_amnt = order_line.invoice_amount_inr
                # else:
                milestone_amnt = order_line.mapped('amount_inr')
                milestone_amnt = sum(milestone_amnt) if milestone_amnt else 0.0
                team_size = self.env['project.assignment'].search([('project_id', '=', order_line1.order_id.project_id.id), ('assign_status', '=', 'confirmed')])
                team_size = team_size.filtered(lambda assgn: (assgn.start_date <= from_date and assgn.end_date >= to_date) or (assgn.end_date >= from_date and assgn.end_date <= to_date) or (assgn.start_date >= from_date and assgn.start_date <= to_date))
                team_size_list = []
                for i in team_size:
                    if i.employee_id.id in [j.employee_id.id for j in team_size_list]:
                        pass
                    else:
                        team_size_list.append(i)
                # if order_line.invoice_amount_inr != 0.0:
                #     revenue_inr = order_line.invoice_amount_inr if order_line else 0.0
                # else:
                revenue_inr = order_line.mapped('amount_inr') if order_line else 0.0
                revenue_inr = sum(revenue_inr) / usd_rate if revenue_inr else 0.0
                if order_line and team_size_list:
                    # if len(alloc_timesheet):
                    #     revenue_inr = ((total_days / milestone_days) * milestone_amnt) * (len(alloc_timesheet) / (len(working_days)*8)) / len(team_size)
                    # else:
                    # revenue_inr = ((total_days / milestone_days) * milestone_amnt) / len(team_size_list)
                    revenue_inr = (milestone_amnt) / len(team_size_list)
                    revenue_inr = revenue_inr / usd_rate
            # if revenue_inr:
            # alloc_project = False
            # for i in revenue_allocation:
            #     if i.get(alloc.project_id.id):
            #         i[alloc.project_id.id].append(revenue_inr)
            #         alloc_project = True
            # if not alloc_project:
            #     revenue_allocation.append({alloc.project_id.id: [revenue_inr]})
            accured_rev = ''
            alloc_month = order.project_id.assignment_ids.filtered(lambda allo: allo.assign_status == 'confirmed' and ((from_date <= allo.start_date and to_date >= allo.start_date) or (from_date <= allo.end_date and to_date >= allo.end_date) or (allo.start_date <= to_date and allo.end_date >= to_date)))
            effective_alloc = []
            for i in alloc_month:
                effective_alloc_per_user = self._get_effective_alloc(i, admin, alloc_month, from_date, to_date, tz)
                effective_alloc.append(effective_alloc_per_user)
            effect_alloc_month = sum(effective_alloc)
            effective_alloc_all = []
            alloc_total_month = order.project_id.assignment_ids.filtered(lambda allo: allo.assign_status == 'confirmed')
            for j in alloc_total_month:
                effective_alloc_all.append(j.project_efforts)
            effect_alloc_total = sum(effective_alloc_all)
            
            revenue_month = order.amount_inr * effect_alloc_month / effect_alloc_total if effect_alloc_total else 0.0
            revenue_per_person = revenue_month * effective_alloc_per_month / effect_alloc_month if effect_alloc_month else 0.0
            accured_rev = revenue_per_person / usd_rate

            duplicate_proj = [d for d in duplicate_alloc if d.project_id.id == alloc.project_id.id]
            same_project = [p for p in duplicate_alloc if p.project_id.name == alloc.project_id.name and p.project_id.company_id.name != alloc.project_id.company_id.name]
            if (duplicate_proj and alloc.employee_id.id in [e.employee_id.id for e in duplicate_proj]) or (same_project):
                pass
            else:
                utilization_line.append({
                    'employee_id': alloc.employee_id.name,
                    'emp_code': alloc.employee_id.identification_id,
                    'customer_id': alloc.project_id.partner_id.id,
                    'project_id': alloc.project_id.id,
                    'bu_head': alloc.project_id.department_id.name,
                    'engagement_model': alloc.project_id.sale_order_id.commercial_details.capitalize() if alloc.project_id and alloc.project_id.sale_order_id else '',
                    'allocation': alloc.allocation_percentage,
                    'effective_alloc': effective_alloc_per,
                    'standard_hours': len(working_days) * 8 if isinstance(working_days, list) else (working_days * 8),
                    'billed_hours': worked_hours,
                    'effective_cost': effective_emp_wage,
                    'cost': emp_wage,
                    'revenue': revenue_inr,
                    'technology': alloc.project_id.primary_skill.name,
                    'total_exp': alloc.employee_id.total_exp,
                    'doj': alloc.employee_id.joining_date,
                    'effective_hours': effective_working_days,
                    'accrued_rev': accured_rev,
                })
                sheet.write(row_count, 0, alloc.employee_id.identification_id)
                sheet.write(row_count, 1, alloc.employee_id.name)
                sheet.write(row_count, 2, alloc.employee_id.sbu_id.name)
                sheet.write(row_count, 3, alloc.project_id.partner_id.customer_group.name if alloc.project_id.partner_id.customer_group else '')
                sheet.write(row_count, 4, alloc.project_id.partner_id.name)
                sheet.write(row_count, 5, alloc.project_id.name)
                sheet.write(row_count, 6, alloc.project_id.whizible_id)
                sheet.write(row_count, 7, alloc.project_id.name_seq)
                sheet.write(row_count, 8, alloc.project_id.sbu_id.name)
                sheet.write(row_count, 9, alloc.project_id.department_id.name)
                sheet.write(row_count, 10, alloc.project_id.payroll_loc.name if alloc.project_id.payroll_loc else '')
                sheet.write(row_count, 11, effective_delivery_geo)
                sheet.write(row_count, 12, alloc.employee_id.employee_category.name if alloc.employee_id.employee_category else '')
                sheet.write(row_count, 13, effective_categ)
                sheet.write(row_count, 14, alloc.employee_id.account.name if alloc.employee_id.account else '')
                sheet.write(row_count, 15, alloc.project_id.sale_order_id.contract_sale_order.payroll_loc.name if alloc.project_id.sale_order_id and alloc.project_id.sale_order_id.contract_sale_order and alloc.project_id.sale_order_id.contract_sale_order.payroll_loc else '')
                sheet.write(row_count, 16, alloc.project_id.partner_id.geo_location.name if alloc.project_id.partner_id.geo_location else '')
                sheet.write(row_count, 17, alloc.project_id.sale_order_id.commercial_details.capitalize() if alloc.project_id and alloc.project_id.sale_order_id else '')
                sheet.write(row_count, 18, effective_engagmnt_model)
                sheet.write(row_count, 19, alloc.project_id.project_location.name if alloc.project_id.project_location else '')
                sheet.write(row_count, 20, effective_onshore)
                sheet.write(row_count, 21, alloc.allocation_percentage)
                sheet.write(row_count, 22, effective_alloc_per)
                sheet.write(row_count, 23, effective_working_days)
                sheet.write(row_count, 24, len(working_days) * 8 if isinstance(working_days, list) else (working_days * 8))
                sheet.write(row_count, 25, worked_hours)
                sheet.write(row_count, 26, '')
                sheet.write(row_count, 27, '')
                sheet.write(row_count, 28, '')
                sheet.write(row_count, 29, effective_emp_wage)
                sheet.write(row_count, 30, emp_wage)
                sheet.write(row_count, 31, revenue_inr)
                sheet.write(row_count, 32, accured_rev)
                sheet.write(row_count, 33, alloc.project_bill_status)
                sheet.write(row_count, 34, effective_billability)
                sheet.write(row_count, 35, alloc.project_id.sale_order_id.lob.name if alloc.project_id.sale_order_id.lob else '')
                sheet.write(row_count, 36, effective_lob)
                sheet.write(row_count, 37, alloc.project_id.primary_skill.name if alloc.project_id and alloc.project_id.primary_skill else '')
                sheet.write(row_count, 38, alloc.project_id.sale_order_id.industry.name if alloc.project_id.sale_order_id.industry else '')
                sheet.write(row_count, 39, '')
                sheet.write(row_count, 40, alloc.description_approve)
                sheet.write(row_count, 41, alloc.project_id.sale_order_id.user_id.name if alloc.project_id.sale_order_id.user_id else '')
                sheet.write(row_count, 42, alloc.employee_id.total_exp if alloc.employee_id.total_exp else '')
                sheet.write(row_count, 43, alloc.employee_id.joining_date.strftime('%d-%b-%Y') if alloc.employee_id.joining_date else '')
                sheet.write(row_count, 44, alloc.employee_id.exit_date.strftime('%d-%b-%Y') if alloc.employee_id.exit_date else '')
                row_count += 1
                duplicate_alloc.append(alloc)
            # else:
            #     non_alloc_project = False
            #     for i in non_revenue_allocation:
            #         if i.get(alloc.project_id.id):
            #             non_alloc_project = True
            #             if alloc.project_bill_status in ['100', '50', '25']:
            #                 i[alloc.project_id.id].append(alloc)
            #     if not non_alloc_project:
            #         non_revenue_allocation.append({alloc.project_id.id: [alloc]})

        # fc_amount = []
        # for line in sale_line_fc:
        #     if not line.order_id.project_id.assignment_ids.filtered(lambda alloc: ((from_date <= alloc.start_date and to_date >= alloc.start_date) or (from_date <= alloc.end_date and to_date >= alloc.end_date) or (alloc.start_date <= to_date and alloc.end_date >= to_date))):
        #         fc_amount.append(line.amount_inr)
        # fc_amount = sum(fc_amount) if fc_amount else 0.0
        sale_amount = [line.amount_inr for line in sale_line if line.employee_id.name == 'Unity' or line.employee_id is False]
        # if sale_amount:
        #     sale_amount = sum(sale_amount)
        #     sale_amount = sale_amount + fc_amount
        #     avg_ptp_amount = sale_amount / len(allocation_on_ptp_list) if len(allocation_on_ptp_list) else 0.0
        # else:
        #     avg_ptp_amount = fc_amount / len(allocation_on_ptp_list) if len(allocation_on_ptp_list) else 0.0
        if sale_amount:
            unity_sale_line = [line for line in sale_line if line.employee_id.name == 'Unity' and line.project_id]
            nouser_sale_line = [line for line in sale_line if not line.employee_id and line.project_id and line.offering_type != 'fixed_cost']
            user_sale_line_no_alloc = [line for line in sale_line if line.employee_id and line.employee_id.name != 'Unity' and line.project_id]
            # user_sale_line_no_alloc = [lin for lin in user_sale_line_no_alloc for alloc in lin.project_id.assignment_ids if (alloc.employee_id.id != lin.employee_id.id) or (alloc.employee_id.id == lin.employee_id.id and not ((from_date <= alloc.start_date and to_date >= alloc.start_date) or (from_date <= alloc.end_date and to_date >= alloc.end_date) or (alloc.start_date <= to_date and alloc.end_date >= to_date)))]
            for sline in unity_sale_line:
                effective_delivery_geo = ''
                effective_engagmnt_model = ''
                effective_lob = ''
                if sline.project_id.payroll_loc and sline.project_id.payroll_loc.name in ['Austria Branch Office', 'GMBH Payroll']:
                    effective_delivery_geo = 'EU'
                elif sline.project_id.payroll_loc and sline.project_id.payroll_loc.name == 'Inc USA':
                    effective_delivery_geo = 'USA'
                elif sline.project_id.payroll_loc and sline.project_id.payroll_loc.name in ['KTH', 'SEZ 3', 'SEZ 6']:
                    effective_delivery_geo = 'India'
                
                if sline.project_id.sale_order_id.commercial_details and sline.project_id.sale_order_id.commercial_details == 'fixed_cost':
                    effective_engagmnt_model = 'Project - Fixed Price'
                elif sline.project_id.sale_order_id.commercial_details and sline.project_id.sale_order_id.commercial_details == 'tnm':
                    effective_engagmnt_model = 'Project - T&M'
                
                if sline.project_id.sale_order_id.lob and sline.project_id.sale_order_id.lob.name == 'Big Data Analytics AI':
                    effective_lob = 'Data Science & AI/ML'
                elif sline.project_id.sale_order_id.lob and sline.project_id.sale_order_id.lob.name == 'Business Process Management':
                    effective_lob = 'Application Monitoring & Support'
                elif sline.project_id.sale_order_id.lob and sline.project_id.sale_order_id.lob.name == 'Data Engineering':
                    effective_lob = 'Data Analytics & Insights'
                elif sline.project_id.sale_order_id.lob and sline.project_id.sale_order_id.lob.name == 'Digital Applications ':
                    effective_lob = 'Product Design & Engg'
                elif sline.project_id.sale_order_id.lob and sline.project_id.sale_order_id.lob.name == 'Digital Commerce':
                    effective_lob = 'Digital Commerce'
                elif sline.project_id.sale_order_id.lob and sline.project_id.sale_order_id.lob.name == 'Managed Cloud AND DevOps':
                    effective_lob = 'Cloud & Infra Modernization'
                elif sline.project_id.sale_order_id.lob and sline.project_id.sale_order_id.lob.name == 'Tech Modernization':
                    effective_lob = 'Tech Modernization'
                elif sline.project_id.sale_order_id.lob and sline.project_id.sale_order_id.lob.name == 'Digital Operations':
                    effective_lob = 'Application Monitoring & Support'
                
                revenue_inr = sline.amount_inr / usd_rate
                utilization_line.append({
                    'employee_id': 'Unity',
                    'customer_id': sline.project_id.partner_id.id,
                    'project_id': sline.project_id.id,
                    'bu_head': sline.project_id.department_id.name,
                    'engagement_model': sline.project_id.sale_order_id.commercial_details.capitalize() if sline.project_id.sale_order_id and sline.project_id.sale_order_id.commercial_details else '',
                    'revenue': revenue_inr,
                    'technology': sline.project_id.primary_skill.name,
                })
                sheet.write(row_count, 0, '')
                sheet.write(row_count, 1, 'Unity')
                sheet.write(row_count, 2, '')
                sheet.write(row_count, 3, sline.project_id.partner_id.customer_group.name if sline.project_id.partner_id.customer_group else '')
                sheet.write(row_count, 4, sline.project_id.partner_id.name)
                sheet.write(row_count, 5, sline.project_id.name)
                sheet.write(row_count, 6, sline.project_id.whizible_id)
                sheet.write(row_count, 7, sline.project_id.name_seq)
                sheet.write(row_count, 8, sline.project_id.sbu_id.name)
                sheet.write(row_count, 9, sline.project_id.department_id.name)
                sheet.write(row_count, 10, sline.project_id.payroll_loc.name if sline.project_id.payroll_loc else '')
                sheet.write(row_count, 11, effective_delivery_geo)
                sheet.write(row_count, 12, '')
                sheet.write(row_count, 13, '')
                sheet.write(row_count, 14, '')
                sheet.write(row_count, 15, sline.project_id.sale_order_id.contract_sale_order.payroll_loc.name if sline.project_id.sale_order_id and sline.project_id.sale_order_id.contract_sale_order and sline.project_id.sale_order_id.contract_sale_order.payroll_loc else '')
                sheet.write(row_count, 16, sline.project_id.partner_id.geo_location.name if sline.project_id.partner_id.geo_location else '')
                sheet.write(row_count, 17, sline.project_id.sale_order_id.commercial_details.capitalize() if sline.project_id and sline.project_id.sale_order_id else '')
                sheet.write(row_count, 18, effective_engagmnt_model)
                sheet.write(row_count, 19, sline.project_id.project_location.name if sline.project_id.project_location else '')
                sheet.write(row_count, 20, '')
                sheet.write(row_count, 21, '')
                sheet.write(row_count, 22, '')
                sheet.write(row_count, 23, '')
                sheet.write(row_count, 24, '')
                sheet.write(row_count, 25, '')
                sheet.write(row_count, 26, '')
                sheet.write(row_count, 27, '')
                sheet.write(row_count, 28, '')
                sheet.write(row_count, 29, '')
                sheet.write(row_count, 30, '')
                sheet.write(row_count, 31, revenue_inr)
                sheet.write(row_count, 32, '')
                sheet.write(row_count, 33, '')
                sheet.write(row_count, 34, 'Bench')
                sheet.write(row_count, 35, sline.project_id.sale_order_id.lob.name if sline.project_id.sale_order_id.lob else '')
                sheet.write(row_count, 36, effective_lob)
                sheet.write(row_count, 37, sline.project_id.primary_skill.name if sline.project_id and sline.project_id.primary_skill else '')
                sheet.write(row_count, 38, sline.project_id.sale_order_id.industry.name if sline.project_id.sale_order_id.industry else '')
                sheet.write(row_count, 39, '')
                sheet.write(row_count, 40, '')
                sheet.write(row_count, 41, sline.project_id.sale_order_id.user_id.name if sline.project_id.sale_order_id.user_id else '')
                sheet.write(row_count, 42, '')
                sheet.write(row_count, 43, '')
                sheet.write(row_count, 44, '')
                row_count += 1
            for uline in nouser_sale_line:
                effective_delivery_geo = ''
                effective_engagmnt_model = ''
                effective_lob = ''
                if uline.project_id.payroll_loc and uline.project_id.payroll_loc.name in ['Austria Brach Office', 'GmBH Payroll']:
                    effective_delivery_geo = 'EU'
                elif uline.project_id.payroll_loc and uline.project_id.payroll_loc.name == 'Inc USA':
                    effective_delivery_geo = 'USA'
                elif uline.project_id.payroll_loc and uline.project_id.payroll_loc.name in ['KTH', 'SEZ 3', 'SEZ 6']:
                    effective_delivery_geo = 'India'
                
                if uline.project_id.sale_order_id.commercial_details and uline.project_id.sale_order_id.commercial_details == 'fixed_cost':
                    effective_engagmnt_model = 'Fixed Price'
                elif uline.project_id.sale_order_id.commercial_details and uline.project_id.sale_order_id.commercial_details == 'tnm':
                    effective_engagmnt_model = 'T&M'
                
                if uline.project_id.sale_order_id.lob and uline.project_id.sale_order_id.lob.name == 'Big Data Analytics AI':
                    effective_lob = 'Data Science & AI/ML'
                elif uline.project_id.sale_order_id.lob and uline.project_id.sale_order_id.lob.name == 'Business Process Management':
                    effective_lob = 'Application Monitoring & Support'
                elif uline.project_id.sale_order_id.lob and uline.project_id.sale_order_id.lob.name == 'Data Engineering':
                    effective_lob = 'Data Analytics & Insights'
                elif uline.project_id.sale_order_id.lob and uline.project_id.sale_order_id.lob.name == 'Digital Applications ':
                    effective_lob = 'Product Design & Engg'
                elif uline.project_id.sale_order_id.lob and uline.project_id.sale_order_id.lob.name == 'Digital Commerce':
                    effective_lob = 'Digital Commerce'
                elif uline.project_id.sale_order_id.lob and uline.project_id.sale_order_id.lob.name == 'Managed Cloud AND DevOps':
                    effective_lob = 'Cloud & Infra Modernization'
                elif uline.project_id.sale_order_id.lob and uline.project_id.sale_order_id.lob.name == 'Tech Modernization':
                    effective_lob = 'Tech Modernization'
                elif uline.project_id.sale_order_id.lob and uline.project_id.sale_order_id.lob.name == 'Digital Operations':
                    effective_lob = 'Application Monitoring & Support'
                
                revenue_inr = uline.amount_inr / usd_rate
                utilization_line.append({
                    'employee_id': 'No User Tagged',
                    'customer_id': uline.project_id.partner_id.id,
                    'project_id': uline.project_id.id,
                    'bu_head': uline.project_id.department_id.name,
                    'engagement_model': uline.project_id.sale_order_id.commercial_details.capitalize() if uline.project_id.sale_order_id and uline.project_id.sale_order_id.commercial_details else '',
                    'revenue': revenue_inr,
                    'technology': uline.project_id.primary_skill.name,
                })
                sheet.write(row_count, 0, '')
                sheet.write(row_count, 1, 'No User Tagged')
                sheet.write(row_count, 2, '')
                sheet.write(row_count, 3, uline.project_id.partner_id.customer_group.name if uline.project_id.partner_id.customer_group else '')
                sheet.write(row_count, 4, uline.project_id.partner_id.name)
                sheet.write(row_count, 5, uline.project_id.name)
                sheet.write(row_count, 6, uline.project_id.whizible_id)
                sheet.write(row_count, 7, uline.project_id.name_seq)
                sheet.write(row_count, 8, uline.project_id.sbu_id.name)
                sheet.write(row_count, 9, uline.project_id.department_id.name)
                sheet.write(row_count, 10, uline.project_id.payroll_loc.name if uline.project_id.payroll_loc else '')
                sheet.write(row_count, 11, effective_delivery_geo)
                sheet.write(row_count, 12, '')
                sheet.write(row_count, 13, '')
                sheet.write(row_count, 14, '')
                sheet.write(row_count, 15, uline.project_id.sale_order_id.contract_sale_order.payroll_loc.name if uline.project_id.sale_order_id and uline.project_id.sale_order_id.contract_sale_order and uline.project_id.sale_order_id.contract_sale_order.payroll_loc else '')
                sheet.write(row_count, 16, uline.project_id.partner_id.geo_location.name if uline.project_id.partner_id.geo_location else '')
                sheet.write(row_count, 17, uline.project_id.sale_order_id.commercial_details.capitalize() if uline.project_id and uline.project_id.sale_order_id else '')
                sheet.write(row_count, 18, effective_engagmnt_model)
                sheet.write(row_count, 19, uline.project_id.project_location.name if uline.project_id.project_location else '')
                sheet.write(row_count, 20, '')
                sheet.write(row_count, 21, '')
                sheet.write(row_count, 22, '')
                sheet.write(row_count, 23, '')
                sheet.write(row_count, 24, '')
                sheet.write(row_count, 25, '')
                sheet.write(row_count, 26, '')
                sheet.write(row_count, 27, '')
                sheet.write(row_count, 28, '')
                sheet.write(row_count, 29, '')
                sheet.write(row_count, 30, '')
                sheet.write(row_count, 31, revenue_inr)
                sheet.write(row_count, 32, '')
                sheet.write(row_count, 33, '')
                sheet.write(row_count, 34, 'Bench')
                sheet.write(row_count, 35, uline.project_id.sale_order_id.lob.name if uline.project_id.sale_order_id.lob else '')
                sheet.write(row_count, 36, effective_lob)
                sheet.write(row_count, 37, uline.project_id.primary_skill.name if uline.project_id and uline.project_id.primary_skill else '')
                sheet.write(row_count, 38, uline.project_id.sale_order_id.industry.name if uline.project_id.sale_order_id.industry else '')
                sheet.write(row_count, 39, '')
                sheet.write(row_count, 40, '')
                sheet.write(row_count, 41, uline.project_id.sale_order_id.user_id.name if uline.project_id.sale_order_id.user_id else '')
                sheet.write(row_count, 42, '')
                sheet.write(row_count, 43, '')
                sheet.write(row_count, 44, '')
                row_count += 1
            for ualine in user_sale_line_no_alloc:
                check_alloc = ualine.employee_id.id not in ualine.project_id.assignment_ids.mapped('employee_id.id')
                alloc_duration = ualine.project_id.assignment_ids.search([('employee_id', '=', ualine.employee_id.id)])
                check_alloc_duration = alloc_duration.filtered(lambda alloc: alloc.project_id.id == ualine.project_id.id and ((from_date <= alloc.start_date and to_date >= alloc.start_date) or (from_date <= alloc.end_date and to_date >= alloc.end_date) or (alloc.start_date <= to_date and alloc.end_date >= to_date)))
                other_company_alloc = [l for l in ualine.order_id.contract_sale_order.order_line if ualine.order_id.contract_sale_order and l.sync_line_id.id == ualine.id]
                revenue_inr = ualine.amount_inr / usd_rate
                effective_delivery_geo = ''
                effective_engagmnt_model = ''
                effective_lob = ''
                if ualine.project_id.payroll_loc and ualine.project_id.payroll_loc.name in ['Austria Branch Office', 'GMBH Payroll']:
                    effective_delivery_geo = 'EU'
                elif ualine.project_id.payroll_loc and ualine.project_id.payroll_loc.name == 'Inc USA':
                    effective_delivery_geo = 'USA'
                elif ualine.project_id.payroll_loc and ualine.project_id.payroll_loc.name in ['KTH', 'SEZ 3', 'SEZ 6']:
                    effective_delivery_geo = 'India'
                
                if ualine.project_id.sale_order_id.commercial_details and ualine.project_id.sale_order_id.commercial_details == 'fixed_cost':
                    effective_engagmnt_model = 'Project - Fixed Price'
                elif ualine.project_id.sale_order_id.commercial_details and ualine.project_id.sale_order_id.commercial_details == 'tnm':
                    effective_engagmnt_model = 'Project - T&M'
                
                if ualine.project_id.sale_order_id.lob and ualine.project_id.sale_order_id.lob.name == 'Big Data Analytics AI':
                    effective_lob = 'Data Science & AI/ML'
                elif ualine.project_id.sale_order_id.lob and ualine.project_id.sale_order_id.lob.name == 'Business Process Management':
                    effective_lob = 'Application Monitoring & Support'
                elif ualine.project_id.sale_order_id.lob and ualine.project_id.sale_order_id.lob.name == 'Data Engineering':
                    effective_lob = 'Data Analytics & Insights'
                elif ualine.project_id.sale_order_id.lob and ualine.project_id.sale_order_id.lob.name == 'Digital Applications ':
                    effective_lob = 'Product Design & Engg'
                elif ualine.project_id.sale_order_id.lob and ualine.project_id.sale_order_id.lob.name == 'Digital Commerce':
                    effective_lob = 'Digital Commerce'
                elif ualine.project_id.sale_order_id.lob and ualine.project_id.sale_order_id.lob.name == 'Managed Cloud AND DevOps':
                    effective_lob = 'Cloud & Infra Modernization'
                elif ualine.project_id.sale_order_id.lob and ualine.project_id.sale_order_id.lob.name == 'Tech Modernization':
                    effective_lob = 'Tech Modernization'
                elif ualine.project_id.sale_order_id.lob and ualine.project_id.sale_order_id.lob.name == 'Digital Operations':
                    effective_lob = 'Application Monitoring & Support'
                # For other company
                o_ualine = other_company_alloc[0] if other_company_alloc else False
                check_other_alloc = False
                if o_ualine:
                    other_alloc = self.env['project.assignment'].search([('employee_id', '=', o_ualine.employee_id.id), ('project_id', '=', o_ualine.project_id.id)])
                    check_other_alloc = other_alloc.filtered(lambda alloc: ((from_date <= alloc.start_date and to_date >= alloc.start_date) or (from_date <= alloc.end_date and to_date >= alloc.end_date) or (alloc.start_date <= to_date and alloc.end_date >= to_date)))
                if other_company_alloc and check_other_alloc:
                    for oalloc in check_other_alloc:
                        if o_ualine.efforts_from and o_ualine.efforts_from == 'ofshore':
                            effective_onshore = 'Offshore'
                        elif o_ualine.efforts_from and o_ualine.efforts_from == 'onsite':
                            effective_onshore = 'On-site'
                        effective_emp_wage = 0.0
                        effective_working_days = 0.0
                        if oalloc.start_date and oalloc.start_date < from_date:
                            date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
                        else:
                            date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(oalloc.start_date)), time.min))
                        if oalloc.end_date and oalloc.end_date > to_date:
                            date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.min))
                        else:
                            date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(oalloc.end_date)), time.min))
                        localize_from_date = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
                        localize_to_date = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.min))
                        standard_working_days = admin.list_work_time_per_day(localize_from_date, localize_to_date, calendar=admin.resource_calendar_id)
                        if date_from == date_to and date_from.date().weekday() not in [5, 6]:
                            working_days = 1
                            effective_alloc_per = (oalloc.allocation_percentage * (working_days * 8)) / (len(standard_working_days) * 8) if len(standard_working_days) else oalloc.allocation_percentage * ((working_days) * 8)
                            effective_alloc_per_month = (oalloc.allocation_percentage * (working_days * 8)) / 100
                        else:
                            working_days = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
                            effective_alloc_per = (oalloc.allocation_percentage * (len(working_days) * 8)) / (len(standard_working_days) * 8)
                            effective_alloc_per_month = (oalloc.allocation_percentage * (len(working_days) * 8)) / 100
                        revenue_inr = o_ualine.amount_inr / usd_rate
                        standard_hours = len(working_days) * 8 if isinstance(working_days, list) else (working_days * 8)
                        effective_working_days = (standard_hours * effective_alloc_per) / 100
                        inr_rate = [i.rate for i in oalloc.employee_id.company_id.currency_id.rate_ids if i.name and i.end_date and to_date and to_date >= i.name and to_date <= i.end_date]
                        inr_rate1 = oalloc.employee_id.emp_wage * inr_rate[0] if oalloc.employee_id.emp_wage and inr_rate else 0.0
                        emp_wage = inr_rate1 / usd_rate
                        effective_emp_wage = emp_wage    
                        accured_rev = ''
                        other_alloc_month = o_ualine.project_id.assignment_ids.filtered(lambda allo: allo.assign_status == 'confirmed' and ((from_date <= allo.start_date and to_date >= allo.start_date) or (from_date <= allo.end_date and to_date >= allo.end_date) or (allo.start_date <= to_date and allo.end_date >= to_date)))
                        effective_alloc = []
                        for i in other_alloc_month:
                            effective_alloc_per_user = self._get_effective_alloc(i, admin, other_alloc_month, from_date, to_date, tz)
                            effective_alloc.append(effective_alloc_per_user)
                        effect_alloc_month = sum(effective_alloc)
                        effective_alloc_all = []
                        alloc_total_month = o_ualine.project_id.assignment_ids.filtered(lambda allo: allo.assign_status == 'confirmed')
                        for j in alloc_total_month:
                            effective_alloc_all.append(j.project_efforts)
                        effect_alloc_total = sum(effective_alloc_all)
                        
                        revenue_month = o_ualine.amount_inr * effect_alloc_month / effect_alloc_total if effect_alloc_total else 0.0
                        revenue_per_person = revenue_month * effective_alloc_per_month / effect_alloc_month if effect_alloc_month else 0.0
                        accured_rev = revenue_per_person / usd_rate

                        utilization_line.append({
                            'employee_id': oalloc.employee_id.name,
                            'emp_code': oalloc.employee_id.identification_id,
                            'customer_id': oalloc.project_id.partner_id.id,
                            'project_id': oalloc.project_id.id,
                            'bu_head': oalloc.project_id.department_id.name,
                            'engagement_model': oalloc.project_id.sale_order_id.commercial_details.capitalize() if alloc.project_id and alloc.project_id.sale_order_id else '',
                            'allocation': oalloc.allocation_percentage,
                            'effective_alloc': effective_alloc_per,
                            'standard_hours': len(working_days) * 8 if isinstance(working_days, list) else (working_days * 8),
                            'billed_hours': worked_hours,
                            'effective_cost': effective_emp_wage,
                            'cost': emp_wage,
                            'revenue': revenue_inr,
                            'technology': oalloc.project_id.primary_skill.name,
                            'total_exp': oalloc.employee_id.total_exp,
                            'doj': oalloc.employee_id.joining_date,
                            'effective_hours': effective_working_days,
                            'accrued_rev': accured_rev,
                        })
                        sheet.write(row_count, 0, check_other_alloc.employee_id.identification_id)
                        sheet.write(row_count, 1, check_other_alloc.employee_id.name)
                        sheet.write(row_count, 2, check_other_alloc.employee_id.sbu_id.name)
                        sheet.write(row_count, 3, check_other_alloc.project_id.partner_id.customer_group.name if check_other_alloc.project_id.partner_id.customer_group else '')
                        sheet.write(row_count, 4, check_other_alloc.project_id.partner_id.name)
                        sheet.write(row_count, 5, check_other_alloc.project_id.name)
                        sheet.write(row_count, 6, check_other_alloc.project_id.whizible_id)
                        sheet.write(row_count, 7, check_other_alloc.project_id.name_seq)
                        sheet.write(row_count, 8, check_other_alloc.project_id.sbu_id.name)
                        sheet.write(row_count, 9, check_other_alloc.project_id.department_id.name)
                        sheet.write(row_count, 10, check_other_alloc.project_id.payroll_loc.name if check_other_alloc.project_id.payroll_loc else '')
                        sheet.write(row_count, 11, effective_delivery_geo)
                        sheet.write(row_count, 12, check_other_alloc.employee_id.employee_category.name if check_other_alloc.employee_id.employee_category else '')
                        sheet.write(row_count, 13, effective_categ)
                        sheet.write(row_count, 14, check_other_alloc.employee_id.account.name if check_other_alloc.employee_id.account else '')
                        sheet.write(row_count, 15, check_other_alloc.project_id.sale_order_id.contract_sale_order.payroll_loc.name if check_other_alloc.project_id.sale_order_id and check_other_alloc.project_id.sale_order_id.contract_sale_order and check_other_alloc.project_id.sale_order_id.contract_sale_order.payroll_loc else '')
                        sheet.write(row_count, 16, check_other_alloc.project_id.partner_id.geo_location.name if check_other_alloc.project_id.partner_id.geo_location else '')
                        sheet.write(row_count, 17, check_other_alloc.project_id.sale_order_id.commercial_details.capitalize() if check_other_alloc.project_id and check_other_alloc.project_id.sale_order_id else '')
                        sheet.write(row_count, 18, effective_engagmnt_model)
                        sheet.write(row_count, 19, o_ualine.efforts_from.capitalize() if o_ualine.efforts_from else '')
                        sheet.write(row_count, 20, effective_onshore)
                        sheet.write(row_count, 21, check_other_alloc.allocation_percentage)
                        sheet.write(row_count, 22, effective_alloc_per)
                        sheet.write(row_count, 23, effective_working_days)
                        sheet.write(row_count, 24, len(working_days) * 8 if isinstance(working_days, list) else (working_days * 8))
                        sheet.write(row_count, 25, worked_hours)
                        sheet.write(row_count, 26, '')
                        sheet.write(row_count, 27, '')
                        sheet.write(row_count, 28, '')
                        sheet.write(row_count, 29, effective_emp_wage)
                        sheet.write(row_count, 30, emp_wage)
                        sheet.write(row_count, 31, revenue_inr)
                        sheet.write(row_count, 32, accured_rev)
                        sheet.write(row_count, 33, check_other_alloc.project_bill_status)
                        sheet.write(row_count, 34, effective_billability)
                        sheet.write(row_count, 35, check_other_alloc.project_id.sale_order_id.lob.name if check_other_alloc.project_id.sale_order_id.lob else '')
                        sheet.write(row_count, 36, effective_lob)
                        sheet.write(row_count, 37, check_other_alloc.project_id.primary_skill.name if check_other_alloc.project_id and check_other_alloc.project_id.primary_skill else '')
                        sheet.write(row_count, 38, check_other_alloc.project_id.sale_order_id.industry.name if check_other_alloc.project_id.sale_order_id.industry else '')
                        sheet.write(row_count, 39, '')
                        sheet.write(row_count, 40, check_other_alloc.description_approve)
                        sheet.write(row_count, 41, check_other_alloc.project_id.sale_order_id.user_id.name if check_other_alloc.project_id.sale_order_id.user_id else '')
                        sheet.write(row_count, 42, check_other_alloc.employee_id.total_exp if check_other_alloc.employee_id.total_exp else '')
                        sheet.write(row_count, 43, check_other_alloc.employee_id.joining_date.strftime('%d-%b-%Y') if check_other_alloc.employee_id.joining_date else '')
                        sheet.write(row_count, 44, check_other_alloc.employee_id.exit_date.strftime('%d-%b-%Y') if check_other_alloc.employee_id.exit_date else '')
                        row_count += 1
                elif revenue_inr > 0 and check_alloc or not check_alloc_duration:
                    utilization_line.append({
                        'employee_id': 'No Allocation',
                        'customer_id': ualine.project_id.partner_id.id,
                        'project_id': ualine.project_id.id,
                        'bu_head': ualine.project_id.department_id.name,
                        'engagement_model': ualine.project_id.sale_order_id.commercial_details.capitalize() if ualine.project_id.sale_order_id and ualine.project_id.sale_order_id.commercial_details else '',
                        'revenue': revenue_inr,
                        'technology': ualine.project_id.primary_skill.name,
                    })
                    sheet.write(row_count, 0, '')
                    sheet.write(row_count, 1, 'No Allocation')
                    sheet.write(row_count, 2, '')
                    sheet.write(row_count, 3, ualine.project_id.partner_id.customer_group.name if ualine.project_id.partner_id.customer_group else '')
                    sheet.write(row_count, 4, ualine.project_id.partner_id.name)
                    sheet.write(row_count, 5, ualine.project_id.name)
                    sheet.write(row_count, 6, ualine.project_id.whizible_id)
                    sheet.write(row_count, 7, ualine.project_id.name_seq)
                    sheet.write(row_count, 8, ualine.project_id.sbu_id.name)
                    sheet.write(row_count, 9, ualine.project_id.department_id.name)
                    sheet.write(row_count, 10, ualine.project_id.payroll_loc.name if ualine.project_id.payroll_loc else '')
                    sheet.write(row_count, 11, effective_delivery_geo)
                    sheet.write(row_count, 12, '')
                    sheet.write(row_count, 13, '')
                    sheet.write(row_count, 14, '')
                    sheet.write(row_count, 15, ualine.project_id.sale_order_id.contract_sale_order.payroll_loc.name if ualine.project_id.sale_order_id and ualine.project_id.sale_order_id.contract_sale_order and ualine.project_id.sale_order_id.contract_sale_order.payroll_loc else '')
                    sheet.write(row_count, 16, ualine.project_id.partner_id.geo_location.name if ualine.project_id.partner_id.geo_location else '')
                    sheet.write(row_count, 17, ualine.project_id.sale_order_id.commercial_details.capitalize() if ualine.project_id and ualine.project_id.sale_order_id else '')
                    sheet.write(row_count, 18, effective_engagmnt_model)
                    sheet.write(row_count, 19, ualine.project_id.project_location.name if ualine.project_id.project_location else '')
                    sheet.write(row_count, 20, '')
                    sheet.write(row_count, 21, '')
                    sheet.write(row_count, 22, '')
                    sheet.write(row_count, 23, '')
                    sheet.write(row_count, 24, '')
                    sheet.write(row_count, 25, '')
                    sheet.write(row_count, 26, '')
                    sheet.write(row_count, 27, '')
                    sheet.write(row_count, 28, '')
                    sheet.write(row_count, 29, '')
                    sheet.write(row_count, 30, '')
                    sheet.write(row_count, 31, revenue_inr)
                    sheet.write(row_count, 32, '')
                    sheet.write(row_count, 33, '')
                    sheet.write(row_count, 34, 'Bench')
                    sheet.write(row_count, 35, ualine.project_id.sale_order_id.lob.name if ualine.project_id.sale_order_id.lob else '')
                    sheet.write(row_count, 36, effective_lob)
                    sheet.write(row_count, 37, ualine.project_id.primary_skill.name if ualine.project_id and ualine.project_id.primary_skill else '')
                    sheet.write(row_count, 38, ualine.project_id.sale_order_id.industry.name if ualine.project_id.sale_order_id.industry else '')
                    sheet.write(row_count, 39, '')
                    sheet.write(row_count, 40, '')
                    sheet.write(row_count, 41, ualine.project_id.sale_order_id.user_id.name if ualine.project_id.sale_order_id.user_id else '')
                    sheet.write(row_count, 42, '')
                    sheet.write(row_count, 43, '')
                    sheet.write(row_count, 44, '')
                    row_count += 1
        
        if sale_line_fc:
            for line in sale_line_fc:
                if not line.order_id.project_id.assignment_ids.filtered(lambda alloc: ((from_date <= alloc.start_date and to_date >= alloc.start_date) or (from_date <= alloc.end_date and to_date >= alloc.end_date) or (alloc.start_date <= to_date and alloc.end_date >= to_date))):
                    effective_delivery_geo = ''
                    effective_engagmnt_model = ''
                    effective_lob = ''
                    if line.project_id.payroll_loc and line.project_id.payroll_loc.name in ['Austria Branch Office', 'GMBH Payroll']:
                        effective_delivery_geo = 'EU'
                    elif line.project_id.payroll_loc and line.project_id.payroll_loc.name == 'Inc USA':
                        effective_delivery_geo = 'USA'
                    elif line.project_id.payroll_loc and line.project_id.payroll_loc.name in ['KTH', 'SEZ 3', 'SEZ 6']:
                        effective_delivery_geo = 'India'
                    
                    if line.project_id.sale_order_id.commercial_details and line.project_id.sale_order_id.commercial_details == 'fixed_cost':
                        effective_engagmnt_model = 'project - Fixed Price'
                    elif line.project_id.sale_order_id.commercial_details and line.project_id.sale_order_id.commercial_details == 'tnm':
                        effective_engagmnt_model = 'project - T&M'
                    
                    if line.project_id.sale_order_id.lob and line.project_id.sale_order_id.lob.name == 'Big Data Analytics AI':
                        effective_lob = 'Data Science & AI/ML'
                    elif line.project_id.sale_order_id.lob and line.project_id.sale_order_id.lob.name == 'Business Process Management':
                        effective_lob = 'Application Monitoring & Support'
                    elif line.project_id.sale_order_id.lob and line.project_id.sale_order_id.lob.name == 'Data Engineering':
                        effective_lob = 'Data Analytics & Insights'
                    elif line.project_id.sale_order_id.lob and line.project_id.sale_order_id.lob.name == 'Digital Applications ':
                        effective_lob = 'Product Design & Engg'
                    elif line.project_id.sale_order_id.lob and line.project_id.sale_order_id.lob.name == 'Digital Commerce':
                        effective_lob = 'Digital Commerce'
                    elif line.project_id.sale_order_id.lob and line.project_id.sale_order_id.lob.name == 'Managed Cloud AND DevOps':
                        effective_lob = 'Cloud & Infra Modernization'
                    elif line.project_id.sale_order_id.lob and line.project_id.sale_order_id.lob.name == 'Tech Modernization':
                        effective_lob = 'Tech Modernization'
                    elif line.project_id.sale_order_id.lob and line.project_id.sale_order_id.lob.name == 'Digital Operations':
                        effective_lob = 'Application Monitoring & Support'
                    revenue_inr = line.amount_inr / usd_rate
                    utilization_line.append({
                        'employee_id': 'No User Fixed Cost',
                        'customer_id': line.project_id.partner_id.id,
                        'project_id': line.project_id.id,
                        'bu_head': line.project_id.department_id.name,
                        'engagement_model': line.project_id.sale_order_id.commercial_details.capitalize() if line.project_id and line.project_id.sale_order_id and line.project_id.sale_order_id.commercial_details else '',
                        'revenue': revenue_inr,
                        'technology': line.project_id.primary_skill.name,
                    })
                    sheet.write(row_count, 0, '')
                    sheet.write(row_count, 1, 'No User Fixed Cost')
                    sheet.write(row_count, 2, '')
                    sheet.write(row_count, 3, line.project_id.partner_id.customer_group.name if line.project_id.partner_id.customer_group else '')
                    sheet.write(row_count, 4, line.project_id.partner_id.name)
                    sheet.write(row_count, 5, line.project_id.name)
                    sheet.write(row_count, 6, line.project_id.whizible_id)
                    sheet.write(row_count, 7, line.project_id.name_seq)
                    sheet.write(row_count, 8, line.project_id.sbu_id.name)
                    sheet.write(row_count, 9, line.project_id.department_id.name)
                    sheet.write(row_count, 10, line.project_id.payroll_loc.name if line.project_id.payroll_loc else '')
                    sheet.write(row_count, 11, effective_delivery_geo)
                    sheet.write(row_count, 12, '')
                    sheet.write(row_count, 13, '')
                    sheet.write(row_count, 14, '')
                    sheet.write(row_count, 15, line.project_id.sale_order_id.contract_sale_order.payroll_loc.name if line.project_id.sale_order_id and line.project_id.sale_order_id.contract_sale_order and line.project_id.sale_order_id.contract_sale_order.payroll_loc else '')
                    sheet.write(row_count, 16, line.project_id.partner_id.geo_location.name if line.project_id.partner_id.geo_location else '')
                    sheet.write(row_count, 17, line.project_id.sale_order_id.commercial_details.capitalize() if line.project_id and line.project_id.sale_order_id else '')
                    sheet.write(row_count, 18, effective_engagmnt_model)
                    sheet.write(row_count, 19, line.project_id.project_location.name if line.project_id.project_location else '')
                    sheet.write(row_count, 20, '')
                    sheet.write(row_count, 21, '')
                    sheet.write(row_count, 22, '')
                    sheet.write(row_count, 23, '')
                    sheet.write(row_count, 24, '')
                    sheet.write(row_count, 25, '')
                    sheet.write(row_count, 26, '')
                    sheet.write(row_count, 27, '')
                    sheet.write(row_count, 28, '')
                    sheet.write(row_count, 29, '')
                    sheet.write(row_count, 30, '')
                    sheet.write(row_count, 31, revenue_inr)
                    sheet.write(row_count, 32, '')
                    sheet.write(row_count, 33, '')
                    sheet.write(row_count, 34, 'Bench')
                    sheet.write(row_count, 35, line.project_id.sale_order_id.lob.name if line.project_id.sale_order_id.lob else '')
                    sheet.write(row_count, 36, effective_lob)
                    sheet.write(row_count, 37, line.project_id.primary_skill.name if line.project_id and line.project_id.primary_skill else '')
                    sheet.write(row_count, 38, line.project_id.sale_order_id.industry.name if line.project_id.sale_order_id.industry else '')
                    sheet.write(row_count, 39, '')
                    sheet.write(row_count, 40, '')
                    sheet.write(row_count, 41, line.project_id.sale_order_id.user_id.name if line.project_id.sale_order_id.user_id else '')
                    sheet.write(row_count, 42, '')
                    sheet.write(row_count, 43, '')
                    sheet.write(row_count, 44, '')
                    row_count += 1
        # for non_rev in non_revenue_allocation:
        #     for key, val in non_rev.items():
        #         project = self.env['project.project'].browse(key)
        #         order_line = project.sale_order_id.order_line.filtered(lambda ol: ol.offering_type == 'tnm' and ol.date_target and ol.start_date and ol.date_target >= from_date and ol.date_target <= to_date and ol.employee_id.name == 'Unity')
        #         if order_line:
        #             revenue_inr = order_line.mapped('amount_inr')
        #             revenue_inr = sum(revenue_inr) / usd_rate
        #             alloc_project = False
        #             for i in revenue_allocation:
        #                 if i.get(project.id):
        #                     i[project.id].append(revenue_inr)
        #                     alloc_project = True
        #             if not alloc_project:
        #                 revenue_allocation.append({project.id: [revenue_inr]})
        #         rev_list = [rev for rev in revenue_allocation if rev.get(key)]
        #         if project.sale_order_id and project.sale_order_id.commercial_details == 'tnm':
        #             orderline = project.sale_order_id.order_line.filtered(lambda lin: lin.date_target and lin.start_date and lin.date_target >= from_date and lin.date_target <= to_date)
        #         else:
        #             orderline = project.sale_order_id.order_line.filtered(lambda lin: lin.date_target and lin.start_date and lin.date_target >= from_date and lin.date_target <= to_date)
        #         total_rev = sum(orderline.mapped('amount_inr'))
        #         total_rev = total_rev / usd_rate
        #         remain_alloc = len(val) if val else 1
        #         if rev_list:
        #             alloc_rev = sum(list(rev_list[0].values())[0]) if list(rev_list[0].values())[0] else 0.0
        #             remain_rev = total_rev - alloc_rev
        #             per_alloc_rev = remain_rev / remain_alloc if remain_rev > 0 else 0
        #         else:
        #             per_alloc_rev = 0.0
        #         for alloc in val:
        #             duplicate_proj = [d for d in duplicate_alloc if d.project_id.id == alloc.project_id.id]
        #             if duplicate_proj and alloc.employee_id.id in [e.employee_id.id for e in duplicate_proj]:
        #                 pass
        #             else:
        #                 sheet.write(row_count, 0, alloc.employee_id.identification_id)
        #                 sheet.write(row_count, 1, alloc.employee_id.name)
        #                 sheet.write(row_count, 2, alloc.project_id.partner_id.customer_group.name if alloc.project_id.partner_id.customer_group else '')
        #                 sheet.write(row_count, 3, alloc.project_id.partner_id.name)
        #                 sheet.write(row_count, 4, alloc.project_id.name)
        #                 sheet.write(row_count, 5, alloc.project_id.department_id.name)
        #                 sheet.write(row_count, 6, alloc.project_id.payroll_loc.name if alloc.project_id.payroll_loc else '')
        #                 sheet.write(row_count, 7, alloc.employee_id.employee_category.name if alloc.employee_id.employee_category else '')
        #                 sheet.write(row_count, 8, alloc.employee_id.account.name if alloc.employee_id.account else '')
        #                 sheet.write(row_count, 9, alloc.project_id.sale_order_id.contract_sale_order.payroll_loc.name if alloc.project_id.sale_order_id and alloc.project_id.sale_order_id.contract_sale_order and alloc.project_id.sale_order_id.contract_sale_order.payroll_loc else '')
        #                 sheet.write(row_count, 10, alloc.project_id.partner_id.geo_location.name if alloc.project_id.partner_id.geo_location else '')
        #                 sheet.write(row_count, 11, alloc.project_id.sale_order_id.commercial_details.capitalize() if alloc.project_id and alloc.project_id.sale_order_id else '')
        #                 sheet.write(row_count, 12, alloc.project_id.project_location.name if alloc.project_id.project_location else '')
        #                 sheet.write(row_count, 13, alloc.allocation_percentage)
        #                 sheet.write(row_count, 14, len(working_days) * 8)
        #                 sheet.write(row_count, 15, worked_hours)
        #                 sheet.write(row_count, 16, '')
        #                 sheet.write(row_count, 17, '')
        #                 sheet.write(row_count, 18, '')
        #                 sheet.write(row_count, 19, alloc.employee_id.emp_wage / usd_rate)
        #                 sheet.write(row_count, 20, per_alloc_rev)
        #                 sheet.write(row_count, 21, alloc.project_id.sale_order_id.lob.name if alloc.project_id.sale_order_id.lob else '')
        #                 sheet.write(row_count, 22, alloc.project_id.primary_skill.name if alloc.project_id and alloc.project_id.primary_skill else '')
        #                 sheet.write(row_count, 23, alloc.project_id.sale_order_id.industry.name if alloc.project_id.sale_order_id.industry else '')
        #                 sheet.write(row_count, 24, '')
        #                 sheet.write(row_count, 25, alloc.description_approve)
        #                 sheet.write(row_count, 26, alloc.project_id.sale_order_id.user_id.name if alloc.project_id.sale_order_id.user_id else '')
        #                 row_count += 1
        #                 duplicate_alloc.append(alloc)
        if saved_utilization:
            saved_utilization.utilization_line = [(0, 0, i) for i in utilization_line]
        if new_utilization:
            new_utilization.utilization_line = [(0, 0, i) for i in utilization_line]
        for emp in remain_emp:
            if self.env.user.has_group('hr.group_hr_user') or self.env.user.has_group('base.group_system') or self.env.user.has_group('project_mgmt.role_operations'):
                if emp.emp_wage:
                    inr_rate = [i.rate for i in emp.company_id.currency_id.rate_ids if i.name and i.end_date and to_date and to_date >= i.name and to_date <= i.end_date]
                    inr_rate = emp.emp_wage * inr_rate[0] if emp.emp_wage and inr_rate else 0.0
                    emp_wage = inr_rate / usd_rate
                else:
                    emp_wage = 0.0
            else:
                emp_wage = 0.0
            if alloc.employee_id.joining_date >= from_date:
                date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(alloc.employee_id.joining_date)), time.min))
            else:
                date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(from_date)), time.min))
            if alloc.employee_id.exit_date and alloc.employee_id.exit_date <= to_date:
                date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(alloc.employee_id.exit_date)), time.min))
            else:
                date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(to_date)), time.min))
            effective_categ = ''
            if emp.employee_category and emp.employee_category.name == 'eZestian':
                effective_categ = 'Employee'
            if emp.employee_category and emp.employee_category.name == 'Contractor':
                effective_categ = 'Consultant'
            working_days = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
            sheet.write(row_count, 0, emp.identification_id)
            sheet.write(row_count, 1, emp.name)
            sheet.write(row_count, 2, emp.sbu_id.name)
            sheet.write(row_count, 3, '')
            sheet.write(row_count, 4, '')
            sheet.write(row_count, 5, '')
            sheet.write(row_count, 6, '')
            sheet.write(row_count, 7, '')
            sheet.write(row_count, 8, '')
            sheet.write(row_count, 9, '')
            sheet.write(row_count, 10, '')
            sheet.write(row_count, 11, '')
            sheet.write(row_count, 12, emp.employee_category.name if emp.employee_category else '')
            sheet.write(row_count, 13, effective_categ)
            sheet.write(row_count, 14, emp.account.name if emp.account else '')
            sheet.write(row_count, 15, '')
            sheet.write(row_count, 16, '')
            sheet.write(row_count, 17, '')
            sheet.write(row_count, 18, '')
            sheet.write(row_count, 19, '')
            sheet.write(row_count, 20, '')
            sheet.write(row_count, 21, '')
            sheet.write(row_count, 22, '')
            sheet.write(row_count, 23, '')
            sheet.write(row_count, 24, len(working_days) * 8)
            sheet.write(row_count, 25, '')
            sheet.write(row_count, 26, '')
            sheet.write(row_count, 27, '')
            sheet.write(row_count, 28, '')
            sheet.write(row_count, 29, '')
            sheet.write(row_count, 30, emp_wage)
            sheet.write(row_count, 31, '')
            sheet.write(row_count, 32, '')
            sheet.write(row_count, 33, '')
            sheet.write(row_count, 34, 'Bench')
            sheet.write(row_count, 35, '')
            sheet.write(row_count, 36, '')
            sheet.write(row_count, 37, '')
            sheet.write(row_count, 38, '')
            sheet.write(row_count, 39, '')
            sheet.write(row_count, 40, '')
            sheet.write(row_count, 41, '')
            sheet.write(row_count, 42, emp.total_exp if emp.total_exp else '')
            sheet.write(row_count, 43, emp.joining_date.strftime('%d-%b-%Y') if emp.joining_date else '')
            sheet.write(row_count, 44, emp.exit_date.strftime('%d-%b-%Y') if emp.exit_date else '')
            row_count += 1

    def generate_xlsx_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet("Team Utilization Report")
        sheet1 = workbook.add_worksheet("Project Without Allocation")
        month = lines.report_month
        year = lines.report_year
        save_report = lines.save_report
        bold = workbook.add_format({'bold': True, 'border': 1})
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        self._get_report_header(sheet, bold)
        self._get_report_body(sheet, number_format, month, year, save_report)
        self._get_report_header_without_alloc(sheet1, bold)
        self._get_report_body_without_alloc(sheet1)
