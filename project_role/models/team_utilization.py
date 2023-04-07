# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _

class ProjectTeamUtilization(models.Model):
    _name = 'project.team.utilization'
    _description = 'Project Team Utilization'
    _rec_name = 'from_date'

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    utilization_line = fields.One2many('project.team.utilization.data', 'utilization_id', string="Utilization Data")
    
class ProjectTeamUtilizationData(models.Model):
    _name = 'project.team.utilization.data'
    _description = 'Project Team Utilization Data'

    utilization_id = fields.Many2one('project.team.utilization', string="Utilization Id")
    from_date = fields.Date(related="utilization_id.from_date", store=True, string="From Date")
    to_date = fields.Date(related="utilization_id.to_date", store=True, string="To Date")
    employee_id = fields.Char(string="e-Zestian")
    emp_code = fields.Char(string="Team Member Code")
    customer_id = fields.Many2one('res.partner', string="Customer")
    project_id = fields.Many2one('project.project', string='Project')
    bu_head = fields.Char(string='BU Head')
    engagement_model = fields.Char(string='Engagement Model')
    allocation = fields.Float(string='Allocation %')
    effective_alloc = fields.Float(string="Effective Allocation")
    standard_hours = fields.Integer(string="Standard Hours")
    effective_hours = fields.Integer(string="Effective Standard Hours")
    accrued_rev = fields.Float(string="Accrued Revenue")
    billed_hours = fields.Float(string="Billed Hours")
    effective_cost = fields.Float(string="Effective Cost")
    cost = fields.Float(string="Cost USD")
    revenue = fields.Float(string="Revenue")
    technology = fields.Char(string="Technology")
    total_exp = fields.Float(string="Total Exp")
    doj = fields.Date(string="Date of Joining")
