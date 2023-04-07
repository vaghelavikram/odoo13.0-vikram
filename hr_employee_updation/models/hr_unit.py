# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HRVendor(models.Model):
    _name = 'hr.vendor'
    _description = 'Vendor'

    name = fields.Char(string='Vendor')


class HrAccount(models.Model):
    _name = 'hr.account'
    _description = 'Account'

    def write(self, vals):
        if self.name == 'Deployable - Billable' and vals.get('name'):
            vals['name'] = 'Deployable - Billable'
        elif self.name == 'Enabling – Support' and vals.get('name'):
            vals['name'] = 'Enabling – Support'
        elif self.name == 'Temporarily Non Billable' and vals.get('name'):
            vals['name'] = 'Temporarily Non Billable'
        elif self.name == 'Temporarily - Deployable' and vals.get('name'):
            vals['name'] = 'Temporarily - Deployable'
        return super(HrAccount, self).write(vals)

    name = fields.Char(string='Account')


class HrBand(models.Model):
    _name = 'hr.band'
    _description = 'Band'

    name = fields.Char(string='Band/Grade')


class HrprimarySkill(models.Model):
    _name = 'hr.primary.skill'
    _description = 'Skills'

    name = fields.Char(string='Skills')
    parent_skill_id = fields.Many2one('hr.primary.skill', string="Parent Skill")
    similar_skill_ids = fields.Many2many('hr.primary.skill', 'primary_skill_rel', 'skill_id', 'similar_skill_id', string="Similar Skills")
    contemporary = fields.Char(string="Contemporary")


class HrPayrollLocation(models.Model):
    _name = 'hr.payroll.location'
    _description = 'Payroll Location'

    name = fields.Char(string='Payroll Location')
    address = fields.Char(string='Address')
    cin = fields.Char(string="CIN")
    company_id = fields.Many2one('res.company', string="Company")
    pan_no = fields.Char(string="Pan No.")
    gst_no = fields.Char(string="GST No.")
    bank_ids = fields.One2many('payroll.location.bank', 'payroll_loc_bank_id', string="Bank Account")


class OrgUnit(models.Model):
    _name = 'organization.unit'
    _description = 'Organization Unit'

    def write(self, vals):
        if self.name == 'DES' and vals.get('name'):
            vals['name'] = 'DES'
        elif self.name == 'DPES' and vals.get('name'):
            vals['name'] = 'DPES'
        elif self.name == 'DES(LTD)' and vals.get('name'):
            vals['name'] = 'DES(LTD)'
        elif self.name == 'IO' and vals.get('name'):
            vals['name'] = 'IO'
        elif self.name == 'Quality Assurance' and vals.get('name'):
            vals['name'] = 'Quality Assurance'
        elif self.name == 'DES(INC)' and vals.get('name'):
            vals['name'] = 'DES(INC)'
        elif self.name == 'DPES(INC)' and vals.get('name'):
            vals['name'] = 'DPES(INC)'
        elif self.name == 'Enabling Team' and vals.get('name'):
            vals['name'] = 'Enabling Team'
        return super(OrgUnit, self).write(vals)

    name = fields.Char(string='organization Unit')


class HrLocationWork(models.Model):
    _name = 'hr.location.work'
    _description = 'HR Work Location'

    def write(self, vals):
        if self.name == 'DIC' and vals.get('name'):
            vals['name'] = 'DIC'
        elif self.name == 'Onsite - India' and vals.get('name'):
            vals['name'] = 'Onsite - India'
        elif self.name == 'Kothrud' and vals.get('name'):
            vals['name'] = 'Kothrud'
        elif self.name == 'Onsite - IO' and vals.get('name'):
            vals['name'] = 'Onsite - IO'
        elif self.name == 'Onsite - Onsite US' and vals.get('name'):
            vals['name'] = 'Onsite - Onsite US'
        elif self.name == 'Onsite - Onsite ROW' and vals.get('name'):
            vals['name'] = 'Onsite - Onsite ROW'
        return super(HrLocationWork, self).write(vals)

    name = fields.Char(string="Location name")
    bank_ids = fields.One2many('res.partner.bank', 'loc_bank_id', string="Bank Account")
    related_login = fields.Many2many('res.users', string="Related e-Zestian Email")
    company_id = fields.Many2one('res.company', string="Company")


class HRGroup(models.Model):
    _name = 'hr.employee.group'
    _description = 'HR Group'

    @api.onchange('department_ids')
    def _onchange_department(self):
        if self.department_ids:
            dup_department = self.search([('department_ids', 'in', self.department_ids.ids[-1])])
            if dup_department:
                raise UserError(_("%s Department already allocated to %s" % (dup_department.department_ids[-1].name, dup_department.name)))

    name = fields.Char(string='Group Name')
    related_hr = fields.Many2many('hr.employee', string='Related HR')
    department_ids = fields.Many2many('hr.department', string="Department")
    # company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)


class PayrollLocationBank(models.Model):
    _name = 'payroll.location.bank'
    _description = 'Payroll Location Bank'

    payroll_loc_bank_id = fields.Many2one('hr.payroll.location', string="Payroll Location")
    name = fields.Char(string="Name")
    beneficiary_name = fields.Char(string="Beneficiary Name")
    bank_id = fields.Many2one('res.bank', string="Bank")
    bank_type = fields.Char(string="Sort Code")
    iban_no = fields.Char(string="IBAN No.")
    company_id = fields.Many2one('res.company', string="Company")


class BobMailConfig(models.Model):
    _name = 'bod.mail.config'
    _description = 'BOD Mail Configuration'

    user_id = fields.Many2one('res.users', string="e-Zestian")
