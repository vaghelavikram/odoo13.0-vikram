# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employee_probation_survey_days = fields.Char(string='Probation Survey Days',
    config_parameter='hr_employee_updation.survey_days')
    employee_fnf_days = fields.Char(string='Fnf Days',
    config_parameter='hr_employee_updation.employee_fnf_days')
