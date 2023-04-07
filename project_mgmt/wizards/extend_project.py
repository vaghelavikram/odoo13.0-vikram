# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ExtendProject(models.TransientModel):
    _name = 'extend.project'
    _description = 'Extend Project'

    actual_start_date = fields.Date(string="Actual Start Date")
    planned_end_date = fields.Date(string="Extend End Date")

    @api.constrains('actual_end_date', 'actual_start_date')
    def _check_date(self):
        if self.planned_end_date and self.actual_start_date and self.planned_end_date < self.actual_start_date:
            raise UserError(_("The start date must be anterior to the end date"))

    def act_extend_project(self):
        if self.env.context.get('active_model') == 'sale.order':
            order = self.env['sale.order'].browse(self.env.context.get('active_id'))
            active_id = order.project_id.id
        else:
            active_id = self._context.get('active_id')
        project = self.env['project.project'].sudo().search([('id', '=', active_id)])
        if self.planned_end_date and project.planned_end_date and self.planned_end_date == project.planned_end_date:
            raise UserError(_('Extend End Date cannot be same as Existing Planned End Date.'))
        if self.planned_end_date and project.planned_end_date and self.planned_end_date < project.planned_end_date:
            raise UserError(_('Extend End Date cannot be Smaller than Existing Planned End Date.'))
        if self.actual_start_date and self.planned_end_date:
            project.sudo().write({
                'actual_start_date': self.actual_start_date,
                'planned_end_date': self.planned_end_date,
            })
            if project.sale_order_id and project.sale_order_id.contract_sale_order and project.sale_order_id.contract_sale_order.project_id:
                project.sale_order_id.contract_sale_order.project_id.sudo().write({
                    'actual_start_date': self.actual_start_date,
                    'planned_end_date': self.planned_end_date
                })
            # if project.sale_order_id:
            #     project.sale_order_id.sudo().write({
            #         'validity_date': self.planned_end_date,
            #     })
            for alloc in self.allocation_ids:
                alloc._compute_employee_allocation(alloc.start_date, alloc.end_date, alloc.employee_id)
                employee = alloc.employee_id
                emp_alloc = self.env['project.assignment'].sudo().search([('employee_id', '=', employee.id), ('assign_status', '=', 'confirmed'), ('id', '!=', alloc.id)])
                for prev_alloc in emp_alloc:
                    if alloc.start_date <= prev_alloc.start_date and self.planned_end_date >= prev_alloc.end_date and prev_alloc.allocation_percentage + alloc.allocation_percentage > 100:
                        raise UserError(_("{1} already allocated by {2}{0} till {3}".format('%',employee.name, employee.project_allocate, employee.project_assign_till.strftime("%d-%b-%Y"))))
                    elif prev_alloc.start_date <= self.planned_end_date and prev_alloc.end_date >= self.planned_end_date and prev_alloc.allocation_percentage + alloc.allocation_percentage > 100:
                        raise UserError(_("{1} already allocated by {2}{0} till {3}".format('%',employee.name, employee.project_allocate, employee.project_assign_till.strftime("%d-%b-%Y"))))
                alloc.sudo().write({'end_date': self.planned_end_date})
