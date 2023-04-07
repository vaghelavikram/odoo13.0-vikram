# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _


class ProjectAssignment(models.Model):
    _name = 'project.ptp.assignment'
    _description = 'Project PTP Assignment'

    start_date = fields.Date(string="Assigned From", tracking=True, default=datetime.today().date())
    end_date = fields.Date(string="Assigned Till", readonly=False, tracking=True)
    employee_id = fields.Many2one('hr.employee', string="e-Zestian", tracking=True)
    allocation_percentage = fields.Integer(string='Allocation(%)', tracking=True, default="100")
    project_bill_status = fields.Selection([('25', '25% Billable'),
                                           ('50', '50% Billable'),
                                           ('100', '100% Billable'),
                                           ('0_unbilled', '0% UnBilled - Critical'),
                                           ('0_unbilled_buffer', '0% Unbilled Buffer'),
                                           ('0_unbilled_shadow', '0% Unbilled Shadow')], string='Billability Status',
                                           tracking=True, default='100')
    project_id = fields.Many2one('project.project', string='Project', required=True, tracking=True, default=lambda self: self.env.context.get('default_project_id'))
    company_id = fields.Many2one('res.company', string='Company', related='project_id.company_id', store=True, readonly=True)
    project_role_id = fields.Many2one('hr.job', string='Assigned to Role', tracking=True)
    assignment_id = fields.Many2one('project.assignment', string="Assignment Id")

    def _cron_active_ptp_allocation(self):
        today = fields.Date.today()
        allocation = self.env['project.assignment'].sudo().search([('assign_status', '=', 'confirmed'), ('allocation_completed', '=', False)])
        for rec in allocation:
            if rec.project_id.payroll_loc.id != rec.employee_id.payroll_loc.id:
                current_alloc = self.sudo().search([('assignment_id', '=', rec.id)], limit=1)
                if not current_alloc:
                    self.sudo().create({
                        'employee_id': rec.employee_id.id,
                        'project_id': rec.project_id.id,
                        'start_date': rec.start_date,
                        'end_date': rec.end_date,
                        'assignment_id': rec.id,
                        'project_role_id': rec.project_role_id.id,
                        'allocation_percentage': rec.allocation_percentage,
                        'project_bill_status': rec.project_bill_status
                    })
                elif current_alloc:
                    current_alloc.sudo().write({
                        'end_date': rec.end_date,
                        'start_date': rec.start_date,
                        'allocation_percentage': rec.allocation_percentage,
                        'project_bill_status': rec.project_bill_status
                    })
        expire_allocation = self.sudo().search([('end_date', '<', today)])
        for exp_alloc in expire_allocation:
            exp_alloc.unlink()

    def _move_to_ptp(self):
        for rec in self:
            ptp_project = False
            if 'DES' == rec.project_id.sbu_id.name:
                ptp_project = self.env['project.project'].search([('name', '=', 'e-Zest-PTP-DES')])
            elif 'DPES' == rec.project_id.sbu_id.name:
                ptp_project = self.env['project.project'].search([('name', '=', 'e-Zest-PTP-DPES')])
            elif 'IO' == rec.project_id.sbu_id.name:
                ptp_project = self.env['project.project'].search([('name', '=', 'e-Zest-PTP-IO')])
            if ptp_project:
                rec.assignment_id.sudo().write({
                    'project_id': ptp_project.id
                })

    def _move_back_ptp_to_project(self):
        for rec in self:
            rec.assignment_id.sudo().write({
                'project_id': rec.project_id.id
            })


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def move_to_ptp(self):
        self.env['project.ptp.assignment'].sudo().search([])._move_to_ptp()

    def move_ptp_to_project(self):
        self.env['project.ptp.assignment'].sudo().search([])._move_back_ptp_to_project()
