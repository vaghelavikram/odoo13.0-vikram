# -*- coding: utf-8 -*-

from odoo import fields, models
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employee_attendance_from_date = fields.Char(string='From Date',
        config_parameter='hr_employee_attendance.from_date')
    employee_attendance_to_date = fields.Char(string='To Date',
        config_parameter='hr_employee_attendance.to_date')
    payroll_from_date = fields.Char(string='Payroll From Date', default=lambda self: fields.Date.to_string(date.today().replace(day=26) + relativedelta(months=-1)),
        config_parameter='hr_employee_attendance.payroll_from_date')
    payroll_to_date = fields.Char(string='Payroll To Date', default=lambda self: fields.Date.to_string(date.today().replace(day=25)),
        config_parameter='hr_employee_attendance.payroll_to_date')
    allocate_pl = fields.Boolean(string='Allocate PL',
        config_parameter='allocate_pl')
