# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, date


class EmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    def action_create_allocation(self):
        view_form_id = self.env.ref('project_role.project_assignment_form').id
        action = {
            'type': 'ir.actions.act_window',
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': _('Allocation'),
            'res_model': 'project.assignment',
            'context': {'form_view_initial_mode': 'edit', 'default_employee_id': self.id}
        }
        return action

    def action_emp_allocation(self):
        view_form_id = self.env.ref('project_role.project_assignment_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'views': [(view_form_id, 'tree')],
            'view_mode': 'tree',
            'name': _('Allocation'),
            'res_model': 'project.assignment',
            'domain': [('employee_id', '=', self.id)]
            # 'context': {'form_view_initial_mode': 'edit', 'default_employee_id': self.id}
        }
        return action

    def _get_project_allocation(self):
        for res in self:
            project_assgn = self.env['project.assignment'].sudo().search([('employee_id', '=', res.id)])
            alloc = 0
            assigned = []
            if project_assgn:
                for rec in project_assgn:
                    if rec.assign_status == 'confirmed':
                        # if rec.end_date and date.today() > rec.end_date:
                        # alloc += rec.allocation_percentage
                        assigned.append(rec.end_date) if rec.end_date else assigned
            # res.project_allocate = alloc
            res.project_assign_till = max(list(set(assigned))) if assigned else False

    def _get_total_billability(self):
        for res in self:
            project_assgn = self.env['project.assignment'].sudo().search([('employee_id', '=', res.id), ('assign_status', '=', 'confirmed')])
            bill = 0
            if project_assgn:
                for rec in project_assgn:
                    if not rec.allocation_completed and rec.project_bill_status in ['25', '50', '100']:
                        bill += int(rec.project_bill_status)
            res.total_billability = bill

    def _get_all_allocations(self):
        for rec in self:
            project_alloc = []
            project = self.env['project.project'].sudo().search([])
            project_assignment = self.env['project.assignment'].sudo().search([('employee_id', '=', rec.id)])
            for assg in project_assignment:
                for i in project:
                    if assg.project_id.id == i.id:
                        project_alloc.append(assg.id)
            rec.allocation_ids = [(6, 0, [alloc for alloc in project_alloc])]
            assgn = []
            for ap in project_assignment:
                assgn.append((ap.project_id.id, ap.start_date, ap.end_date, ap))
            assgn = sorted(assgn)
            final = []
            for ap in assgn:
                if final and ap[0] == final[-1][0].project_id.id:
                    start_date = ap[1]
                    end_date = ap[2]
                    if ap[1] and ap[1] > final[-1][1]:
                        start_date = final[-1][1]
                    if ap[2] and ap[2] < final[-1][2]:
                        end_date = final[-1][2]
                    final.remove(final[-1])
                    final.append((ap[3], start_date, end_date))
                else:
                    final.append((ap[3], ap[1], ap[2]))

                # if assgn and ap.project_id == assgn[-1][0]:
                #     start_date = ap.start_date
                #     if ap.start_date and assgn[-1][1] < ap.start_date:
                #         start_date = assgn[-1][1]
                #     if ap.end_date and assgn[-1][2] > ap.end_date:
                #         end_date = assgn[-1][2]
                #     import pdb; pdb.set_trace()
                #     assgn.remove(assgn[-1])
                #     assgn.append(tuple((ap.project_id, start_date, end_date, ap)))
                # else:
                #     assgn.append(tuple((ap.project_id, ap.start_date, ap.end_date, ap)))
            comp_exp = self.env['hr.resume.line'].sudo().search([('name', '=', rec.company_id.name), ('date_end', '=', False), ('employee_id', '=', rec.id)], limit=1)
            comp_exp.project_line_ids = [(5, 0, 0)]
            for emp_assign in final:
                comp_exp.project_line_ids = [(0, 0, {
                    'project_line_id': comp_exp.id,
                    'project_name': emp_assign[0].project_id.name,
                    'project_skill': emp_assign[0].project_id.primary_skill.name,
                    'project_start': emp_assign[1],
                    'project_end': emp_assign[2],
                    'project_role': emp_assign[0].project_role_id.name,
                    'responsibility': emp_assign[0].responsibility,
                    'project_scope': emp_assign[0].project_id.scope
                })]

    def _search_total_billability(self, operator, value):
        employees_domain = []
        for i in self.env['hr.employee'].search([]):
            if operator == '<=' and i.total_billability <= value:
                employees_domain.append(('id','=', i.id))
            elif operator == '>=' and i.total_billability >= value:
                employees_domain.append(('id','=', i.id))
            elif operator == '<' and i.total_billability < value:
                employees_domain.append(('id','=', i.id))
            elif operator == '>' and i.total_billability > value:
                employees_domain.append(('id','=', i.id))
            elif operator == '=' and i.total_billability == value:
                employees_domain.append(('id','=', i.id))
            elif operator == '!=' and i.total_billability != value:
                employees_domain.append(('id','=', i.id))
            else:
                employees_domain.append(('id','=', None))
        for rec in range(0,len(employees_domain)-1):
            employees_domain.insert(rec,'|')
        return employees_domain

    def _search_project_assign(self, operator, value):
        employees_domain = []
        if value:
            value = datetime.strptime(value, '%m-%d-%Y').date()
        for i in self.env['hr.employee'].search([]):
            if i.project_assign_till and operator == '<=' and i.project_assign_till <= value:
                employees_domain.append(('id','=', i.id))
            elif i.project_assign_till and operator == '>=' and i.project_assign_till >= value:
                employees_domain.append(('id','=', i.id))
            elif i.project_assign_till and operator == '<' and i.project_assign_till < value:
                employees_domain.append(('id','=', i.id))
            elif i.project_assign_till and operator == '>' and i.project_assign_till > value:
                employees_domain.append(('id','=', i.id))
            elif i.project_assign_till and operator == '=' and i.project_assign_till == value:
                employees_domain.append(('id','=', i.id))
            elif not value and operator == '=' and i.project_assign_till == value:
                employees_domain.append(('id','=', i.id))
            elif i.project_assign_till and operator == '!=' and i.project_assign_till != value:
                employees_domain.append(('id','=', i.id))
            else:
                employees_domain.append(('id','=', None))
        employees_domain = list(set(employees_domain))
        for rec in range(0,len(employees_domain)-1):
            employees_domain.insert(rec,'|')
        return employees_domain

    project_allocate = fields.Integer(string="Project Allocation")
    project_assign_till = fields.Date(string="Project Assigned Till", compute="_get_project_allocation", search="_search_project_assign")
    total_billability = fields.Integer(string="Total Billability", compute="_get_total_billability", search="_search_total_billability")
    allocate = fields.Char(string="Allocation")
    allocation_ids = fields.One2many('project.assignment', 'employee_id', compute="_get_all_allocations", string="Allocations")

    def write(self, vals):
        if vals.get('is_ezestian'):
            if self.project_allocate == 0 and self.project_assign_till is False and self.account.name in ['Deployable - Billable', 'Temporarily - Deployable']:
                project = self.env['project.project'].sudo().search([('name', '=', 'On Bench Internal Project'), ('active', '=', False)])
                self.env['project.assignment'].sudo().create({
                    'project_id': project.id,
                    'employee_id': self.id,
                    'allocation_percentage': 0,
                    'project_bill_status': '0_unbilled',
                    'start_date': str(fields.Date.today()),
                    'end_date': str(fields.Date.today()),
                    'assign_status': 'confirmed'
                })
        return super(EmployeeInherit, self).write(vals)
