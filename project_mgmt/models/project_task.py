# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from lxml import etree

class TaskInherit(models.Model):
    _inherit = "project.task"

    @api.depends('is_allocate', 'project_id', 'start_date')
    def _compute_user_id(self):
        users = []
        for rec in self:
            if rec.project_id and rec.project_id.assignment_ids and rec.start_date:
                for assign in rec.project_id.assignment_ids:
                    if not assign.allocation_completed and assign.employee_id and assign.employee_id.user_id and rec.start_date and assign.start_date <= rec.start_date:
                        users.append(assign.employee_id.user_id.id)
            rec.user_ids = users

    @api.onchange('start_date', 'date_deadline')
    def _onchange_start_end_date(self):
        current_user = self.env.user
        if self.sale_line_id and self.sale_line_id.offering_type == 'fixed_cost':
            if (current_user.user_has_groups('project_mgmt.group_project_manager') or current_user.user_has_groups('project_mgmt.group_project_operations') or current_user.user_has_groups('project_mgmt.group_project_operations_copy') or current_user.user_has_groups('base.group_erp_manager')):
                self.is_parent_task = True
        if self.parent_id:
            self.parent_id = False
        res = {}
        domain = [
            ('project_id', '=', self.project_id.id),
            ('date_deadline', '>=', self.date_deadline),
            ('start_date', '<=', self.start_date),
            ('sale_line_id', 'not in', ['accepted_by_client', 'reinvoice', 'paid']),
        ]
        if (current_user.user_has_groups('project_mgmt.group_project_manager') or current_user.user_has_groups('project_mgmt.group_project_operations') or current_user.user_has_groups('project_mgmt.group_project_operations_copy') or current_user.user_has_groups('base.group_erp_manager')):
            domain = domain
        else:
            domain += [('user_id', '=', current_user.id)]
        domain += ['|', ('parent_id', '=', False), ('is_parent_task', '=', True)]
        res['domain'] = {'parent_id': domain}
        return res

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        super(TaskInherit, self)._onchange_parent_id()
        if self.parent_id:
            self.planned_hours = self.parent_id.planned_hours
            self.sale_line_id = self.parent_id.sale_line_id.id

    @api.constrains('start_date', 'date_deadline')
    def _check_project(self):
        if self.date_deadline and self.start_date and self.date_deadline < self.start_date:
            raise UserError(_('Date Deadline must be greater than start date.'))
        # if self.task_type == 'activity' and not self.parent_id:
        #     raise UserError(_("Parent Task is mandatory."))

    @api.constrains('timesheet_ids')
    def _check_project_timesheet(self):
        for sheet in self.timesheet_ids:
            if self.user_id and sheet.employee_id.user_id.id != self.user_id.id and not (self.env.user.user_has_groups('project_mgmt.group_project_operations') or self.env.user.user_has_groups('project_mgmt.group_project_operations_copy')):
                # if sheet.employee_id.parent_id.user_id.id != self.env.user.id:
                raise UserError(_('You cannot edit timesheet of another e-Zestian.'))
            if self.sale_line_id.product_states in ['accepted_by_client', 'reinvoice', 'paid'] and not (self.env.user.user_has_groups('hr.group_hr_user')):
                raise UserError(_('You cannot fill timesheet once invoice is raised.'))

    @api.depends('user_id')
    def _compute_is_assign(self):
        current_user = self.env.user
        for rec in self:
            rec.edit_task_access = False
            if current_user.user_has_groups('project_mgmt.group_project_operations') or current_user.user_has_groups('project_mgmt.group_project_operations_copy'):
                rec.edit_task_access = True
            if rec.user_id.id == current_user.id or current_user.user_has_groups('project_mgmt.group_project_operations') or current_user.user_has_groups('project_mgmt.group_project_operations_copy') or current_user.user_has_groups('base.group_erp_manager') or current_user.user_has_groups('project_mgmt.group_project_manager'):
                rec.is_assign = True
            elif not rec.user_id and (current_user.user_has_groups('project_mgmt.group_project_manager') or current_user.user_has_groups('project_mgmt.group_project_operations_copy') or current_user.user_has_groups('project_mgmt.group_project_operations') or current_user.user_has_groups('base.group_erp_manager')):
                rec.is_assign = True
            else:
                rec.is_assign = False

    user_ids = fields.Many2many('res.users', compute="_compute_user_id")
    is_allocate = fields.Boolean(string="Allocate?")
    edit_task_access = fields.Boolean(string="Edit Task", compute="_compute_is_assign")
    # user_id = fields.Many2one('res.users', string='Assigned to',
    #     default=_get_user_id, index=True, tracking=True)
    task_type = fields.Selection([('milestone', 'Milestone'), ('activity', 'Activity')], string="Task Type", default="activity")
    start_date = fields.Date(string="Start Date")
    is_assign = fields.Boolean(string="Is Assign", compute="_compute_is_assign")
    is_parent_task = fields.Boolean(string="Is Parent task?", help="This helps to use as a parent task for user if true\n else will not show as parent task")
