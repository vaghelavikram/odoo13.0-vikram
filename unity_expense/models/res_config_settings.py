# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    responsible_account1 = fields.Many2one('res.users', string='Responsible Accountant 1',
        config_parameter='unity_expense.responsible_account1')
    responsible_account2 = fields.Many2one('res.users', string='Responsible Accountant 2',
        config_parameter='unity_expense.responsible_account2')
    responsible_payment = fields.Many2one('res.users', string='Responsible Payment Approval',
        config_parameter='unity_expense.responsible_payment')

