# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from odoo.exceptions import UserError


class ProjectReportEmail(models.Model):
    _name = 'project.report.email'
    _description = 'Project Report Email'

    report_type = fields.Selection([
        ('internal_project', 'Internal Project'),
        ('unbilled_today', 'Unbilled Today'),
        ('project_emp_ext', 'Project Employee Role Require Extention'),
        ('unassigned_today', 'Unassigned Today'),
        ('unassigned_today_des', 'Unassigned Today DES'),
        ('unassigned_today_dpes', 'Unassigned Today DPES'),
        ('unassigned_today_io', 'Unassigned Today IO'),
        ('current_alloc_ux', 'Current Allocation UI and UX'),
        ('current_alloc_io', 'Current Allocation IO'),
        ('active_consultant', 'Active Deployable Consultant Current Allocation'),
        ('project_ryg', 'Project Review status (RYG)'),
        ('project_report_account', 'Project Report for Accounts Team'),
        ('operations_summary', 'Operations Summary'),
        ('onbench_contractor', 'On-bench Contractors'),
        ('missing_milestone', 'Missing Milestone'),
        ('long_leave', 'Long Leave'),
        ('milestone_summary', 'Month Wise Revenue'),
        ('invoice_due', 'Invoice Due Report'),
        ('not_sync_order', 'Orders Not in Sync'),
        ('invoice_due_print', 'Invoice Due for Printing')], string='Reports Type')
    employee_id = fields.Many2many('hr.employee', string='e-Zestian')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)

class MilestoneDifferenceReport(models.Model):
    _name = 'milestone.difference.report'
    _description = 'Milestone Difference Report'

    date = fields.Date(string="Date")
    milestone_ids = fields.One2many('milestone.difference.data', 'milestone_difference_id', string="Milestone Data")

class MilestoneData(models.Model):
    _name = 'milestone.difference.data'
    _description = 'Milestone Difference Data'

    month_name = fields.Char(string="Month")
    sbu = fields.Char(string="SBU")
    total = fields.Float(string="Total")
    difference_amt = fields.Float(string="Difference Amount")
    milestone_difference_id = fields.Many2one('milestone.difference.report')
    date = fields.Date(string="Date", related="milestone_difference_id.date", store=True)

class OperationsSummary(models.Model):
    _name = 'operations.summary'
    _description = 'Operations Summary'
    _rec_name = 'date'

    date = fields.Date(string="Date")
    operation_data_line = fields.One2many('operations.summary.data', 'summary_id', string="Summary Data")

class OperationsSummaryData(models.Model):
    _name = 'operations.summary.data'
    _description = 'Operations Summary Data'

    summary_id = fields.Many2one('operations.summary', string="Summary ID")
    date = fields.Date(related="summary_id.date", store=True)
    data_type = fields.Selection([('sbu_wise', 'SBU-Wise'), ('team_member_wise', 'Team Member-Wise'), ('company_wise', 'Company-Wise'), ('global', 'Global')], string="Data Type")
    data_name = fields.Char(string="Data Name")
    total_ezestian = fields.Integer(string="Total e-Zestian")
    total_deployable = fields.Integer(string="Total Deployable")
    non_deployable = fields.Integer(string="Non Deployable")
    more_100_billable = fields.Integer(string="More than 100 Billable")
    billable_100 = fields.Integer(string="100% Billable")
    billable_75 = fields.Integer(string="75% Billable")
    billable_50 = fields.Integer(string="50% Billable")
    billable_25 = fields.Integer(string="25% Billable")
    billable_0 = fields.Integer(string="0% Billable")
    billable_per = fields.Float(string="Billable %")
    allocation_100 = fields.Integer(string="100% Allocation")
    allocated_partially = fields.Integer(string="Partially Allocated")
    unallocated = fields.Integer(string="Unallocated")
    allocated_per = fields.Float(string="Allocation %")
    resigned = fields.Integer(string="Resigned Member")
    probation = fields.Integer(string="Probation Member")
    confirmed = fields.Integer(string="Confirmed Member")
