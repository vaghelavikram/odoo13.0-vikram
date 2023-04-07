# -*- coding: utf-8 -*-
from datetime import datetime, date

from odoo import models, fields, api, _
from odoo.addons.base.models import res_partner


class PartnerInherit(models.Model):
    _inherit = 'res.partner'

    geo_location = fields.Many2one('geo.location', string="Geo Location")
    department_id = fields.Many2one('hr.department', string="Related SBU")
    revenue_potential = fields.Float(string="Revenue Potential(INR)")
    delivery_owner = fields.Many2one('hr.employee', string="Delivery Owner")
    account_owner = fields.Many2one('hr.employee', string="Account Owner")
    technical_owner = fields.Many2one('hr.employee', string="Technical Owner")
    hubspot_id = fields.Char(string="Hubspot Customer Id")
    lob = fields.Many2many('line.business', string="Line of Business")
    cost_center = fields.Char(string="Cost Center")
    vendor_id = fields.Char(string="Vendor Id/pid")
    customer_group = fields.Many2one('res.partner', string="Group Customer")
    active_customer = fields.Boolean(string="Active Customer", compute="_get_active_customer",search='_search_active_customer')
    customer_type = fields.Selection([('new_logo', 'NEW LOGO'),
         ('new', 'NEW NEW'),
         ('existing', 'EXISTING')], string="Customer Type")
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('other', 'Other Address'),
         ("private", "Private Address"),
        ], string='Address Type',
        default='other',
        help="Invoice & Delivery addresses are used in sales orders. Private addresses are only visible by authorized users.")

    @api.onchange('parent_id')
    def _onchnage_parent_id(self):
        self.street = self.parent_id.street
        self.street2 = self.parent_id.street2
        self.zip = self.parent_id.zip
        self.city = self.parent_id.city
        self.country_id = self.parent_id.country_id
        self.state_id = self.parent_id.state_id
        self.department_id = self.parent_id.department_id
        self.geo_location = self.parent_id.geo_location
        self.phone = self.parent_id.phone
        self.mobile = self.parent_id.mobile
        self.email = self.parent_id.email
        self.website = self.parent_id.website
        self.title = self.parent_id.title
        self.function = self.parent_id.function

    @api.depends('sale_order_count', 'name')
    def _get_active_customer(self):
        for rec in self:
            c_month = date.today().month
            c_year = date.today().year
            start_date = False
            end_date = False
            if c_month >= 4:
                c_year = c_year
                n_year = c_year + 1
                start_date = datetime.strptime('01-04-%s' % (c_year), '%d-%m-%Y').date()
                end_date = datetime.strptime('31-03-%s' % (n_year), '%d-%m-%Y').date()
            else:
                c_year = c_year
                p_year = c_year - 1
                start_date = datetime.strptime('01-04-%s' % (p_year), '%d-%m-%Y').date()
                end_date = datetime.strptime('31-03-%s' % (c_year), '%d-%m-%Y').date()
            sale_order = self.env['sale.order'].sudo().search([('partner_id', '=', rec.id), ('state', '!=', 'cancel')])
            sale_order_fy = sale_order.filtered(lambda order: (order.validity_date and order.validity_date >= start_date and order.validity_date <= end_date))
            if sale_order_fy:
                rec.active_customer = True
            else:
                rec.active_customer = False

    def _search_active_customer(self, operator, value):
        customer_domain = []
        for i in self.env['res.partner'].search([('customer_rank', '>', 0)]):
            if operator == '=' and i.active_customer is True:
                customer_domain.append(('id', '=', i.id))
            elif operator == '!=' and i.active_customer is False:
                customer_domain.append(('id', '=', i.id))
        for rec in range(0, len(customer_domain) - 1):
            customer_domain.insert(rec, '|')
        return customer_domain

class GeoLocation(models.Model):
    _name = 'geo.location'
    _description = 'Geo Location'

    name = fields.Char(string="Name")

class LineBusiness(models.Model):
    _name = 'line.business'
    _description = 'Line Business'

    name = fields.Char(string="Name")
