# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class AllocationUtilization(models.TransientModel):
    _name = 'allocation.utilization.report'
    _description = 'Allocation Utilization'

    @api.model
    def default_get(self, fields):
        res = super(AllocationUtilization, self).default_get(fields)
        today_date = date.today()
        if today_date.month == 1:
            res['report_month'] = str(today_date.month)
        else:
            res['report_month'] = str(today_date.month - 1)
        res['report_year'] = self.env['utilization.report.year'].sudo().search([('name', '=', today_date.year)], limit=1).id
        return res

    report_month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], string="Month")
    report_year = fields.Many2one('utilization.report.year', string="Year", domain=[('name', '<=', fields.Date.today().year)])
    save_report = fields.Boolean(string="Save Report", default=False)

    def act_download_report(self):
        data = self.read()
        datas = {
            'ids': [],
            'model': 'hr.employee',
            'form': [self.report_month, self.report_year, self.save_report]
        }
        current_id = self
        return self.env.ref('project_role.report_utilization_data_xlsx').report_action(current_id, data=datas)


class UtilizationReportYear(models.Model):
    _name = 'utilization.report.year'
    _description = 'Utilization Report Year'

    name = fields.Integer(string="Year Name", required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Year Name already exists!"),
    ]
