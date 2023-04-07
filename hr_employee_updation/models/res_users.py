# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class User(models.Model):
    _inherit = 'res.users'

    # def write(self, vals):
    #     if vals.get('spouse_name') or vals.get('chlid1_name') or vals.get('chlid2_name')\
    #     or vals.get('spouse_age') or vals.get('child1_age') or vals.get('child2_age')\
    #     or vals.get('spouse_birth_date') or vals.get('child1_birth_date') or vals.get('child2_birth_date'):
    #         self.employee_id.sudo().write({
    #             'spouse_name': vals.get('spouse_name'),
    #             'chlid1_name': vals.get('chlid1_name'),
    #             'chlid2_name': vals.get('chlid2_name'),
    #             'spouse_age': vals.get('spouse_age'),
    #             'child1_age': vals.get('child1_age'),
    #             'child2_age': vals.get('child2_age'),
    #             'spouse_birth_date': vals.get('spouse_birth_date'),
    #             'child1_birth_date': vals.get('child1_birth_date'),
    #             'child2_birth_date': vals.get('child2_birth_date')
    #         })
    #     return super(User, self).write(vals)

    spouse_name = fields.Char(related="employee_id.spouse_name", string="Spouse Name")
    chlid1_name = fields.Char(related="employee_id.chlid1_name", string="Child1 Name")
    chlid2_name = fields.Char(related="employee_id.chlid2_name", string="Child2 Name")
    spouse_age = fields.Float(related="employee_id.spouse_age", string="Spouse Age")
    child1_age = fields.Float(related="employee_id.child1_age", string="Child1 Age")
    child2_age = fields.Float(related="employee_id.child2_age", string="Child2 Age")
    spouse_birth_date = fields.Date(related="employee_id.spouse_birth_date", string="Spouse Birth Date")
    child1_birth_date = fields.Date(related="employee_id.child1_birth_date", string="Child1 Birth Date")
    child2_birth_date = fields.Date(related="employee_id.child2_birth_date", string="child2 Birth Date")
    # spouse_name1 = fields.Char(string="Spouse Name")
    # chlid1_name1 = fields.Char(string="Child1 Name")
    # chlid2_name1 = fields.Char(string="Child2 Name")
    # spouse_age1 = fields.Float(string="Spouse Age")
    # child1_age1 = fields.Float(string="Child1 Age")
    # child2_age1 = fields.Float(string="Child2 Age")
    # spouse_birth_date1 = fields.Date(string="Spouse Birth Date")
    # child1_birth_date1 = fields.Date(string="Child1 Birth Date")
    # child2_birth_date1 = fields.Date(string="child2 Birth Date")
