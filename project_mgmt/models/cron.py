# -*- coding: utf-8 -*-

from odoo import models, fields
import xlsxwriter
from io import BytesIO
import base64
from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from babel.numbers import format_currency

import logging

_logger = logging.getLogger(__name__)


class ProjectInherit(models.Model):
    _inherit = 'project.project'

    def _cron_project_report_accounts_team(self):
        today = fields.Date.today()
        month_second = today + relativedelta(day=2)
        month_16 = today + relativedelta(day=16)
        month_last = today + relativedelta(day=31)
        email_project_report_account = self.env['project.report.email'].search([('report_type','=','project_report_account')]).employee_id.mapped('work_email')
        project = self.env['project.project'].sudo().search([]).filtered(lambda proj: proj.create_date.date().month == today.month and proj.create_date.date().year == today.year and proj.state in ['active', 'closed', 'on_hold'])
        if project and (today == month_second or today == month_16 or today == month_last):
            message_body = 'This month Project Report:'
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'Project ID' + '</th>'\
                                '<th>' + 'Location ID' + '</th>'\
                                '<th>' + 'Intra Company' + '</th>'\
                                '<th>' + 'Project Name' + '</th>'\
                                '<th>' + 'Customer Name' + '</th>'\
                                '<th>' + 'Billing Location' + '</th>'\
                                '<th>' + 'Contrct Signing Entity' + '</th>'\
                                '<th>' + 'Contract Execution Entity' + '</th>'\
                                '<th>' + 'Project Start Date' + '</th>'\
                                '<th>' + 'Project End Date' + '</th>'\
                                '<th>' + 'Project Status' + '</th>'\
                            '</tr>'
            if email_project_report_account:
                project_count = 1
                for rec in project:
                    intra_company = rec.sale_order_id.group_multi_company if rec.sale_order_id else ''
                    contract_execution = rec.sale_order_id.company_sign_id.name if rec.sale_order_id else ''
                    contract_sign = rec.sale_order_id.contract_sign_id.name if rec.sale_order_id else ''
                    message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(project_count) + '</td>'\
                                    '<td>' + str(rec.abbreviated_name) + '</td>'\
                                    '<td>' + str(rec.company_id.name) + '</td>'\
                                    '<td>' + str(intra_company) + '</td>'\
                                    '<td>' + str(rec.name) + '</td>'\
                                    '<td>' + str(rec.partner_id.name) + '</td>'\
                                    '<td>' + str(rec.payroll_loc.name) + '</td>'\
                                    '<td>' + str(contract_sign) + '</td>'\
                                    '<td>' + str(contract_execution) + '</td>'\
                                    '<td>' + str(rec.actual_start_date) + '</td>'\
                                    '<td>' + str(rec.actual_end_date) + '</td>'\
                                    '<td>' + str(rec.state.capitalize()) + '</td>'\
                                '</tr>'
                    project_count += 1
                message_body += '</table>' + '<br/>' + '<br/>'
                template_values = {
                    'subject': 'This Month Project Report',
                    'body_html': message_body,
                    'email_from': 'unity@e-zest.in',
                    'email_to': ','.join(i for i in email_project_report_account),
                    'email_cc': 'unity@e-zest.in',
                    'auto_delete': False,
                }
                self.env['mail.mail'].create(template_values).sudo().send()

    def _cron_project_report_milestone_summary(self):
        today = fields.Date.today()
        c_month = today.month
        c_year = today.year
        start_date = False
        end_date = False
        milestone_report = self.env['milestone.difference.report'].create({
            'date': fields.Date.today()
        })
        difference_data = []
        if c_month >= 4:
            c_year = c_year
            n_year = c_year + 1
            start_date = datetime.strptime('01-04-%s' % (c_year), '%d-%m-%Y').date()
            end_date = datetime.strptime('31-03-%s' % (n_year), '%d-%m-%Y').date()
        else:
            c_year = c_year
            p_year = c_year - 1
            start_date = datetime.strptime('01-04-%s' % (p_year), '%d-%m-%Y').date()
            end_date = datetime.strptime('31-03-%s' % (c_year), '%d-%m-%Y').date()
        email_project_report_milestone = self.env['project.report.email'].search([('report_type', '=', 'milestone_summary')]).employee_id.mapped('work_email')
        order_line = self.env['sale.order.line'].sudo().search([('display_type', '!=', 'line_section'), ('state', 'not in', ['cancel']), ('price_total', '>', 0), ('date_target', '>=', start_date), ('date_target', '<=', end_date)])
        order_line = order_line.filtered(lambda line: line.order_id.group_multi_company is False)
        order_line_sbu = list(set(order_line.mapped('sbu_name')))
        color = {0: '#faebd7', 1: '#f0f8ff', 2: '#f5f5dc', 3: '#fff8dc', 4: '#c2eae18f', 5: '#bdbdbd8f', 6: '#69a6ad6b', 7: '#62ad7d85'}
        previous_day = fields.Date.today() - timedelta(days=1)
        previous_report = self.env['milestone.difference.report'].search([('date', '=', previous_day)], limit=1)
        if not previous_report:
            previous_day = fields.Date.today() - timedelta(days=2)
            previous_report = self.env['milestone.difference.report'].search([('date', '=', previous_day)], limit=1)
        if order_line and email_project_report_milestone:
            financial_month = list(OrderedDict(((start_date + timedelta(i)).strftime(r"%B-%y"), None) for i in range((end_date - start_date).days)).keys())
            fin_total_amount = order_line.mapped('amount_inr')
            fin_total_amount = sum(fin_total_amount)
            message_body = 'Milestone Summary Report:'
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'
            message_body += '<th>' + 'Month' + '</th>'
            color_count = 0
            if previous_report:
                bck_color = color.get(color_count)
                message_body += '<th colspan="2" style="background-color:%s">' % (bck_color) + 'Total' + '</th>'
                color_count = 1
                for sbu in order_line_sbu:
                    bck_color = color.get(color_count)
                    message_body += '<th colspan="2" style="background-color:%s">' % (bck_color) + str(sbu) + '</th>'
                    color_count += 1
                message_body += '<tr><td></td>'
                message_body += '<td><b>Total</b></td><td><b>Difference</b></td>'
                for sbu in order_line_sbu:
                    message_body += '<td><b>Total</b></td><td><b>Difference</b></td>'
                message_body += '</tr>'
                prev_milestone = previous_report.milestone_ids
                for fin in financial_month:
                    total = []
                    message_body += '<tr style="text-align:center;">'\
                                    '<td><b>' + fin + '</b></td>'
                    color_count = 0
                    #Total Computation
                    for sbu in order_line_sbu:
                        amount_total = []
                        for rec in order_line:
                            fin_month = datetime.strptime(fin, '%B-%y').date()
                            if rec.sbu_name == sbu and rec.date_target.month == fin_month.month and rec.date_target.year == fin_month.year:
                                amount_total.append(rec.amount_inr) if rec.amount_inr else 0.0
                        amount_total = sum(amount_total)
                        total.append(amount_total)
                    #First Total
                    total = sum(total)
                    total_diff = prev_milestone.filtered(lambda miles: miles.month_name == fin and miles.sbu == 'total')
                    total_diff = total_diff.total
                    total_diff_final1 = total - total_diff
                    difference_data.append({'month_name': fin, 'sbu': 'total', 'total': total, 'difference_amt': total_diff_final1})
                    bck_color = color.get(color_count)
                    # total = format_currency(round(total, 2), 'INR', locale='en_IN').split()
                    # total_diff_final = format_currency(round(total_diff_final, 2), 'INR', locale='en_IN').split()
                    total = "{:0,.2f}".format(float(round(total, 2)))
                    total = total.split('.')[0]
                    total_diff_final = "{:0,.2f}".format(float(round(total_diff_final1, 2)))
                    total_diff_final = total_diff_final.split('.')[0]
                    if round(float(total_diff_final1), 2) > 0:
                        diff_color = '#6f8636'
                    elif round(float(total_diff_final1), 2) < 0:
                        diff_color = '#e65e1d'
                    elif round(float(total_diff_final1), 2) == 0:
                        diff_color = '#736d6d'
                    else:
                        diff_color = bck_color
                    message_body += '<td style="background-color:%s"><b>' % (bck_color) + str(total) + '</b></td>'
                    message_body += '<td style="background-color:%s"><b>' % (diff_color) + str(total_diff_final) + '</b></td>'
                    # Then SBU
                    color_count = 1
                    for sbu in order_line_sbu:
                        amount_total = []
                        for rec in order_line:
                            fin_month = datetime.strptime(fin, '%B-%y').date()
                            if rec.sbu_name == sbu and rec.date_target.month == fin_month.month and rec.date_target.year == fin_month.year:
                                amount_total.append(rec.amount_inr) if rec.amount_inr else 0.0
                        amount_total = sum(amount_total)
                        milestn = prev_milestone.filtered(lambda miles: miles.month_name == fin and miles.sbu == sbu)
                        amount_total_diff = milestn.total
                        amount_total_diff_finl = amount_total - amount_total_diff
                        bck_color = color.get(color_count)
                        # amount = format_currency(round(amount_total, 2), 'INR', locale='en_IN').split()
                        # amount_diff_finl = format_currency(round(amount_total_diff_finl, 2), 'INR', locale='en_IN').split()
                        amount = "{:0,.2f}".format(float(round(amount_total, 2)))
                        amount = amount.split('.')[0]
                        amount_diff_finl = "{:0,.2f}".format(float(round(amount_total_diff_finl, 2)))
                        amount_diff_finl = amount_diff_finl.split('.')[0]
                        if round(float(amount_total_diff_finl), 2) == 0:
                            amount_diff_finl = 0
                        message_body += '<td style="background-color:%s">' % (bck_color) + str(amount) + '</td>'
                        if round(float(amount_total_diff_finl), 2) > 0:
                            diff_color = '#6f8636'
                        elif round(float(amount_total_diff_finl), 2) < 0:
                            diff_color = '#e65e1d'
                        elif round(float(amount_total_diff_finl), 2) == 0:
                            diff_color = '#736d6d'
                        else:
                            diff_color = bck_color
                        message_body += '<td style="background-color:%s">' % (diff_color) + str(amount_diff_finl) + '</td>'
                        color_count += 1
                        difference_data.append({'month_name': fin, 'sbu': sbu, 'total': amount_total, 'difference_amt': amount_total_diff_finl})
                message_body += '<tr style="text-align:center;">'\
                            '<td><b>' + 'Total' + '</b></td>'
                # FInal Total First Total
                color_count = 0
                bck_color = color.get(color_count)
                fin_total_diff = prev_milestone.filtered(lambda miles: miles.month_name == 'total' and miles.sbu == 'total')
                fin_total_diff = fin_total_diff.total
                fin_total_diff_finl1 = fin_total_amount - fin_total_diff
                difference_data.append({'month_name': 'total', 'sbu': 'total', 'total': fin_total_amount, 'difference_amt': fin_total_diff_finl1})
                # fin_total = format_currency(round(fin_total_amount, 2), 'INR', locale='en_IN').split()
                # fin_total_diff_finl = format_currency(round(fin_total_diff_finl, 2), 'INR', locale='en_IN').split()
                fin_total = "{:0,.2f}".format(float(round(fin_total_amount, 2)))
                fin_total = fin_total.split('.')[0]
                fin_total_diff_finl = "{:0,.2f}".format(float(round(fin_total_diff_finl1, 2)))
                fin_total_diff_finl = fin_total_diff_finl.split('.')[0]
                if round(float(fin_total_diff_finl1), 2) > 0:
                    diff_color = '#6f8636'
                elif round(float(fin_total_diff_finl1), 2) < 0:
                    diff_color = '#e65e1d'
                elif round(float(fin_total_diff_finl1), 2) == 0:
                    diff_color = '#736d6d'
                else:
                    diff_color = bck_color
                message_body += '<td style="background-color:%s"><b>' % (bck_color) + str(fin_total) + '</b></td>'
                message_body += '<td style="background-color:%s"><b>' % (diff_color) + str(fin_total_diff_finl) + '</b></td>'
            
                # FInal Total Then SBU
                color_count = 1
                for sbu in order_line_sbu:
                    total_amount = order_line.filtered(lambda line: line.sbu_name == sbu)
                    total_amount = total_amount.mapped('amount_inr')
                    total_amount = sum(total_amount)
                    total_amount_diff = prev_milestone.filtered(lambda miles: miles.month_name == 'total' and miles.sbu == sbu)
                    total_amount_diff = total_amount_diff.total
                    total_amount_diff_finl1 = total_amount - total_amount_diff
                    bck_color = color.get(color_count)
                    difference_data.append({'month_name': 'total', 'sbu': sbu, 'total': total_amount, 'difference_amt': total_amount_diff_finl1})
                    # total_amount = format_currency(round(total_amount, 2), 'INR', locale='en_IN').split()
                    # total_amount_diff_finl = format_currency(round(total_amount_diff_finl, 2), 'INR', locale='en_IN').split()
                    total_amount = "{:0,.2f}".format(float(round(total_amount, 2)))
                    total_amount = total_amount.split('.')[0]
                    total_amount_diff_finl = "{:0,.2f}".format(float(round(total_amount_diff_finl1, 2)))
                    total_amount_diff_finl = total_amount_diff_finl.split('.')[0]
                    if round(float(total_amount_diff_finl1), 2) > 0:
                        diff_color = '#6f8636'
                    elif round(float(total_amount_diff_finl1), 2) < 0:
                        diff_color = '#e65e1d'
                    elif round(float(total_amount_diff_finl1), 2) == 0:
                        diff_color = '#736d6d'
                    else:
                        diff_color = bck_color
                    message_body += '<td style="background-color:%s"><b>' % (bck_color) + str(total_amount) + '</b></td>'
                    message_body += '<td style="background-color:%s"><b>' % (diff_color) + str(total_amount_diff_finl) + '</b></td>'
                    color_count += 1
                milestone_report.milestone_ids = [(0, 0, i) for i in difference_data]
            else:
                bck_color = color.get(color_count)
                message_body += '<th style="background-color:%s">' % (bck_color) + 'Total' + '</th>'
                color_count = 1
                for sbu in order_line_sbu:
                    bck_color = color.get(color_count)
                    message_body += '<th style="background-color:%s">' % (bck_color) + str(sbu) + '</th>'
                    color_count += 1
                for fin in financial_month:
                    total = []
                    message_body += '<tr style="text-align:center;">'\
                                    '<td><b>' + fin + '</b></td>'
                    for sbu in order_line_sbu:
                        amount_total = []
                        for rec in order_line:
                            fin_month = datetime.strptime(fin, '%B-%y').date()
                            if rec.sbu_name == sbu and rec.date_target.month == fin_month.month and rec.date_target.year == fin_month.year:
                                amount_total.append(rec.amount_inr) if rec.amount_inr else 0.0
                        amount_total = sum(amount_total)
                        total.append(amount_total)
                    color_count = 0
                    total = sum(total)
                    difference_data.append({'month_name': fin, 'sbu': 'total', 'total': total})
                    bck_color = color.get(color_count)
                    # total = format_currency(round(total, 2), 'INR', locale='en_IN').split()
                    total = "{:0,.2f}".format(float(round(total, 2)))
                    total = total.split('.')[0]
                    message_body += '<td style="background-color:%s"><b>' % (bck_color) + str(total) + '</b></td>'
                    color_count = 1
                    for sbu in order_line_sbu:
                        amount_total = []
                        for rec in order_line:
                            fin_month = datetime.strptime(fin, '%B-%y').date()
                            if rec.sbu_name == sbu and rec.date_target.month == fin_month.month and rec.date_target.year == fin_month.year:
                                amount_total.append(rec.amount_inr) if rec.amount_inr else 0.0
                        amount_total = sum(amount_total)
                        bck_color = color.get(color_count)
                        # amount = format_currency(round(amount_total, 2), 'INR', locale='en_IN').split()
                        amount = "{:0,.2f}".format(float(round(amount_total, 2)))
                        amount = amount.split('.')[0]
                        message_body += '<td style="background-color:%s">' % (bck_color) + str(amount) + '</td>'
                        color_count += 1
                        difference_data.append({'month_name': fin, 'sbu': sbu, 'total': amount_total})
                message_body += '<tr style="text-align:center;">'\
                                '<td><b>' + 'Total' + '</b></td>'
                color_count = 0
                bck_color = color.get(color_count)
                difference_data.append({'month_name': 'total', 'sbu': 'total', 'total': fin_total_amount})
                # fin_total = format_currency(round(fin_total_amount, 2), 'INR', locale='en_IN').split()
                fin_total = "{:0,.2f}".format(float(round(fin_total_amount, 2)))
                fin_total = fin_total.split('.')[0]
                message_body += '<td style="background-color:%s"><b>' % (bck_color) + str(fin_total) + '</b></td>'
                color_count = 1
                for sbu in order_line_sbu:
                    total_amount = order_line.filtered(lambda line: line.sbu_name == sbu)
                    total_amount = total_amount.mapped('amount_inr')
                    total_amount = sum(total_amount)
                    bck_color = color.get(color_count)
                    difference_data.append({'month_name': 'total', 'sbu': sbu, 'total': total_amount})
                    # total_amount = format_currency(round(total_amount, 2), 'INR', locale='en_IN').split()
                    total_amount = "{:0,.2f}".format(float(round(total_amount, 2)))
                    total_amount = total_amount.split('.')[0]
                    message_body += '<td style="background-color:%s"><b>' % (bck_color) + str(total_amount) + '</b></td>'
                    color_count += 1
                milestone_report.milestone_ids = [(0, 0, i) for i in difference_data]
            # output = BytesIO()
            # workbook = xlsxwriter.Workbook(output)
            # sheet = workbook.add_worksheet("Milestone Summary Today %s" % (fields.Date.today().strftime('%d-%b-%Y')))
            # bold = workbook.add_format({'bold': True})
            # sheet.write(0, 1, 'Total', bold)
            # col_count = 2
            # row_count = 0
            # for fin in financial_month:
            #     sheet.write(row_count, col_count, fin, bold)
            #     col_count += 1
            # row_count = 1
            # col_count = 2
            # fin_total = []
            # for fin in financial_month:
            #     total = []
            #     for rec in order_line:
            #         fin_month = datetime.strptime(fin, '%B-%y').date()
            #         if rec.date_target.month == fin_month.month and rec.date_target.year == fin_month.year:
            #             total.append(rec.amount_inr) if rec.amount_inr else 0.0
            #     total = sum(total)
            #     fin_total.append(total)
            #     sheet.write(row_count, col_count, total, bold)
            #     col_count += 1
            # sheet.write(1, 1, sum(fin_total), bold)
            # row_count = 2
            # col_count = 2
            # sheet.write(1, 0, 'Total', bold)
            # for sbu in order_line_sbu:
            #     sheet.write(row_count, 0, sbu, bold)
            #     col_count = 1
            #     total_amount = []
            #     for fin in financial_month:
            #         amount_total = []
            #         for rec in order_line:
            #             fin_month = datetime.strptime(fin, '%B-%y').date()
            #             if rec.sbu_name == sbu and rec.date_target.month == fin_month.month and rec.date_target.year == fin_month.year:
            #                 amount_total.append(rec.amount_inr) if rec.amount_inr else 0.0
            #         amount_total = sum(amount_total)
            #         total_amount.append(amount_total)
            #         sheet.write(row_count, col_count, amount_total)
            #         col_count += 1
            #     sheet.write(row_count, 1, sum(total_amount), bold)
            #     row_count += 1
            # workbook.close()
            # content = output.getvalue()
            # b64_xlsx = base64.b64encode(content)
            # attachment_name_operation_summary = 'Milestone_Summary_Report'
            # attachment_operation_summary = {
            #     'name': attachment_name_operation_summary + '.xlsx',
            #     'description': attachment_name_operation_summary,
            #     'type': 'binary',
            #     'datas': b64_xlsx,
            #     'store_fname': attachment_name_operation_summary,
            #     'res_model': 'project.project',
            #     'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            # }
            # previous_report.unlink()
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Month Wise Revenue - %s' % fields.Date.today().strftime('%d-%b-%Y'),
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_project_report_milestone),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
                # 'attachment_ids': [(0, 0, attachment_operation_summary)]
            }
            self.env['mail.mail'].create(template_values).sudo().send()
            # attach = self.env['ir.attachment'].sudo().search([('res_model', '=', 'project.project'), ('description', '=', attachment_name_operation_summary)])
            # attach.sudo().unlink()

    def _cron_project_report_per_sbu_email(self):
        email_unassigned_today_des = self.env['project.report.email'].search([('report_type','=','unassigned_today_des')]).employee_id.mapped('work_email')
        email_unassigned_today_dpes = self.env['project.report.email'].search([('report_type','=','unassigned_today_dpes')]).employee_id.mapped('work_email')
        email_unassigned_today_io = self.env['project.report.email'].search([('report_type','=','unassigned_today_io')]).employee_id.mapped('work_email')
        # Unassigned Today DES Report
        employee_unassign_des = self.env['hr.employee'].search([('project_allocate','<',100),('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']), ('is_ezestian', '=', True), ('company_id', '=', 'e-Zest Solutions Ltd.'), ('department_id', 'ilike', 'BOD / Operations / DES')])
        employee_unassign_dpes = self.env['hr.employee'].search([('project_allocate','<',100),('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']), ('is_ezestian', '=', True), ('company_id', '=', 'e-Zest Solutions Ltd.'), ('department_id', 'ilike', 'BOD / Operations / DPES')])
        employee_unassign_io = self.env['hr.employee'].search([('project_allocate','<',100),('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']), ('is_ezestian', '=', True), ('company_id', '=', 'e-Zest Solutions Ltd.'), ('department_id', 'ilike', 'BOD / Operations / IO')])
        emp_total_unassign_des = self.env['hr.employee'].search([
            ('project_allocate','=',0),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('department_id', 'ilike', 'BOD / Operations / DES'),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        emp_partial_unassign_des = self.env['hr.employee'].search([
            ('project_allocate','>',0),
            ('project_allocate','<',100),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('department_id', 'ilike', 'BOD / Operations / DES'),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        if email_unassigned_today_des and (emp_total_unassign_des or emp_partial_unassign_des):
            message_body = 'Fully Unassigned: %s <br/> Partial Assigned: %s <br/>' % (len(emp_total_unassign_des), len(emp_partial_unassign_des))
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'e-Zestian Name' + '</th>'\
                                '<th>' + 'e-Zestian Status' + '</th>'\
                                '<th>' + 'Manager Name' + '</th>'\
                                '<th>' + 'Primary Skill' + '</th>'\
                                '<th>' + 'Total Experience' + '</th>'\
                                '<th>' + 'SBU' + '</th>'\
                                '<th>' + 'Allocated Percentage' + '</th>'\
                                '<th>' + 'On Bench Since (Days)' + '</th>'\
                                '<th>' + 'Payroll Location of Team Member' + '</th>'\
                                '<th>' + 'Grade' + '</th>'\
                                '<th>' + 'Last Project Name' + '</th>'\
                                '<th>' + 'Assigned Till' + '</th>'\
                                '<th>' + 'Last Billability Status' + '</th>'\
                                '<th>' + 'Comment' + '</th>'\
                            '</tr>'
            if emp_total_unassign_des:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15">' + 'Fully Unallocated' + '</td>'\
                    '</tr>'
                emp_unassign_count = 1
                emp_unassign_sort = [(rec.skills.name, rec) for rec in emp_total_unassign_des if rec.skills]
                emp_unassign_sort.sort()
                emp_unassign = [rec[1] for rec in emp_unassign_sort]
                emp_unassign.extend([rec for rec in emp_total_unassign_des if not rec.skills and (rec.project_assign_till is False or rec.project_assign_till < datetime.today().date())])
                for emp in emp_unassign:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0 and rec.assign_status == 'confirmed']
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0 and rec.assign_status == 'confirmed']
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    if emp.exit_date:
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;">'\
                                        '<td>' + str(emp_unassign_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_unassign_count += 1
            if emp_partial_unassign_des:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15">' + 'Partially Unallocated' + '</td>'\
                    '</tr>'
                emp_partial_unassign_count = 1
                emp_partial_assign_sort = [(rec.skills.name, rec) for rec in emp_partial_unassign_des if rec.skills]
                emp_partial_assign_sort.sort()
                emp_partial_assign = [rec[1] for rec in emp_partial_assign_sort]
                emp_partial_assign.extend([rec for rec in emp_partial_unassign_des if not rec.skills])
                for emp in emp_partial_assign:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0]
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0]
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    if emp.exit_date:
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;">'\
                                        '<td>' + str(emp_unassign_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_partial_unassign_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Unassigned Today Report DES',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_unassigned_today_des),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()
        # # Unassigned Today DPES Report
        emp_total_unassign_dpes = self.env['hr.employee'].search([
            ('project_allocate','=',0),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('department_id', 'ilike', 'BOD / Operations / DPES'),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        emp_partial_unassign_dpes = self.env['hr.employee'].search([
            ('project_allocate','>',0),
            ('project_allocate','<',100),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('department_id', 'ilike', 'BOD / Operations / DPES'),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        if email_unassigned_today_dpes and (emp_total_unassign_dpes or emp_partial_unassign_dpes):
            message_body = 'Fully Unassigned: %s <br/> Partial Assigned: %s <br/>' % (len(emp_total_unassign_dpes), len(emp_partial_unassign_dpes))
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'e-Zestian Name' + '</th>'\
                                '<th>' + 'e-Zestian Status' + '</th>'\
                                '<th>' + 'Manager Name' + '</th>'\
                                '<th>' + 'Primary Skill' + '</th>'\
                                '<th>' + 'Total Experience' + '</th>'\
                                '<th>' + 'SBU' + '</th>'\
                                '<th>' + 'Allocated Percentage' + '</th>'\
                                '<th>' + 'On Bench Since (Days)' + '</th>'\
                                '<th>' + 'Payroll Location of Team Member' + '</th>'\
                                '<th>' + 'Grade' + '</th>'\
                                '<th>' + 'Last Project Name' + '</th>'\
                                '<th>' + 'Date of Relieving' + '</th>'\
                                '<th>' + 'Last Billability Status' + '</th>'\
                                '<th>' + 'Comment' + '</th>'\
                            '</tr>'
            if emp_total_unassign_dpes:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15">' + 'Fully Unallocated' + '</td>'\
                    '</tr>'
                emp_unassign_count = 1
                emp_unassign_sort = [(rec.skills.name, rec) for rec in emp_total_unassign_dpes if rec.skills]
                emp_unassign_sort.sort()
                emp_unassign = [rec[1] for rec in emp_unassign_sort]
                emp_unassign.extend([rec for rec in emp_total_unassign_dpes if not rec.skills and (rec.project_assign_till is False or rec.project_assign_till < datetime.today().date())])
                for emp in emp_unassign:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0 and rec.assign_status == 'confirmed']
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0 and rec.assign_status == 'confirmed']
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    if emp.exit_date:
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;">'\
                                        '<td>' + str(emp_unassign_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_unassign_count += 1
            if emp_partial_unassign_dpes:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15">' + 'Partially Unallocated' + '</td>'\
                    '</tr>'
                emp_partial_unassign_count = 1
                emp_partial_assign_sort = [(rec.skills.name, rec) for rec in emp_partial_unassign_dpes if rec.skills]
                emp_partial_assign_sort.sort()
                emp_partial_assign = [rec[1] for rec in emp_partial_assign_sort]
                emp_partial_assign.extend([rec for rec in emp_partial_unassign_dpes if not rec.skills])
                for emp in emp_partial_assign:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0]
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0]
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    if emp.exit_date:
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;">'\
                                        '<td>' + str(emp_unassign_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_partial_unassign_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Unassigned Today Report DPES',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_unassigned_today_dpes),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()
        # Unassigned Today IO Report
        emp_total_unassign_io = self.env['hr.employee'].search([
            ('project_allocate','=',0),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('department_id', 'ilike', 'BOD / Operations / IO'),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        emp_partial_unassign_io = self.env['hr.employee'].search([
            ('project_allocate','>',0),
            ('project_allocate','<',100),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('department_id', 'ilike', 'BOD / Operations / IO'),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        if email_unassigned_today_io and (emp_total_unassign_io or emp_partial_unassign_io):
            message_body = 'Fully Unassigned: %s <br/> Partial Assigned: %s <br/>' % (len(emp_total_unassign_io), len(emp_partial_unassign_io))
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'e-Zestian Name' + '</th>'\
                                '<th>' + 'e-Zestian Status' + '</th>'\
                                '<th>' + 'Manager Name' + '</th>'\
                                '<th>' + 'Primary Skill' + '</th>'\
                                '<th>' + 'Total Experience' + '</th>'\
                                '<th>' + 'SBU' + '</th>'\
                                '<th>' + 'Allocated Percentage' + '</th>'\
                                '<th>' + 'On Bench Since (Days)' + '</th>'\
                                '<th>' + 'Payroll Location of Team Member' + '</th>'\
                                '<th>' + 'Grade' + '</th>'\
                                '<th>' + 'Last Project Name' + '</th>'\
                                '<th>' + 'Date of Relieving' + '</th>'\
                                '<th>' + 'Last Billability Status' + '</th>'\
                                '<th>' + 'Comment' + '</th>'\
                            '</tr>'
            if emp_total_unassign_io:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15">' + 'Fully Unallocated' + '</td>'\
                    '</tr>'
                emp_unassign_count = 1
                emp_unassign_sort = [(rec.skills.name, rec) for rec in emp_total_unassign_io if rec.skills]
                emp_unassign_sort.sort()
                emp_unassign = [rec[1] for rec in emp_unassign_sort]
                emp_unassign.extend([rec for rec in emp_total_unassign_io if not rec.skills and (rec.project_assign_till is False or rec.project_assign_till < datetime.today().date())])
                for emp in emp_unassign:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0 and rec.assign_status == 'confirmed']
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0 and rec.assign_status == 'confirmed']
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    if emp.exit_date:
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;">'\
                                        '<td>' + str(emp_unassign_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_unassign_count += 1
            if emp_partial_unassign_io:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15">' + 'Partially Unallocated' + '</td>'\
                    '</tr>'
                emp_partial_unassign_count = 1
                emp_partial_assign_sort = [(rec.skills.name, rec) for rec in emp_partial_unassign_io if rec.skills]
                emp_partial_assign_sort.sort()
                emp_partial_assign = [rec[1] for rec in emp_partial_assign_sort]
                emp_partial_assign.extend([rec for rec in emp_partial_unassign_io if not rec.skills])
                for emp in emp_partial_assign:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0]
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0]
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    if emp.exit_date:
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;">'\
                                        '<td>' + str(emp_unassign_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_partial_unassign_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Unassigned Today Report IO',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_unassigned_today_io),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

    def _cron_project_ryg_summary(self):
        ryg_email = self.env['project.report.email'].search([('report_type','=','project_ryg')]).employee_id.mapped('work_email')
        today = fields.Date.today()
        if today.weekday() == 0:
            last_week_from = today - timedelta(7)
            last_week_to = last_week_from + timedelta(6)
            project = self.env['project.project'].search([('actual_start_date', '<=', today), ('actual_end_date','=',False), ('state','=','active'), ('ryg_review', '=', 'yes')])
            ryg_updated = [r for rec in project for r in rec.ryg_id if rec.ryg_id and r.start_date == last_week_from]
            ryg_not_updated = [p for p in project if not p.ryg_id.filtered(lambda self: self.start_date == last_week_from and self.end_date == last_week_to)]
            green_count = [g for g in ryg_updated if g.ryg_status == 'green']
            yellow_count = [y for y in ryg_updated if y.ryg_status == 'yellow']
            red_count = [r for r in ryg_updated if r.ryg_status == 'red']
            message_body = 'Hi All<br/><br/>'
            message_body += 'Summary of Project Review status (RYG) for %s to %s as below' % (last_week_from, last_week_to)
            message_body += '<br/><br/><p>Total Project Covered - %s (Project delivered from e-Zest)</p>'\
                '<p>Total No. of Projects for which review status is updated - %s</p>'\
                '<p>Total No. of Projects for which review status is RED - %s</p>'\
                '<p>Total No. of Projects for which review status is YELLOW - %s</p>'\
                '<p>Total No. of Projects for which review status is GREEN - %s</p>'\
                '<p>Total No. of Projects for which review status is not updated - %s</p>' % (len(project), len(ryg_updated), len(red_count), len(yellow_count), len(green_count), len(list(set(ryg_not_updated))))
            if green_count or yellow_count or red_count or ryg_not_updated:
                message_body += '<br/><br/>Refer following projects for which status is RED, YELLOW & GREEN<br/>'
                message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
                message_body += '<tr style="text-align:center;">'\
                                    '<th>' + 'Sr. No.' + '</th>'\
                                    '<th>' + 'Business Unit' + '</th>'\
                                    '<th>' + 'Project Code' + '</th>'\
                                    '<th>' + 'Project Name' + '</th>'\
                                    '<th>' + 'Project Manager' + '</th>'\
                                    '<th>' + 'Status' + '</th>'\
                                    '<th>' + 'Actual Start Date' + '</th>'\
                                    '<th>' + 'Planned End Date' + '</th>'\
                                    '<th>' + 'Risks' + '</th>'\
                                    '<th>' + 'Achievements' + '</th>'\
                                '</tr>'
            if red_count:
                message_body += '<tr style="text-align:center;">'\
                            '<td colspan="8">' + 'RED Status' + '</td>'\
                            '</tr>'
                count_red = 1
                for r in red_count:
                    message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(count_red) + '</td>'\
                                    '<td>' + str(r.business_unit.name) + '</td>'\
                                    '<td>' + str(r.project_code) + '</td>'\
                                    '<td>' + str(r.project_id.name) + '</td>'\
                                    '<td>' + str(r.project_manager.name) + '</td>'\
                                    '<td>' + str(r.ryg_status) + '</td>'\
                                    '<td>' + str(r.project_id.actual_start_date) + '</td>'\
                                    '<td>' + str(r.project_id.planned_end_date) + '</td>'\
                                    '<td>' + str(r.remarks) + '</td>'\
                                    '<td>' + str(r.achievement) + '</td>'\
                                '</tr>'
                    count_red += 1
            if yellow_count:
                message_body += '<tr style="text-align:center;">'\
                            '<td colspan="8">' + 'YELLOW Status' + '</td>'\
                            '</tr>'
                count_yellow = 1
                for y in yellow_count:
                    message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(count_yellow) + '</td>'\
                                    '<td>' + str(y.business_unit.name) + '</td>'\
                                    '<td>' + str(y.project_code) + '</td>'\
                                    '<td>' + str(y.project_id.name) + '</td>'\
                                    '<td>' + str(y.project_manager.name) + '</td>'\
                                    '<td>' + str(y.ryg_status) + '</td>'\
                                    '<td>' + str(y.project_id.actual_start_date) + '</td>'\
                                    '<td>' + str(y.project_id.planned_end_date) + '</td>'\
                                    '<td>' + str(y.remarks) + '</td>'\
                                    '<td>' + str(y.achievement) + '</td>'\
                                '</tr>'
                    count_yellow += 1
            if green_count:
                message_body += '<tr style="text-align:center;">'\
                            '<td colspan="8">' + 'GREEN Status' + '</td>'\
                            '</tr>'
                count_green = 1
                for g in green_count:
                    message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(count_green) + '</td>'\
                                    '<td>' + str(g.business_unit.name) + '</td>'\
                                    '<td>' + str(g.project_code) + '</td>'\
                                    '<td>' + str(g.project_id.name) + '</td>'\
                                    '<td>' + str(g.project_manager.name) + '</td>'\
                                    '<td>' + str(g.ryg_status) + '</td>'\
                                    '<td>' + str(g.project_id.actual_start_date) + '</td>'\
                                    '<td>' + str(g.project_id.planned_end_date) + '</td>'\
                                    '<td>' + str(g.remarks) + '</td>'\
                                    '<td>' + str(g.achievement) + '</td>'\
                                '</tr>'
                    count_green += 1
            if ryg_not_updated:
                message_body += '<tr style="text-align:center;">'\
                            '<td colspan="8">' + 'RYG Not Updated' + '</td>'\
                            '</tr>'
                count_not_ryg = 1
                for n in ryg_not_updated:
                    message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(count_not_ryg) + '</td>'\
                                    '<td>' + str(n.department_id.name) + '</td>'\
                                    '<td>' + str(n.abbreviated_name) + '</td>'\
                                    '<td>' + str(n.name) + '</td>'\
                                    '<td>' + str(n.user_id.name) + '</td>'\
                                    '<td>' + str('-') + '</td>'\
                                    '<td>' + str(n.actual_start_date) + '</td>'\
                                    '<td>' + str(n.planned_end_date) + '</td>'\
                                    '<td>' + str('-') + '</td>'\
                                    '<td>' + str('-') + '</td>'\
                                '</tr>'
                    count_not_ryg += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            message_body += 'Thanks<br/>Operations Team<br/>'
            template_values = {
                'subject': 'Summary of Project Review status (RYG) for %s to %s' % (last_week_from, last_week_to),
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in ryg_email),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

    def _cron_project_report_email(self):
        email_internal = self.env['project.report.email'].search([('report_type','=','internal_project')]).employee_id.mapped('work_email')
        email_unbilled = self.env['project.report.email'].search([('report_type','=','unbilled_today')]).employee_id.mapped('work_email')
        email_project_ext = self.env['project.report.email'].search([('report_type','=','project_emp_ext')]).employee_id.mapped('work_email')
        email_alloc_unassign = self.env['project.report.email'].search([('report_type','=','unassigned_today')]).employee_id.mapped('work_email')
        email_missing_milestone = self.env['project.report.email'].search([('report_type','=','missing_milestone')]).employee_id.mapped('work_email')
        email_alloc_ux = self.env['project.report.email'].search([('report_type','=','current_alloc_ux')]).employee_id.mapped('work_email')
        email_alloc_io = self.env['project.report.email'].search([('report_type','=','current_alloc_io')]).employee_id.mapped('work_email')
        email_active_cons = self.env['project.report.email'].search([('report_type','=','active_consultant')]).employee_id.mapped('work_email')
        email_onbench_contractor = self.env['project.report.email'].search([('report_type','=','onbench_contractor')]).employee_id.mapped('work_email')
        exec_email = self.env['project.report.email'].search([('report_type','=','operations_summary')]).employee_id.mapped('work_email')
        # Internal Project
        # non_billable_project = self.search([('billable','=',False),('state','=','active')])
        # if email_internal and non_billable_project:
        #     internal_count = 1
        #     message_body = '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
        #     message_body += '<tr style="text-align:center;">'\
        #                         '<th>' + 'Sr. No.' + '</th>'\
        #                         '<th>' + 'Project Name' + '</th>'\
        #                         '<th>' + 'e-Zestian Name' + '</th>'\
        #                         '<th>' + 'Primary Skill' + '</th>'\
        #                         '<th>' + 'Skills' + '</th>'\
        #                         '<th>' + 'e-Zestian Total Experience' + '</th>'\
        #                         '<th>' + 'Allocation Start Date' + '</th>'\
        #                         '<th>' + 'Allocation End Date' + '</th>'\
        #                         '<th>' + 'Allocation Percentage' + '</th>'\
        #                         '<th>' + 'SBU' + '</th>'\
        #                     '</tr>'
        #     for rec in non_billable_project:
        #         for alloc in rec.assignment_ids:
        #             message_body += '<tr style="text-align:center;">'\
        #                                 '<td>' + str(internal_count) + '</td>'\
        #                                 '<td>' + str(alloc.project_id.name) + '</td>'\
        #                                 '<td>' + str(alloc.employee_id.name) + '</td>'\
        #                                 '<td>' + str(alloc.employee_id.skills.name)+ '</td>'\
        #                                 '<td>' + str(alloc.employee_id.employee_skills) + '</td>'\
        #                                 '<td>' + str(alloc.employee_id.total_exp) + '</td>'\
        #                                 '<td>' + str(alloc.start_date) + '</td>'\
        #                                 '<td>' + str(alloc.end_date) + '</td>'\
        #                                 '<td>' + str(alloc.allocation_percentage) + '</td>'\
        #                                 '<td>' + str(alloc.project_id.department_id.name) + '</td>'\
        #                                 '<td>' + str(alloc.project_id.user_id.name) + '</td>'\
        #                             '</tr>'
        #             internal_count += 1
        #     message_body += '</table>' + '<br/>' + '<br/>'
        #     template_values = {
        #         'subject': 'Internal Project Report',
        #         'body_html': message_body,
        #         'email_from': 'unity@e-zest.in',
        #         'email_to': ','.join(i for i in email_internal),
        #         'email_cc': 'unity@e-zest.in',
        #         'auto_delete': False,
        #     }
        #     self.env['mail.mail'].create(template_values).sudo().send()

        # Project Employee Role Require Extention Report
        # emp_project_ext = self.env['project.assignment'].search([('end_date','<=',fields.Date.today())])
        # if email_project_ext and emp_project_ext:
        #     project_ext_count = 1
        #     message_body = '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
        #     message_body += '<tr style="text-align:center;">'\
        #                         '<th>' + 'Sr. No.' + '</th>'\
        #                         '<th>' + 'Project Name' + '</th>'\
        #                         '<th>' + 'e-Zestian Name' + '</th>'\
        #                         '<th>' + 'e-Zestian Total Experience' + '</th>'\
        #                         '<th>' + 'SBU' + '</th>'\
        #                         '<th>' + 'Expected Start Date' + '</th>'\
        #                         '<th>' + 'Expected End Date' + '</th>'\
        #                         '<th>' + 'Allocation Percentage' + '</th>'\
        #                         '<th>' + 'Is Resource Billable' + '</th>'\
        #                     '</tr>'
        #     for alloc in emp_project_ext:
        #         if alloc.project_id.state == 'active':
        #             message_body += '<tr style="text-align:center;">'\
        #                                 '<td>' + str(project_ext_count) + '</td>'\
        #                                 '<td>' + str(alloc.project_id.name) + '</td>'\
        #                                 '<td>' + str(alloc.employee_id.name) + '</td>'\
        #                                 '<td>' + str(alloc.employee_id.total_exp) + '</td>'\
        #                                 '<td>' + str(alloc.project_id.department_id.name) + '</td>'\
        #                                 '<td>' + str(alloc.project_id.planned_start_date) + '</td>'\
        #                                 '<td>' + str(alloc.project_id.planned_end_date) + '</td>'\
        #                                 '<td>' + str(alloc.allocation_percentage) + '</td>'\
        #                                 '<td>' + str(alloc.project_bill_status.capitalize()) + '</td>'\
        #                             '</tr>'
        #             project_ext_count += 1
        #     message_body += '</table>' + '<br/>' + '<br/>'
        #     template_values = {
        #         'subject': 'Project Employee Role Require Extention Report',
        #         'body_html': message_body,
        #         'email_from': 'unity@e-zest.in',
        #         'email_to': ','.join(i for i in email_project_ext),
        #         'email_cc': 'unity@e-zest.in',
        #         'auto_delete': False,
        #     }
        #     self.env['mail.mail'].create(template_values).sudo().send()

        # --- EXECUTIVE REPORT ---
        # total ezestian
        emp_company = self.env['hr.employee'].search_count([('joining_date','!=',False)])
        emp_ltd_company = self.env['hr.employee'].search_count([('company_id','=','e-Zest Solutions Ltd.'),('joining_date','!=',False)])
        emp_inc_company = self.env['hr.employee'].search_count([('company_id','=','e-Zest Solutions Inc.'),('joining_date','!=',False)])
        emp_gmbh_company = self.env['hr.employee'].search_count([('company_id','=','e-Zest Solutions GmbH'),('joining_date','!=',False)])
        emp_uk_company = self.env['hr.employee'].search_count([('company_id','=','e-Zest Solutions Ltd (UK)'),('joining_date','!=',False)])
        emp_austria_company = self.env['hr.employee'].search_count([('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),('joining_date','!=',False)])

        emp_consultant = self.env['hr.employee'].search_count([('employee_category','=','Contractor'),('joining_date','!=',False)])
        emp_rookie = self.env['hr.employee'].search_count([('employee_category','=','Intern'),('joining_date','!=',False)])
        emp_ezestian = self.env['hr.employee'].search_count([('employee_category','=','eZestian'),('joining_date','!=',False)])

        # total Deployable
        emp_company_deployable = self.env['hr.employee'].search_count([
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_ltd_company_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_inc_company_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_gmbh_company_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_uk_company_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_austria_company_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_consultant_deployable = self.env['hr.employee'].search_count([
                                ('employee_category','=','Contractor'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_rookie_deployable = self.env['hr.employee'].search_count([
                                ('employee_category','=','Intern'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_ezestian_deployable = self.env['hr.employee'].search_count([
                                ('employee_category','=','eZestian'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # total Non Deployable
        emp_company_non_deployable = self.env['hr.employee'].search_count([
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_ltd_company_non_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_inc_company_non_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_uk_company_non_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_gmbh_company_non_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_austria_company_non_deployable = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_consultant_non_deployable = self.env['hr.employee'].search_count([
                                ('employee_category','=','Contractor'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_rookie_non_deployable = self.env['hr.employee'].search_count([
                                ('employee_category','=','Intern'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_ezestian_non_deployable = self.env['hr.employee'].search_count([
                                ('employee_category','=','eZestian'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # currently company allocated
        emp_company_allocated_100 = self.env['hr.employee'].search_count([
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_company_unallocated = self.env['hr.employee'].search_count([
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_company_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_company_allocated_partial = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_company_allocated_partial = sum([i.project_allocate for i in emp_company_allocated_partial]) // 100
        # currently ltd company allocated
        emp_ltd_company_allocated_100 = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_ltd_company_unallocated = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_ltd_company_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_ltd_company_allocated_partial = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_ltd_company_allocated_partial = sum([i.project_allocate for i in emp_ltd_company_allocated_partial]) // 100
        # currently inc company allocated
        emp_inc_company_allocated_100 = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_inc_company_unallocated = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_inc_company_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_inc_company_allocated_partial = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_inc_company_allocated_partial = sum([i.project_allocate for i in emp_inc_company_allocated_partial]) // 100
        # currently uk company allocated
        emp_uk_company_allocated_100 = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_uk_company_unallocated = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_uk_company_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_uk_company_allocated_partial = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_uk_company_allocated_partial = sum([i.project_allocate for i in emp_uk_company_allocated_partial]) // 100
        # currently gmbh company allocated
        emp_gmbh_company_allocated_100 = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_gmbh_company_unallocated = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_gmbh_company_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_gmbh_company_allocated_partial = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_gmbh_company_allocated_partial = sum([i.project_allocate for i in emp_gmbh_company_allocated_partial]) // 100
        # currently austria company allocated
        emp_austria_company_allocated_100 = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_austria_company_unallocated = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_austria_company_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_austria_company_allocated_partial = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate', '<', 100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_austria_company_allocated_partial = sum([i.project_allocate for i in emp_austria_company_allocated_partial]) // 100
        # currently consultant allocated
        emp_consultant_allocated_100 = self.env['hr.employee'].search_count([
                                ('employee_category','=','Contractor'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_consultant_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('employee_category','=','Contractor'),
                                ('joining_date','!=',False),
                                ('project_allocate', '<', 100),
                                ('project_allocate', '>', 0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_consultant_allocated_partial = self.env['hr.employee'].search([
                                ('employee_category','=','Contractor'),
                                ('joining_date','!=',False),
                                ('project_allocate', '<', 100),
                                ('project_allocate', '>', 0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_consultant_allocated_partial = sum([i.project_allocate for i in emp_consultant_allocated_partial]) // 100

        emp_consultant_allocated_unallocated = self.env['hr.employee'].search_count([
                                ('employee_category','=','Contractor'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # currently rookie allocated
        emp_rookie_allocated_100 = self.env['hr.employee'].search_count([
                                ('employee_category','=','Intern'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_rookie_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('employee_category','=','Intern'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_rookie_allocated_partial = self.env['hr.employee'].search([
                                ('employee_category','=','Intern'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_rookie_allocated_partial = sum([i.project_allocate for i in emp_rookie_allocated_partial]) // 100

        emp_rookie_allocated_unallocated = self.env['hr.employee'].search_count([
                                ('employee_category','=','Intern'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # currently ezestian allocated
        emp_ezestian_allocated_100 = self.env['hr.employee'].search_count([
                                ('employee_category','=','eZestian'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        emp_ezestian_allocated_partial_count = self.env['hr.employee'].search_count([
                                ('employee_category','=','eZestian'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_ezestian_allocated_partial = self.env['hr.employee'].search([
                                ('employee_category','=','eZestian'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_ezestian_allocated_partial = sum([i.project_allocate for i in emp_ezestian_allocated_partial]) // 100

        emp_ezestian_allocated_unallocated = self.env['hr.employee'].search_count([
                                ('employee_category','=','eZestian'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # currently company resigned/probation/confirmed
        company_resigned = self.env['hr.employee'].search([
                                ('joining_date','!=',False)])
        company_resigned_count = company_resigned.filtered(lambda x: x.resign_date)
        company_resigned = len(company_resigned_count)

        company_probation = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        company_probation_count = company_probation.filtered(lambda x: not x.resign_date)
        company_probation = len(company_probation_count)

        company_confirmed = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('confirmation_status','=','confirmed')])
        company_confirmed_count = company_confirmed.filtered(lambda x: not x.resign_date)
        company_confirmed = len(company_confirmed_count)

        # currently ltd company resigned/probation/confirmed
        company_ltd_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False)])
        company_ltd_resigned_count = company_ltd_resigned.filtered(lambda x: x.resign_date)
        company_ltd_resigned = len(company_ltd_resigned_count)

        company_ltd_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        company_ltd_probation_count = company_ltd_probation.filtered(lambda x: not x.resign_date)
        company_ltd_probation = len(company_ltd_probation_count)

        company_ltd_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('confirmation_status','=','confirmed')])
        company_ltd_confirmed_count = company_ltd_confirmed.filtered(lambda x: not x.resign_date)
        company_ltd_confirmed = len(company_ltd_confirmed_count)

        # currently ltd company resigned/probation/confirmed
        company_inc_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False)])
        company_inc_resigned_count = company_inc_resigned.filtered(lambda x: x.resign_date)
        company_inc_resigned = len(company_inc_resigned_count)

        company_inc_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        company_inc_probation_count = company_inc_probation.filtered(lambda x: not x.resign_date)
        company_inc_probation = len(company_inc_probation_count)

        company_inc_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('confirmation_status','=','confirmed')])
        company_inc_confirmed_count = company_inc_confirmed.filtered(lambda x: not x.resign_date)
        company_inc_confirmed = len(company_inc_confirmed_count)

        # currently uk company resigned/probation/confirmed
        company_uk_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False)])
        company_uk_resigned_count = company_uk_resigned.filtered(lambda x: x.resign_date)
        company_uk_resigned = len(company_uk_resigned_count)

        company_uk_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        company_uk_probation_count = company_uk_probation.filtered(lambda x: not x.resign_date)
        company_uk_probation = len(company_uk_probation_count)

        company_uk_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('confirmation_status','=','confirmed')])
        company_uk_confirmed_count = company_uk_confirmed.filtered(lambda x: not x.resign_date)
        company_uk_confirmed = len(company_uk_confirmed_count)

        # currently gmbh company resigned/probation/confirmed
        company_gmbh_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False)])
        company_gmbh_resigned_count = company_gmbh_resigned.filtered(lambda x: x.resign_date)
        company_gmbh_resigned = len(company_gmbh_resigned_count)

        company_gmbh_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        company_gmbh_probation_count = company_gmbh_probation.filtered(lambda x: not x.resign_date)
        company_gmbh_probation = len(company_gmbh_probation_count)

        company_gmbh_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('confirmation_status','=','confirmed')])
        company_gmbh_confirmed_count = company_gmbh_confirmed.filtered(lambda x: not x.resign_date)
        company_gmbh_confirmed = len(company_gmbh_confirmed_count)

        # currently austria company resigned/probation/confirmed
        company_austria_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False)])
        company_austria_resigned_count = company_austria_resigned.filtered(lambda x: x.resign_date)
        company_austria_resigned = len(company_austria_resigned_count)

        company_austria_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        company_austria_probation_count = company_austria_probation.filtered(lambda x: not x.resign_date)
        company_austria_probation = len(company_austria_probation_count)

        company_austria_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('confirmation_status','=','confirmed')])
        company_austria_confirmed_count = company_austria_confirmed.filtered(lambda x: not x.resign_date)
        company_austria_confirmed = len(company_austria_confirmed_count)

        # currently consultant resigned/probation/confirmed
        emp_consultant_resigned = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','Contractor')])
        emp_consultant_resigned_count = emp_consultant_resigned.filtered(lambda x: x.resign_date)
        emp_consultant_resigned = len(emp_consultant_resigned_count)

        emp_consultant_probation = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','Contractor'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        emp_consultant_probation_count = emp_consultant_probation.filtered(lambda x: not x.resign_date)
        emp_consultant_probation = len(emp_consultant_probation_count)

        emp_consultant_confirmed = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','Contractor'),
                                ('confirmation_status','=','confirmed')])
        emp_consultant_confirmed_count = emp_consultant_confirmed.filtered(lambda x: not x.resign_date)
        emp_consultant_confirmed = len(emp_consultant_confirmed_count)

        # currently rookie resigned/probation/confirmed
        emp_rookie_resigned = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','Intern')])
        emp_rookie_resigned_count = emp_rookie_resigned.filtered(lambda x: x.resign_date)
        emp_rookie_resigned = len(emp_rookie_resigned_count)

        emp_rookie_probation = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','Intern'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        emp_rookie_probation_count = emp_rookie_probation.filtered(lambda x: not x.resign_date)
        emp_rookie_probation = len(emp_rookie_probation_count)

        emp_rookie_confirmed = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','Intern'),
                                ('confirmation_status','=','confirmed')])
        emp_rookie_confirmed_count = emp_rookie_confirmed.filtered(lambda x: not x.resign_date)
        emp_rookie_confirmed = len(emp_rookie_confirmed_count)

        # currently ezestian resigned/probation/confirmed
        emp_ezestian_resigned = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','eZestian')])
        emp_ezestian_resigned_count = emp_ezestian_resigned.filtered(lambda x: x.resign_date)
        emp_ezestian_resigned = len(emp_ezestian_resigned_count)

        emp_ezestian_probation = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','eZestian'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        emp_ezestian_probation_count = emp_ezestian_probation.filtered(lambda x: not x.resign_date)
        emp_ezestian_probation = len(emp_ezestian_probation_count)

        emp_ezestian_confirmed = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('employee_category','=','eZestian'),
                                ('confirmation_status','=','confirmed')])
        emp_ezestian_confirmed_count = emp_ezestian_confirmed.filtered(lambda x: not x.resign_date)
        emp_ezestian_confirmed = len(emp_ezestian_confirmed_count)

        # currently company billed
        emp_company_billable = self.env['hr.employee'].search([
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_company_billable_more_100 = emp_company_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_company_billable_more_100):
            emp_company_billable_more_100_count = sum([i.total_billability for i in emp_company_billable_more_100]) / 100
            emp_company_billable_more_100_len = len(emp_company_billable_more_100)
        else:
            emp_company_billable_more_100_count = 0
            emp_company_billable_more_100_len = 0
        emp_company_billable_100 = emp_company_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_company_billable_100):
            emp_company_billable_100_count = len(emp_company_billable_100)
        else:
            emp_company_billable_100_count = 0
        emp_company_billable_50 = emp_company_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_company_billable_50):
            emp_company_billable_50_count = len(emp_company_billable_50)
        else:
            emp_company_billable_50_count = 0
        emp_company_billable_75 = emp_company_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_company_billable_75):
            emp_company_billable_75_count = len(emp_company_billable_75)
        else:
            emp_company_billable_75_count = 0
        emp_company_billable_25 = emp_company_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_company_billable_25):
            emp_company_billable_25_count = len(emp_company_billable_25)
        else:
            emp_company_billable_25_count = 0
        emp_company_billable_0 = emp_company_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_company_billable_0):
            emp_company_billable_0_count = len(emp_company_billable_0)
        else:
            emp_company_billable_0_count = 0
        # currently company billed
        emp_ltd_company_billable = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_ltd_company_billable_more_100 = emp_ltd_company_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_ltd_company_billable_more_100):
            emp_ltd_company_billable_more_100_count = sum([i.total_billability for i in emp_ltd_company_billable_more_100]) / 100
            emp_ltd_company_billable_more_100_len = len(emp_ltd_company_billable_more_100)
        else:
            emp_ltd_company_billable_more_100_count = 0
            emp_ltd_company_billable_more_100_len = 0
        emp_ltd_company_billable_100 = emp_ltd_company_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_ltd_company_billable_100):
            emp_ltd_company_billable_100_count = len(emp_ltd_company_billable_100)
        else:
            emp_ltd_company_billable_100_count = 0
        emp_ltd_company_billable_50 = emp_ltd_company_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_ltd_company_billable_50):
            emp_ltd_company_billable_50_count = len(emp_ltd_company_billable_50)
        else:
            emp_ltd_company_billable_50_count = 0
        emp_ltd_company_billable_75 = emp_ltd_company_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_ltd_company_billable_75):
            emp_ltd_company_billable_75_count = len(emp_ltd_company_billable_75)
        else:
            emp_ltd_company_billable_75_count = 0
        emp_ltd_company_billable_25 = emp_ltd_company_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_ltd_company_billable_25):
            emp_ltd_company_billable_25_count = len(emp_ltd_company_billable_25)
        else:
            emp_ltd_company_billable_25_count = 0
        emp_ltd_company_billable_0 = emp_ltd_company_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_ltd_company_billable_0):
            emp_ltd_company_billable_0_count = len(emp_ltd_company_billable_0)
        else:
            emp_ltd_company_billable_0_count = 0

        # currently inc company billed
        emp_inc_company_billable = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_inc_company_billable_more_100 = emp_inc_company_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_inc_company_billable_more_100):
            emp_inc_company_billable_more_100_count = sum([i.total_billability for i in emp_inc_company_billable_more_100]) / 100
            emp_inc_company_billable_more_100_len = len(emp_inc_company_billable_more_100)
        else:
            emp_inc_company_billable_more_100_count = 0
            emp_inc_company_billable_more_100_len = 0
        emp_inc_company_billable_100 = emp_inc_company_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_inc_company_billable_100):
            emp_inc_company_billable_100_count = len(emp_inc_company_billable_100)
        else:
            emp_inc_company_billable_100_count = 0
        emp_inc_company_billable_50 = emp_inc_company_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_inc_company_billable_50):
            emp_inc_company_billable_50_count = len(emp_inc_company_billable_50)
        else:
            emp_inc_company_billable_50_count = 0
        emp_inc_company_billable_75 = emp_inc_company_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_inc_company_billable_75):
            emp_inc_company_billable_75_count = len(emp_inc_company_billable_75)
        else:
            emp_inc_company_billable_75_count = 0
        emp_inc_company_billable_25 = emp_inc_company_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_inc_company_billable_25):
            emp_inc_company_billable_25_count = len(emp_inc_company_billable_25)
        else:
            emp_inc_company_billable_25_count = 0
        emp_inc_company_billable_0 = emp_inc_company_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_inc_company_billable_0):
            emp_inc_company_billable_0_count = len(emp_inc_company_billable_0)
        else:
            emp_inc_company_billable_0_count = 0

        # currently uk company billed
        emp_uk_company_billable = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_uk_company_billable_more_100 = emp_uk_company_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_uk_company_billable_more_100):
            emp_uk_company_billable_more_100_count = sum([i.total_billability for i in emp_uk_company_billable_more_100]) / 100
            emp_uk_company_billable_more_100_len = len(emp_uk_company_billable_more_100)
        else:
            emp_uk_company_billable_more_100_count = 0
            emp_uk_company_billable_more_100_len = 0
        emp_uk_company_billable_100 = emp_uk_company_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_uk_company_billable_100):
            emp_uk_company_billable_100_count = len(emp_uk_company_billable_100)
        else:
            emp_uk_company_billable_100_count = 0
        emp_uk_company_billable_50 = emp_uk_company_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_uk_company_billable_50):
            emp_uk_company_billable_50_count = len(emp_uk_company_billable_50)
        else:
            emp_uk_company_billable_50_count = 0
        emp_uk_company_billable_75 = emp_uk_company_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_uk_company_billable_75):
            emp_uk_company_billable_75_count = len(emp_uk_company_billable_75)
        else:
            emp_uk_company_billable_75_count = 0
        emp_uk_company_billable_25 = emp_uk_company_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_uk_company_billable_25):
            emp_uk_company_billable_25_count = len(emp_uk_company_billable_25)
        else:
            emp_uk_company_billable_25_count = 0
        emp_uk_company_billable_0 = emp_uk_company_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_uk_company_billable_0):
            emp_uk_company_billable_0_count = len(emp_uk_company_billable_0)
        else:
            emp_uk_company_billable_0_count = 0

        # currently gmbh company billed
        emp_gmbh_company_billable = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_gmbh_company_billable_more_100 = emp_gmbh_company_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_gmbh_company_billable_more_100):
            emp_gmbh_company_billable_more_100_count = sum([i.total_billability for i in emp_gmbh_company_billable_more_100]) / 100
            emp_gmbh_company_billable_more_100_len = len(emp_gmbh_company_billable_more_100)
        else:
            emp_gmbh_company_billable_more_100_count = 0
            emp_gmbh_company_billable_more_100_len = 0
        emp_gmbh_company_billable_100 = emp_gmbh_company_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_gmbh_company_billable_100):
            emp_gmbh_company_billable_100_count = len(emp_gmbh_company_billable_100)
        else:
            emp_gmbh_company_billable_100_count = 0
        emp_gmbh_company_billable_50 = emp_gmbh_company_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_gmbh_company_billable_50):
            emp_gmbh_company_billable_50_count = len(emp_gmbh_company_billable_50)
        else:
            emp_gmbh_company_billable_50_count = 0
        emp_gmbh_company_billable_75 = emp_gmbh_company_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_gmbh_company_billable_75):
            emp_gmbh_company_billable_75_count = len(emp_gmbh_company_billable_75)
        else:
            emp_gmbh_company_billable_75_count = 0
        emp_gmbh_company_billable_25 = emp_gmbh_company_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_gmbh_company_billable_25):
            emp_gmbh_company_billable_25_count = len(emp_gmbh_company_billable_25)
        else:
            emp_gmbh_company_billable_25_count = 0
        emp_gmbh_company_billable_0 = emp_gmbh_company_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_gmbh_company_billable_0):
            emp_gmbh_company_billable_0_count = len(emp_gmbh_company_billable_0)
        else:
            emp_gmbh_company_billable_0_count = 0
        
        # currently austria company billed
        emp_austria_company_billable = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_austria_company_billable_more_100 = emp_austria_company_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_austria_company_billable_more_100):
            emp_austria_company_billable_more_100_count = sum([i.total_billability for i in emp_austria_company_billable_more_100]) / 100
            emp_austria_company_billable_more_100_len = len(emp_austria_company_billable_more_100)
        else:
            emp_austria_company_billable_more_100_count = 0
            emp_austria_company_billable_more_100_len = 0
        emp_austria_company_billable_100 = emp_austria_company_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_austria_company_billable_100):
            emp_austria_company_billable_100_count = len(emp_austria_company_billable_100)
        else:
            emp_austria_company_billable_100_count = 0
        emp_austria_company_billable_50 = emp_austria_company_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_austria_company_billable_50):
            emp_austria_company_billable_50_count = len(emp_austria_company_billable_50)
        else:
            emp_austria_company_billable_50_count = 0
        emp_austria_company_billable_75 = emp_austria_company_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_austria_company_billable_75):
            emp_austria_company_billable_75_count = len(emp_austria_company_billable_75)
        else:
            emp_austria_company_billable_75_count = 0
        emp_austria_company_billable_25 = emp_austria_company_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_austria_company_billable_25):
            emp_austria_company_billable_25_count = len(emp_austria_company_billable_25)
        else:
            emp_austria_company_billable_25_count = 0
        emp_austria_company_billable_0 = emp_austria_company_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_austria_company_billable_0):
            emp_austria_company_billable_0_count = len(emp_austria_company_billable_0)
        else:
            emp_austria_company_billable_0_count = 0
        # currently consultant billed
        emp_consultant_billable = self.env['hr.employee'].search([
                                ('employee_category','=','Contractor'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_consultant_billable_more_100 = emp_consultant_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_consultant_billable_more_100):
            emp_consultant_billable_more_100_count = sum([i.total_billability for i in emp_consultant_billable_more_100]) / 100
            emp_consultant_billable_more_100_len = len(emp_consultant_billable_more_100)
        else:
            emp_consultant_billable_more_100_count = 0
            emp_consultant_billable_more_100_len = 0
        emp_consultant_billable_100 = emp_consultant_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_consultant_billable_100):
            emp_consultant_billable_100_count = len(emp_consultant_billable_100)
        else:
            emp_consultant_billable_100_count = 0
        emp_consultant_billable_75 = emp_consultant_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_consultant_billable_75):
            emp_consultant_billable_75_count = len(emp_consultant_billable_75)
        else:
            emp_consultant_billable_75_count = 0
        emp_consultant_billable_50 = emp_consultant_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_consultant_billable_50):
            emp_consultant_billable_50_count = len(emp_consultant_billable_50)
        else:
            emp_consultant_billable_50_count = 0
        emp_consultant_billable_25 = emp_consultant_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_consultant_billable_25):
            emp_consultant_billable_25_count = len(emp_consultant_billable_25)
        else:
            emp_consultant_billable_25_count = 0
        emp_consultant_billable_0 = emp_consultant_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_consultant_billable_0):
            emp_consultant_billable_0_count = len(emp_consultant_billable_0)
        else:
            emp_consultant_billable_0_count = 0
        # currently rookie billed
        emp_rookie_billable = self.env['hr.employee'].search([
                                ('employee_category','=','Intern'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_rookie_billable_more_100 = emp_rookie_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_rookie_billable_more_100):
            emp_rookie_billable_more_100_count = sum([i.total_billability for i in emp_rookie_billable_more_100]) / 100
            emp_rookie_billable_more_100_len = len(emp_rookie_billable_more_100)
        else:
            emp_rookie_billable_more_100_count = 0
            emp_rookie_billable_more_100_len = 0
        emp_rookie_billable_100 = emp_rookie_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_rookie_billable_100):
            emp_rookie_billable_100_count = len(emp_rookie_billable_100)
        else:
            emp_rookie_billable_100_count = 0
        emp_rookie_billable_50 = emp_rookie_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_rookie_billable_50):
            emp_rookie_billable_50_count = len(emp_rookie_billable_50)
        else:
            emp_rookie_billable_50_count = 0
        emp_rookie_billable_75 = emp_rookie_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_rookie_billable_75):
            emp_rookie_billable_75_count = len(emp_rookie_billable_75)
        else:
            emp_rookie_billable_75_count = 0
        emp_rookie_billable_25 = emp_rookie_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_rookie_billable_25):
            emp_rookie_billable_25_count = len(emp_rookie_billable_25)
        else:
            emp_rookie_billable_25_count = 0
        emp_rookie_billable_0 = emp_rookie_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_rookie_billable_0):
            emp_rookie_billable_0_count = len(emp_rookie_billable_0)
        else:
            emp_rookie_billable_0_count = 0
        # allocated percentage
        if emp_company_deployable:
            company_allocate_percent = (((emp_company_allocated_partial + emp_company_allocated_100 + emp_company_unallocated)*100)//emp_company_deployable)
        else:
            company_allocate_percent = 0

        # currently ezestian billed
        emp_ezestian_billable = self.env['hr.employee'].search([
                                ('employee_category','=','eZestian'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        emp_ezestian_billable_more_100 = emp_ezestian_billable.filtered(lambda x: x.total_billability > 100)
        if len(emp_ezestian_billable_more_100):
            emp_ezestian_billable_more_100_count = sum([i.total_billability for i in emp_ezestian_billable_more_100]) / 100
            emp_ezestian_billable_more_100_len = len(emp_ezestian_billable_more_100)
        else:
            emp_ezestian_billable_more_100_count = 0
            emp_ezestian_billable_more_100_len = 0
        emp_ezestian_billable_100 = emp_ezestian_billable.filtered(lambda x: x.total_billability == 100)
        if len(emp_ezestian_billable_100):
            emp_ezestian_billable_100_count = len(emp_ezestian_billable_100)
        else:
            emp_ezestian_billable_100_count = 0
        emp_ezestian_billable_50 = emp_ezestian_billable.filtered(lambda x: x.total_billability == 50)
        if len(emp_ezestian_billable_50):
            emp_ezestian_billable_50_count = len(emp_ezestian_billable_50)
        else:
            emp_ezestian_billable_50_count = 0
        emp_ezestian_billable_75 = emp_ezestian_billable.filtered(lambda x: x.total_billability == 75)
        if len(emp_ezestian_billable_75):
            emp_ezestian_billable_75_count = len(emp_ezestian_billable_75)
        else:
            emp_ezestian_billable_75_count = 0
        emp_ezestian_billable_25 = emp_ezestian_billable.filtered(lambda x: x.total_billability == 25)
        if len(emp_ezestian_billable_25):
            emp_ezestian_billable_25_count = len(emp_ezestian_billable_25)
        else:
            emp_ezestian_billable_25_count = 0
        emp_ezestian_billable_0 = emp_ezestian_billable.filtered(lambda x: x.total_billability == 0)
        if len(emp_ezestian_billable_0):
            emp_ezestian_billable_0_count = len(emp_ezestian_billable_0)
        else:
            emp_ezestian_billable_0_count = 0
        # allocated percentage
        if emp_company_deployable:
            company_allocate_percent = (((emp_company_allocated_partial + emp_company_allocated_100)*100)//emp_company_deployable)
        else:
            company_allocate_percent = 0

        # ltd allocated percentage
        if emp_ltd_company_deployable:
            company_ltd_allocate_percent = (((emp_ltd_company_allocated_partial + emp_ltd_company_allocated_100)*100)//emp_ltd_company_deployable)
        else:
            company_ltd_allocate_percent = 0

        # inc allocated percentage
        if emp_inc_company_deployable:
            company_inc_allocate_percent = (((emp_inc_company_allocated_partial + emp_inc_company_allocated_100)*100)//emp_inc_company_deployable)
        else:
            company_inc_allocate_percent = 0

        # uk allocated percentage
        if emp_uk_company_deployable:
            company_uk_allocate_percent = (((emp_uk_company_allocated_partial + emp_uk_company_allocated_100)*100)//emp_uk_company_deployable)
        else:
            company_uk_allocate_percent = 0

        # gmbh allocated percentage
        if emp_gmbh_company_deployable:
            company_gmbh_allocate_percent = (((emp_gmbh_company_allocated_partial + emp_gmbh_company_allocated_100)*100)//emp_gmbh_company_deployable)
        else:
            company_gmbh_allocate_percent = 0

        # austria allocated percentage
        if emp_austria_company_deployable:
            company_austria_allocate_percent = (((emp_austria_company_allocated_partial + emp_austria_company_allocated_100)*100)//emp_austria_company_deployable)
        else:
            company_austria_allocate_percent = 0

        # billable percentage
        if emp_company_deployable:
            cmp_100 = (100 / 100) * emp_company_billable_100_count
            cmp_75 = (75 / 100) * emp_company_billable_75_count
            cmp_50 = (50 / 100) * emp_company_billable_50_count
            cmp_25 = (25 / 100) * emp_company_billable_25_count
            company_billable_percent = (((emp_company_billable_more_100_count + cmp_100 + cmp_75 + cmp_50 + cmp_25) * 100) // emp_company_deployable)
        else:
            company_billable_percent = 0

        # ltd billable percentage
        if emp_ltd_company_deployable:
            ltd_cmp_100 = (100 / 100) * emp_ltd_company_billable_100_count
            ltd_cmp_75 = (75 / 100) * emp_ltd_company_billable_75_count
            ltd_cmp_50 = (50 / 100) * emp_ltd_company_billable_50_count
            ltd_cmp_25 = (25 / 100) * emp_ltd_company_billable_25_count
            company_ltd_billable_percent = (((emp_ltd_company_billable_more_100_count + ltd_cmp_100 + ltd_cmp_75 + ltd_cmp_50 + ltd_cmp_25) * 100) // emp_ltd_company_deployable)
        else:
            company_ltd_billable_percent = 0

        # inc billable percentage
        if emp_inc_company_deployable:
            inc_cmp_100 = (100 / 100) * emp_inc_company_billable_100_count
            inc_cmp_75 = (75 / 100) * emp_inc_company_billable_75_count
            inc_cmp_50 = (50 / 100) * emp_inc_company_billable_50_count
            inc_cmp_25 = (25 / 100) * emp_inc_company_billable_25_count
            company_inc_billable_percent = (((emp_inc_company_billable_more_100_count + inc_cmp_100 + inc_cmp_75 + inc_cmp_50 + inc_cmp_25) * 100) // emp_inc_company_deployable)
        else:
            company_inc_billable_percent = 0

        # uk billable percentage
        if emp_uk_company_deployable:
            uk_cmp_100 = (100 / 100) * emp_uk_company_billable_100_count
            uk_cmp_75 = (75 / 100) * emp_uk_company_billable_75_count
            uk_cmp_50 = (50 / 100) * emp_uk_company_billable_50_count
            uk_cmp_25 = (25 / 100) * emp_uk_company_billable_25_count
            company_uk_billable_percent = (((emp_uk_company_billable_more_100_count + uk_cmp_100 + uk_cmp_75 + uk_cmp_50 + uk_cmp_25) * 100) // emp_uk_company_deployable)
        else:
            company_uk_billable_percent = 0

        # gmbh billable percentage
        if emp_gmbh_company_deployable:
            gmbh_cmp_100 = (100 / 100) * emp_gmbh_company_billable_100_count
            gmbh_cmp_75 = (75 / 100) * emp_gmbh_company_billable_75_count
            gmbh_cmp_50 = (50 / 100) * emp_gmbh_company_billable_50_count
            gmbh_cmp_25 = (25 / 100) * emp_gmbh_company_billable_25_count
            company_gmbh_billable_percent = (((emp_gmbh_company_billable_more_100_count + gmbh_cmp_100 + gmbh_cmp_75 + gmbh_cmp_50 + gmbh_cmp_25) * 100) // emp_gmbh_company_deployable)
        else:
            company_gmbh_billable_percent = 0

        # austria billable percentage
        if emp_austria_company_deployable:
            austria_cmp_100 = (100 / 100) * emp_austria_company_billable_100_count
            austria_cmp_75 = (75 / 100) * emp_austria_company_billable_75_count
            austria_cmp_50 = (50 / 100) * emp_austria_company_billable_50_count
            austria_cmp_25 = (25 / 100) * emp_austria_company_billable_25_count
            company_austria_billable_percent = (((emp_austria_company_billable_more_100_count + austria_cmp_100 + austria_cmp_75 + austria_cmp_50 + austria_cmp_25) * 100) // emp_austria_company_deployable)
        else:
            company_austria_billable_percent = 0

        # consultant allocated percentage
        if emp_consultant_deployable:
            consultant_allocate_percent = (((emp_consultant_allocated_partial + emp_consultant_allocated_100) * 100)//emp_consultant_deployable)
        else:
            consultant_allocate_percent = 0

        # consultant billable percentage
        if emp_consultant_deployable:
            consultant_100 = (100 / 100) * emp_consultant_billable_100_count
            consultant_75 = (75 / 100) * emp_consultant_billable_75_count
            consultant_50 = (50 / 100) * emp_consultant_billable_50_count
            consultant_25 = (25 / 100) * emp_consultant_billable_25_count
            consultant_billable_percent = (((emp_consultant_billable_more_100_count + consultant_100 + consultant_75 + consultant_50 + consultant_25) * 100) // emp_consultant_deployable)
        else:
            consultant_billable_percent = 0

        # rookie allocated percentage
        if emp_rookie_deployable:
            rookie_allocate_percent = (((emp_rookie_allocated_partial + emp_rookie_allocated_100) * 100)//emp_rookie_deployable)
        else:
            rookie_allocate_percent = 0

        # rookie billable percentage
        if emp_rookie_deployable:
            rookie_100 = (100 / 100) * emp_rookie_billable_100_count
            rookie_75 = (75 / 100) * emp_rookie_billable_75_count
            rookie_50 = (50 / 100) * emp_rookie_billable_50_count
            rookie_25 = (25 / 100) * emp_rookie_billable_25_count
            rookie_billable_percent = (((emp_rookie_billable_more_100_count + rookie_100 + rookie_75 + rookie_50 + rookie_25) * 100) // emp_rookie_deployable)
        else:
            rookie_billable_percent = 0

        # ezestian allocated percentage
        if emp_ezestian_deployable:
            ezestian_allocate_percent = (((emp_ezestian_allocated_partial + emp_ezestian_allocated_100) * 100)//emp_ezestian_deployable)
        else:
            ezestian_allocate_percent = 0

        # ezestian billable percentage
        if emp_ezestian_deployable:
            ezestian_100 = (100 / 100) * emp_ezestian_billable_100_count
            ezestian_75 = (75 / 100) * emp_ezestian_billable_75_count
            ezestian_50 = (50 / 100) * emp_ezestian_billable_50_count
            ezestian_25 = (25 / 100) * emp_ezestian_billable_25_count
            ezestian_billable_percent = (((emp_ezestian_billable_more_100_count + ezestian_100 + ezestian_50 + ezestian_75 + ezestian_25) * 100) // emp_ezestian_deployable)
        else:
            ezestian_billable_percent = 0

        # Ltd. DES total
        total_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('joining_date','!=',False)])
        # DPES total
        total_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False)])
        # IO total
        total_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False)])
        # Non sbu total
        total_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False)])

        # UK DES total
        total_uk_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('joining_date','!=',False)])
        # DPES total
        total_uk_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False)])
        # IO total
        total_uk_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False)])
        # Non sbu total
        total_uk_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False)])

        # Inc. DES total
        total_inc_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('joining_date','!=',False)])
        # DPES total
        total_inc_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False)])
        # IO total
        total_inc_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False)])
        # Non sbu total
        total_inc_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False)])

        # Austria DES total
        total_austria_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('joining_date','!=',False)])
        # DPES total
        total_austria_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False)])
        # IO total
        total_austria_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False)])
        # Non sbu total
        total_austria_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False)])

        # gmbh DES total
        total_gmbh_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('joining_date','!=',False)])
        # DPES total
        total_gmbh_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False)])
        # IO total
        total_gmbh_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False)])
        # Non sbu total
        total_gmbh_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False)])

        # DES deployable ltd
        deployable_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES deployable
        deployable_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO deployable
        deployable_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        deployable_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES deployable uk
        deployable_uk_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES deployable
        deployable_uk_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO deployable
        deployable_uk_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        deployable_uk_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES deployable inc
        deployable_inc_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES deployable
        deployable_inc_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO deployable
        deployable_inc_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        deployable_inc_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES deployable gmbh
        deployable_gmbh_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES deployable
        deployable_gmbh_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO deployable
        deployable_gmbh_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        deployable_gmbh_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES deployable austria
        deployable_austria_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES deployable
        deployable_austria_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO deployable
        deployable_austria_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        deployable_austria_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES non deployable ltd
        non_deployable_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES non deployable
        non_deployable_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO Non deployable
        non_deployable_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        non_deployable_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES non deployable uk
        non_deployable_uk_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES non deployable
        non_deployable_uk_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO Non deployable
        non_deployable_uk_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        non_deployable_uk_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES non deployable inc
        non_deployable_inc_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES non deployable
        non_deployable_inc_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO Non deployable
        non_deployable_inc_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        non_deployable_inc_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES non deployable gmbh
        non_deployable_gmbh_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH/ Operations / DES'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES non deployable
        non_deployable_gmbh_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH/ Operations / DPES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO Non deployable
        non_deployable_gmbh_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH/ Operations / IO'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        non_deployable_gmbh_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD GmbH/ Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH/ Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH/ Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES non deployable austria
        non_deployable_austria_des = self.env['hr.employee'].search_count([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES non deployable
        non_deployable_austria_dpes = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO Non deployable
        non_deployable_austria_io = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        non_deployable_austria_non_sbu = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('account', 'not in', ['Deployable - Billable', 'Temporarily - Deployable']),
                                ('joining_date','!=',False)])

        # DES allocated ltd
        allocated_des_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_partial = sum([i.project_allocate for i in allocated_des_partial]) // 100
        allocated_des_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES allocated
        allocated_dpes_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_partial = sum([i.project_allocate for i in allocated_dpes_partial]) // 100
        allocated_dpes_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO allocated
        allocated_io_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_io_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_partial = sum([i.project_allocate for i in allocated_io_partial]) // 100

        allocated_io_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # Non sbu allocated
        allocated_non_sbu_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_non_sbu_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_non_sbu_partial = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_non_sbu_partial = sum([i.project_allocate for i in allocated_non_sbu_partial]) // 100

        allocated_non_sbu_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # DES allocated uk
        allocated_des_uk_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_uk_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_uk_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_uk_partial = sum([i.project_allocate for i in allocated_des_uk_partial]) // 100
        allocated_des_uk_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES allocated
        allocated_dpes_uk_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_uk_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_uk_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_uk_partial = sum([i.project_allocate for i in allocated_dpes_uk_partial]) // 100
        allocated_dpes_uk_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO allocated
        allocated_io_uk_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_io_uk_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_uk_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_uk_partial = sum([i.project_allocate for i in allocated_io_uk_partial]) // 100

        allocated_io_uk_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # Non sbu allocated
        allocated_uk_non_sbu_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_uk_non_sbu_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_uk_non_sbu_partial = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_uk_non_sbu_partial = sum([i.project_allocate for i in allocated_uk_non_sbu_partial]) // 100

        allocated_uk_non_sbu_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # DES allocated inc
        allocated_des_inc_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_inc_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_inc_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_inc_partial = sum([i.project_allocate for i in allocated_des_inc_partial]) // 100
        allocated_des_inc_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES allocated
        allocated_dpes_inc_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_inc_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_inc_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_inc_partial = sum([i.project_allocate for i in allocated_dpes_inc_partial]) // 100
        allocated_dpes_inc_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO allocated
        allocated_io_inc_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_io_inc_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_inc_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_inc_partial = sum([i.project_allocate for i in allocated_io_inc_partial]) // 100

        allocated_io_inc_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # Non sbu allocated
        allocated_inc_non_sbu_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_inc_non_sbu_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_inc_non_sbu_partial = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_inc_non_sbu_partial = sum([i.project_allocate for i in allocated_inc_non_sbu_partial]) // 100

        allocated_inc_non_sbu_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # DES allocated gmbh
        allocated_des_gmbh_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_gmbh_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_gmbh_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_gmbh_partial = sum([i.project_allocate for i in allocated_des_gmbh_partial]) // 100
        allocated_des_gmbh_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES allocated
        allocated_dpes_gmbh_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_gmbh_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_gmbh_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_gmbh_partial = sum([i.project_allocate for i in allocated_dpes_gmbh_partial]) // 100
        allocated_dpes_gmbh_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO allocated
        allocated_io_gmbh_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_io_gmbh_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_gmbh_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_gmbh_partial = sum([i.project_allocate for i in allocated_io_gmbh_partial]) // 100

        allocated_io_gmbh_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # Non sbu allocated
        allocated_gmbh_non_sbu_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_gmbh_non_sbu_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_gmbh_non_sbu_partial = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_gmbh_non_sbu_partial = sum([i.project_allocate for i in allocated_gmbh_non_sbu_partial]) // 100

        allocated_gmbh_non_sbu_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # DES allocated austria
        allocated_des_austria_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_austria_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_austria_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_des_austria_partial = sum([i.project_allocate for i in allocated_des_austria_partial]) // 100
        allocated_des_austria_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # DPES allocated
        allocated_dpes_austria_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_austria_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_austria_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_dpes_austria_partial = sum([i.project_allocate for i in allocated_dpes_austria_partial]) // 100
        allocated_dpes_austria_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # IO allocated
        allocated_io_austria_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_io_austria_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_austria_partial = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_io_austria_partial = sum([i.project_allocate for i in allocated_io_austria_partial]) // 100

        allocated_io_austria_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        # Non sbu allocated
        allocated_austria_non_sbu_100 = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        allocated_austria_non_sbu_partial_count = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_austria_non_sbu_partial = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','>',0),
                                ('project_allocate','<',100),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        allocated_austria_non_sbu_partial = sum([i.project_allocate for i in allocated_austria_non_sbu_partial]) // 100

        allocated_austria_non_sbu_unallocated = self.env['hr.employee'].search_count([
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('project_allocate','=',0),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])

        # ltd currently des resigned/probation/confirmed
        des_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / DES')])
        des_resigned_count = des_resigned.filtered(lambda x: x.resign_date)
        des_resigned = len(des_resigned_count)

        des_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        des_probation_count = des_probation.filtered(lambda x: not x.resign_date)
        des_probation = len(des_probation_count)

        des_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        des_confirmed_count = des_confirmed.filtered(lambda x: not x.resign_date)
        des_confirmed = len(des_confirmed_count)

        # currently dpes resigned/probation/confirmed
        dpes_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / DPES')])
        dpes_resigned_count = dpes_resigned.filtered(lambda x: x.resign_date)
        dpes_resigned = len(dpes_resigned_count)

        dpes_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        dpes_probation_count = dpes_probation.filtered(lambda x: not x.resign_date)
        dpes_probation = len(dpes_probation_count)

        dpes_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('confirmation_status','=','confirmed')])
        dpes_confirmed_count = dpes_confirmed.filtered(lambda x: not x.resign_date)
        dpes_confirmed = len(dpes_confirmed_count)

        # currently io resigned/probation/confirmed
        io_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / IO')])
        io_resigned_count = io_resigned.filtered(lambda x: x.resign_date)
        io_resigned = len(io_resigned_count)

        io_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        io_probation_count = io_probation.filtered(lambda x: not x.resign_date)
        io_probation = len(io_probation_count)

        io_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('confirmation_status','=','confirmed')])
        io_confirmed_count = io_confirmed.filtered(lambda x: not x.resign_date)
        io_confirmed = len(io_confirmed_count)

        # currently non sbu resigned/probation/confirmed
        non_sbu_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES')])
        non_sbu_resigned_count = non_sbu_resigned.filtered(lambda x: x.resign_date)
        non_sbu_resigned = len(non_sbu_resigned_count)

        non_sbu_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        non_sbu_probation_count = non_sbu_probation.filtered(lambda x: not x.resign_date)
        non_sbu_probation = len(non_sbu_probation_count)

        non_sbu_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        non_sbu_confirmed_count = non_sbu_confirmed.filtered(lambda x: not x.resign_date)
        non_sbu_confirmed = len(non_sbu_confirmed_count)

        # inc currently des resigned/probation/confirmed
        des_inc_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES')])
        des_inc_resigned_count = des_inc_resigned.filtered(lambda x: x.resign_date)
        des_inc_resigned = len(des_inc_resigned_count)

        des_inc_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        des_inc_probation_count = des_inc_probation.filtered(lambda x: not x.resign_date)
        des_inc_probation = len(des_inc_probation_count)

        des_inc_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        des_inc_confirmed_count = des_inc_confirmed.filtered(lambda x: not x.resign_date)
        des_inc_confirmed = len(des_inc_confirmed_count)

        # currently dpes resigned/probation/confirmed
        dpes_inc_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES')])
        dpes_inc_resigned_count = dpes_inc_resigned.filtered(lambda x: x.resign_date)
        dpes_inc_resigned = len(dpes_inc_resigned_count)

        dpes_inc_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        dpes_inc_probation_count = dpes_inc_probation.filtered(lambda x: not x.resign_date)
        dpes_inc_probation = len(dpes_inc_probation_count)

        dpes_inc_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('confirmation_status','=','confirmed')])
        dpes_inc_confirmed_count = dpes_inc_confirmed.filtered(lambda x: not x.resign_date)
        dpes_inc_confirmed = len(dpes_inc_confirmed_count)

        # currently io resigned/probation/confirmed
        io_inc_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO')])
        io_inc_resigned_count = io_inc_resigned.filtered(lambda x: x.resign_date)
        io_inc_resigned = len(io_inc_resigned_count)

        io_inc_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        io_inc_probation_count = io_inc_probation.filtered(lambda x: not x.resign_date)
        io_inc_probation = len(io_inc_probation_count)

        io_inc_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('confirmation_status','=','confirmed')])
        io_inc_confirmed_count = io_inc_confirmed.filtered(lambda x: not x.resign_date)
        io_inc_confirmed = len(io_inc_confirmed_count)

        # currently non sbu resigned/probation/confirmed
        non_sbu_inc_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES')])
        non_sbu_inc_resigned_count = non_sbu_inc_resigned.filtered(lambda x: x.resign_date)
        non_sbu_inc_resigned = len(non_sbu_inc_resigned_count)

        non_sbu_inc_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        non_sbu_inc_probation_count = non_sbu_inc_probation.filtered(lambda x: not x.resign_date)
        non_sbu_inc_probation = len(non_sbu_inc_probation_count)

        non_sbu_inc_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        non_sbu_inc_confirmed_count = non_sbu_inc_confirmed.filtered(lambda x: not x.resign_date)
        non_sbu_inc_confirmed = len(non_sbu_inc_confirmed_count)

        # gmbh currently des resigned/probation/confirmed
        des_gmbh_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES')])
        des_gmbh_resigned_count = des_gmbh_resigned.filtered(lambda x: x.resign_date)
        des_gmbh_resigned = len(des_gmbh_resigned_count)

        des_gmbh_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        des_gmbh_probation_count = des_gmbh_probation.filtered(lambda x: not x.resign_date)
        des_gmbh_probation = len(des_gmbh_probation_count)

        des_gmbh_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        des_gmbh_confirmed_count = des_gmbh_confirmed.filtered(lambda x: not x.resign_date)
        des_gmbh_confirmed = len(des_gmbh_confirmed_count)

        # currently dpes resigned/probation/confirmed
        dpes_gmbh_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES')])
        dpes_gmbh_resigned_count = dpes_gmbh_resigned.filtered(lambda x: x.resign_date)
        dpes_gmbh_resigned = len(dpes_gmbh_resigned_count)

        dpes_gmbh_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        dpes_gmbh_probation_count = dpes_gmbh_probation.filtered(lambda x: not x.resign_date)
        dpes_gmbh_probation = len(dpes_gmbh_probation_count)

        dpes_gmbh_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('confirmation_status','=','confirmed')])
        dpes_gmbh_confirmed_count = dpes_gmbh_confirmed.filtered(lambda x: not x.resign_date)
        dpes_gmbh_confirmed = len(dpes_gmbh_confirmed_count)

        # currently io resigned/probation/confirmed
        io_gmbh_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO')])
        io_gmbh_resigned_count = io_gmbh_resigned.filtered(lambda x: x.resign_date)
        io_gmbh_resigned = len(io_gmbh_resigned_count)

        io_gmbh_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        io_gmbh_probation_count = io_gmbh_probation.filtered(lambda x: not x.resign_date)
        io_gmbh_probation = len(io_gmbh_probation_count)

        io_gmbh_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('confirmation_status','=','confirmed')])
        io_gmbh_confirmed_count = io_gmbh_confirmed.filtered(lambda x: not x.resign_date)
        io_gmbh_confirmed = len(io_gmbh_confirmed_count)

        # currently non sbu resigned/probation/confirmed
        non_sbu_gmbh_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES')])
        non_sbu_gmbh_resigned_count = non_sbu_gmbh_resigned.filtered(lambda x: x.resign_date)
        non_sbu_gmbh_resigned = len(non_sbu_gmbh_resigned_count)

        non_sbu_gmbh_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        non_sbu_gmbh_probation_count = non_sbu_gmbh_probation.filtered(lambda x: not x.resign_date)
        non_sbu_gmbh_probation = len(non_sbu_gmbh_probation_count)

        non_sbu_gmbh_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        non_sbu_gmbh_confirmed_count = non_sbu_gmbh_confirmed.filtered(lambda x: not x.resign_date)
        non_sbu_gmbh_confirmed = len(non_sbu_gmbh_confirmed_count)

        # austria currently des resigned/probation/confirmed
        des_austria_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES')])
        des_austria_resigned_count = des_austria_resigned.filtered(lambda x: x.resign_date)
        des_austria_resigned = len(des_austria_resigned_count)

        des_austria_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        des_austria_probation_count = des_austria_probation.filtered(lambda x: not x.resign_date)
        des_austria_probation = len(des_austria_probation_count)

        des_austria_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        des_austria_confirmed_count = des_austria_confirmed.filtered(lambda x: not x.resign_date)
        des_austria_confirmed = len(des_austria_confirmed_count)

        # currently dpes resigned/probation/confirmed
        dpes_austria_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES')])
        dpes_austria_resigned_count = dpes_austria_resigned.filtered(lambda x: x.resign_date)
        dpes_austria_resigned = len(dpes_austria_resigned_count)

        dpes_austria_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        dpes_austria_probation_count = dpes_austria_probation.filtered(lambda x: not x.resign_date)
        dpes_austria_probation = len(dpes_austria_probation_count)

        dpes_austria_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('confirmation_status','=','confirmed')])
        dpes_austria_confirmed_count = dpes_austria_confirmed.filtered(lambda x: not x.resign_date)
        dpes_austria_confirmed = len(dpes_austria_confirmed_count)

        # currently io resigned/probation/confirmed
        io_austria_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO')])
        io_austria_resigned_count = io_austria_resigned.filtered(lambda x: x.resign_date)
        io_austria_resigned = len(io_austria_resigned_count)

        io_austria_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        io_austria_probation_count = io_austria_probation.filtered(lambda x: not x.resign_date)
        io_austria_probation = len(io_austria_probation_count)

        io_austria_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('confirmation_status','=','confirmed')])
        io_austria_confirmed_count = io_austria_confirmed.filtered(lambda x: not x.resign_date)
        io_austria_confirmed = len(io_austria_confirmed_count)

        # currently non sbu resigned/probation/confirmed
        non_sbu_austria_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES')])
        non_sbu_austria_resigned_count = non_sbu_austria_resigned.filtered(lambda x: x.resign_date)
        non_sbu_austria_resigned = len(non_sbu_austria_resigned_count)

        non_sbu_austria_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        non_sbu_austria_probation_count = non_sbu_austria_probation.filtered(lambda x: not x.resign_date)
        non_sbu_austria_probation = len(non_sbu_austria_probation_count)

        non_sbu_austria_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        non_sbu_austria_confirmed_count = non_sbu_austria_confirmed.filtered(lambda x: not x.resign_date)
        non_sbu_austria_confirmed = len(non_sbu_austria_confirmed_count)

        # uk currently des resigned/probation/confirmed
        des_uk_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / DES')])
        des_uk_resigned_count = des_uk_resigned.filtered(lambda x: x.resign_date)
        des_uk_resigned = len(des_uk_resigned_count)

        des_uk_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        des_uk_probation_count = des_uk_probation.filtered(lambda x: not x.resign_date)
        des_uk_probation = len(des_uk_probation_count)

        des_uk_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        des_uk_confirmed_count = des_uk_confirmed.filtered(lambda x: not x.resign_date)
        des_uk_confirmed = len(des_uk_confirmed_count)

        # currently dpes resigned/probation/confirmed
        dpes_uk_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES')])
        dpes_uk_resigned_count = dpes_uk_resigned.filtered(lambda x: x.resign_date)
        dpes_uk_resigned = len(dpes_uk_resigned_count)

        dpes_uk_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        dpes_uk_probation_count = dpes_uk_probation.filtered(lambda x: not x.resign_date)
        dpes_uk_probation = len(dpes_uk_probation_count)

        dpes_uk_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('confirmation_status','=','confirmed')])
        dpes_uk_confirmed_count = dpes_uk_confirmed.filtered(lambda x: not x.resign_date)
        dpes_uk_confirmed = len(dpes_uk_confirmed_count)

        # currently io resigned/probation/confirmed
        io_uk_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / IO')])
        io_uk_resigned_count = io_uk_resigned.filtered(lambda x: x.resign_date)
        io_uk_resigned = len(io_uk_resigned_count)

        io_uk_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        io_uk_probation_count = io_uk_probation.filtered(lambda x: not x.resign_date)
        io_uk_probation = len(io_uk_probation_count)

        io_uk_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('confirmation_status','=','confirmed')])
        io_uk_confirmed_count = io_uk_confirmed.filtered(lambda x: not x.resign_date)
        io_uk_confirmed = len(io_uk_confirmed_count)

        # currently non sbu resigned/probation/confirmed
        non_sbu_uk_resigned = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES')])
        non_sbu_uk_resigned_count = non_sbu_uk_resigned.filtered(lambda x: x.resign_date)
        non_sbu_uk_resigned = len(non_sbu_uk_resigned_count)

        non_sbu_uk_probation = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('confirmation_status','in',['due', 'in_progress', 'extended'])])
        non_sbu_uk_probation_count = non_sbu_uk_probation.filtered(lambda x: not x.resign_date)
        non_sbu_uk_probation = len(non_sbu_uk_probation_count)

        non_sbu_uk_confirmed = self.env['hr.employee'].search([
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('confirmation_status','=','confirmed')])
        non_sbu_uk_confirmed_count = non_sbu_uk_confirmed.filtered(lambda x: not x.resign_date)
        non_sbu_uk_confirmed = len(non_sbu_uk_confirmed_count)

        # DES billed ltd.
        billable_des = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_des_more_100 = billable_des.filtered(lambda x: x.total_billability > 100)
        if len(billable_des_more_100):
            billable_des_more_100_count = sum([i.total_billability for i in billable_des_more_100]) / 100
            billable_des_more_100_len = len(billable_des_more_100)
        else:
            billable_des_more_100_count = 0
            billable_des_more_100_len = 0
        billable_des_100 = billable_des.filtered(lambda x: x.total_billability == 100)
        if len(billable_des_100):
            billable_des_100_count = len(billable_des_100)
        else:
            billable_des_100_count = 0
        billable_des_75 = billable_des.filtered(lambda x: x.total_billability == 75)
        if len(billable_des_75):
            billable_des_75_count = len(billable_des_75)
        else:
            billable_des_75_count = 0
        billable_des_50 = billable_des.filtered(lambda x: x.total_billability == 50)
        if len(billable_des_50):
            billable_des_50_count = len(billable_des_50)
        else:
            billable_des_50_count = 0
        billable_des_25 = billable_des.filtered(lambda x: x.total_billability == 25)
        if len(billable_des_25):
            billable_des_25_count = len(billable_des_25)
        else:
            billable_des_25_count = 0
        billable_des_0 = billable_des.filtered(lambda x: x.total_billability == 0)
        if len(billable_des_0):
            billable_des_0_count = len(billable_des_0)
        else:
            billable_des_0_count = 0
        # DPES billed
        billable_dpes = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_dpes_more_100 = billable_dpes.filtered(lambda x: x.total_billability > 100)
        if len(billable_dpes_more_100):
            billable_dpes_more_100_count = sum([i.total_billability for i in billable_dpes_more_100]) / 100
            billable_dpes_more_100_len = len(billable_dpes_more_100)
        else:
            billable_dpes_more_100_count = 0
            billable_dpes_more_100_len = 0
        billable_dpes_100 = billable_dpes.filtered(lambda x: x.total_billability == 100)
        if len(billable_dpes_100):
            billable_dpes_100_count = len(billable_dpes_100)
        else:
            billable_dpes_100_count = 0
        billable_dpes_75 = billable_dpes.filtered(lambda x: x.total_billability == 75)
        if len(billable_dpes_75):
            billable_dpes_75_count = len(billable_dpes_75)
        else:
            billable_dpes_75_count = 0
        billable_dpes_25 = billable_dpes.filtered(lambda x: x.total_billability == 25)
        if len(billable_dpes_25):
            billable_dpes_25_count = len(billable_dpes_25)
        else:
            billable_dpes_25_count = 0
        billable_dpes_50 = billable_dpes.filtered(lambda x: x.total_billability == 50)
        if len(billable_dpes_50):
            billable_dpes_50_count = len(billable_dpes_50)
        else:
            billable_dpes_50_count = 0
        billable_dpes_0 = billable_dpes.filtered(lambda x: x.total_billability == 0)
        if len(billable_dpes_0):
            billable_dpes_0_count = len(billable_dpes_0)
        else:
            billable_dpes_0_count = 0
        # IO billed
        billable_io = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_io_more_100 = billable_io.filtered(lambda x: x.total_billability > 100)
        if len(billable_io_more_100):
            billable_io_more_100_count = sum([i.total_billability for i in billable_io_more_100]) / 100
            billable_io_more_100_len = len(billable_io_more_100)
        else:
            billable_io_more_100_count = 0
            billable_io_more_100_len = 0
        billable_io_100 = billable_io.filtered(lambda x: x.total_billability == 100)
        if len(billable_io_100):
            billable_io_100_count = len(billable_io_100)
        else:
            billable_io_100_count = 0
        billable_io_75 = billable_io.filtered(lambda x: x.total_billability == 75)
        if len(billable_io_75):
            billable_io_75_count = len(billable_io_75)
        else:
            billable_io_75_count = 0
        billable_io_50 = billable_io.filtered(lambda x: x.total_billability == 50)
        if len(billable_io_50):
            billable_io_50_count = len(billable_io_50)
        else:
            billable_io_50_count = 0
        billable_io_25 = billable_io.filtered(lambda x: x.total_billability == 25)
        if len(billable_io_25):
            billable_io_25_count = len(billable_io_25)
        else:
            billable_io_25_count = 0
        billable_io_0 = billable_io.filtered(lambda x: x.total_billability == 0)
        if len(billable_io_0):
            billable_io_0_count = len(billable_io_0)
        else:
            billable_io_0_count = 0
        
        # Non sbu billed
        billable_non_sbu = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_non_sbu_more_100 = billable_non_sbu.filtered(lambda x: x.total_billability > 100)
        if len(billable_non_sbu_more_100):
            billable_non_sbu_more_100_count = sum([i.total_billability for i in billable_non_sbu_more_100]) / 100
            billable_non_sbu_more_100_len = len(billable_non_sbu_more_100)
        else:
            billable_non_sbu_more_100_count = 0
            billable_non_sbu_more_100_len = 0
        billable_non_sbu_100 = billable_non_sbu.filtered(lambda x: x.total_billability == 100)
        if len(billable_non_sbu_100):
            billable_non_sbu_100_count = len(billable_non_sbu_100)
        else:
            billable_non_sbu_100_count = 0
        billable_non_sbu_75 = billable_non_sbu.filtered(lambda x: x.total_billability == 75)
        if len(billable_non_sbu_75):
            billable_non_sbu_75_count = len(billable_non_sbu_75)
        else:
            billable_non_sbu_75_count = 0
        billable_non_sbu_50 = billable_non_sbu.filtered(lambda x: x.total_billability == 50)
        if len(billable_non_sbu_50):
            billable_non_sbu_50_count = len(billable_non_sbu_50)
        else:
            billable_non_sbu_50_count = 0
        billable_non_sbu_25 = billable_non_sbu.filtered(lambda x: x.total_billability == 25)
        if len(billable_non_sbu_25):
            billable_non_sbu_25_count = len(billable_non_sbu_25)
        else:
            billable_non_sbu_25_count = 0
        billable_non_sbu_0 = billable_non_sbu.filtered(lambda x: x.total_billability == 0)
        if len(billable_non_sbu_0):
            billable_non_sbu_0_count = len(billable_non_sbu_0)
        else:
            billable_non_sbu_0_count = 0
        
        # DES billed uk.
        billable_uk_des = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_uk_des_more_100 = billable_uk_des.filtered(lambda x: x.total_billability > 100)
        if len(billable_uk_des_more_100):
            billable_uk_des_more_100_count = sum([i.total_billability for i in billable_uk_des_more_100]) / 100
            billable_uk_des_more_100_len = len(billable_uk_des_more_100)
        else:
            billable_uk_des_more_100_count = 0
            billable_uk_des_more_100_len = 0
        billable_uk_des_100 = billable_uk_des.filtered(lambda x: x.total_billability == 100)
        if len(billable_uk_des_100):
            billable_uk_des_100_count = len(billable_uk_des_100)
        else:
            billable_uk_des_100_count = 0
        billable_uk_des_75 = billable_uk_des.filtered(lambda x: x.total_billability == 75)
        if len(billable_uk_des_75):
            billable_uk_des_75_count = len(billable_uk_des_75)
        else:
            billable_uk_des_75_count = 0
        billable_uk_des_50 = billable_uk_des.filtered(lambda x: x.total_billability == 50)
        if len(billable_uk_des_50):
            billable_uk_des_50_count = len(billable_uk_des_50)
        else:
            billable_uk_des_50_count = 0
        billable_uk_des_25 = billable_uk_des.filtered(lambda x: x.total_billability == 25)
        if len(billable_uk_des_25):
            billable_uk_des_25_count = len(billable_uk_des_25)
        else:
            billable_uk_des_25_count = 0
        billable_uk_des_0 = billable_uk_des.filtered(lambda x: x.total_billability == 0)
        if len(billable_uk_des_0):
            billable_uk_des_0_count = len(billable_uk_des_0)
        else:
            billable_uk_des_0_count = 0
        # DPES billed
        billable_uk_dpes = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD UK / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_uk_dpes_more_100 = billable_uk_dpes.filtered(lambda x: x.total_billability > 100)
        if len(billable_uk_dpes_more_100):
            billable_uk_dpes_more_100_count = sum([i.total_billability for i in billable_uk_dpes_more_100]) / 100
            billable_uk_dpes_more_100_len = len(billable_uk_dpes_more_100)
        else:
            billable_uk_dpes_more_100_count = 0
            billable_uk_dpes_more_100_len = 0
        billable_uk_dpes_100 = billable_uk_dpes.filtered(lambda x: x.total_billability == 100)
        if len(billable_uk_dpes_100):
            billable_uk_dpes_100_count = len(billable_uk_dpes_100)
        else:
            billable_uk_dpes_100_count = 0
        billable_uk_dpes_75 = billable_uk_dpes.filtered(lambda x: x.total_billability == 75)
        if len(billable_uk_dpes_75):
            billable_uk_dpes_75_count = len(billable_uk_dpes_75)
        else:
            billable_uk_dpes_75_count = 0
        billable_uk_dpes_25 = billable_uk_dpes.filtered(lambda x: x.total_billability == 25)
        if len(billable_uk_dpes_25):
            billable_uk_dpes_25_count = len(billable_uk_dpes_25)
        else:
            billable_uk_dpes_25_count = 0
        billable_uk_dpes_50 = billable_uk_dpes.filtered(lambda x: x.total_billability == 50)
        if len(billable_uk_dpes_50):
            billable_uk_dpes_50_count = len(billable_uk_dpes_50)
        else:
            billable_uk_dpes_50_count = 0
        billable_uk_dpes_0 = billable_uk_dpes.filtered(lambda x: x.total_billability == 0)
        if len(billable_uk_dpes_0):
            billable_uk_dpes_0_count = len(billable_uk_dpes_0)
        else:
            billable_uk_dpes_0_count = 0
        # IO billed
        billable_uk_io = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD UK / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_uk_io_more_100 = billable_uk_io.filtered(lambda x: x.total_billability > 100)
        if len(billable_uk_io_more_100):
            billable_uk_io_more_100_count = sum([i.total_billability for i in billable_uk_io_more_100]) / 100
            billable_uk_io_more_100_len = len(billable_uk_io_more_100)
        else:
            billable_uk_io_more_100_count = 0
            billable_uk_io_more_100_len = 0
        billable_uk_io_100 = billable_uk_io.filtered(lambda x: x.total_billability == 100)
        if len(billable_uk_io_100):
            billable_uk_io_100_count = len(billable_uk_io_100)
        else:
            billable_uk_io_100_count = 0
        billable_uk_io_75 = billable_uk_io.filtered(lambda x: x.total_billability == 75)
        if len(billable_uk_io_75):
            billable_uk_io_75_count = len(billable_uk_io_75)
        else:
            billable_uk_io_75_count = 0
        billable_uk_io_50 = billable_uk_io.filtered(lambda x: x.total_billability == 50)
        if len(billable_uk_io_50):
            billable_uk_io_50_count = len(billable_uk_io_50)
        else:
            billable_uk_io_50_count = 0
        billable_uk_io_25 = billable_uk_io.filtered(lambda x: x.total_billability == 25)
        if len(billable_uk_io_25):
            billable_uk_io_25_count = len(billable_uk_io_25)
        else:
            billable_uk_io_25_count = 0
        billable_uk_io_0 = billable_uk_io.filtered(lambda x: x.total_billability == 0)
        if len(billable_uk_io_0):
            billable_uk_io_0_count = len(billable_uk_io_0)
        else:
            billable_uk_io_0_count = 0
        
        # Non sbu billed
        billable_uk_non_sbu = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD UK / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD UK / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd (UK)'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_uk_non_sbu_more_100 = billable_uk_non_sbu.filtered(lambda x: x.total_billability > 100)
        if len(billable_uk_non_sbu_more_100):
            billable_uk_non_sbu_more_100_count = sum([i.total_billability for i in billable_uk_non_sbu_more_100]) / 100
            billable_uk_non_sbu_more_100_len = len(billable_uk_non_sbu_more_100)
        else:
            billable_uk_non_sbu_more_100_count = 0
            billable_uk_non_sbu_more_100_len = 0
        billable_uk_non_sbu_100 = billable_uk_non_sbu.filtered(lambda x: x.total_billability == 100)
        if len(billable_uk_non_sbu_100):
            billable_uk_non_sbu_100_count = len(billable_uk_non_sbu_100)
        else:
            billable_uk_non_sbu_100_count = 0
        billable_uk_non_sbu_75 = billable_uk_non_sbu.filtered(lambda x: x.total_billability == 75)
        if len(billable_uk_non_sbu_75):
            billable_uk_non_sbu_75_count = len(billable_uk_non_sbu_75)
        else:
            billable_uk_non_sbu_75_count = 0
        billable_uk_non_sbu_50 = billable_uk_non_sbu.filtered(lambda x: x.total_billability == 50)
        if len(billable_uk_non_sbu_50):
            billable_uk_non_sbu_50_count = len(billable_uk_non_sbu_50)
        else:
            billable_uk_non_sbu_50_count = 0
        billable_uk_non_sbu_25 = billable_uk_non_sbu.filtered(lambda x: x.total_billability == 25)
        if len(billable_uk_non_sbu_25):
            billable_uk_non_sbu_25_count = len(billable_uk_non_sbu_25)
        else:
            billable_uk_non_sbu_25_count = 0
        billable_uk_non_sbu_0 = billable_uk_non_sbu.filtered(lambda x: x.total_billability == 0)
        if len(billable_uk_non_sbu_0):
            billable_uk_non_sbu_0_count = len(billable_uk_non_sbu_0)
        else:
            billable_uk_non_sbu_0_count = 0

        # DES billed inc.
        billable_inc_des = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_inc_des_more_100 = billable_inc_des.filtered(lambda x: x.total_billability > 100)
        if len(billable_inc_des_more_100):
            billable_inc_des_more_100_count = sum([i.total_billability for i in billable_inc_des_more_100]) / 100
            billable_inc_des_more_100_len = len(billable_inc_des_more_100)
        else:
            billable_inc_des_more_100_count = 0
            billable_inc_des_more_100_len = 0
        billable_inc_des_100 = billable_inc_des.filtered(lambda x: x.total_billability == 100)
        if len(billable_inc_des_100):
            billable_inc_des_100_count = len(billable_inc_des_100)
        else:
            billable_inc_des_100_count = 0
        billable_inc_des_75 = billable_inc_des.filtered(lambda x: x.total_billability == 75)
        if len(billable_inc_des_75):
            billable_inc_des_75_count = len(billable_inc_des_75)
        else:
            billable_inc_des_75_count = 0
        billable_inc_des_50 = billable_inc_des.filtered(lambda x: x.total_billability == 50)
        if len(billable_inc_des_50):
            billable_inc_des_50_count = len(billable_inc_des_50)
        else:
            billable_inc_des_50_count = 0
        billable_inc_des_25 = billable_inc_des.filtered(lambda x: x.total_billability == 25)
        if len(billable_inc_des_25):
            billable_inc_des_25_count = len(billable_inc_des_25)
        else:
            billable_inc_des_25_count = 0
        billable_inc_des_0 = billable_inc_des.filtered(lambda x: x.total_billability == 0)
        if len(billable_inc_des_0):
            billable_inc_des_0_count = len(billable_inc_des_0)
        else:
            billable_inc_des_0_count = 0
        # DPES billed
        billable_inc_dpes = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Inc / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_inc_dpes_more_100 = billable_inc_dpes.filtered(lambda x: x.total_billability > 100)
        if len(billable_inc_dpes_more_100):
            billable_inc_dpes_more_100_count = sum([i.total_billability for i in billable_inc_dpes_more_100]) / 100
            billable_inc_dpes_more_100_len = len(billable_inc_dpes_more_100)
        else:
            billable_inc_dpes_more_100_count = 0
            billable_inc_dpes_more_100_len = 0
        billable_inc_dpes_100 = billable_inc_dpes.filtered(lambda x: x.total_billability == 100)
        if len(billable_inc_dpes_100):
            billable_inc_dpes_100_count = len(billable_inc_dpes_100)
        else:
            billable_inc_dpes_100_count = 0
        billable_inc_dpes_75 = billable_inc_dpes.filtered(lambda x: x.total_billability == 75)
        if len(billable_inc_dpes_75):
            billable_inc_dpes_75_count = len(billable_inc_dpes_75)
        else:
            billable_inc_dpes_75_count = 0
        billable_inc_dpes_25 = billable_inc_dpes.filtered(lambda x: x.total_billability == 25)
        if len(billable_inc_dpes_25):
            billable_inc_dpes_25_count = len(billable_inc_dpes_25)
        else:
            billable_inc_dpes_25_count = 0
        billable_inc_dpes_50 = billable_inc_dpes.filtered(lambda x: x.total_billability == 50)
        if len(billable_inc_dpes_50):
            billable_inc_dpes_50_count = len(billable_inc_dpes_50)
        else:
            billable_inc_dpes_50_count = 0
        billable_inc_dpes_0 = billable_inc_dpes.filtered(lambda x: x.total_billability == 0)
        if len(billable_inc_dpes_0):
            billable_inc_dpes_0_count = len(billable_inc_dpes_0)
        else:
            billable_inc_dpes_0_count = 0
        # IO billed
        billable_inc_io = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Inc / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_inc_io_more_100 = billable_inc_io.filtered(lambda x: x.total_billability > 100)
        if len(billable_inc_io_more_100):
            billable_inc_io_more_100_count = sum([i.total_billability for i in billable_inc_io_more_100]) / 100
            billable_inc_io_more_100_len = len(billable_inc_io_more_100)
        else:
            billable_inc_io_more_100_count = 0
            billable_inc_io_more_100_len = 0
        billable_inc_io_100 = billable_inc_io.filtered(lambda x: x.total_billability == 100)
        if len(billable_inc_io_100):
            billable_inc_io_100_count = len(billable_inc_io_100)
        else:
            billable_inc_io_100_count = 0
        billable_inc_io_75 = billable_inc_io.filtered(lambda x: x.total_billability == 75)
        if len(billable_inc_io_75):
            billable_inc_io_75_count = len(billable_inc_io_75)
        else:
            billable_inc_io_75_count = 0
        billable_inc_io_50 = billable_inc_io.filtered(lambda x: x.total_billability == 50)
        if len(billable_inc_io_50):
            billable_inc_io_50_count = len(billable_inc_io_50)
        else:
            billable_inc_io_50_count = 0
        billable_inc_io_25 = billable_inc_io.filtered(lambda x: x.total_billability == 25)
        if len(billable_inc_io_25):
            billable_inc_io_25_count = len(billable_inc_io_25)
        else:
            billable_inc_io_25_count = 0
        billable_inc_io_0 = billable_inc_io.filtered(lambda x: x.total_billability == 0)
        if len(billable_inc_io_0):
            billable_inc_io_0_count = len(billable_inc_io_0)
        else:
            billable_inc_io_0_count = 0
        
        # Non sbu billed
        billable_inc_non_sbu = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD Inc / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Inc / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Inc.'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_inc_non_sbu_more_100 = billable_inc_non_sbu.filtered(lambda x: x.total_billability > 100)
        if len(billable_inc_non_sbu_more_100):
            billable_inc_non_sbu_more_100_count = sum([i.total_billability for i in billable_inc_non_sbu_more_100]) / 100
            billable_inc_non_sbu_more_100_len = len(billable_inc_non_sbu_more_100)
        else:
            billable_inc_non_sbu_more_100_count = 0
            billable_inc_non_sbu_more_100_len = 0
        billable_inc_non_sbu_100 = billable_inc_non_sbu.filtered(lambda x: x.total_billability == 100)
        if len(billable_inc_non_sbu_100):
            billable_inc_non_sbu_100_count = len(billable_inc_non_sbu_100)
        else:
            billable_inc_non_sbu_100_count = 0
        billable_inc_non_sbu_75 = billable_inc_non_sbu.filtered(lambda x: x.total_billability == 75)
        if len(billable_inc_non_sbu_75):
            billable_inc_non_sbu_75_count = len(billable_inc_non_sbu_75)
        else:
            billable_inc_non_sbu_75_count = 0
        billable_inc_non_sbu_50 = billable_inc_non_sbu.filtered(lambda x: x.total_billability == 50)
        if len(billable_inc_non_sbu_50):
            billable_inc_non_sbu_50_count = len(billable_inc_non_sbu_50)
        else:
            billable_inc_non_sbu_50_count = 0
        billable_inc_non_sbu_25 = billable_inc_non_sbu.filtered(lambda x: x.total_billability == 25)
        if len(billable_inc_non_sbu_25):
            billable_inc_non_sbu_25_count = len(billable_inc_non_sbu_25)
        else:
            billable_inc_non_sbu_25_count = 0
        billable_inc_non_sbu_0 = billable_inc_non_sbu.filtered(lambda x: x.total_billability == 0)
        if len(billable_inc_non_sbu_0):
            billable_inc_non_sbu_0_count = len(billable_inc_non_sbu_0)
        else:
            billable_inc_non_sbu_0_count = 0

        # DES billed gmbh.
        billable_gmbh_des = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_gmbh_des_more_100 = billable_gmbh_des.filtered(lambda x: x.total_billability > 100)
        if len(billable_gmbh_des_more_100):
            billable_gmbh_des_more_100_count = sum([i.total_billability for i in billable_gmbh_des_more_100]) / 100
            billable_gmbh_des_more_100_len = len(billable_gmbh_des_more_100)
        else:
            billable_gmbh_des_more_100_count = 0
            billable_gmbh_des_more_100_len = 0
        billable_gmbh_des_100 = billable_gmbh_des.filtered(lambda x: x.total_billability == 100)
        if len(billable_gmbh_des_100):
            billable_gmbh_des_100_count = len(billable_gmbh_des_100)
        else:
            billable_gmbh_des_100_count = 0
        billable_gmbh_des_75 = billable_gmbh_des.filtered(lambda x: x.total_billability == 75)
        if len(billable_gmbh_des_75):
            billable_gmbh_des_75_count = len(billable_gmbh_des_75)
        else:
            billable_gmbh_des_75_count = 0
        billable_gmbh_des_50 = billable_gmbh_des.filtered(lambda x: x.total_billability == 50)
        if len(billable_gmbh_des_50):
            billable_gmbh_des_50_count = len(billable_gmbh_des_50)
        else:
            billable_gmbh_des_50_count = 0
        billable_gmbh_des_25 = billable_gmbh_des.filtered(lambda x: x.total_billability == 25)
        if len(billable_gmbh_des_25):
            billable_gmbh_des_25_count = len(billable_gmbh_des_25)
        else:
            billable_gmbh_des_25_count = 0
        billable_gmbh_des_0 = billable_gmbh_des.filtered(lambda x: x.total_billability == 0)
        if len(billable_gmbh_des_0):
            billable_gmbh_des_0_count = len(billable_gmbh_des_0)
        else:
            billable_gmbh_des_0_count = 0
        # DPES billed
        billable_gmbh_dpes = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_gmbh_dpes_more_100 = billable_gmbh_dpes.filtered(lambda x: x.total_billability > 100)
        if len(billable_gmbh_dpes_more_100):
            billable_gmbh_dpes_more_100_count = sum([i.total_billability for i in billable_gmbh_dpes_more_100]) / 100
            billable_gmbh_dpes_more_100_len = len(billable_gmbh_dpes_more_100)
        else:
            billable_gmbh_dpes_more_100_count = 0
            billable_gmbh_dpes_more_100_len = 0
        billable_gmbh_dpes_100 = billable_gmbh_dpes.filtered(lambda x: x.total_billability == 100)
        if len(billable_gmbh_dpes_100):
            billable_gmbh_dpes_100_count = len(billable_gmbh_dpes_100)
        else:
            billable_gmbh_dpes_100_count = 0
        billable_gmbh_dpes_75 = billable_gmbh_dpes.filtered(lambda x: x.total_billability == 75)
        if len(billable_gmbh_dpes_75):
            billable_gmbh_dpes_75_count = len(billable_gmbh_dpes_75)
        else:
            billable_gmbh_dpes_75_count = 0
        billable_gmbh_dpes_25 = billable_gmbh_dpes.filtered(lambda x: x.total_billability == 25)
        if len(billable_gmbh_dpes_25):
            billable_gmbh_dpes_25_count = len(billable_gmbh_dpes_25)
        else:
            billable_gmbh_dpes_25_count = 0
        billable_gmbh_dpes_50 = billable_gmbh_dpes.filtered(lambda x: x.total_billability == 50)
        if len(billable_gmbh_dpes_50):
            billable_gmbh_dpes_50_count = len(billable_gmbh_dpes_50)
        else:
            billable_gmbh_dpes_50_count = 0
        billable_gmbh_dpes_0 = billable_gmbh_dpes.filtered(lambda x: x.total_billability == 0)
        if len(billable_gmbh_dpes_0):
            billable_gmbh_dpes_0_count = len(billable_gmbh_dpes_0)
        else:
            billable_gmbh_dpes_0_count = 0
        # IO billed
        billable_gmbh_io = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD GmbH / Operations / IO'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_gmbh_io_more_100 = billable_gmbh_io.filtered(lambda x: x.total_billability > 100)
        if len(billable_gmbh_io_more_100):
            billable_gmbh_io_more_100_count = sum([i.total_billability for i in billable_gmbh_io_more_100]) / 100
            billable_gmbh_io_more_100_len = len(billable_gmbh_io_more_100)
        else:
            billable_gmbh_io_more_100_count = 0
            billable_gmbh_io_more_100_len = 0
        billable_gmbh_io_100 = billable_gmbh_io.filtered(lambda x: x.total_billability == 100)
        if len(billable_gmbh_io_100):
            billable_gmbh_io_100_count = len(billable_gmbh_io_100)
        else:
            billable_gmbh_io_100_count = 0
        billable_gmbh_io_75 = billable_gmbh_io.filtered(lambda x: x.total_billability == 75)
        if len(billable_gmbh_io_75):
            billable_gmbh_io_75_count = len(billable_gmbh_io_75)
        else:
            billable_gmbh_io_75_count = 0
        billable_gmbh_io_50 = billable_gmbh_io.filtered(lambda x: x.total_billability == 50)
        if len(billable_gmbh_io_50):
            billable_gmbh_io_50_count = len(billable_gmbh_io_50)
        else:
            billable_gmbh_io_50_count = 0
        billable_gmbh_io_25 = billable_gmbh_io.filtered(lambda x: x.total_billability == 25)
        if len(billable_gmbh_io_25):
            billable_gmbh_io_25_count = len(billable_gmbh_io_25)
        else:
            billable_gmbh_io_25_count = 0
        billable_gmbh_io_0 = billable_gmbh_io.filtered(lambda x: x.total_billability == 0)
        if len(billable_gmbh_io_0):
            billable_gmbh_io_0_count = len(billable_gmbh_io_0)
        else:
            billable_gmbh_io_0_count = 0
        
        # Non sbu billed
        billable_gmbh_non_sbu = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD GmbH / Operations / DES'),
                                ('company_id','=','e-Zest Solutions GmbH'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_gmbh_non_sbu_more_100 = billable_gmbh_non_sbu.filtered(lambda x: x.total_billability > 100)
        if len(billable_gmbh_non_sbu_more_100):
            billable_gmbh_non_sbu_more_100_count = sum([i.total_billability for i in billable_gmbh_non_sbu_more_100]) / 100
            billable_gmbh_non_sbu_more_100_len = len(billable_gmbh_non_sbu_more_100)
        else:
            billable_gmbh_non_sbu_more_100_count = 0
            billable_gmbh_non_sbu_more_100_len = 0
        billable_gmbh_non_sbu_100 = billable_gmbh_non_sbu.filtered(lambda x: x.total_billability == 100)
        if len(billable_gmbh_non_sbu_100):
            billable_gmbh_non_sbu_100_count = len(billable_gmbh_non_sbu_100)
        else:
            billable_gmbh_non_sbu_100_count = 0
        billable_gmbh_non_sbu_75 = billable_gmbh_non_sbu.filtered(lambda x: x.total_billability == 75)
        if len(billable_gmbh_non_sbu_75):
            billable_gmbh_non_sbu_75_count = len(billable_gmbh_non_sbu_75)
        else:
            billable_gmbh_non_sbu_75_count = 0
        billable_gmbh_non_sbu_50 = billable_gmbh_non_sbu.filtered(lambda x: x.total_billability == 50)
        if len(billable_gmbh_non_sbu_50):
            billable_gmbh_non_sbu_50_count = len(billable_gmbh_non_sbu_50)
        else:
            billable_gmbh_non_sbu_50_count = 0
        billable_gmbh_non_sbu_25 = billable_gmbh_non_sbu.filtered(lambda x: x.total_billability == 25)
        if len(billable_gmbh_non_sbu_25):
            billable_gmbh_non_sbu_25_count = len(billable_gmbh_non_sbu_25)
        else:
            billable_gmbh_non_sbu_25_count = 0
        billable_gmbh_non_sbu_0 = billable_gmbh_non_sbu.filtered(lambda x: x.total_billability == 0)
        if len(billable_gmbh_non_sbu_0):
            billable_gmbh_non_sbu_0_count = len(billable_gmbh_non_sbu_0)
        else:
            billable_gmbh_non_sbu_0_count = 0

        # DES billed austria.
        billable_austria_des = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_austria_des_more_100 = billable_austria_des.filtered(lambda x: x.total_billability > 100)
        if len(billable_austria_des_more_100):
            billable_austria_des_more_100_count = sum([i.total_billability for i in billable_austria_des_more_100]) / 100
            billable_austria_des_more_100_len = len(billable_austria_des_more_100)
        else:
            billable_austria_des_more_100_count = 0
            billable_austria_des_more_100_len = 0
        billable_austria_des_100 = billable_austria_des.filtered(lambda x: x.total_billability == 100)
        if len(billable_austria_des_100):
            billable_austria_des_100_count = len(billable_austria_des_100)
        else:
            billable_austria_des_100_count = 0
        billable_austria_des_75 = billable_austria_des.filtered(lambda x: x.total_billability == 75)
        if len(billable_austria_des_75):
            billable_austria_des_75_count = len(billable_austria_des_75)
        else:
            billable_austria_des_75_count = 0
        billable_austria_des_50 = billable_austria_des.filtered(lambda x: x.total_billability == 50)
        if len(billable_austria_des_50):
            billable_austria_des_50_count = len(billable_austria_des_50)
        else:
            billable_austria_des_50_count = 0
        billable_austria_des_25 = billable_austria_des.filtered(lambda x: x.total_billability == 25)
        if len(billable_austria_des_25):
            billable_austria_des_25_count = len(billable_austria_des_25)
        else:
            billable_austria_des_25_count = 0
        billable_austria_des_0 = billable_austria_des.filtered(lambda x: x.total_billability == 0)
        if len(billable_austria_des_0):
            billable_austria_des_0_count = len(billable_austria_des_0)
        else:
            billable_austria_des_0_count = 0
        # DPES billed
        billable_austria_dpes = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Austria / Operations / DPES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_austria_dpes_more_100 = billable_austria_dpes.filtered(lambda x: x.total_billability > 100)
        if len(billable_austria_dpes_more_100):
            billable_austria_dpes_more_100_count = sum([i.total_billability for i in billable_austria_dpes_more_100]) / 100
            billable_austria_dpes_more_100_len = len(billable_austria_dpes_more_100)
        else:
            billable_austria_dpes_more_100_count = 0
            billable_austria_dpes_more_100_len = 0
        billable_austria_dpes_100 = billable_austria_dpes.filtered(lambda x: x.total_billability == 100)
        if len(billable_austria_dpes_100):
            billable_austria_dpes_100_count = len(billable_austria_dpes_100)
        else:
            billable_austria_dpes_100_count = 0
        billable_austria_dpes_75 = billable_austria_dpes.filtered(lambda x: x.total_billability == 75)
        if len(billable_austria_dpes_75):
            billable_austria_dpes_75_count = len(billable_austria_dpes_75)
        else:
            billable_austria_dpes_75_count = 0
        billable_austria_dpes_25 = billable_austria_dpes.filtered(lambda x: x.total_billability == 25)
        if len(billable_austria_dpes_25):
            billable_austria_dpes_25_count = len(billable_austria_dpes_25)
        else:
            billable_austria_dpes_25_count = 0
        billable_austria_dpes_50 = billable_austria_dpes.filtered(lambda x: x.total_billability == 50)
        if len(billable_austria_dpes_50):
            billable_austria_dpes_50_count = len(billable_austria_dpes_50)
        else:
            billable_austria_dpes_50_count = 0
        billable_austria_dpes_0 = billable_austria_dpes.filtered(lambda x: x.total_billability == 0)
        if len(billable_austria_dpes_0):
            billable_austria_dpes_0_count = len(billable_austria_dpes_0)
        else:
            billable_austria_dpes_0_count = 0
        # IO billed
        billable_austria_io = self.env['hr.employee'].search([
                                ('department_id', 'ilike', 'BOD Austria / Operations / IO'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_austria_io_more_100 = billable_austria_io.filtered(lambda x: x.total_billability > 100)
        if len(billable_austria_io_more_100):
            billable_austria_io_more_100_count = sum([i.total_billability for i in billable_austria_io_more_100]) / 100
            billable_austria_io_more_100_len = len(billable_austria_io_more_100)
        else:
            billable_austria_io_more_100_count = 0
            billable_austria_io_more_100_len = 0
        billable_austria_io_100 = billable_austria_io.filtered(lambda x: x.total_billability == 100)
        if len(billable_austria_io_100):
            billable_austria_io_100_count = len(billable_austria_io_100)
        else:
            billable_austria_io_100_count = 0
        billable_austria_io_75 = billable_austria_io.filtered(lambda x: x.total_billability == 75)
        if len(billable_austria_io_75):
            billable_austria_io_75_count = len(billable_austria_io_75)
        else:
            billable_austria_io_75_count = 0
        billable_austria_io_50 = billable_austria_io.filtered(lambda x: x.total_billability == 50)
        if len(billable_austria_io_50):
            billable_austria_io_50_count = len(billable_austria_io_50)
        else:
            billable_austria_io_50_count = 0
        billable_austria_io_25 = billable_austria_io.filtered(lambda x: x.total_billability == 25)
        if len(billable_austria_io_25):
            billable_austria_io_25_count = len(billable_austria_io_25)
        else:
            billable_austria_io_25_count = 0
        billable_austria_io_0 = billable_austria_io.filtered(lambda x: x.total_billability == 0)
        if len(billable_austria_io_0):
            billable_austria_io_0_count = len(billable_austria_io_0)
        else:
            billable_austria_io_0_count = 0
        
        # Non sbu billed
        billable_austria_non_sbu = self.env['hr.employee'].search([
                                ('department_id', 'not ilike', 'BOD Austria / Operations / IO'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DPES'),
                                ('department_id', 'not ilike', 'BOD Austria / Operations / DES'),
                                ('company_id','=','e-Zest Solutions Ltd, Zweigniederlassung Österreich'),
                                ('joining_date','!=',False),
                                ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable'])])
        billable_austria_non_sbu_more_100 = billable_austria_non_sbu.filtered(lambda x: x.total_billability > 100)
        if len(billable_austria_non_sbu_more_100):
            billable_austria_non_sbu_more_100_count = sum([i.total_billability for i in billable_austria_non_sbu_more_100]) / 100
            billable_austria_non_sbu_more_100_len = len(billable_austria_non_sbu_more_100)
        else:
            billable_austria_non_sbu_more_100_count = 0
            billable_austria_non_sbu_more_100_len = 0
        billable_austria_non_sbu_100 = billable_austria_non_sbu.filtered(lambda x: x.total_billability == 100)
        if len(billable_austria_non_sbu_100):
            billable_austria_non_sbu_100_count = len(billable_austria_non_sbu_100)
        else:
            billable_austria_non_sbu_100_count = 0
        billable_austria_non_sbu_75 = billable_austria_non_sbu.filtered(lambda x: x.total_billability == 75)
        if len(billable_austria_non_sbu_75):
            billable_austria_non_sbu_75_count = len(billable_austria_non_sbu_75)
        else:
            billable_austria_non_sbu_75_count = 0
        billable_austria_non_sbu_50 = billable_austria_non_sbu.filtered(lambda x: x.total_billability == 50)
        if len(billable_austria_non_sbu_50):
            billable_austria_non_sbu_50_count = len(billable_austria_non_sbu_50)
        else:
            billable_austria_non_sbu_50_count = 0
        billable_austria_non_sbu_25 = billable_austria_non_sbu.filtered(lambda x: x.total_billability == 25)
        if len(billable_austria_non_sbu_25):
            billable_austria_non_sbu_25_count = len(billable_austria_non_sbu_25)
        else:
            billable_austria_non_sbu_25_count = 0
        billable_austria_non_sbu_0 = billable_austria_non_sbu.filtered(lambda x: x.total_billability == 0)
        if len(billable_austria_non_sbu_0):
            billable_austria_non_sbu_0_count = len(billable_austria_non_sbu_0)
        else:
            billable_austria_non_sbu_0_count = 0
        
        # ltd des allocated percentage
        if deployable_des:
            allocate_percent_des = (((allocated_des_100 + allocated_des_partial)*100)//deployable_des)
        else:
            allocate_percent_des = 0

        # des billable percentage
        if deployable_des:
            des_100 = (100 / 100) * billable_des_100_count
            des_75 = (75 / 100) * billable_des_75_count
            des_50 = (50 / 100) * billable_des_50_count
            des_25 = (25 / 100) * billable_des_25_count
            billable_percent_des = (((billable_des_more_100_count + des_100 + des_75 + des_50 + des_25) * 100) // deployable_des)
        else:
            billable_percent_des = 0

        # dpes allocated percentage
        if deployable_dpes:
            allocate_percent_dpes = (((allocated_dpes_100 + allocated_dpes_partial) * 100)//deployable_dpes)
        else:
            allocate_percent_dpes = 0

        # dpes billable percentage
        if deployable_dpes:
            dpes_100 = (100 / 100) * billable_dpes_100_count
            dpes_75 = (75 / 100) * billable_dpes_75_count
            dpes_50 = (50 / 100) * billable_dpes_50_count
            dpes_25 = (25 / 100) * billable_dpes_25_count
            billable_percent_dpes = (((billable_dpes_more_100_count + dpes_100 + dpes_75 + dpes_50 + dpes_25) * 100) // deployable_dpes)
        else:
            billable_percent_dpes = 0

        # io allocated percentage
        if deployable_io:
            allocate_percent_io = (((allocated_io_partial + allocated_io_100) * 100)//deployable_io)
        else:
            allocate_percent_io = 0

        # io billable percentage
        if deployable_io:
            io_100 = (100 / 100) * billable_io_100_count
            io_75 = (75 / 100) * billable_io_75_count
            io_50 = (50 / 100) * billable_io_50_count
            io_25 = (25 / 100) * billable_io_25_count
            billable_percent_io = (((billable_io_more_100_count + io_100 + io_50 + io_75 + io_25) * 100) // deployable_io)
        else:
            billable_percent_io = 0
        # non sbu allocated percentage
        if deployable_non_sbu:
            allocate_percent_non_sbu = (((allocated_non_sbu_partial + allocated_non_sbu_100) * 100)//deployable_non_sbu)
        else:
            allocate_percent_non_sbu = 0

        # non sbu billable percentage
        if deployable_non_sbu:
            non_sbu_100 = (100 / 100) * billable_non_sbu_100_count
            non_sbu_75 = (75 / 100) * billable_non_sbu_75_count
            non_sbu_50 = (50 / 100) * billable_non_sbu_50_count
            non_sbu_25 = (25 / 100) * billable_non_sbu_25_count
            billable_percent_non_sbu = (((billable_non_sbu_more_100_count + non_sbu_100 + non_sbu_50 + non_sbu_75 + non_sbu_25) * 100) // deployable_non_sbu)
        else:
            billable_percent_non_sbu = 0

        # uk des allocated percentage
        if deployable_uk_des:
            allocate_percent_uk_des = (((allocated_des_uk_100 + allocated_des_uk_partial)*100)//deployable_uk_des)
        else:
            allocate_percent_uk_des = 0

        # des billable percentage
        if deployable_uk_des:
            des_uk_100 = (100 / 100) * billable_uk_des_100_count
            des_uk_75 = (75 / 100) * billable_uk_des_75_count
            des_uk_50 = (50 / 100) * billable_uk_des_50_count
            des_uk_25 = (25 / 100) * billable_uk_des_25_count
            billable_percent_uk_des = (((billable_uk_des_more_100_count + des_uk_100 + des_uk_75 + des_uk_50 + des_uk_25) * 100) // deployable_uk_des)
        else:
            billable_percent_uk_des = 0

        # dpes allocated percentage
        if deployable_uk_dpes:
            allocate_percent_uk_dpes = (((allocated_dpes_uk_100 + allocated_dpes_uk_partial) * 100)//deployable_uk_dpes)
        else:
            allocate_percent_uk_dpes = 0

        # dpes billable percentage
        if deployable_uk_dpes:
            dpes_uk_100 = (100 / 100) * billable_uk_dpes_100_count
            dpes_uk_75 = (75 / 100) * billable_uk_dpes_75_count
            dpes_uk_50 = (50 / 100) * billable_uk_dpes_50_count
            dpes_uk_25 = (25 / 100) * billable_uk_dpes_25_count
            billable_percent_uk_dpes = (((billable_uk_dpes_more_100_count + dpes_uk_100 + dpes_uk_75 + dpes_uk_50 + dpes_uk_25) * 100) // deployable_uk_dpes)
        else:
            billable_percent_uk_dpes = 0

        # io allocated percentage
        if deployable_uk_io:
            allocate_percent_uk_io = (((allocated_io_uk_partial + allocated_io_uk_100) * 100)//deployable_uk_io)
        else:
            allocate_percent_uk_io = 0

        # io billable percentage
        if deployable_uk_io:
            io_uk_100 = (100 / 100) * billable_uk_io_100_count
            io_uk_75 = (75 / 100) * billable_uk_io_75_count
            io_uk_50 = (50 / 100) * billable_uk_io_50_count
            io_uk_25 = (25 / 100) * billable_uk_io_25_count
            billable_percent_uk_io = (((billable_uk_io_more_100_count + io_uk_100 + io_uk_50 + io_uk_75 + io_uk_25) * 100) // deployable_uk_io)
        else:
            billable_percent_uk_io = 0
        # non sbu allocated percentage
        if deployable_uk_non_sbu:
            allocate_percent_uk_non_sbu = (((allocated_uk_non_sbu_partial + allocated_uk_non_sbu_100) * 100)//deployable_uk_non_sbu)
        else:
            allocate_percent_uk_non_sbu = 0

        # non sbu billable percentage
        if deployable_uk_non_sbu:
            non_sbu_uk_100 = (100 / 100) * billable_uk_non_sbu_100_count
            non_sbu_uk_75 = (75 / 100) * billable_uk_non_sbu_75_count
            non_sbu_uk_50 = (50 / 100) * billable_uk_non_sbu_50_count
            non_sbu_uk_25 = (25 / 100) * billable_uk_non_sbu_25_count
            billable_percent_uk_non_sbu = (((billable_uk_non_sbu_more_100_count + non_sbu_uk_100 + non_sbu_uk_50 + non_sbu_uk_75 + non_sbu_uk_25) * 100) // deployable_uk_non_sbu)
        else:
            billable_percent_uk_non_sbu = 0

        # inc des allocated percentage
        if deployable_inc_des:
            allocate_percent_inc_des = (((allocated_des_inc_100 + allocated_des_inc_partial)*100)//deployable_inc_des)
        else:
            allocate_percent_inc_des = 0

        # des billable percentage
        if deployable_inc_des:
            des_inc_100 = (100 / 100) * billable_inc_des_100_count
            des_inc_75 = (75 / 100) * billable_inc_des_75_count
            des_inc_50 = (50 / 100) * billable_inc_des_50_count
            des_inc_25 = (25 / 100) * billable_inc_des_25_count
            billable_percent_inc_des = (((billable_inc_des_more_100_count + des_inc_100 + des_inc_75 + des_inc_50 + des_inc_25) * 100) // deployable_inc_des)
        else:
            billable_percent_inc_des = 0

        # dpes allocated percentage
        if deployable_inc_dpes:
            allocate_percent_inc_dpes = (((allocated_dpes_inc_100 + allocated_dpes_inc_partial) * 100)//deployable_inc_dpes)
        else:
            allocate_percent_inc_dpes = 0

        # dpes billable percentage
        if deployable_inc_dpes:
            dpes_inc_100 = (100 / 100) * billable_inc_dpes_100_count
            dpes_inc_75 = (75 / 100) * billable_inc_dpes_75_count
            dpes_inc_50 = (50 / 100) * billable_inc_dpes_50_count
            dpes_inc_25 = (25 / 100) * billable_inc_dpes_25_count
            billable_percent_inc_dpes = (((billable_inc_dpes_more_100_count + dpes_inc_100 + dpes_inc_75 + dpes_inc_50 + dpes_inc_25) * 100) // deployable_inc_dpes)
        else:
            billable_percent_inc_dpes = 0

        # io allocated percentage
        if deployable_inc_io:
            allocate_percent_inc_io = (((allocated_io_inc_partial + allocated_io_inc_100) * 100)//deployable_inc_io)
        else:
            allocate_percent_inc_io = 0

        # io billable percentage
        if deployable_inc_io:
            io_inc_100 = (100 / 100) * billable_inc_io_100_count
            io_inc_75 = (75 / 100) * billable_inc_io_75_count
            io_inc_50 = (50 / 100) * billable_inc_io_50_count
            io_inc_25 = (25 / 100) * billable_inc_io_25_count
            billable_percent_inc_io = (((billable_inc_io_more_100_count + io_inc_100 + io_inc_50 + io_inc_75 + io_inc_25) * 100) // deployable_inc_io)
        else:
            billable_percent_inc_io = 0
        # non sbu allocated percentage
        if deployable_inc_non_sbu:
            allocate_percent_inc_non_sbu = (((allocated_inc_non_sbu_partial + allocated_inc_non_sbu_100) * 100)//deployable_inc_non_sbu)
        else:
            allocate_percent_inc_non_sbu = 0

        # non sbu billable percentage
        if deployable_inc_non_sbu:
            non_sbu_inc_100 = (100 / 100) * billable_inc_non_sbu_100_count
            non_sbu_inc_75 = (75 / 100) * billable_inc_non_sbu_75_count
            non_sbu_inc_50 = (50 / 100) * billable_inc_non_sbu_50_count
            non_sbu_inc_25 = (25 / 100) * billable_inc_non_sbu_25_count
            billable_percent_inc_non_sbu = (((billable_inc_non_sbu_more_100_count + non_sbu_inc_100 + non_sbu_inc_50 + non_sbu_inc_75 + non_sbu_inc_25) * 100) // deployable_inc_non_sbu)
        else:
            billable_percent_inc_non_sbu = 0

        # austria des allocated percentage
        if deployable_austria_des:
            allocate_percent_austria_des = (((allocated_des_austria_100 + allocated_des_austria_partial)*100)//deployable_austria_des)
        else:
            allocate_percent_austria_des = 0

        # des billable percentage
        if deployable_austria_des:
            des_austria_100 = (100 / 100) * billable_austria_des_100_count
            des_austria_75 = (75 / 100) * billable_austria_des_75_count
            des_austria_50 = (50 / 100) * billable_austria_des_50_count
            des_austria_25 = (25 / 100) * billable_austria_des_25_count
            billable_percent_austria_des = (((billable_austria_des_more_100_count + des_austria_100 + des_austria_75 + des_austria_50 + des_austria_25) * 100) // deployable_austria_des)
        else:
            billable_percent_austria_des = 0

        # dpes allocated percentage
        if deployable_austria_dpes:
            allocate_percent_austria_dpes = (((allocated_dpes_austria_100 + allocated_dpes_austria_partial) * 100)//deployable_austria_dpes)
        else:
            allocate_percent_austria_dpes = 0

        # dpes billable percentage
        if deployable_austria_dpes:
            dpes_austria_100 = (100 / 100) * billable_austria_dpes_100_count
            dpes_austria_75 = (75 / 100) * billable_austria_dpes_75_count
            dpes_austria_50 = (50 / 100) * billable_austria_dpes_50_count
            dpes_austria_25 = (25 / 100) * billable_austria_dpes_25_count
            billable_percent_austria_dpes = (((billable_austria_dpes_more_100_count + dpes_austria_100 + dpes_austria_75 + dpes_austria_50 + dpes_austria_25) * 100) // deployable_austria_dpes)
        else:
            billable_percent_austria_dpes = 0

        # io allocated percentage
        if deployable_austria_io:
            allocate_percent_austria_io = (((allocated_io_austria_partial + allocated_io_austria_100) * 100)//deployable_austria_io)
        else:
            allocate_percent_austria_io = 0

        # io billable percentage
        if deployable_austria_io:
            io_austria_100 = (100 / 100) * billable_austria_io_100_count
            io_austria_75 = (75 / 100) * billable_austria_io_75_count
            io_austria_50 = (50 / 100) * billable_austria_io_50_count
            io_austria_25 = (25 / 100) * billable_austria_io_25_count
            billable_percent_austria_io = (((billable_austria_io_more_100_count + io_austria_100 + io_austria_50 + io_austria_75 + io_austria_25) * 100) // deployable_austria_io)
        else:
            billable_percent_austria_io = 0
        # non sbu allocated percentage
        if deployable_austria_non_sbu:
            allocate_percent_austria_non_sbu = (((allocated_austria_non_sbu_partial + allocated_austria_non_sbu_100) * 100)//deployable_austria_non_sbu)
        else:
            allocate_percent_austria_non_sbu = 0

        # non sbu billable percentage
        if deployable_austria_non_sbu:
            non_sbu_austria_100 = (100 / 100) * billable_austria_non_sbu_100_count
            non_sbu_austria_75 = (75 / 100) * billable_austria_non_sbu_75_count
            non_sbu_austria_50 = (50 / 100) * billable_austria_non_sbu_50_count
            non_sbu_austria_25 = (25 / 100) * billable_austria_non_sbu_25_count
            billable_percent_austria_non_sbu = (((billable_austria_non_sbu_more_100_count + non_sbu_austria_100 + non_sbu_austria_50 + non_sbu_austria_75 + non_sbu_austria_25) * 100) // deployable_austria_non_sbu)
        else:
            billable_percent_austria_non_sbu = 0

        # gmbh des allocated percentage
        if deployable_gmbh_des:
            allocate_percent_gmbh_des = (((allocated_des_gmbh_100 + allocated_des_gmbh_partial)*100)//deployable_gmbh_des)
        else:
            allocate_percent_gmbh_des = 0

        # des billable percentage
        if deployable_gmbh_des:
            des_gmbh_100 = (100 / 100) * billable_gmbh_des_100_count
            des_gmbh_75 = (75 / 100) * billable_gmbh_des_75_count
            des_gmbh_50 = (50 / 100) * billable_gmbh_des_50_count
            des_gmbh_25 = (25 / 100) * billable_gmbh_des_25_count
            billable_percent_gmbh_des = (((billable_gmbh_des_more_100_count + des_gmbh_100 + des_gmbh_75 + des_gmbh_50 + des_gmbh_25) * 100) // deployable_gmbh_des)
        else:
            billable_percent_gmbh_des = 0

        # dpes allocated percentage
        if deployable_gmbh_dpes:
            allocate_percent_gmbh_dpes = (((allocated_dpes_gmbh_100 + allocated_dpes_gmbh_partial) * 100)//deployable_gmbh_dpes)
        else:
            allocate_percent_gmbh_dpes = 0

        # dpes billable percentage
        if deployable_gmbh_dpes:
            dpes_gmbh_100 = (100 / 100) * billable_gmbh_dpes_100_count
            dpes_gmbh_75 = (75 / 100) * billable_gmbh_dpes_75_count
            dpes_gmbh_50 = (50 / 100) * billable_gmbh_dpes_50_count
            dpes_gmbh_25 = (25 / 100) * billable_gmbh_dpes_25_count
            billable_percent_gmbh_dpes = (((billable_gmbh_dpes_more_100_count + dpes_gmbh_100 + dpes_gmbh_75 + dpes_gmbh_50 + dpes_gmbh_25) * 100) // deployable_gmbh_dpes)
        else:
            billable_percent_gmbh_dpes = 0

        # io allocated percentage
        if deployable_gmbh_io:
            allocate_percent_gmbh_io = (((allocated_io_gmbh_partial + allocated_io_gmbh_100) * 100)//deployable_gmbh_io)
        else:
            allocate_percent_gmbh_io = 0

        # io billable percentage
        if deployable_gmbh_io:
            io_gmbh_100 = (100 / 100) * billable_gmbh_io_100_count
            io_gmbh_75 = (75 / 100) * billable_gmbh_io_75_count
            io_gmbh_50 = (50 / 100) * billable_gmbh_io_50_count
            io_gmbh_25 = (25 / 100) * billable_gmbh_io_25_count
            billable_percent_gmbh_io = (((billable_gmbh_io_more_100_count + io_gmbh_100 + io_gmbh_50 + io_gmbh_75 + io_gmbh_25) * 100) // deployable_gmbh_io)
        else:
            billable_percent_gmbh_io = 0
        # non sbu allocated percentage
        if deployable_gmbh_non_sbu:
            allocate_percent_gmbh_non_sbu = (((allocated_gmbh_non_sbu_partial + allocated_gmbh_non_sbu_100) * 100)//deployable_gmbh_non_sbu)
        else:
            allocate_percent_gmbh_non_sbu = 0

        # non sbu billable percentage
        if deployable_gmbh_non_sbu:
            non_sbu_gmbh_100 = (100 / 100) * billable_gmbh_non_sbu_100_count
            non_sbu_gmbh_75 = (75 / 100) * billable_gmbh_non_sbu_75_count
            non_sbu_gmbh_50 = (50 / 100) * billable_gmbh_non_sbu_50_count
            non_sbu_gmbh_25 = (25 / 100) * billable_gmbh_non_sbu_25_count
            billable_percent_gmbh_non_sbu = (((billable_gmbh_non_sbu_more_100_count + non_sbu_gmbh_100 + non_sbu_gmbh_50 + non_sbu_gmbh_75 + non_sbu_gmbh_25) * 100) // deployable_gmbh_non_sbu)
        else:
            billable_percent_gmbh_non_sbu = 0

        operations_data = self.env['operations.summary'].search([('date', '=', fields.Date.today())])
        if operations_data:
            operations_data.operation_data_line = [(5, 0, 0)]
        else:
            operations_data = self.env['operations.summary'].create({'date': fields.Date.today()})
        summary_data = [{
            'data_type': 'sbu_wise',
            'data_name': 'DES',
            'total_ezestian': total_des,
            'total_deployable': deployable_des,
            'non_deployable': non_deployable_des,
            'more_100_billable': billable_des_more_100_len,
            'billable_100': billable_des_100_count,
            'billable_75': billable_des_75_count,
            'billable_50': billable_des_50_count,
            'billable_25': billable_des_25_count,
            'billable_0': billable_des_0_count,
            'billable_per': billable_percent_des,
            'allocation_100': allocated_des_100,
            'allocated_partially': allocated_des_partial_count,
            'unallocated': allocated_des_unallocated,
            'allocated_per': allocate_percent_des,
            'resigned': des_resigned,
            'probation': des_probation,
            'confirmed': des_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'DPES',
            'total_ezestian': total_dpes,
            'total_deployable': deployable_dpes,
            'non_deployable': non_deployable_dpes,
            'more_100_billable': billable_dpes_more_100_len,
            'billable_100': billable_dpes_100_count,
            'billable_75': billable_dpes_75_count,
            'billable_50': billable_dpes_50_count,
            'billable_25': billable_dpes_25_count,
            'billable_0': billable_dpes_0_count,
            'billable_per': billable_percent_dpes,
            'allocation_100': allocated_dpes_100,
            'allocated_partially': allocated_dpes_partial_count,
            'unallocated': allocated_dpes_unallocated,
            'allocated_per': allocate_percent_dpes,
            'resigned': dpes_resigned,
            'probation': dpes_probation,
            'confirmed': dpes_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'IO',
            'total_ezestian': total_io,
            'total_deployable': deployable_io,
            'non_deployable': non_deployable_io,
            'more_100_billable': billable_io_more_100_len,
            'billable_100': billable_io_100_count,
            'billable_75': billable_io_75_count,
            'billable_50': billable_io_50_count,
            'billable_25': billable_io_25_count,
            'billable_0': billable_io_0_count,
            'billable_per': billable_percent_io,
            'allocation_100': allocated_io_100,
            'allocated_partially': allocated_io_partial_count,
            'unallocated': allocated_io_unallocated,
            'allocated_per': allocate_percent_io,
            'resigned': io_resigned,
            'probation': io_probation,
            'confirmed': io_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Non-SBU',
            'total_ezestian': total_non_sbu,
            'total_deployable': deployable_non_sbu,
            'non_deployable': non_deployable_non_sbu,
            'more_100_billable': billable_non_sbu_more_100_len,
            'billable_100': billable_non_sbu_100_count,
            'billable_75': billable_non_sbu_75_count,
            'billable_50': billable_non_sbu_50_count,
            'billable_25': billable_non_sbu_25_count,
            'billable_0': billable_non_sbu_0_count,
            'billable_per': billable_percent_non_sbu,
            'allocation_100': allocated_non_sbu_100,
            'allocated_partially': allocated_non_sbu_partial_count,
            'unallocated': allocated_non_sbu_unallocated,
            'allocated_per': allocate_percent_non_sbu,
            'resigned': non_sbu_resigned,
            'probation': non_sbu_probation,
            'confirmed': non_sbu_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Inc DES',
            'total_ezestian': total_inc_des,
            'total_deployable': deployable_inc_des,
            'non_deployable': non_deployable_inc_des,
            'more_100_billable': billable_inc_des_more_100_len,
            'billable_100': billable_inc_des_100_count,
            'billable_75': billable_inc_des_75_count,
            'billable_50': billable_inc_des_50_count,
            'billable_25': billable_inc_des_25_count,
            'billable_0': billable_inc_des_0_count,
            'billable_per': billable_percent_inc_des,
            'allocation_100': allocated_des_inc_100,
            'allocated_partially': allocated_des_inc_partial_count,
            'unallocated': allocated_des_inc_unallocated,
            'allocated_per': allocate_percent_inc_des,
            'resigned': des_inc_resigned,
            'probation': des_inc_probation,
            'confirmed': des_inc_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Inc DPES',
            'total_ezestian': total_inc_dpes,
            'total_deployable': deployable_inc_dpes,
            'non_deployable': non_deployable_inc_dpes,
            'more_100_billable': billable_inc_dpes_more_100_len,
            'billable_100': billable_inc_dpes_100_count,
            'billable_75': billable_inc_dpes_75_count,
            'billable_50': billable_inc_dpes_50_count,
            'billable_25': billable_inc_dpes_25_count,
            'billable_0': billable_inc_dpes_0_count,
            'billable_per': billable_percent_inc_dpes,
            'allocation_100': allocated_dpes_inc_100,
            'allocated_partially': allocated_dpes_inc_partial_count,
            'unallocated': allocated_dpes_inc_unallocated,
            'allocated_per': allocate_percent_inc_dpes,
            'resigned': dpes_inc_resigned,
            'probation': dpes_inc_probation,
            'confirmed': dpes_inc_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Inc IO',
            'total_ezestian': total_inc_io,
            'total_deployable': deployable_inc_io,
            'non_deployable': non_deployable_inc_io,
            'more_100_billable': billable_inc_io_more_100_len,
            'billable_100': billable_inc_io_100_count,
            'billable_75': billable_inc_io_75_count,
            'billable_50': billable_inc_io_50_count,
            'billable_25': billable_inc_io_25_count,
            'billable_0': billable_inc_io_0_count,
            'billable_per': billable_percent_inc_io,
            'allocation_100': allocated_io_inc_100,
            'allocated_partially': allocated_io_inc_partial_count,
            'unallocated': allocated_io_inc_unallocated,
            'allocated_per': allocate_percent_inc_io,
            'resigned': io_inc_resigned,
            'probation': io_inc_probation,
            'confirmed': io_inc_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Inc Non-SBU',
            'total_ezestian': total_inc_non_sbu,
            'total_deployable': deployable_inc_non_sbu,
            'non_deployable': non_deployable_inc_non_sbu,
            'more_100_billable': billable_inc_non_sbu_more_100_len,
            'billable_100': billable_inc_non_sbu_100_count,
            'billable_75': billable_inc_non_sbu_75_count,
            'billable_50': billable_inc_non_sbu_50_count,
            'billable_25': billable_inc_non_sbu_25_count,
            'billable_0': billable_inc_non_sbu_0_count,
            'billable_per': billable_percent_inc_non_sbu,
            'allocation_100': allocated_inc_non_sbu_100,
            'allocated_partially': allocated_inc_non_sbu_partial_count,
            'unallocated': allocated_inc_non_sbu_unallocated,
            'allocated_per': allocate_percent_inc_non_sbu,
            'resigned': non_sbu_inc_resigned,
            'probation': non_sbu_inc_probation,
            'confirmed': non_sbu_inc_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'UK DES',
            'total_ezestian': total_uk_des,
            'total_deployable': deployable_uk_des,
            'non_deployable': non_deployable_uk_des,
            'more_100_billable': billable_uk_des_more_100_len,
            'billable_100': billable_uk_des_100_count,
            'billable_75': billable_uk_des_75_count,
            'billable_50': billable_uk_des_50_count,
            'billable_25': billable_uk_des_25_count,
            'billable_0': billable_uk_des_0_count,
            'billable_per': billable_percent_uk_des,
            'allocation_100': allocated_des_uk_100,
            'allocated_partially': allocated_des_uk_partial_count,
            'unallocated': allocated_des_uk_unallocated,
            'allocated_per': allocate_percent_uk_des,
            'resigned': des_uk_resigned,
            'probation': des_uk_probation,
            'confirmed': des_uk_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'UK DPES',
            'total_ezestian': total_uk_dpes,
            'total_deployable': deployable_uk_dpes,
            'non_deployable': non_deployable_uk_dpes,
            'more_100_billable': billable_uk_dpes_more_100_len,
            'billable_100': billable_uk_dpes_100_count,
            'billable_75': billable_uk_dpes_75_count,
            'billable_50': billable_uk_dpes_50_count,
            'billable_25': billable_uk_dpes_25_count,
            'billable_0': billable_uk_dpes_0_count,
            'billable_per': billable_percent_uk_dpes,
            'allocation_100': allocated_dpes_uk_100,
            'allocated_partially': allocated_dpes_uk_partial_count,
            'unallocated': allocated_dpes_uk_unallocated,
            'allocated_per': allocate_percent_uk_dpes,
            'resigned': dpes_uk_resigned,
            'probation': dpes_uk_probation,
            'confirmed': dpes_uk_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'UK IO',
            'total_ezestian': total_uk_io,
            'total_deployable': deployable_uk_io,
            'non_deployable': non_deployable_uk_io,
            'more_100_billable': billable_uk_io_more_100_len,
            'billable_100': billable_uk_io_100_count,
            'billable_75': billable_uk_io_75_count,
            'billable_50': billable_uk_io_50_count,
            'billable_25': billable_uk_io_25_count,
            'billable_0': billable_uk_io_0_count,
            'billable_per': billable_percent_uk_io,
            'allocation_100': allocated_io_uk_100,
            'allocated_partially': allocated_io_uk_partial_count,
            'unallocated': allocated_io_uk_unallocated,
            'allocated_per': allocate_percent_uk_io,
            'resigned': io_uk_resigned,
            'probation': io_uk_probation,
            'confirmed': io_uk_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'UK Non-SBU',
            'total_ezestian': total_uk_non_sbu,
            'total_deployable': deployable_uk_non_sbu,
            'non_deployable': non_deployable_uk_non_sbu,
            'more_100_billable': billable_uk_non_sbu_more_100_len,
            'billable_100': billable_uk_non_sbu_100_count,
            'billable_75': billable_uk_non_sbu_75_count,
            'billable_50': billable_uk_non_sbu_50_count,
            'billable_25': billable_uk_non_sbu_25_count,
            'billable_0': billable_uk_non_sbu_0_count,
            'billable_per': billable_percent_uk_non_sbu,
            'allocation_100': allocated_uk_non_sbu_100,
            'allocated_partially': allocated_uk_non_sbu_partial_count,
            'unallocated': allocated_uk_non_sbu_unallocated,
            'allocated_per': allocate_percent_uk_non_sbu,
            'resigned': non_sbu_uk_resigned,
            'probation': non_sbu_uk_probation,
            'confirmed': non_sbu_uk_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'GmbH DES',
            'total_ezestian': total_gmbh_des,
            'total_deployable': deployable_gmbh_des,
            'non_deployable': non_deployable_gmbh_des,
            'more_100_billable': billable_gmbh_des_more_100_len,
            'billable_100': billable_gmbh_des_100_count,
            'billable_75': billable_gmbh_des_75_count,
            'billable_50': billable_gmbh_des_50_count,
            'billable_25': billable_gmbh_des_25_count,
            'billable_0': billable_gmbh_des_0_count,
            'billable_per': billable_percent_gmbh_des,
            'allocation_100': allocated_des_gmbh_100,
            'allocated_partially': allocated_des_gmbh_partial_count,
            'unallocated': allocated_des_gmbh_unallocated,
            'allocated_per': allocate_percent_gmbh_des,
            'resigned': des_gmbh_resigned,
            'probation': des_gmbh_probation,
            'confirmed': des_gmbh_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'GmbH DPES',
            'total_ezestian': total_gmbh_dpes,
            'total_deployable': deployable_gmbh_dpes,
            'non_deployable': non_deployable_gmbh_dpes,
            'more_100_billable': billable_gmbh_dpes_more_100_len,
            'billable_100': billable_gmbh_dpes_100_count,
            'billable_75': billable_gmbh_dpes_75_count,
            'billable_50': billable_gmbh_dpes_50_count,
            'billable_25': billable_gmbh_dpes_25_count,
            'billable_0': billable_gmbh_dpes_0_count,
            'billable_per': billable_percent_gmbh_dpes,
            'allocation_100': allocated_dpes_gmbh_100,
            'allocated_partially': allocated_dpes_gmbh_partial_count,
            'unallocated': allocated_dpes_gmbh_unallocated,
            'allocated_per': allocate_percent_gmbh_dpes,
            'resigned': dpes_gmbh_resigned,
            'probation': dpes_gmbh_probation,
            'confirmed': dpes_gmbh_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'GmbH IO',
            'total_ezestian': total_gmbh_io,
            'total_deployable': deployable_gmbh_io,
            'non_deployable': non_deployable_gmbh_io,
            'more_100_billable': billable_gmbh_io_more_100_len,
            'billable_100': billable_gmbh_io_100_count,
            'billable_75': billable_gmbh_io_75_count,
            'billable_50': billable_gmbh_io_50_count,
            'billable_25': billable_gmbh_io_25_count,
            'billable_0': billable_gmbh_io_0_count,
            'billable_per': billable_percent_gmbh_io,
            'allocation_100': allocated_io_gmbh_100,
            'allocated_partially': allocated_io_gmbh_partial_count,
            'unallocated': allocated_io_gmbh_unallocated,
            'allocated_per': allocate_percent_gmbh_io,
            'resigned': io_gmbh_resigned,
            'probation': io_gmbh_probation,
            'confirmed': io_gmbh_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'GmbH Non-SBU',
            'total_ezestian': total_gmbh_non_sbu,
            'total_deployable': deployable_gmbh_non_sbu,
            'non_deployable': non_deployable_gmbh_non_sbu,
            'more_100_billable': billable_gmbh_non_sbu_more_100_len,
            'billable_100': billable_gmbh_non_sbu_100_count,
            'billable_75': billable_gmbh_non_sbu_75_count,
            'billable_50': billable_gmbh_non_sbu_50_count,
            'billable_25': billable_gmbh_non_sbu_25_count,
            'billable_0': billable_gmbh_non_sbu_0_count,
            'billable_per': billable_percent_gmbh_non_sbu,
            'allocation_100': allocated_gmbh_non_sbu_100,
            'allocated_partially': allocated_gmbh_non_sbu_partial_count,
            'unallocated': allocated_gmbh_non_sbu_unallocated,
            'allocated_per': allocate_percent_gmbh_non_sbu,
            'resigned': non_sbu_gmbh_resigned,
            'probation': non_sbu_gmbh_probation,
            'confirmed': non_sbu_gmbh_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Austria DES',
            'total_ezestian': total_austria_des,
            'total_deployable': deployable_austria_des,
            'non_deployable': non_deployable_austria_des,
            'more_100_billable': billable_austria_des_more_100_len,
            'billable_100': billable_austria_des_100_count,
            'billable_75': billable_austria_des_75_count,
            'billable_50': billable_austria_des_50_count,
            'billable_25': billable_austria_des_25_count,
            'billable_0': billable_austria_des_0_count,
            'billable_per': billable_percent_austria_des,
            'allocation_100': allocated_des_austria_100,
            'allocated_partially': allocated_des_austria_partial_count,
            'unallocated': allocated_des_austria_unallocated,
            'allocated_per': allocate_percent_austria_des,
            'resigned': des_austria_resigned,
            'probation': des_austria_probation,
            'confirmed': des_austria_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Austria DPES',
            'total_ezestian': total_austria_dpes,
            'total_deployable': deployable_austria_dpes,
            'non_deployable': non_deployable_austria_dpes,
            'more_100_billable': billable_austria_dpes_more_100_len,
            'billable_100': billable_austria_dpes_100_count,
            'billable_75': billable_austria_dpes_75_count,
            'billable_50': billable_austria_dpes_50_count,
            'billable_25': billable_austria_dpes_25_count,
            'billable_0': billable_austria_dpes_0_count,
            'billable_per': billable_percent_austria_dpes,
            'allocation_100': allocated_dpes_austria_100,
            'allocated_partially': allocated_dpes_austria_partial_count,
            'unallocated': allocated_dpes_austria_unallocated,
            'allocated_per': allocate_percent_austria_dpes,
            'resigned': dpes_austria_resigned,
            'probation': dpes_austria_probation,
            'confirmed': dpes_austria_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Austria IO',
            'total_ezestian': total_austria_io,
            'total_deployable': deployable_austria_io,
            'non_deployable': non_deployable_austria_io,
            'more_100_billable': billable_austria_io_more_100_len,
            'billable_100': billable_austria_io_100_count,
            'billable_75': billable_austria_io_75_count,
            'billable_50': billable_austria_io_50_count,
            'billable_25': billable_austria_io_25_count,
            'billable_0': billable_austria_io_0_count,
            'billable_per': billable_percent_austria_io,
            'allocation_100': allocated_io_austria_100,
            'allocated_partially': allocated_io_austria_partial_count,
            'unallocated': allocated_io_austria_unallocated,
            'allocated_per': allocate_percent_austria_io,
            'resigned': io_austria_resigned,
            'probation': io_austria_probation,
            'confirmed': io_austria_confirmed,
        }, {
            'data_type': 'sbu_wise',
            'data_name': 'Austria Non-SBU',
            'total_ezestian': total_austria_non_sbu,
            'total_deployable': deployable_austria_non_sbu,
            'non_deployable': non_deployable_austria_non_sbu,
            'more_100_billable': billable_austria_non_sbu_more_100_len,
            'billable_100': billable_austria_non_sbu_100_count,
            'billable_75': billable_austria_non_sbu_75_count,
            'billable_50': billable_austria_non_sbu_50_count,
            'billable_25': billable_austria_non_sbu_25_count,
            'billable_0': billable_austria_non_sbu_0_count,
            'billable_per': billable_percent_austria_non_sbu,
            'allocation_100': allocated_austria_non_sbu_100,
            'allocated_partially': allocated_austria_non_sbu_partial_count,
            'unallocated': allocated_austria_non_sbu_unallocated,
            'allocated_per': allocate_percent_austria_non_sbu,
            'resigned': non_sbu_austria_resigned,
            'probation': non_sbu_austria_probation,
            'confirmed': non_sbu_austria_confirmed,
        }, {
            'data_type': 'team_member_wise',
            'data_name': 'Consultant',
            'total_ezestian': emp_consultant,
            'total_deployable': emp_consultant_deployable,
            'non_deployable': emp_consultant_non_deployable,
            'more_100_billable': emp_consultant_billable_more_100_len,
            'billable_100': emp_consultant_billable_100_count,
            'billable_75': emp_consultant_billable_75_count,
            'billable_50': emp_consultant_billable_50_count,
            'billable_25': emp_consultant_billable_25_count,
            'billable_0': emp_consultant_billable_0_count,
            'billable_per': consultant_billable_percent,
            'allocation_100': emp_consultant_allocated_100,
            'allocated_partially': emp_consultant_allocated_partial_count,
            'unallocated': emp_consultant_allocated_unallocated,
            'allocated_per': consultant_allocate_percent,
            'resigned': emp_consultant_resigned,
            'probation': emp_consultant_probation,
            'confirmed': emp_consultant_confirmed,
        }, {
            'data_type': 'team_member_wise',
            'data_name': 'Intern',
            'total_ezestian': emp_rookie,
            'total_deployable': emp_rookie_deployable,
            'non_deployable': emp_rookie_non_deployable,
            'more_100_billable': emp_rookie_billable_more_100_len,
            'billable_100': emp_rookie_billable_100_count,
            'billable_75': emp_rookie_billable_75_count,
            'billable_50': emp_rookie_billable_50_count,
            'billable_25': emp_rookie_billable_25_count,
            'billable_0': emp_rookie_billable_0_count,
            'billable_per': rookie_billable_percent,
            'allocation_100': emp_rookie_allocated_100,
            'allocated_partially': emp_rookie_allocated_partial_count,
            'unallocated': emp_rookie_allocated_unallocated,
            'allocated_per': rookie_allocate_percent,
            'resigned': emp_rookie_resigned,
            'probation': emp_rookie_probation,
            'confirmed': emp_rookie_confirmed,
        }, {
            'data_type': 'team_member_wise',
            'data_name': 'e-Zestian',
            'total_ezestian': emp_ezestian,
            'total_deployable': emp_ezestian_deployable,
            'non_deployable': emp_ezestian_non_deployable,
            'more_100_billable': emp_ezestian_billable_more_100_len,
            'billable_100': emp_ezestian_billable_100_count,
            'billable_75': emp_ezestian_billable_75_count,
            'billable_50': emp_ezestian_billable_50_count,
            'billable_25': emp_ezestian_billable_25_count,
            'billable_0': emp_ezestian_billable_0_count,
            'billable_per': ezestian_billable_percent,
            'allocation_100': emp_ezestian_allocated_100,
            'allocated_partially': emp_ezestian_allocated_partial_count,
            'unallocated': emp_ezestian_allocated_unallocated,
            'allocated_per': ezestian_allocate_percent,
            'resigned': emp_ezestian_resigned,
            'probation': emp_ezestian_probation,
            'confirmed': emp_ezestian_confirmed,
        }, {
            'data_type': 'company_wise',
            'data_name': 'e-Zest Solutions Ltd.',
            'total_ezestian': emp_ltd_company,
            'total_deployable': emp_ltd_company_deployable,
            'non_deployable': emp_ltd_company_non_deployable,
            'more_100_billable': emp_ltd_company_billable_more_100_len,
            'billable_100': emp_ltd_company_billable_100_count,
            'billable_75': emp_ltd_company_billable_75_count,
            'billable_50': emp_ltd_company_billable_50_count,
            'billable_25': emp_ltd_company_billable_25_count,
            'billable_0': emp_ltd_company_billable_0_count,
            'billable_per': company_ltd_billable_percent,
            'allocation_100': emp_ltd_company_allocated_100,
            'allocated_partially': emp_ltd_company_allocated_partial_count,
            'unallocated': emp_ltd_company_unallocated,
            'allocated_per': company_ltd_allocate_percent,
            'resigned': company_ltd_resigned,
            'probation': company_ltd_probation,
            'confirmed': company_ltd_confirmed,
        }, {
            'data_type': 'company_wise',
            'data_name': 'e-Zest Solutions Inc.',
            'total_ezestian': emp_inc_company,
            'total_deployable': emp_inc_company_deployable,
            'non_deployable': emp_inc_company_non_deployable,
            'more_100_billable': emp_inc_company_billable_more_100_len,
            'billable_100': emp_inc_company_billable_100_count,
            'billable_75': emp_inc_company_billable_75_count,
            'billable_50': emp_inc_company_billable_50_count,
            'billable_25': emp_inc_company_billable_25_count,
            'billable_0': emp_inc_company_billable_0_count,
            'billable_per': company_inc_billable_percent,
            'allocation_100': emp_inc_company_allocated_100,
            'allocated_partially': emp_inc_company_allocated_partial_count,
            'unallocated': emp_inc_company_unallocated,
            'allocated_per': company_inc_allocate_percent,
            'resigned': company_inc_resigned,
            'probation': company_inc_probation,
            'confirmed': company_inc_confirmed,
        }, {
            'data_type': 'company_wise',
            'data_name': 'e-Zest Solutions Ltd (UK)',
            'total_ezestian': emp_uk_company,
            'total_deployable': emp_uk_company_deployable,
            'non_deployable': emp_uk_company_non_deployable,
            'more_100_billable': emp_uk_company_billable_more_100_len,
            'billable_100': emp_uk_company_billable_100_count,
            'billable_75': emp_uk_company_billable_75_count,
            'billable_50': emp_uk_company_billable_50_count,
            'billable_25': emp_uk_company_billable_25_count,
            'billable_0': emp_uk_company_billable_0_count,
            'billable_per': company_uk_billable_percent,
            'allocation_100': emp_uk_company_allocated_100,
            'allocated_partially': emp_uk_company_allocated_partial_count,
            'unallocated': emp_uk_company_unallocated,
            'allocated_per': company_uk_allocate_percent,
            'resigned': company_uk_resigned,
            'probation': company_uk_probation,
            'confirmed': company_uk_confirmed,
        }, {
            'data_type': 'company_wise',
            'data_name': 'e-Zest Solutions GmbH',
            'total_ezestian': emp_gmbh_company,
            'total_deployable': emp_gmbh_company_deployable,
            'non_deployable': emp_gmbh_company_non_deployable,
            'more_100_billable': emp_gmbh_company_billable_more_100_len,
            'billable_100': emp_gmbh_company_billable_100_count,
            'billable_75': emp_gmbh_company_billable_75_count,
            'billable_50': emp_gmbh_company_billable_50_count,
            'billable_25': emp_gmbh_company_billable_25_count,
            'billable_0': emp_gmbh_company_billable_0_count,
            'billable_per': company_gmbh_billable_percent,
            'allocation_100': emp_gmbh_company_allocated_100,
            'allocated_partially': emp_gmbh_company_allocated_partial_count,
            'unallocated': emp_gmbh_company_unallocated,
            'allocated_per': company_gmbh_allocate_percent,
            'resigned': company_gmbh_resigned,
            'probation': company_gmbh_probation,
            'confirmed': company_gmbh_confirmed,
        }, {
            'data_type': 'company_wise',
            'data_name': 'e-Zest Solutions Ltd, Zweigniederlassung Österreich',
            'total_ezestian': emp_austria_company,
            'total_deployable': emp_austria_company_deployable,
            'non_deployable': emp_austria_company_non_deployable,
            'more_100_billable': emp_austria_company_billable_more_100_len,
            'billable_100': emp_austria_company_billable_100_count,
            'billable_75': emp_austria_company_billable_75_count,
            'billable_50': emp_austria_company_billable_50_count,
            'billable_25': emp_austria_company_billable_25_count,
            'billable_0': emp_austria_company_billable_0_count,
            'billable_per': company_austria_billable_percent,
            'allocation_100': emp_austria_company_allocated_100,
            'allocated_partially': emp_austria_company_allocated_partial_count,
            'unallocated': emp_austria_company_unallocated,
            'allocated_per': company_austria_allocate_percent,
            'resigned': company_austria_resigned,
            'probation': company_austria_probation,
            'confirmed': company_austria_confirmed,
        }, {
            'data_type': 'global',
            'data_name': 'Global',
            'total_ezestian': emp_company,
            'total_deployable': emp_company_deployable,
            'non_deployable': emp_company_non_deployable,
            'more_100_billable': emp_company_billable_more_100_len,
            'billable_100': emp_company_billable_100_count,
            'billable_75': emp_company_billable_75_count,
            'billable_50': emp_company_billable_50_count,
            'billable_25': emp_company_billable_25_count,
            'billable_0': emp_company_billable_0_count,
            'billable_per': company_billable_percent,
            'allocation_100': emp_company_allocated_100,
            'allocated_partially': emp_company_allocated_partial_count,
            'unallocated': emp_company_unallocated,
            'allocated_per': company_allocate_percent,
            'resigned': company_resigned,
            'probation': company_probation,
            'confirmed': company_confirmed,
        }]
        operations_data.operation_data_line = [(0, 0, i) for i in summary_data]    
        if exec_email:
            message_body = '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th rowspan="2">' + 'Sr. No.' + '</th>'\
                                '<th rowspan="2">' + '' + '</th>'\
                                '<th rowspan="2">' + 'Total e-Zestian' + '</th>'\
                                '<th rowspan="2">' + 'Total Deployable' + '</th>'\
                                '<th rowspan="2">' + 'Non-deployable' + '</th>'\
                                '<th colspan="7">' + 'Currently Billed' + '</th>'\
                                '<th colspan="4">' + 'Currently Allocated' + '</th>'\
                                '<th colspan="3">' + 'Statuswise' + '</th>'\
                            '</tr>'

            message_body += '<tr style="text-align:center;">'\
                                '<td>' + 'More than 100%' + '</td>'\
                                '<td>' + '100%' + '</td>'\
                                '<td>' + '75%' + '</td>'\
                                '<td>' + '50%' + '</td>'\
                                '<td>' + '25%' + '</td>'\
                                '<td>' + '0%' + '</td>'\
                                '<td>' + 'Billable %' + '</td>'\
                                '<td>' + '100% Allocated' + '</td>'\
                                '<td>' + 'Partially Allocated' + '</td>'\
                                '<td>' + 'Un-allocated' + '</td>'\
                                '<td>' + 'Allocation %' + '</td>'\
                                '<td>' + 'Resigned' + '</td>'\
                                '<td>' + 'Probation' + '</td>'\
                                '<td>' + 'Confirmed' + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(1) + '</td>'\
                                '<td>' + str('Global') + '</td>'\
                                '<td>' + str(emp_company) + '</td>'\
                                '<td>' + str(emp_company_deployable) + '</td>'\
                                '<td>' + str(emp_company_non_deployable) + '</td>'\
                                '<td>' + str(emp_company_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_company_billable_100_count) + '</td>'\
                                '<td>' + str(emp_company_billable_75_count) + '</td>'\
                                '<td>' + str(emp_company_billable_50_count) + '</td>'\
                                '<td>' + str(emp_company_billable_25_count) + '</td>'\
                                '<td>' + str(emp_company_billable_0_count) + '</td>'\
                                '<td>' + str(company_billable_percent) + '</td>'\
                                '<td>' + str(emp_company_allocated_100) + '</td>'\
                                '<td>' + str(emp_company_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_company_unallocated) + '</td>'\
                                '<td>' + str(company_allocate_percent) + '</td>'\
                                '<td>' + str(company_resigned) + '</td>'\
                                '<td>' + str(company_probation) + '</td>'\
                                '<td>' + str(company_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(2) + '</td>'\
                                '<td colspan="16">' + 'Comapny-wise' + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(3) + '</td>'\
                                '<td>' + str('e-Zest Solutions Ltd.') + '</td>'\
                                '<td>' + str(emp_ltd_company) + '</td>'\
                                '<td>' + str(emp_ltd_company_deployable) + '</td>'\
                                '<td>' + str(emp_ltd_company_non_deployable) + '</td>'\
                                '<td>' + str(emp_ltd_company_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_ltd_company_billable_100_count) + '</td>'\
                                '<td>' + str(emp_ltd_company_billable_75_count) + '</td>'\
                                '<td>' + str(emp_ltd_company_billable_50_count) + '</td>'\
                                '<td>' + str(emp_ltd_company_billable_25_count) + '</td>'\
                                '<td>' + str(emp_ltd_company_billable_0_count) + '</td>'\
                                '<td>' + str(company_ltd_billable_percent) + '</td>'\
                                '<td>' + str(emp_ltd_company_allocated_100) + '</td>'\
                                '<td>' + str(emp_ltd_company_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_ltd_company_unallocated) + '</td>'\
                                '<td>' + str(company_ltd_allocate_percent) + '</td>'\
                                '<td>' + str(company_ltd_resigned) + '</td>'\
                                '<td>' + str(company_ltd_probation) + '</td>'\
                                '<td>' + str(company_ltd_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(4) + '</td>'\
                                '<td>' + str('e-Zest Solutions Inc.') + '</td>'\
                                '<td>' + str(emp_inc_company) + '</td>'\
                                '<td>' + str(emp_inc_company_deployable) + '</td>'\
                                '<td>' + str(emp_inc_company_non_deployable) + '</td>'\
                                '<td>' + str(emp_inc_company_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_inc_company_billable_100_count) + '</td>'\
                                '<td>' + str(emp_inc_company_billable_75_count) + '</td>'\
                                '<td>' + str(emp_inc_company_billable_50_count) + '</td>'\
                                '<td>' + str(emp_inc_company_billable_25_count) + '</td>'\
                                '<td>' + str(emp_inc_company_billable_0_count) + '</td>'\
                                '<td>' + str(company_inc_billable_percent) + '</td>'\
                                '<td>' + str(emp_inc_company_allocated_100) + '</td>'\
                                '<td>' + str(emp_inc_company_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_inc_company_unallocated) + '</td>'\
                                '<td>' + str(company_inc_allocate_percent) + '</td>'\
                                '<td>' + str(company_inc_resigned) + '</td>'\
                                '<td>' + str(company_inc_probation) + '</td>'\
                                '<td>' + str(company_inc_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(5) + '</td>'\
                                '<td>' + str('e-Zest Solutions Ltd (UK)') + '</td>'\
                                '<td>' + str(emp_uk_company) + '</td>'\
                                '<td>' + str(emp_uk_company_deployable) + '</td>'\
                                '<td>' + str(emp_uk_company_non_deployable) + '</td>'\
                                '<td>' + str(emp_uk_company_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_uk_company_billable_100_count) + '</td>'\
                                '<td>' + str(emp_uk_company_billable_75_count) + '</td>'\
                                '<td>' + str(emp_uk_company_billable_50_count) + '</td>'\
                                '<td>' + str(emp_uk_company_billable_25_count) + '</td>'\
                                '<td>' + str(emp_uk_company_billable_0_count) + '</td>'\
                                '<td>' + str(company_uk_billable_percent) + '</td>'\
                                '<td>' + str(emp_uk_company_allocated_100) + '</td>'\
                                '<td>' + str(emp_uk_company_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_uk_company_unallocated) + '</td>'\
                                '<td>' + str(company_uk_allocate_percent) + '</td>'\
                                '<td>' + str(company_uk_resigned) + '</td>'\
                                '<td>' + str(company_uk_probation) + '</td>'\
                                '<td>' + str(company_uk_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(6) + '</td>'\
                                '<td>' + str('e-Zest Solutions GmbH') + '</td>'\
                                '<td>' + str(emp_gmbh_company) + '</td>'\
                                '<td>' + str(emp_gmbh_company_deployable) + '</td>'\
                                '<td>' + str(emp_gmbh_company_non_deployable) + '</td>'\
                                '<td>' + str(emp_gmbh_company_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_gmbh_company_billable_100_count) + '</td>'\
                                '<td>' + str(emp_gmbh_company_billable_75_count) + '</td>'\
                                '<td>' + str(emp_gmbh_company_billable_50_count) + '</td>'\
                                '<td>' + str(emp_gmbh_company_billable_25_count) + '</td>'\
                                '<td>' + str(emp_gmbh_company_billable_0_count) + '</td>'\
                                '<td>' + str(company_gmbh_billable_percent) + '</td>'\
                                '<td>' + str(emp_gmbh_company_allocated_100) + '</td>'\
                                '<td>' + str(emp_gmbh_company_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_gmbh_company_unallocated) + '</td>'\
                                '<td>' + str(company_gmbh_allocate_percent) + '</td>'\
                                '<td>' + str(company_gmbh_resigned) + '</td>'\
                                '<td>' + str(company_gmbh_probation) + '</td>'\
                                '<td>' + str(company_gmbh_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(7) + '</td>'\
                                '<td>' + str('e-Zest Solutions Ltd, Zweigniederlassung Österreich') + '</td>'\
                                '<td>' + str(emp_austria_company) + '</td>'\
                                '<td>' + str(emp_austria_company_deployable) + '</td>'\
                                '<td>' + str(emp_austria_company_non_deployable) + '</td>'\
                                '<td>' + str(emp_austria_company_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_austria_company_billable_100_count) + '</td>'\
                                '<td>' + str(emp_austria_company_billable_75_count) + '</td>'\
                                '<td>' + str(emp_austria_company_billable_50_count) + '</td>'\
                                '<td>' + str(emp_austria_company_billable_25_count) + '</td>'\
                                '<td>' + str(emp_austria_company_billable_0_count) + '</td>'\
                                '<td>' + str(company_austria_billable_percent) + '</td>'\
                                '<td>' + str(emp_austria_company_allocated_100) + '</td>'\
                                '<td>' + str(emp_austria_company_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_austria_company_unallocated) + '</td>'\
                                '<td>' + str(company_austria_allocate_percent) + '</td>'\
                                '<td>' + str(company_austria_resigned) + '</td>'\
                                '<td>' + str(company_austria_probation) + '</td>'\
                                '<td>' + str(company_austria_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(8) + '</td>'\
                                '<td colspan="16">' + 'SBU-wise (Ltd.)' + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(9) + '</td>'\
                                '<td>' + str('DES') + '</td>'\
                                '<td>' + str(total_des) + '</td>'\
                                '<td>' + str(deployable_des) + '</td>'\
                                '<td>' + str(non_deployable_des) + '</td>'\
                                '<td>' + str(billable_des_more_100_len) + '</td>'\
                                '<td>' + str(billable_des_100_count) + '</td>'\
                                '<td>' + str(billable_des_75_count) + '</td>'\
                                '<td>' + str(billable_des_50_count) + '</td>'\
                                '<td>' + str(billable_des_25_count) + '</td>'\
                                '<td>' + str(billable_des_0_count) + '</td>'\
                                '<td>' + str(billable_percent_des) + '</td>'\
                                '<td>' + str(allocated_des_100) + '</td>'\
                                '<td>' + str(allocated_des_partial_count) + '</td>'\
                                '<td>' + str(allocated_des_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_des) + '</td>'\
                                '<td>' + str(des_resigned) + '</td>'\
                                '<td>' + str(des_probation) + '</td>'\
                                '<td>' + str(des_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(10) + '</td>'\
                                '<td>' + str('DPES') + '</td>'\
                                '<td>' + str(total_dpes) + '</td>'\
                                '<td>' + str(deployable_dpes) + '</td>'\
                                '<td>' + str(non_deployable_dpes) + '</td>'\
                                '<td>' + str(billable_dpes_more_100_len) + '</td>'\
                                '<td>' + str(billable_dpes_100_count) + '</td>'\
                                '<td>' + str(billable_dpes_75_count) + '</td>'\
                                '<td>' + str(billable_dpes_50_count) + '</td>'\
                                '<td>' + str(billable_dpes_25_count) + '</td>'\
                                '<td>' + str(billable_dpes_0_count) + '</td>'\
                                '<td>' + str(billable_percent_dpes) + '</td>'\
                                '<td>' + str(allocated_dpes_100) + '</td>'\
                                '<td>' + str(allocated_dpes_partial_count) + '</td>'\
                                '<td>' + str(allocated_dpes_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_dpes) + '</td>'\
                                '<td>' + str(dpes_resigned) + '</td>'\
                                '<td>' + str(dpes_probation) + '</td>'\
                                '<td>' + str(dpes_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(11) + '</td>'\
                                '<td>' + str('IO') + '</td>'\
                                '<td>' + str(total_io) + '</td>'\
                                '<td>' + str(deployable_io) + '</td>'\
                                '<td>' + str(non_deployable_io) + '</td>'\
                                '<td>' + str(billable_io_more_100_len) + '</td>'\
                                '<td>' + str(billable_io_100_count) + '</td>'\
                                '<td>' + str(billable_io_75_count) + '</td>'\
                                '<td>' + str(billable_io_50_count) + '</td>'\
                                '<td>' + str(billable_io_25_count) + '</td>'\
                                '<td>' + str(billable_io_0_count) + '</td>'\
                                '<td>' + str(billable_percent_io) + '</td>'\
                                '<td>' + str(allocated_io_100) + '</td>'\
                                '<td>' + str(allocated_io_partial_count) + '</td>'\
                                '<td>' + str(allocated_io_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_io) + '</td>'\
                                '<td>' + str(io_resigned) + '</td>'\
                                '<td>' + str(io_probation) + '</td>'\
                                '<td>' + str(io_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(12) + '</td>'\
                                '<td>' + str('Non SBU') + '</td>'\
                                '<td>' + str(total_non_sbu) + '</td>'\
                                '<td>' + str(deployable_non_sbu) + '</td>'\
                                '<td>' + str(non_deployable_non_sbu) + '</td>'\
                                '<td>' + str(billable_non_sbu_more_100_len) + '</td>'\
                                '<td>' + str(billable_non_sbu_100_count) + '</td>'\
                                '<td>' + str(billable_non_sbu_75_count) + '</td>'\
                                '<td>' + str(billable_non_sbu_50_count) + '</td>'\
                                '<td>' + str(billable_non_sbu_25_count) + '</td>'\
                                '<td>' + str(billable_non_sbu_0_count) + '</td>'\
                                '<td>' + str(billable_percent_non_sbu) + '</td>'\
                                '<td>' + str(allocated_non_sbu_100) + '</td>'\
                                '<td>' + str(allocated_non_sbu_partial_count) + '</td>'\
                                '<td>' + str(allocated_non_sbu_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_non_sbu) + '</td>'\
                                '<td>' + str(non_sbu_resigned) + '</td>'\
                                '<td>' + str(non_sbu_probation) + '</td>'\
                                '<td>' + str(non_sbu_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(13) + '</td>'\
                                '<td colspan="16">' + 'SBU-wise (UK)' + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(14) + '</td>'\
                                '<td>' + str('DES') + '</td>'\
                                '<td>' + str(total_uk_des) + '</td>'\
                                '<td>' + str(deployable_uk_des) + '</td>'\
                                '<td>' + str(non_deployable_uk_des) + '</td>'\
                                '<td>' + str(billable_uk_des_more_100_len) + '</td>'\
                                '<td>' + str(billable_uk_des_100_count) + '</td>'\
                                '<td>' + str(billable_uk_des_75_count) + '</td>'\
                                '<td>' + str(billable_uk_des_50_count) + '</td>'\
                                '<td>' + str(billable_uk_des_25_count) + '</td>'\
                                '<td>' + str(billable_uk_des_0_count) + '</td>'\
                                '<td>' + str(billable_percent_uk_des) + '</td>'\
                                '<td>' + str(allocated_des_uk_100) + '</td>'\
                                '<td>' + str(allocated_des_uk_partial_count) + '</td>'\
                                '<td>' + str(allocated_des_uk_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_uk_des) + '</td>'\
                                '<td>' + str(des_uk_resigned) + '</td>'\
                                '<td>' + str(des_uk_probation) + '</td>'\
                                '<td>' + str(des_uk_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(15) + '</td>'\
                                '<td>' + str('DPES') + '</td>'\
                                '<td>' + str(total_uk_dpes) + '</td>'\
                                '<td>' + str(deployable_uk_dpes) + '</td>'\
                                '<td>' + str(non_deployable_uk_dpes) + '</td>'\
                                '<td>' + str(billable_uk_dpes_more_100_len) + '</td>'\
                                '<td>' + str(billable_uk_dpes_100_count) + '</td>'\
                                '<td>' + str(billable_uk_dpes_75_count) + '</td>'\
                                '<td>' + str(billable_uk_dpes_50_count) + '</td>'\
                                '<td>' + str(billable_uk_dpes_25_count) + '</td>'\
                                '<td>' + str(billable_uk_dpes_0_count) + '</td>'\
                                '<td>' + str(billable_percent_uk_dpes) + '</td>'\
                                '<td>' + str(allocated_dpes_uk_100) + '</td>'\
                                '<td>' + str(allocated_dpes_uk_partial_count) + '</td>'\
                                '<td>' + str(allocated_dpes_uk_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_uk_dpes) + '</td>'\
                                '<td>' + str(dpes_uk_resigned) + '</td>'\
                                '<td>' + str(dpes_uk_probation) + '</td>'\
                                '<td>' + str(dpes_uk_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(16) + '</td>'\
                                '<td>' + str('IO') + '</td>'\
                                '<td>' + str(total_uk_io) + '</td>'\
                                '<td>' + str(deployable_uk_io) + '</td>'\
                                '<td>' + str(non_deployable_uk_io) + '</td>'\
                                '<td>' + str(billable_uk_io_more_100_len) + '</td>'\
                                '<td>' + str(billable_uk_io_100_count) + '</td>'\
                                '<td>' + str(billable_uk_io_75_count) + '</td>'\
                                '<td>' + str(billable_uk_io_50_count) + '</td>'\
                                '<td>' + str(billable_uk_io_25_count) + '</td>'\
                                '<td>' + str(billable_uk_io_0_count) + '</td>'\
                                '<td>' + str(billable_percent_uk_io) + '</td>'\
                                '<td>' + str(allocated_io_uk_100) + '</td>'\
                                '<td>' + str(allocated_io_uk_partial_count) + '</td>'\
                                '<td>' + str(allocated_io_uk_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_uk_io) + '</td>'\
                                '<td>' + str(io_uk_resigned) + '</td>'\
                                '<td>' + str(io_uk_probation) + '</td>'\
                                '<td>' + str(io_uk_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(17) + '</td>'\
                                '<td>' + str('Non SBU') + '</td>'\
                                '<td>' + str(total_uk_non_sbu) + '</td>'\
                                '<td>' + str(deployable_uk_non_sbu) + '</td>'\
                                '<td>' + str(non_deployable_uk_non_sbu) + '</td>'\
                                '<td>' + str(billable_uk_non_sbu_more_100_len) + '</td>'\
                                '<td>' + str(billable_uk_non_sbu_100_count) + '</td>'\
                                '<td>' + str(billable_uk_non_sbu_75_count) + '</td>'\
                                '<td>' + str(billable_uk_non_sbu_50_count) + '</td>'\
                                '<td>' + str(billable_uk_non_sbu_25_count) + '</td>'\
                                '<td>' + str(billable_uk_non_sbu_0_count) + '</td>'\
                                '<td>' + str(billable_percent_uk_non_sbu) + '</td>'\
                                '<td>' + str(allocated_uk_non_sbu_100) + '</td>'\
                                '<td>' + str(allocated_uk_non_sbu_partial_count) + '</td>'\
                                '<td>' + str(allocated_uk_non_sbu_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_uk_non_sbu) + '</td>'\
                                '<td>' + str(non_sbu_uk_resigned) + '</td>'\
                                '<td>' + str(non_sbu_uk_probation) + '</td>'\
                                '<td>' + str(non_sbu_uk_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(18) + '</td>'\
                                '<td colspan="16">' + 'SBU-wise (GmbH)' + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(19) + '</td>'\
                                '<td>' + str('DES') + '</td>'\
                                '<td>' + str(total_gmbh_des) + '</td>'\
                                '<td>' + str(deployable_gmbh_des) + '</td>'\
                                '<td>' + str(non_deployable_gmbh_des) + '</td>'\
                                '<td>' + str(billable_gmbh_des_more_100_len) + '</td>'\
                                '<td>' + str(billable_gmbh_des_100_count) + '</td>'\
                                '<td>' + str(billable_gmbh_des_75_count) + '</td>'\
                                '<td>' + str(billable_gmbh_des_50_count) + '</td>'\
                                '<td>' + str(billable_gmbh_des_25_count) + '</td>'\
                                '<td>' + str(billable_gmbh_des_0_count) + '</td>'\
                                '<td>' + str(billable_percent_gmbh_des) + '</td>'\
                                '<td>' + str(allocated_des_gmbh_100) + '</td>'\
                                '<td>' + str(allocated_des_gmbh_partial_count) + '</td>'\
                                '<td>' + str(allocated_des_gmbh_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_gmbh_des) + '</td>'\
                                '<td>' + str(des_gmbh_resigned) + '</td>'\
                                '<td>' + str(des_gmbh_probation) + '</td>'\
                                '<td>' + str(des_gmbh_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(20) + '</td>'\
                                '<td>' + str('DPES') + '</td>'\
                                '<td>' + str(total_gmbh_dpes) + '</td>'\
                                '<td>' + str(deployable_gmbh_dpes) + '</td>'\
                                '<td>' + str(non_deployable_gmbh_dpes) + '</td>'\
                                '<td>' + str(billable_gmbh_dpes_more_100_len) + '</td>'\
                                '<td>' + str(billable_gmbh_dpes_100_count) + '</td>'\
                                '<td>' + str(billable_gmbh_dpes_75_count) + '</td>'\
                                '<td>' + str(billable_gmbh_dpes_50_count) + '</td>'\
                                '<td>' + str(billable_gmbh_dpes_25_count) + '</td>'\
                                '<td>' + str(billable_gmbh_dpes_0_count) + '</td>'\
                                '<td>' + str(billable_percent_gmbh_dpes) + '</td>'\
                                '<td>' + str(allocated_dpes_gmbh_100) + '</td>'\
                                '<td>' + str(allocated_dpes_gmbh_partial_count) + '</td>'\
                                '<td>' + str(allocated_dpes_gmbh_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_gmbh_dpes) + '</td>'\
                                '<td>' + str(dpes_gmbh_resigned) + '</td>'\
                                '<td>' + str(dpes_gmbh_probation) + '</td>'\
                                '<td>' + str(dpes_gmbh_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(21) + '</td>'\
                                '<td>' + str('IO') + '</td>'\
                                '<td>' + str(total_gmbh_io) + '</td>'\
                                '<td>' + str(deployable_gmbh_io) + '</td>'\
                                '<td>' + str(non_deployable_gmbh_io) + '</td>'\
                                '<td>' + str(billable_gmbh_io_more_100_len) + '</td>'\
                                '<td>' + str(billable_gmbh_io_100_count) + '</td>'\
                                '<td>' + str(billable_gmbh_io_75_count) + '</td>'\
                                '<td>' + str(billable_gmbh_io_50_count) + '</td>'\
                                '<td>' + str(billable_gmbh_io_25_count) + '</td>'\
                                '<td>' + str(billable_gmbh_io_0_count) + '</td>'\
                                '<td>' + str(billable_percent_gmbh_io) + '</td>'\
                                '<td>' + str(allocated_io_gmbh_100) + '</td>'\
                                '<td>' + str(allocated_io_gmbh_partial_count) + '</td>'\
                                '<td>' + str(allocated_io_gmbh_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_gmbh_io) + '</td>'\
                                '<td>' + str(io_gmbh_resigned) + '</td>'\
                                '<td>' + str(io_gmbh_probation) + '</td>'\
                                '<td>' + str(io_gmbh_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(22) + '</td>'\
                                '<td>' + str('Non SBU') + '</td>'\
                                '<td>' + str(total_gmbh_non_sbu) + '</td>'\
                                '<td>' + str(deployable_gmbh_non_sbu) + '</td>'\
                                '<td>' + str(non_deployable_gmbh_non_sbu) + '</td>'\
                                '<td>' + str(billable_gmbh_non_sbu_more_100_len) + '</td>'\
                                '<td>' + str(billable_gmbh_non_sbu_100_count) + '</td>'\
                                '<td>' + str(billable_gmbh_non_sbu_75_count) + '</td>'\
                                '<td>' + str(billable_gmbh_non_sbu_50_count) + '</td>'\
                                '<td>' + str(billable_gmbh_non_sbu_25_count) + '</td>'\
                                '<td>' + str(billable_gmbh_non_sbu_0_count) + '</td>'\
                                '<td>' + str(billable_percent_gmbh_non_sbu) + '</td>'\
                                '<td>' + str(allocated_gmbh_non_sbu_100) + '</td>'\
                                '<td>' + str(allocated_gmbh_non_sbu_partial_count) + '</td>'\
                                '<td>' + str(allocated_gmbh_non_sbu_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_gmbh_non_sbu) + '</td>'\
                                '<td>' + str(non_sbu_gmbh_resigned) + '</td>'\
                                '<td>' + str(non_sbu_gmbh_probation) + '</td>'\
                                '<td>' + str(non_sbu_gmbh_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(23) + '</td>'\
                                '<td colspan="16">' + 'SBU-wise (Austria)' + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(24) + '</td>'\
                                '<td>' + str('DES') + '</td>'\
                                '<td>' + str(total_austria_des) + '</td>'\
                                '<td>' + str(deployable_austria_des) + '</td>'\
                                '<td>' + str(non_deployable_austria_des) + '</td>'\
                                '<td>' + str(billable_austria_des_more_100_len) + '</td>'\
                                '<td>' + str(billable_austria_des_100_count) + '</td>'\
                                '<td>' + str(billable_austria_des_75_count) + '</td>'\
                                '<td>' + str(billable_austria_des_50_count) + '</td>'\
                                '<td>' + str(billable_austria_des_25_count) + '</td>'\
                                '<td>' + str(billable_austria_des_0_count) + '</td>'\
                                '<td>' + str(billable_percent_austria_des) + '</td>'\
                                '<td>' + str(allocated_des_austria_100) + '</td>'\
                                '<td>' + str(allocated_des_austria_partial_count) + '</td>'\
                                '<td>' + str(allocated_des_austria_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_austria_des) + '</td>'\
                                '<td>' + str(des_austria_resigned) + '</td>'\
                                '<td>' + str(des_austria_probation) + '</td>'\
                                '<td>' + str(des_austria_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(25) + '</td>'\
                                '<td>' + str('DPES') + '</td>'\
                                '<td>' + str(total_austria_dpes) + '</td>'\
                                '<td>' + str(deployable_austria_dpes) + '</td>'\
                                '<td>' + str(non_deployable_austria_dpes) + '</td>'\
                                '<td>' + str(billable_austria_dpes_more_100_len) + '</td>'\
                                '<td>' + str(billable_austria_dpes_100_count) + '</td>'\
                                '<td>' + str(billable_austria_dpes_75_count) + '</td>'\
                                '<td>' + str(billable_austria_dpes_50_count) + '</td>'\
                                '<td>' + str(billable_austria_dpes_25_count) + '</td>'\
                                '<td>' + str(billable_austria_dpes_0_count) + '</td>'\
                                '<td>' + str(billable_percent_austria_dpes) + '</td>'\
                                '<td>' + str(allocated_dpes_austria_100) + '</td>'\
                                '<td>' + str(allocated_dpes_austria_partial_count) + '</td>'\
                                '<td>' + str(allocated_dpes_austria_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_austria_dpes) + '</td>'\
                                '<td>' + str(dpes_austria_resigned) + '</td>'\
                                '<td>' + str(dpes_austria_probation) + '</td>'\
                                '<td>' + str(dpes_austria_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(26) + '</td>'\
                                '<td>' + str('IO') + '</td>'\
                                '<td>' + str(total_austria_io) + '</td>'\
                                '<td>' + str(deployable_austria_io) + '</td>'\
                                '<td>' + str(non_deployable_austria_io) + '</td>'\
                                '<td>' + str(billable_austria_io_more_100_len) + '</td>'\
                                '<td>' + str(billable_austria_io_100_count) + '</td>'\
                                '<td>' + str(billable_austria_io_75_count) + '</td>'\
                                '<td>' + str(billable_austria_io_50_count) + '</td>'\
                                '<td>' + str(billable_austria_io_25_count) + '</td>'\
                                '<td>' + str(billable_austria_io_0_count) + '</td>'\
                                '<td>' + str(billable_percent_austria_io) + '</td>'\
                                '<td>' + str(allocated_io_austria_100) + '</td>'\
                                '<td>' + str(allocated_io_austria_partial_count) + '</td>'\
                                '<td>' + str(allocated_io_austria_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_austria_io) + '</td>'\
                                '<td>' + str(io_austria_resigned) + '</td>'\
                                '<td>' + str(io_austria_probation) + '</td>'\
                                '<td>' + str(io_austria_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(27) + '</td>'\
                                '<td>' + str('Non SBU') + '</td>'\
                                '<td>' + str(total_austria_non_sbu) + '</td>'\
                                '<td>' + str(deployable_austria_non_sbu) + '</td>'\
                                '<td>' + str(non_deployable_austria_non_sbu) + '</td>'\
                                '<td>' + str(billable_austria_non_sbu_more_100_len) + '</td>'\
                                '<td>' + str(billable_austria_non_sbu_100_count) + '</td>'\
                                '<td>' + str(billable_austria_non_sbu_75_count) + '</td>'\
                                '<td>' + str(billable_austria_non_sbu_50_count) + '</td>'\
                                '<td>' + str(billable_austria_non_sbu_25_count) + '</td>'\
                                '<td>' + str(billable_austria_non_sbu_0_count) + '</td>'\
                                '<td>' + str(billable_percent_austria_non_sbu) + '</td>'\
                                '<td>' + str(allocated_austria_non_sbu_100) + '</td>'\
                                '<td>' + str(allocated_austria_non_sbu_partial_count) + '</td>'\
                                '<td>' + str(allocated_austria_non_sbu_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_austria_non_sbu) + '</td>'\
                                '<td>' + str(non_sbu_austria_resigned) + '</td>'\
                                '<td>' + str(non_sbu_austria_probation) + '</td>'\
                                '<td>' + str(non_sbu_austria_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(28) + '</td>'\
                                '<td colspan="16">' + 'SBU-wise (Inc.)' + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(29) + '</td>'\
                                '<td>' + str('DES') + '</td>'\
                                '<td>' + str(total_inc_des) + '</td>'\
                                '<td>' + str(deployable_inc_des) + '</td>'\
                                '<td>' + str(non_deployable_inc_des) + '</td>'\
                                '<td>' + str(billable_inc_des_more_100_len) + '</td>'\
                                '<td>' + str(billable_inc_des_100_count) + '</td>'\
                                '<td>' + str(billable_inc_des_75_count) + '</td>'\
                                '<td>' + str(billable_inc_des_50_count) + '</td>'\
                                '<td>' + str(billable_inc_des_25_count) + '</td>'\
                                '<td>' + str(billable_inc_des_0_count) + '</td>'\
                                '<td>' + str(billable_percent_inc_des) + '</td>'\
                                '<td>' + str(allocated_des_inc_100) + '</td>'\
                                '<td>' + str(allocated_des_inc_partial_count) + '</td>'\
                                '<td>' + str(allocated_des_inc_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_inc_des) + '</td>'\
                                '<td>' + str(des_inc_resigned) + '</td>'\
                                '<td>' + str(des_inc_probation) + '</td>'\
                                '<td>' + str(des_inc_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(30) + '</td>'\
                                '<td>' + str('DPES') + '</td>'\
                                '<td>' + str(total_inc_dpes) + '</td>'\
                                '<td>' + str(deployable_inc_dpes) + '</td>'\
                                '<td>' + str(non_deployable_inc_dpes) + '</td>'\
                                '<td>' + str(billable_inc_dpes_more_100_len) + '</td>'\
                                '<td>' + str(billable_inc_dpes_100_count) + '</td>'\
                                '<td>' + str(billable_inc_dpes_75_count) + '</td>'\
                                '<td>' + str(billable_inc_dpes_50_count) + '</td>'\
                                '<td>' + str(billable_inc_dpes_25_count) + '</td>'\
                                '<td>' + str(billable_inc_dpes_0_count) + '</td>'\
                                '<td>' + str(billable_percent_inc_dpes) + '</td>'\
                                '<td>' + str(allocated_dpes_inc_100) + '</td>'\
                                '<td>' + str(allocated_dpes_inc_partial_count) + '</td>'\
                                '<td>' + str(allocated_dpes_inc_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_inc_dpes) + '</td>'\
                                '<td>' + str(dpes_inc_resigned) + '</td>'\
                                '<td>' + str(dpes_inc_probation) + '</td>'\
                                '<td>' + str(dpes_inc_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(31) + '</td>'\
                                '<td>' + str('IO') + '</td>'\
                                '<td>' + str(total_inc_io) + '</td>'\
                                '<td>' + str(deployable_inc_io) + '</td>'\
                                '<td>' + str(non_deployable_inc_io) + '</td>'\
                                '<td>' + str(billable_inc_io_more_100_len) + '</td>'\
                                '<td>' + str(billable_inc_io_100_count) + '</td>'\
                                '<td>' + str(billable_inc_io_75_count) + '</td>'\
                                '<td>' + str(billable_inc_io_50_count) + '</td>'\
                                '<td>' + str(billable_inc_io_25_count) + '</td>'\
                                '<td>' + str(billable_inc_io_0_count) + '</td>'\
                                '<td>' + str(billable_percent_inc_io) + '</td>'\
                                '<td>' + str(allocated_io_inc_100) + '</td>'\
                                '<td>' + str(allocated_io_inc_partial_count) + '</td>'\
                                '<td>' + str(allocated_io_inc_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_inc_io) + '</td>'\
                                '<td>' + str(io_inc_resigned) + '</td>'\
                                '<td>' + str(io_inc_probation) + '</td>'\
                                '<td>' + str(io_inc_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(32) + '</td>'\
                                '<td>' + str('Non SBU') + '</td>'\
                                '<td>' + str(total_inc_non_sbu) + '</td>'\
                                '<td>' + str(deployable_inc_non_sbu) + '</td>'\
                                '<td>' + str(non_deployable_inc_non_sbu) + '</td>'\
                                '<td>' + str(billable_inc_non_sbu_more_100_len) + '</td>'\
                                '<td>' + str(billable_inc_non_sbu_100_count) + '</td>'\
                                '<td>' + str(billable_inc_non_sbu_75_count) + '</td>'\
                                '<td>' + str(billable_inc_non_sbu_50_count) + '</td>'\
                                '<td>' + str(billable_inc_non_sbu_25_count) + '</td>'\
                                '<td>' + str(billable_inc_non_sbu_0_count) + '</td>'\
                                '<td>' + str(billable_percent_inc_non_sbu) + '</td>'\
                                '<td>' + str(allocated_inc_non_sbu_100) + '</td>'\
                                '<td>' + str(allocated_inc_non_sbu_partial_count) + '</td>'\
                                '<td>' + str(allocated_inc_non_sbu_unallocated) + '</td>'\
                                '<td>' + str(allocate_percent_inc_non_sbu) + '</td>'\
                                '<td>' + str(non_sbu_inc_resigned) + '</td>'\
                                '<td>' + str(non_sbu_inc_probation) + '</td>'\
                                '<td>' + str(non_sbu_inc_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(33) + '</td>'\
                                '<td colspan="16">' + 'Team member-wise' + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(34) + '</td>'\
                                '<td>' + str('Consultant') + '</td>'\
                                '<td>' + str(emp_consultant) + '</td>'\
                                '<td>' + str(emp_consultant_deployable) + '</td>'\
                                '<td>' + str(emp_consultant_non_deployable) + '</td>'\
                                '<td>' + str(emp_consultant_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_consultant_billable_100_count) + '</td>'\
                                '<td>' + str(emp_consultant_billable_75_count) + '</td>'\
                                '<td>' + str(emp_consultant_billable_50_count) + '</td>'\
                                '<td>' + str(emp_consultant_billable_25_count) + '</td>'\
                                '<td>' + str(emp_consultant_billable_0_count) + '</td>'\
                                '<td>' + str(consultant_billable_percent) + '</td>'\
                                '<td>' + str(emp_consultant_allocated_100) + '</td>'\
                                '<td>' + str(emp_consultant_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_consultant_allocated_unallocated) + '</td>'\
                                '<td>' + str(consultant_allocate_percent) + '</td>'\
                                '<td>' + str(emp_consultant_resigned) + '</td>'\
                                '<td>' + str(emp_consultant_probation) + '</td>'\
                                '<td>' + str(emp_consultant_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(35) + '</td>'\
                                '<td>' + str('Intern') + '</td>'\
                                '<td>' + str(emp_rookie) + '</td>'\
                                '<td>' + str(emp_rookie_deployable) + '</td>'\
                                '<td>' + str(emp_rookie_non_deployable) + '</td>'\
                                '<td>' + str(emp_rookie_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_rookie_billable_100_count) + '</td>'\
                                '<td>' + str(emp_rookie_billable_75_count) + '</td>'\
                                '<td>' + str(emp_rookie_billable_50_count) + '</td>'\
                                '<td>' + str(emp_rookie_billable_25_count) + '</td>'\
                                '<td>' + str(emp_rookie_billable_0_count) + '</td>'\
                                '<td>' + str(rookie_billable_percent) + '</td>'\
                                '<td>' + str(emp_rookie_allocated_100) + '</td>'\
                                '<td>' + str(emp_rookie_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_rookie_allocated_unallocated) + '</td>'\
                                '<td>' + str(rookie_allocate_percent) + '</td>'\
                                '<td>' + str(emp_rookie_resigned) + '</td>'\
                                '<td>' + str(emp_rookie_probation) + '</td>'\
                                '<td>' + str(emp_rookie_confirmed) + '</td>'\
                            '</tr>'\
                            '<tr style="text-align:center;">'\
                                '<td>' + str(36) + '</td>'\
                                '<td>' + str('e-Zestian') + '</td>'\
                                '<td>' + str(emp_ezestian) + '</td>'\
                                '<td>' + str(emp_ezestian_deployable) + '</td>'\
                                '<td>' + str(emp_ezestian_non_deployable) + '</td>'\
                                '<td>' + str(emp_ezestian_billable_more_100_len) + '</td>'\
                                '<td>' + str(emp_ezestian_billable_100_count) + '</td>'\
                                '<td>' + str(emp_ezestian_billable_75_count) + '</td>'\
                                '<td>' + str(emp_ezestian_billable_50_count) + '</td>'\
                                '<td>' + str(emp_ezestian_billable_25_count) + '</td>'\
                                '<td>' + str(emp_ezestian_billable_0_count) + '</td>'\
                                '<td>' + str(ezestian_billable_percent) + '</td>'\
                                '<td>' + str(emp_ezestian_allocated_100) + '</td>'\
                                '<td>' + str(emp_ezestian_allocated_partial_count) + '</td>'\
                                '<td>' + str(emp_ezestian_allocated_unallocated) + '</td>'\
                                '<td>' + str(ezestian_allocate_percent) + '</td>'\
                                '<td>' + str(emp_ezestian_resigned) + '</td>'\
                                '<td>' + str(emp_ezestian_probation) + '</td>'\
                                '<td>' + str(emp_ezestian_confirmed) + '</td>'\
                            '</tr>'
            message_body += '</table>' + '<br/>' + '<br/>'
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            sheet = workbook.add_worksheet("Operations Summary Today %s"%(fields.Date.today().strftime('%d-%b-%Y')))
            # prepare sheet
            bold = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
            # 1st row
            sheet.merge_range('A1:A2', 'Sr. No.', bold)
            sheet.merge_range('B1:B2', '', bold)
            sheet.merge_range('C1:C2', 'Total e-Zestian', bold)
            sheet.merge_range('D1:D2', 'Total Deployable', bold)
            sheet.merge_range('E1:E2', 'Non-deployable', bold)
            sheet.merge_range('F1:L1', 'Currently Billed', bold)
            sheet.merge_range('M1:P1', 'Currently Allocated', bold)
            sheet.merge_range('Q1:S1', 'Statuswise', bold)
            # 2nd row
            sheet.write(1, 5, 'More than 100%', bold)
            sheet.write(1, 6, '100%', bold)
            sheet.write(1, 7, '75%', bold)
            sheet.write(1, 8, '50%', bold)
            sheet.write(1, 9, '25%', bold)
            sheet.write(1, 10, '0%', bold)
            sheet.write(1, 11, 'Billable %', bold)
            sheet.write(1, 12, '100% Allocated', bold)
            sheet.write(1, 13, 'Partially Allocated', bold)
            sheet.write(1, 14, 'Un-allocated', bold)
            sheet.write(1, 15, 'Allocation %', bold)
            sheet.write(1, 16, 'Resigned', bold)
            sheet.write(1, 17, 'Probation', bold)
            sheet.write(1, 18, 'Confirmed', bold)
            # 3rd row
            sheet.write(2, 0, '1', bold)
            sheet.write(2, 1, 'e-Zest Solutions Ltd.', bold)
            sheet.write(2, 2, str(emp_company), False)
            sheet.write(2, 3, str(emp_company_deployable), False)
            sheet.write(2, 4, str(emp_company_non_deployable), False)
            sheet.write(2, 5, str(emp_company_billable_more_100_len), False)
            sheet.write(2, 6, str(emp_company_billable_100_count), False)
            sheet.write(2, 7, str(emp_company_billable_75_count), False)
            sheet.write(2, 8, str(emp_company_billable_50_count), False)
            sheet.write(2, 9, str(emp_company_billable_25_count), False)
            sheet.write(2, 10, str(emp_company_billable_0_count), False)
            sheet.write(2, 11, str(company_billable_percent), False)
            sheet.write(2, 12, str(emp_company_allocated_100), False)
            sheet.write(2, 14, str(emp_company_allocated_partial_count), False)
            sheet.write(2, 14, str(emp_company_unallocated), False)
            sheet.write(2, 15, str(company_allocate_percent), False)
            sheet.write(2, 16, str(company_resigned), False)
            sheet.write(2, 17, str(company_probation), False)
            sheet.write(2, 18, str(company_confirmed), False)
            # 4th row
            sheet.merge_range('A4:S4', 'SBU-Wise', bold)
            # 5th row
            sheet.write(4, 0, '2', False)
            sheet.write(4, 1, 'DES', False)
            sheet.write(4, 2, str(total_des), False)
            sheet.write(4, 3, str(deployable_des), False)
            sheet.write(4, 4, str(non_deployable_des), False)
            sheet.write(4, 5, str(billable_des_more_100_len), False)
            sheet.write(4, 6, str(billable_des_100_count), False)
            sheet.write(4, 7, str(billable_des_75_count), False)
            sheet.write(4, 8, str(billable_des_50_count), False)
            sheet.write(4, 9, str(billable_des_25_count), False)
            sheet.write(4, 10, str(billable_des_0_count), False)
            sheet.write(4, 11, str(billable_percent_des), False)
            sheet.write(4, 12, str(allocated_des_100), False)
            sheet.write(4, 13, str(allocated_des_partial_count), False)
            sheet.write(4, 14, str(allocated_des_unallocated), False)
            sheet.write(4, 15, str(allocate_percent_des), False)
            sheet.write(4, 16, str(des_resigned), False)
            sheet.write(4, 17, str(des_probation), False)
            sheet.write(4, 18, str(des_confirmed), False)
            # 6th row
            sheet.write(5, 0, '3', False)
            sheet.write(5, 1, 'DPES', False)
            sheet.write(5, 2, str(total_dpes), False)
            sheet.write(5, 3, str(deployable_dpes), False)
            sheet.write(5, 4, str(non_deployable_dpes), False)
            sheet.write(5, 5, str(billable_dpes_more_100_len), False)
            sheet.write(5, 6, str(billable_dpes_100_count), False)
            sheet.write(5, 7, str(billable_dpes_75_count), False)
            sheet.write(5, 8, str(billable_dpes_50_count), False)
            sheet.write(5, 9, str(billable_dpes_25_count), False)
            sheet.write(5, 10, str(billable_dpes_0_count), False)
            sheet.write(5, 11, str(billable_percent_dpes), False)
            sheet.write(5, 12, str(allocated_dpes_100), False)
            sheet.write(5, 13, str(allocated_dpes_partial_count), False)
            sheet.write(5, 14, str(allocated_dpes_unallocated), False)
            sheet.write(5, 15, str(allocate_percent_dpes), False)
            sheet.write(5, 16, str(dpes_resigned), False)
            sheet.write(5, 17, str(dpes_probation), False)
            sheet.write(5, 18, str(dpes_confirmed), False)
            # 7th row
            sheet.write(6, 0, '4', False)
            sheet.write(6, 1, 'IO', False)
            sheet.write(6, 2, str(total_io), False)
            sheet.write(6, 3, str(deployable_io), False)
            sheet.write(6, 4, str(non_deployable_io), False)
            sheet.write(6, 5, str(billable_io_more_100_len), False)
            sheet.write(6, 6, str(billable_io_100_count), False)
            sheet.write(6, 7, str(billable_io_75_count), False)
            sheet.write(6, 8, str(billable_io_50_count), False)
            sheet.write(6, 9, str(billable_io_25_count), False)
            sheet.write(6, 10, str(billable_io_0_count), False)
            sheet.write(6, 11, str(billable_percent_io), False)
            sheet.write(6, 12, str(allocated_io_100), False)
            sheet.write(6, 13, str(allocated_io_partial_count), False)
            sheet.write(6, 14, str(allocated_io_unallocated), False)
            sheet.write(6, 15, str(allocate_percent_io), False)
            sheet.write(6, 16, str(io_resigned), False)
            sheet.write(6, 17, str(io_probation), False)
            sheet.write(6, 18, str(io_confirmed), False)
            # 8th row
            sheet.write(7, 0, '5', False)
            sheet.write(7, 1, 'Non SBU', False)
            sheet.write(7, 2, str(total_non_sbu), False)
            sheet.write(7, 3, str(deployable_non_sbu), False)
            sheet.write(7, 4, str(non_deployable_non_sbu), False)
            sheet.write(7, 5, str(billable_non_sbu_more_100_len), False)
            sheet.write(7, 6, str(billable_non_sbu_100_count), False)
            sheet.write(7, 7, str(billable_non_sbu_75_count), False)
            sheet.write(7, 8, str(billable_non_sbu_50_count), False)
            sheet.write(7, 9, str(billable_non_sbu_25_count), False)
            sheet.write(7, 10, str(billable_non_sbu_0_count), False)
            sheet.write(7, 11, str(billable_percent_non_sbu), False)
            sheet.write(7, 12, str(allocated_non_sbu_100), False)
            sheet.write(7, 13, str(allocated_non_sbu_partial_count), False)
            sheet.write(7, 14, str(allocated_non_sbu_unallocated), False)
            sheet.write(7, 15, str(allocate_percent_non_sbu), False)
            sheet.write(7, 16, str(non_sbu_resigned), False)
            sheet.write(7, 17, str(non_sbu_probation), False)
            sheet.write(7, 18, str(non_sbu_confirmed), False)
            # 9th row
            sheet.merge_range('A9:S9', 'Team Member-Wise', bold)
            # 10th row
            sheet.write(9, 0, '6', False)
            sheet.write(9, 1, 'Consultant', False)
            sheet.write(9, 2, str(emp_consultant), False)
            sheet.write(9, 3, str(emp_consultant_deployable), False)
            sheet.write(9, 4, str(emp_consultant_non_deployable), False)
            sheet.write(9, 5, str(emp_consultant_billable_more_100_len), False)
            sheet.write(9, 6, str(emp_consultant_billable_100_count), False)
            sheet.write(9, 7, str(emp_consultant_billable_75_count), False)
            sheet.write(9, 8, str(emp_consultant_billable_50_count), False)
            sheet.write(9, 9, str(emp_consultant_billable_25_count), False)
            sheet.write(9, 10, str(emp_consultant_billable_0_count), False)
            sheet.write(9, 11, str(consultant_billable_percent), False)
            sheet.write(9, 12, str(emp_consultant_allocated_100), False)
            sheet.write(9, 13, str(emp_consultant_allocated_partial_count), False)
            sheet.write(9, 14, str(emp_consultant_allocated_unallocated), False)
            sheet.write(9, 15, str(consultant_allocate_percent), False)
            sheet.write(9, 16, str(emp_consultant_resigned), False)
            sheet.write(9, 17, 'NA', False)
            sheet.write(9, 18, 'NA', False)
            # 11th row
            sheet.write(10, 0, '7', False)
            sheet.write(10, 1, 'Intern', False)
            sheet.write(10, 2, str(emp_rookie), False)
            sheet.write(10, 3, str(emp_rookie_deployable), False)
            sheet.write(10, 4, str(emp_rookie_non_deployable), False)
            sheet.write(10, 5, str(emp_rookie_billable_more_100_len), False)
            sheet.write(10, 6, str(emp_rookie_billable_100_count), False)
            sheet.write(10, 7, str(emp_rookie_billable_75_count), False)
            sheet.write(10, 8, str(emp_rookie_billable_50_count), False)
            sheet.write(10, 9, str(emp_rookie_billable_25_count), False)
            sheet.write(10, 10, str(emp_rookie_billable_0_count), False)
            sheet.write(10, 11, str(rookie_billable_percent), False)
            sheet.write(10, 12, str(emp_rookie_allocated_100), False)
            sheet.write(10, 13, str(emp_rookie_allocated_partial_count), False)
            sheet.write(10, 14, str(emp_rookie_allocated_unallocated), False)
            sheet.write(10, 15, str(rookie_allocate_percent), False)
            sheet.write(10, 16, str(emp_rookie_resigned), False)
            sheet.write(10, 17, 'NA', False)
            sheet.write(10, 18, 'NA', False)
            # 12th row
            sheet.write(11, 0, '8', False)
            sheet.write(11, 1, 'e-Zestian', False)
            sheet.write(11, 2, str(emp_ezestian), False)
            sheet.write(11, 3, str(emp_ezestian_deployable), False)
            sheet.write(11, 4, str(emp_ezestian_non_deployable), False)
            sheet.write(11, 5, str(emp_ezestian_billable_more_100_len), False)
            sheet.write(11, 6, str(emp_ezestian_billable_100_count), False)
            sheet.write(11, 7, str(emp_ezestian_billable_75_count), False)
            sheet.write(11, 8, str(emp_ezestian_billable_50_count), False)
            sheet.write(11, 9, str(emp_ezestian_billable_25_count), False)
            sheet.write(11, 10, str(emp_ezestian_billable_0_count), False)
            sheet.write(11, 11, str(ezestian_billable_percent), False)
            sheet.write(11, 12, str(emp_ezestian_allocated_100), False)
            sheet.write(11, 13, str(emp_ezestian_allocated_partial_count), False)
            sheet.write(11, 14, str(emp_ezestian_allocated_unallocated), False)
            sheet.write(11, 15, str(ezestian_allocate_percent), False)
            sheet.write(11, 16, str(emp_ezestian_resigned), False)
            sheet.write(11, 17, str(emp_ezestian_probation), False)
            sheet.write(11, 18, str(emp_ezestian_confirmed), False)

            # if len(emp_company_billable_more_100):
            #     count_100 = 1
            #     message_body += '<h6>List of e-Zestian more than 100% Billable</h6>'
            #     message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            #     message_body += '<tr style="text-align:center;">'\
            #                         '<th>' + 'Sr. No.' + '</th>'\
            #                         '<th>' + 'e-Zestian Name' + '</th>'\
            #                         '<th>' + 'Manager Name' + '</th>'\
            #                         '<th>' + 'Primary Skill' + '</th>'\
            #                         '<th>' + 'Skills' + '</th>'\
            #                         '<th>' + 'Total Experience' + '</th>'\
            #                         '<th>' + 'SBU' + '</th>'\
            #                         '<th>' + 'Allocated Percentage' + '</th>'\
            #                         '<th>' + 'Payroll Location of Team Member' + '</th>'\
            #                         '<th>' + 'Grade' + '</th>'\
            #                     '</tr>'
            #     for emp in emp_company_billable_more_100:
            #         if emp.employee_skill_ids:
            #             skills = []
            #             for skill in emp.employee_skill_ids:
            #                 if skill.level_progress > 50:
            #                     skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
            #             emp_skills = ', '.join(skills)
            #         else:
            #             emp_skills = False
            #         message_body += '<tr style="text-align:center;">'\
            #                             '<td>' + str(count_100) + '</td>'\
            #                             '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
            #                             '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
            #                             '<td>' + str(emp.skills.name) + '</td>'\
            #                             '<td>' + str(emp_skills) + '</td>'\
            #                             '<td>' + str(emp.total_exp) + '</td>'\
            #                             '<td>' + str(emp.department_id.name) + '</td>'\
            #                             '<td>' + str(emp.project_allocate) + '</td>'\
            #                             '<td>' + str(emp.payroll_loc.name) + '</td>'\
            #                             '<td>' + str(emp.band_grade.name) + '</td>'\
            #                         '</tr>'
            #         count_100 += 1
            #     message_body += '</table>' + '<br/>' + '<br/>'
            #     emp_sheet = workbook.add_worksheet("List of e-Zestian more than 100% Billable")
            #     # prepare sheet
            #     bold = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
            #     # header
            #     emp_sheet.write(0, 0, 'Sr. No.', bold)
            #     emp_sheet.write(0, 1, 'e-Zestian Name', bold)
            #     emp_sheet.write(0, 2, 'Manager Name', bold)
            #     emp_sheet.write(0, 3, 'Primary Skill', bold)
            #     emp_sheet.write(0, 4, 'Skills', bold)
            #     emp_sheet.write(0, 5, 'Total Experience', bold)
            #     emp_sheet.write(0, 6, 'SBU', bold)
            #     emp_sheet.write(0, 7, 'Allocated Percentage', bold)
            #     emp_sheet.write(0, 8, 'Payroll Location od Team Member', bold)
            #     emp_sheet.write(0, 9, 'Grade', bold)
            #     #rows
            #     row_count = 1
            #     for emp in emp_company_billable_more_100:
            #         if emp.employee_skill_ids:
            #             skills = []
            #             for skill in emp.employee_skill_ids:
            #                 if skill.level_progress > 50:
            #                     skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
            #             emp_skills = ', '.join(skills)
            #         else:
            #             emp_skills = False
            #         emp_sheet.write(row_count, 0, row_count, bold)
            #         emp_sheet.write(row_count, 1, str(emp.name) + ' (' + str(emp.mobile_phone) + ')', bold)
            #         emp_sheet.write(row_count, 2, str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')', bold)
            #         emp_sheet.write(row_count, 3, str(emp.skills.name), bold)
            #         emp_sheet.write(row_count, 4, str(emp_skills), bold)
            #         emp_sheet.write(row_count, 5, str(emp.total_exp), bold)
            #         emp_sheet.write(row_count, 6, str(emp.department_id.name), bold)
            #         emp_sheet.write(row_count, 7, str(emp.project_allocate), bold)
            #         emp_sheet.write(row_count, 8, str(emp.payroll_loc.name), bold)
            #         emp_sheet.write(row_count, 9, str(emp.band_grade.name), bold)
            #         row_count += 1
            # close workbook
            workbook.close()
            content = output.getvalue()
            b64_xlsx = base64.b64encode(content)
            attachment_name_operation_summary = 'operations_summary_report'
            attachment_operation_summary = {
                'name': attachment_name_operation_summary + '.xlsx',
                'description': attachment_name_operation_summary,
                'type': 'binary',
                'datas': b64_xlsx,
                'store_fname': attachment_name_operation_summary,
                'res_model': 'project.project',
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            template_values = {
                'subject': 'Operations Summary Report - %s' % fields.Date.today().strftime('%d-%b-%Y'),
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in exec_email) or 'exec@e-zest.in',
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
                'attachment_ids': [(0, 0, attachment_operation_summary)]
            }
            self.env['mail.mail'].create(template_values).sudo().send()
            attach = self.env['ir.attachment'].sudo().search([('res_model', '=', 'project.project'), ('description', '=', attachment_name_operation_summary)])
            attach.sudo().unlink()
        # Unassigned Today Report
        employee_unassign = self.env['hr.employee'].search([('project_allocate', '<', 100), ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']), ('is_ezestian', '=', True), ('company_id', '=', 'e-Zest Solutions Ltd.')])
        emp_total_unassign = self.env['hr.employee'].search([
            ('project_allocate', '=', 0),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('joining_date', '!=', False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        emp_partial_unassign = self.env['hr.employee'].search([
            ('project_allocate', '>', 0),
            ('project_allocate', '<', 100),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('joining_date', '!=', False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        if email_alloc_unassign and (emp_total_unassign or emp_partial_unassign):
            message_body = 'Fully Unassigned: %s <br/> Partial Assigned: %s <br/>' % (len(emp_total_unassign), len(emp_partial_unassign))
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'e-Zestian Name' + '</th>'\
                                '<th>' + 'e-Zestian Status' + '</th>'\
                                '<th>' + 'Manager Name' + '</th>'\
                                '<th>' + 'Primary Skill' + '</th>'\
                                '<th>' + 'Skills' + '</th>'\
                                '<th>' + 'Total Experience' + '</th>'\
                                '<th>' + 'SBU' + '</th>'\
                                '<th>' + 'Allocated Percentage' + '</th>'\
                                '<th>' + 'On Bench Since (Days)' + '</th>'\
                                '<th>' + 'Payroll Location of Team Member' + '</th>'\
                                '<th>' + 'Grade' + '</th>'\
                                '<th>' + 'Last Project Name' + '</th>'\
                                '<th>' + 'Assigned Till' + '</th>'\
                                '<th>' + 'Last Billability Status' + '</th>'\
                                '<th>' + 'Comment' + '</th>'\
                            '</tr>'
            if emp_total_unassign:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15">' + 'Fully Unallocated' + '</td>'\
                    '</tr>'
                emp_unassign_count = 1
                emp_unassign_sort = [((fields.Date.today() - rec.project_assign_till).days, rec) for rec in emp_total_unassign if rec.project_assign_till]
                emp_unassign_sort.sort(reverse=True)
                emp_unassign = [rec[1] for rec in emp_unassign_sort]
                emp_unassign.extend([rec for rec in emp_total_unassign if rec.project_assign_till is False])
                for emp in emp_unassign:
                    resign = self.env['hr.resignation'].search([('employee_id', '=', emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0 and rec.assign_status == 'confirmed']
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0 and rec.assign_status == 'confirmed']
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    color = ''
                    if emp.exit_date:
                        if emp.exit_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.exit_date < fields.Date.today():
                            color = '#bd200e'
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        if resign.expected_revealing_date and resign.expected_revealing_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif resign.expected_revealing_date and resign.expected_revealing_date < fields.Date.today():
                            color = '#bd200e'
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;color:' + color + '">'\
                                        '<td>' + str(emp_unassign_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp_skills) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_unassign_count += 1
            if emp_partial_unassign:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15">' + 'Partially Unallocated' + '</td>'\
                    '</tr>'
                emp_partial_unassign_count = 1
                emp_partial_assign_sort = [(rec.skills.name, rec) for rec in emp_partial_unassign if rec.skills]
                emp_partial_assign_sort.sort()
                emp_partial_assign = [rec[1] for rec in emp_partial_assign_sort]
                emp_partial_assign.extend([rec for rec in emp_partial_unassign if not rec.skills])
                for emp in emp_partial_assign:
                    resign = self.env['hr.resignation'].search([('employee_id', '=', emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0]
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0]
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    color = ''
                    if emp.exit_date:
                        if emp.exit_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.exit_date < fields.Date.today():
                            color = '#bd200e'
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        if resign.expected_revealing_date and resign.expected_revealing_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif resign.expected_revealing_date and resign.expected_revealing_date < fields.Date.today():
                            color = '#bd200e'
                        # resign = self.env['hr.resignation'].search([('employee_id', '=', emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;color:' + color + '">'\
                                        '<td>' + str(emp_partial_unassign_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp_skills) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_partial_unassign_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Unassigned Today Report',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_alloc_unassign),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

        # Unbillable Today Report
        emp_total_unbillable = self.env['hr.employee'].search([
            ('total_billability','=',0),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        emp_partial_unbillable = self.env['hr.employee'].search([
            ('total_billability','>',0),
            ('total_billability','<',100),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        emp_more_billable = self.env['hr.employee'].search([
            ('total_billability','>',100),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('joining_date','!=',False),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        if email_unbilled and (emp_total_unbillable or emp_partial_unbillable or emp_more_billable):
            message_body = '<h5>' + 'Fully UnBilled: %s <br/> Partial Unbilled: %s <br/> More than 100 Billed: %s </h5>' % (len(emp_total_unbillable), len(emp_partial_unbillable), len(emp_more_billable))
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'e-Zestian Name' + '</th>'\
                                '<th>' + 'e-Zestian Status' + '</th>'\
                                '<th>' + 'Manager Name' + '</th>'\
                                '<th>' + 'Primary Skill' + '</th>'\
                                '<th>' + 'Skills' + '</th>'\
                                '<th>' + 'Total Experience' + '</th>'\
                                '<th>' + 'SBU' + '</th>'\
                                '<th>' + 'Billability Percentage' + '</th>'\
                                '<th>' + 'On Bench Since (Days)' + '</th>'\
                                '<th>' + 'Payroll Location of Team Member' + '</th>'\
                                '<th>' + 'Grade' + '</th>'\
                                '<th>' + 'Last Project Name' + '</th>'\
                                '<th>' + 'Date of Relieving' + '</th>'\
                                '<th>' + 'Last Billability Status' + '</th>'\
                                '<th>' + 'Comment' + '</th>'\
                            '</tr>'
            if emp_total_unbillable:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15"><h5>' + 'Fully UnBillable' + '</h5></td>'\
                    '</tr>'
                emp_unbillable_count = 1
                emp_unbillable_sort = [(rec.skills.name, rec) for rec in emp_total_unbillable if rec.skills]
                emp_unbillable_sort.sort()
                emp_unbillable = [rec[1] for rec in emp_unbillable_sort]
                emp_unbillable.extend([rec for rec in emp_total_unbillable if not rec.skills and (rec.project_assign_till is False or rec.project_assign_till < datetime.today().date())])
                for emp in emp_unbillable:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.total_billability == 0 and rec.assign_status == 'confirmed']
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.total_billability > 0 and rec.assign_status == 'confirmed']
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        comment = emp_alloc_latest[-1][1].description_approve
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    color = ''
                    if emp.exit_date:
                        if emp.exit_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.exit_date < fields.Date.today():
                            color = '#bd200e'
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        if emp.resign_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.resign_date < fields.Date.today():
                            color = '#bd200e'
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;color:' + color + '">'\
                                        '<td>' + str(emp_unbillable_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp_skills) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.total_billability) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_unbillable_count += 1
            if emp_partial_unbillable:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15"><h5>' + 'Partially Billable' + '</h5></td>'\
                    '</tr>'
                emp_partial_billable_count = 1
                emp_partial_billable_sort = [(rec.skills.name, rec) for rec in emp_partial_unbillable if rec.skills]
                emp_partial_billable_sort.sort()
                emp_partial_billable = [rec[1] for rec in emp_partial_billable_sort]
                emp_partial_billable.extend([rec for rec in emp_partial_unbillable if not rec.skills])
                for emp in emp_partial_billable:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.total_billability == 0]
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.total_billability > 0]
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        comment = emp_alloc[-1][1].description_approve
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        comment = emp_alloc_latest[-1][1].description_approve
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    color = ''
                    if emp.exit_date:
                        if emp.exit_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.exit_date < fields.Date.today():
                            color = '#bd200e'
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        if emp.resign_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.resign_date < fields.Date.today():
                            color = '#bd200e'
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;color:' + color + '">'\
                                        '<td>' + str(emp_partial_billable_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp_skills) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.total_billability) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_partial_billable_count += 1
            if emp_more_billable:
                message_body += '<tr style="text-align:center;">'\
                        '<td colspan="15"><h5>' + 'More than 100% Billable' + '</h5></td>'\
                    '</tr>'
                emp_nore_billable_count = 1
                emp_nore_billable_sort = [(rec.skills.name, rec) for rec in emp_more_billable if rec.skills]
                emp_nore_billable_sort.sort()
                emp_nore_billable = [rec[1] for rec in emp_nore_billable_sort]
                emp_nore_billable.extend([rec for rec in emp_more_billable if not rec.skills])
                for emp in emp_nore_billable:
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.total_billability == 0]
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.total_billability > 0]
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        comment = emp_alloc[-1][1].description_approve
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        comment = emp_alloc_latest[-1][1].description_approve
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    color = ''
                    if emp.exit_date:
                        if emp.exit_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.exit_date < fields.Date.today():
                            color = '#bd200e'
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        if emp.exit_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.exit_date < fields.Date.today():
                            color = '#bd200e'
                        resign = self.env['hr.resignation'].search([('employee_id','=',emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;color:' + color + '">'\
                                        '<td>' + str(emp_nore_billable_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp_skills) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.total_billability) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_nore_billable_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'UnBillable and More than 100% Billable Today Report',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_alloc_unassign),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

        # Current Allocation IO Report
        project_io = self.search([('department_id', 'ilike', 'BOD / Operations / IO'), ('state','=','active')])
        if email_alloc_io and project_io:
            project_io_count = 1
            message_body = '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'Team Member Name' + '</th>'\
                                '<th>' + 'Skills' + '</th>'\
                                '<th>' + 'Total Experience' + '</th>'\
                                '<th>' + 'Project Name' + '</th>'\
                                '<th>' + 'Project Code' + '</th>'\
                                '<th>' + 'Billable Status' + '</th>'\
                                '<th>' + 'Allocation Percentage' + '</th>'\
                                '<th>' + 'Allocation Start Date' + '</th>'\
                                '<th>' + 'Allocation End Date' + '</th>'\
                                '<th>' + 'SBU' + '</th>'\
                                '<th>' + 'Manager Name' + '</th>'\
                                '<th>' + 'Free After (Days)' + '</th>'\
                            '</tr>'
            emp_alloc = [(alloc.end_date, alloc) for io in project_io for alloc in io.assignment_ids if alloc.assign_status == 'confirmed']
            emp_alloc.sort(reverse=True)
            for alloc in emp_alloc:
                alloc = alloc[1]
                if alloc.assign_status == 'confirmed':
                    today = fields.Date.today()
                    if alloc.end_date > today:
                        free_day = (alloc.end_date - today).days
                    else:
                        free_day = 'Unassigned'
                    message_body += '<tr style="text-align:center;">'\
                                        '<td>' + str(project_io_count) + '</td>'\
                                        '<td>' + str(alloc.employee_id.name) + '</td>'\
                                        '<td>' + str(alloc.employee_id.skills.name) + '</td>'\
                                        '<td>' + str(alloc.employee_id.total_exp) + '</td>'\
                                        '<td>' + str(alloc.project_id.name) + '</td>'\
                                        '<td>' + str(alloc.project_id.abbreviated_name) + '</td>'\
                                        '<td>' + str(alloc.project_bill_status) + '</td>'\
                                        '<td>' + str(alloc.allocation_percentage) + '</td>'\
                                        '<td>' + str(alloc.start_date.strftime("%d-%b-%y")) + '</td>'\
                                        '<td>' + str(alloc.end_date.strftime("%d-%b-%y")) + '</td>'\
                                        '<td>' + str(alloc.project_id.department_id.name) + '</td>'\
                                        '<td>' + str(alloc.project_id.user_id.name) + '</td>'\
                                        '<td>' + str(free_day) + '</td>'\
                                    '</tr>'
                    project_io_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Current Allocation IO Report',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_alloc_io),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()
        # Onbench_contractor
        onbench_contractr = self.env['hr.employee'].search([
            ('project_allocate', '=', 0),
            ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
            ('joining_date', '!=', False),
            ('employee_category', '=', 'Contractor'),
            ('company_id', '=', 'e-Zest Solutions Ltd.')
        ])
        if email_onbench_contractor and (onbench_contractr):
            message_body = 'On-bench Contractors: %s <br/>' % (len(onbench_contractr))
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'e-Zestian Name' + '</th>'\
                                '<th>' + 'e-Zestian Status' + '</th>'\
                                '<th>' + 'Manager Name' + '</th>'\
                                '<th>' + 'Primary Skill' + '</th>'\
                                '<th>' + 'Skills' + '</th>'\
                                '<th>' + 'Total Experience' + '</th>'\
                                '<th>' + 'SBU' + '</th>'\
                                '<th>' + 'Allocated Percentage' + '</th>'\
                                '<th>' + 'On Bench Since (Days)' + '</th>'\
                                '<th>' + 'Payroll Location of Team Member' + '</th>'\
                                '<th>' + 'Grade' + '</th>'\
                                '<th>' + 'Last Project Name' + '</th>'\
                                '<th>' + 'Assigned Till' + '</th>'\
                                '<th>' + 'Last Billability Status' + '</th>'\
                                '<th>' + 'Comment' + '</th>'\
                            '</tr>'
            if onbench_contractr:
                emp_onbench_count = 1
                emp_onbench_sort = [((fields.Date.today() - rec.project_assign_till).days, rec) for rec in onbench_contractr if rec.project_assign_till]
                emp_onbench_sort.sort(reverse=True)
                emp_onbench = [rec[1] for rec in emp_onbench_sort]
                emp_onbench.extend([rec for rec in onbench_contractr if rec.project_assign_till is False])
                for emp in emp_onbench:
                    resign = self.env['hr.resignation'].search([('employee_id', '=', emp.id), ('state', 'in', ['confirm', 'approved'])], limit=1)
                    emp_alloc = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate == 0 and rec.assign_status == 'confirmed']
                    emp_alloc.sort()
                    emp_alloc_latest = [(rec.end_date, rec) for rec in emp.allocation_ids if emp.project_allocate > 0 and rec.assign_status == 'confirmed']
                    emp_alloc_latest.sort()
                    unassigned_days = 0
                    if emp_alloc:
                        last_project_name = emp_alloc[-1][1].project_id.name
                        relieving_date = emp_alloc[-1][1].end_date
                        project_relieving_date = emp_alloc[-1][1].end_date.strftime("%d-%b-%y")
                        unassigned_days = (fields.Date.today() - relieving_date).days
                        last_billability_status = emp_alloc[-1][1].project_bill_status
                        comment = emp_alloc[-1][1].description_approve
                    elif emp_alloc_latest:
                        last_project_name = emp_alloc_latest[-1][1].project_id.name
                        project_relieving_date = emp_alloc_latest[-1][1].end_date.strftime("%d-%b-%y")
                        last_billability_status = emp_alloc_latest[-1][1].project_bill_status
                        comment = emp_alloc_latest[-1][1].description_approve
                    else:
                        last_project_name = '-'
                        project_relieving_date = '-'
                        last_billability_status = '-'
                        comment = '-'
                    # ezestian status
                    color = ''
                    if emp.exit_date:
                        if emp.exit_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif emp.exit_date < fields.Date.today():
                            color = '#bd200e'
                        if emp.employee_category.name == 'Contractor':
                            ezestian_status = 'Contractor' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                        else:
                            ezestian_status = 'Resign' + '(' + emp.exit_date.strftime('%d-%b-%Y') + ')'
                    elif emp.resign_date:
                        if resign.expected_revealing_date and resign.expected_revealing_date >= fields.Date.today():
                            color = '#dc6a21'
                        elif resign.expected_revealing_date and resign.expected_revealing_date < fields.Date.today():
                            color = '#bd200e'
                        ezestian_status = 'Resign' + '(' + resign.expected_revealing_date.strftime('%d-%b-%Y') + ')'
                    elif emp.employee_category:
                        ezestian_status = emp.employee_category.name
                    if emp.employee_skill_ids:
                        skills = []
                        for skill in emp.employee_skill_ids:
                            if skill.level_progress > 50:
                                skills.append(skill.skill_id.name + '-' + skill.skill_level_id.name)
                        emp_skills = ', '.join(skills)
                    else:
                        emp_skills = False
                    message_body += '<tr style="text-align:center;color:' + color + '">'\
                                        '<td>' + str(emp_onbench_count) + '</td>'\
                                        '<td>' + str(emp.name) + ' (' + str(emp.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(ezestian_status) + '</td>'\
                                        '<td>' + str(emp.parent_id.name) + ' (' + str(emp.parent_id.mobile_phone) + ')' + '</td>'\
                                        '<td>' + str(emp.skills.name) + '</td>'\
                                        '<td>' + str(emp_skills) + '</td>'\
                                        '<td>' + str(emp.total_exp) + '</td>'\
                                        '<td>' + str(emp.department_id.name) + '</td>'\
                                        '<td>' + str(emp.project_allocate) + '</td>'\
                                        '<td>' + str(unassigned_days) + '</td>'\
                                        '<td>' + str(emp.payroll_loc.name) + '</td>'\
                                        '<td>' + str(emp.band_grade.name) + '</td>'\
                                        '<td>' + str(last_project_name) + '</td>'\
                                        '<td>' + str(project_relieving_date) + '</td>'\
                                        '<td>' + str(last_billability_status) + '</td>'\
                                        '<td>' + str(comment) + '</td>'\
                                    '</tr>'
                    emp_onbench_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'On-bench Contractor Today Report',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_onbench_contractor),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

        # Missing Milestone
        orders = self.env['sale.order'].search([('state', '=', 'sale')])
        if email_missing_milestone:
            message_body = 'Milestone Last Date and Project End Date Mistached.'
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'Customer Name' + '</th>'\
                                '<th>' + 'Project Code' + '</th>'\
                                '<th>' + 'Project Name' + '</th>'\
                                '<th>' + 'Order Name' + '</th>'\
                                '<th>' + 'Department' + '</th>'\
                                '<th>' + 'Last Milestone Date' + '</th>'\
                                '<th>' + 'Project End Date' + '</th>'\
                            '</tr>'
        milestone_sr_no = 1
        for order in orders:
            if order.project_id and not order.project_id.is_internal:
                order_line = [i.date_target for i in order.order_line if i.display_type != 'line_section']
                order_line = max(order_line) if len(order_line) else False
                if email_missing_milestone and order_line and order.project_id and order_line != order.project_id.planned_end_date:
                    message_body += '<tr style="text-align:center;">'\
                                        '<td>' + str(milestone_sr_no) + '</td>'\
                                        '<td>' + str(order.partner_id.name) + '</td>'\
                                        '<td>' + str(order.project_id.name_seq) + '</td>'\
                                        '<td>' + str(order.project_id.name) + '</td>'\
                                        '<td>' + str(order.name) + '</td>'\
                                        '<td>' + str(order.department_id.name) + '</td>'\
                                        '<td>' + str(order_line.strftime("%d-%b-%Y")) + '</td>'\
                                        '<td>' + str(order.project_id.planned_end_date.strftime("%d-%b-%Y")) if order.project_id.planned_end_date else False + '</td>'\
                                    '</tr>'
                    milestone_sr_no += 1
        if email_missing_milestone:
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Missing Milestones',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_active_cons),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

        # UI UX Report
        allocation_ui_ux = self.env['project.assignment'].search([('end_date', '>=', fields.Date.today()), ('assign_status', '=', 'confirmed')])
        allocation_ui_ux = allocation_ui_ux.filtered(lambda allo: allo.employee_id.skills.name == 'UI' or allo.employee_id.skills.name == 'UX')
        if email_alloc_ux and allocation_ui_ux:
            alloc_ux_count = 1
            message_body = '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'Team Member Name' + '</th>'\
                                '<th>' + 'Skills' + '</th>'\
                                '<th>' + 'Total Experience' + '</th>'\
                                '<th>' + 'Project Name' + '</th>'\
                                '<th>' + 'Project Code' + '</th>'\
                                '<th>' + 'Billable Status' + '</th>'\
                                '<th>' + 'Allocation Percentage' + '</th>'\
                                '<th>' + 'Allocation Start Date' + '</th>'\
                                '<th>' + 'Allocation End Date' + '</th>'\
                                '<th>' + 'SBU' + '</th>'\
                                '<th>' + 'Manager Name' + '</th>'\
                            '</tr>'
            for alloc in allocation_ui_ux:
                message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(alloc_ux_count) + '</td>'\
                                    '<td>' + str(alloc.employee_id.name) + '</td>'\
                                    '<td>' + str(alloc.employee_id.skills.name) + '</td>'\
                                    '<td>' + str(alloc.employee_id.total_exp) + '</td>'\
                                    '<td>' + str(alloc.project_id.name) + '</td>'\
                                    '<td>' + str(alloc.project_id.abbreviated_name) + '</td>'\
                                    '<td>' + str(alloc.project_bill_status) + '</td>'\
                                    '<td>' + str(alloc.allocation_percentage) + '</td>'\
                                    '<td>' + str(alloc.start_date.strftime("%d-%b-%y")) + '</td>'\
                                    '<td>' + str(alloc.end_date.strftime("%d-%b-%y")) + '</td>'\
                                    '<td>' + str(alloc.project_id.department_id.name) + '</td>'\
                                    '<td>' + str(alloc.project_id.user_id.name) + '</td>'\
                                '</tr>'
                alloc_ux_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Current Allocation UI UX Report',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_alloc_ux),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()
        
        # Active Deployable Consultant Current Allocation Report
        # emp_consultant = self.env['hr.employee'].search([('employee_category','<=','Contractor'),('account','=','Deployable - Billable')])
        # if email_active_cons and emp_consultant:
        #     email_active_cons_count = 1
        #     message_body = '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
        #     message_body += '<tr style="text-align:center;">'\
        #                         '<th>' + 'Sr. No.' + '</th>'\
        #                         '<th>' + 'Customer Name' + '</th>'\
        #                         '<th>' + 'Project Code' + '</th>'\
        #                         '<th>' + 'Project Name' + '</th>'\
        #                         '<th>' + 'OU' + '</th>'\
        #                         '<th>' + 'Team Member Name' + '</th>'\
        #                         '<th>' + 'Billable Status' + '</th>'\
        #                         '<th>' + 'Allocation Percentage' + '</th>'\
        #                         '<th>' + 'Department' + '</th>'\
        #                         '<th>' + 'Total Experience' + '</th>'\
        #                     '</tr>'
        #     for consultant in emp_consultant:
        #         if len(consultant.allocation_ids) > 0:
        #             for consultant_alloc in consultant.allocation_ids:
        #                 message_body += '<tr style="text-align:center;">'\
        #                                     '<td>' + str(email_active_cons) + '</td>'\
        #                                     '<td>' + str(consultant_alloc.project_id.customer_id.name) + '</td>'\
        #                                     '<td>' + str(consultant_alloc.project_id.abbreviated_name) + '</td>'\
        #                                     '<td>' + str(consultant_alloc.project_id.name) + '</td>'\
        #                                     '<td>' + '-'+'</td>'\
        #                                     '<td>' + str(consultant_alloc.employee_id.name) + '</td>'\
        #                                     '<td>' + str(consultant_alloc.project_bill_status.capitalize()) + '</td>'\
        #                                     '<td>' + str(consultant_alloc.allocation_percentage) + '</td>'\
        #                                     '<td>' + str(consultant_alloc.project_id.department_id.name) + '</td>'\
        #                                     '<td>' + str(consultant_alloc.employee_id.total_exp) + '</td>'\
        #                                 '</tr>'
        #                 email_active_cons += 1
        #     message_body += '</table>' + '<br/>' + '<br/>'
        #     template_values = {
        #         'subject': 'Active Deployable Consultant Current Allocation Report',
        #         'body_html': message_body,
        #         'email_from': 'unity@e-zest.in',
        #         'email_to': ','.join(i for i in email_active_cons),
        #         'email_cc': 'unity@e-zest.in',
        #         'auto_delete': False,
        #     }
        #     self.env['mail.mail'].create(template_values).sudo().send()

    def _get_order_lines(self, order_lines):
        new_lines = {}
        for line in order_lines:
            if new_lines.get(line.order_id.id):
                new_lines[line.order_id.id].append(line)
            else:
                new_lines[line.order_id.id] = [line]
        for i, j in new_lines.items():
            dates_dic = {}
            for k in j:
                # Change for resloving invoice report email 
                # if k.price_subtotal:
                if dates_dic.get(k.date_target.strftime('%b-%y')):
                    dates_dic[k.date_target.strftime('%b-%y')].append(k.price_subtotal)
                else:
                    dates_dic[k.date_target.strftime('%b-%y')] = [k.price_subtotal]
            if dates_dic:
                new_lines[i] = dates_dic
        return new_lines
    
    def _prepare_invoice_report_body(self, new_lines, message_body):
        invoice_due_count = 1
        for order_id, val_list in new_lines.items():
            # Change for resloving invoice report email 
            # for month_nam, total in val_list.items():
            for month_nam, total in val_list:
                order = self.env['sale.order'].browse(order_id)
                milestone_name = order.name + ' ' + month_nam
                message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(invoice_due_count) + '</td>'\
                                    '<td>' + str(order.sbu_id.name) + '</td>'\
                                    '<td>' + str(order.partner_id.name) + '</td>'\
                                    '<td>' + str(order.project_id.name) + '</td>'\
                                    '<td>' + str(order.project_id.user_id.name) + '</td>'\
                                    '<td>' + str(milestone_name) + '</td>'\
                                    '<td>' + str(sum(total)) + '</td>'\
                                    '<td>' + str(order.company_id.name) + '</td>'\
                                '</tr>'
                invoice_due_count += 1
        return message_body
            
    def _cron_project_invoice_due_report(self):
        email_invoice_due = self.env['project.report.email'].search([('report_type','=','invoice_due')]).employee_id.mapped('work_email')
        email_invoice_due_print = self.env['project.report.email'].search([('report_type','=','invoice_due_print')]).employee_id.mapped('work_email')
        order = self.env['sale.order'].search([('state', '=', 'sale'), ('group_multi_company', '=', False)])
        # Invoice Due
        today_date = fields.Date.today()
        june_date = fields.Date.today() + relativedelta(day=1, month=6, year=2021)
        order_lines = order.order_line.filtered(lambda line: line.product_states not in ['accepted_by_client', 'reinvoice', 'paid', 'not_consider'] and line.date_target and line.date_target < today_date and line.date_target > june_date and line.display_type != 'line_section' and (line.price_unit != 0 or line.product_uom_qty != 0))        
        new_lines = self._get_order_lines(order_lines)
        if email_invoice_due and new_lines:
            message_body = "Hello,<br/>"\
                    "Following invoices are due for raising. Kindly take actions to send request for raising the invoice to accounts team at the earliest:<br/>"
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'SBU Name' + '</th>'\
                                '<th>' + 'Customer Name' + '</th>'\
                                '<th>' + 'Project Name' + '</th>'\
                                '<th>' + 'Project Manager' + '</th>'\
                                '<th>' + 'Milestone Details' + '</th>'\
                                '<th>' + 'Amount' + '</th>'\
                                '<th>' + 'Company' + '</th>'\
                            '</tr>'
            message_body = self._prepare_invoice_report_body(new_lines, message_body)
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Report to highlight invoices which are not raised by the project/operations team',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_invoice_due),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

        # Invoice Due for Print
        order = self.env['sale.order'].search([('state', '=', 'sale'), ('group_multi_company', '=', False)])
        order_line = order.order_line.filtered(lambda sline: sline.invoice_status in ['to invoice', 'partial', 'to_invoice_new'] and sline.display_type != 'line_section' and sline.product_states in ['accepted_by_client', 'reinvoice'])
        new_lines = self._get_order_lines(order_line)
        if new_lines and email_invoice_due_print:
            message_body = "Hello,<br/>"\
                    "Following invoices are waiting action from you to raise them, print and move them to 'Fully Invoices' status:<br/>"
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'SBU Name' + '</th>'\
                                '<th>' + 'Customer Name' + '</th>'\
                                '<th>' + 'Project Name' + '</th>'\
                                '<th>' + 'Project Manager' + '</th>'\
                                '<th>' + 'Milestone Details' + '</th>'\
                                '<th>' + 'Amount' + '</th>'\
                                '<th>' + 'Company' + '</th>'\
                            '</tr>'
            message_body = self._prepare_invoice_report_body(new_lines, message_body)
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Report to highlight invoices which are not printed yet by the accounts team',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_invoice_due_print),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

    def _cron_not_in_syn_order(self):
        email_not_sync_order = self.env['project.report.email'].search([('report_type', '=', 'not_sync_order')]).employee_id.mapped('work_email')
        sale_orders = self.env['sale.order'].search([('state', '=', 'sale'), ('group_multi_company', '=', False)])
        not_sync_order = []
        for sale_order in sale_orders:
            if sale_order.contract_sale_order and sale_order.amount_inr != sale_order.contract_sale_order.amount_inr:
                not_sync_order.append(sale_order)
        if email_not_sync_order and not_sync_order:
            message_body = 'Work Orders which are not synced'
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'Work Order' + '</th>'\
                                '<th>' + 'Customer' + '</th>'\
                                '<th>' + 'Project Name' + '</th>'\
                                '<th>' + 'Contract Sale Order' + '</th>'\
                                '<th>' + 'Amount' + '</th>'\
                                '<th>' + 'Contract Sale Order Amount' + '</th>'\
                                '<th>' + 'Contrct Signing Entity' + '</th>'\
                                '<th>' + 'Contract Execution Entity' + '</th>'\
                            '</tr>'
            count = 1
            for rec in not_sync_order:
                contract_execution = rec.company_sign_id.name or ''
                contract_sign = rec.contract_sign_id.name or ''
                message_body += '<tr style="text-align:center;">'\
                                '<td>' + str(count) + '</td>'\
                                '<td>' + str(rec.name) + '</td>'\
                                '<td>' + str(rec.partner_id.name) + '</td>'\
                                '<td>' + str(rec.project_id.name) + '</td>'\
                                '<td>' + str(rec.contract_sale_order.name) + '</td>'\
                                '<td>' + str(rec.amount_total) + '</td>'\
                                '<td>' + str(rec.contract_sale_order.amount_total) + '</td>'\
                                '<td>' + str(contract_sign) + '</td>'\
                                '<td>' + str(contract_execution) + '</td>'\
                            '</tr>'
                count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Unsynced Work Orders',
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(i for i in email_not_sync_order),
                'email_cc': 'unity@e-zest.in',
                'auto_delete': False,
            }
            self.env['mail.mail'].create(template_values).sudo().send()
