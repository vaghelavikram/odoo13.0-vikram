# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrPlannedExpense(models.Model):
    _name = "hr.planned.expense"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Planned Expense"
    _order = "date desc, id desc"

    @api.model
    def _default_employee_id(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.model
    def _default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id')

    @api.model
    def _get_employee_id_domain(self):
        res = [('id', '=', 0)] # Nothing accepted by domain, by default
        if self.user_has_groups('hr_expense.group_hr_expense_manager') or self.user_has_groups('account.group_account_user'):
            res = [] # Then, domain accepts everything
        elif self.user_has_groups('hr_expense.group_hr_expense_user') and self.env.user.employee_ids:
            employee = self.env.user.employee_ids[0]
            res = ['|', '|', ('department_id.manager_id.id', '=', employee.id),
                   ('parent_id.id', '=', employee.id), ('expense_manager_id.id', '=', employee.id)]
        elif self.env.user.employee_ids:
            employee = self.env.user.employee_ids[0]
            res = [('id', '=', employee.id)]
        return res

    @api.constrains('date','end_date')
    def _check_expense_date(self):
        if self.date < fields.Date.today():
            raise UserError(_("You can't apply planned expense for previous date."))
        if self.date > self.end_date:
            raise UserError(_("The Planned Expense date must be anterior to the end date."))

    name = fields.Char('Description', readonly=True, required=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]})
    date = fields.Date(readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, default=fields.Date.context_today, string="Planned Expense Date")
    end_date = fields.Date(readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, default=fields.Date.context_today, string="End Date")
    employee_id = fields.Many2one('hr.employee', string="e-Zestian", required=True, readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, default=_default_employee_id, domain=lambda self: self._get_employee_id_domain())
    product_id = fields.Many2one('product.product', string='Expense Type', readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, domain=[('can_be_expensed', '=', True)], required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=_default_product_uom_id)
    unit_amount = fields.Float("Expected Amount", digits='Product Price')
    company_currency_id = fields.Many2one('res.currency', string="Report Company Currency", related='sheet_id.currency_id', store=True, readonly=False)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id)
    description = fields.Text('Details of Expense', readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]})
    payment_mode = fields.Selection([
        ("own_account", "Cash"),
        ("company_account", "Bank/Online"),
        ("card", "Card")
    ], default='own_account', states={'second_approved': [('readonly', True)], 'approved': [('readonly', True)], 'reported': [('readonly', True)]}, string="Pay Through")
    expense_status = fields.Selection([
        ("planned", "Planned"),
        ("recurring", "Recurring")
    ], default='planned', states={'second_approved': [('readonly', True)], 'approved': [('readonly', True)], 'reported': [('readonly', True)]}, string="Expense Status")
    recurring_status = fields.Selection([
        ("monthly", "Monthly"),
        ("quaterly", "Quaterly"),
        ("yearly", "Yearly")
    ], default='monthly', states={'second_approved': [('readonly', True)], 'approved': [('readonly', True)], 'reported': [('readonly', True)]}, string="Recurring Status")
    recurring_valid = fields.Date('Recurring Valid Till')
    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('reported', 'Submitted'),
        ('approved', 'Approved'),
        ('second_approved', 'BU Approved'),
        ('account_verified', 'Account Verified'),
        ('payment', 'Payment Approved'),
        ('paid', 'Paid'),
        ('done', 'done'),
        ('refused', 'Refused')
    ], compute='_compute_state', string='Status', copy=False, index=True, readonly=True, store=True, help="Status of the expense.")
    sheet_id = fields.Many2one('hr.planned.expense.sheet', string="Expense Report", readonly=True, copy=False)
    is_refused = fields.Boolean("Explicitely Refused by manager or acccountant", readonly=True, copy=False)
    project_id = fields.Many2one('project.project', string='Project Name', track_visibility='onchange',)
    project_code = fields.Char(string='Whizible ID', track_visibility='onchange',)
    is_bill_client = fields.Selection([('yes','YES'),('no','No')], default="no", required=1, string='Is Billable to Client', track_visibility='onchange',)
    bill_as = fields.Selection([('debit_note', 'Debit Note'), ('sale_invoice', 'Sales Invoice No.')], string='To be Billed As', track_visibility='onchange',)
    debit_note = fields.Char(string='Debit No./Sales Invoice No.', track_visibility='onchange')
    department_manager = fields.Many2one('res.users', string="Department Manager", compute="_compute_parent_department_manager")
    org_unit = fields.Many2one(related="employee_id.department_id", string="Cost Center")
    is_advance = fields.Boolean(string="Advance Required?")
    advance_amount = fields.Float(string="Advance Amount", digits='Product Price', track_visibility='onchange')
    is_manager = fields.Boolean(string='Is Manager', compute="_compute_is_manager")

    @api.depends('employee_id')
    def _compute_is_manager(self):
        manager = self.employee_id.parent_id.user_id if self.employee_id.parent_id else self.employee_id.user_id
        check_group = manager.user_has_groups('unity_expense.group_hr_expense_user_manager') or manager.user_has_groups('unity_expense.group_hr_expense_dept_manager') or manager.user_has_groups('unity_expense.group_hr_expense_manager')
        if check_group:
            self.is_manager = True
        else:
            self.is_manager = False

    def _get_parent_manager(self, employee_id):
        if not 'hr.department' in str(employee_id):
            if employee_id.department_id.parent_id:
                manager_name = employee_id.department_id.parent_id.manager_id.user_id
            else: 
                manager_name = employee_id.department_id.manager_id.user_id
            if employee_id.department_id.parent_id:
                return self._get_parent_manager(employee_id.department_id.parent_id)
        else:
            manager_name = employee_id.manager_id.user_id
            if employee_id.parent_id:
                return self._get_parent_manager(employee_id.parent_id)
        return manager_name

    @api.depends('employee_id')
    def _compute_parent_department_manager(self):
        for rec in self:
            parent_manager = self._get_parent_manager(rec.employee_id)
            rec.department_manager = parent_manager

    @api.depends('sheet_id', 'sheet_id.state')
    def _compute_state(self):
        for expense in self:
            if not expense.sheet_id or expense.sheet_id.state == 'draft':
                expense.state = "draft"
            elif expense.sheet_id.state == "cancel":
                expense.state = "refused"
            elif expense.sheet_id.state == "approve":
                expense.state = "approved"
            elif expense.sheet_id.state == "second_approve":
                expense.state = "second_approved"
            elif expense.sheet_id.state == "account_verified":
                expense.state = "account_verified"
            elif expense.sheet_id.state == "payment":
                expense.state = "payment"
            elif expense.sheet_id.state == "paid":
                expense.state = "paid"
            else:
                expense.state = "draft"

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.planned.expense'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.name:
                self.name = self.product_id.display_name or ''
            self.unit_amount = self.product_id.price_compute('standard_price')[self.product_id.id]
            self.product_uom_id = self.product_id.uom_id
            self.tax_ids = self.product_id.supplier_taxes_id
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            if account:
                self.account_id = account

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        if self.product_id and self.product_uom_id.category_id != self.product_id.uom_id.category_id:
            raise UserError(_('Selected Unit of Measure does not belong to the same category as the product Unit of Measure.'))

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    def unlink(self):
        for expense in self:
            if expense.state in ['second_approved', 'approved']:
                raise UserError(_('You cannot delete a posted or approved expense.'))
        return super(HrPlannedExpense, self).unlink()

    @api.model
    def get_empty_list_help(self, help_message):
        if help_message and "o_view_nocontent_smiling_face" not in help_message:
            use_mailgateway = self.env['ir.config_parameter'].sudo().get_param('hr_expense.use_mailgateway')
            alias_record = use_mailgateway and self.env.ref('hr_expense.mail_alias_expense') or False
            if alias_record and alias_record.alias_domain and alias_record.alias_name:
                link = "<a id='o_mail_test' href='mailto:%(email)s?subject=Lunch%%20with%%20customer%%3A%%20%%2412.32'>%(email)s</a>" % {
                    'email': '%s@%s' % (alias_record.alias_name, alias_record.alias_domain)
                }
                return '<p class="o_view_nocontent_smiling_face">%s</p><p class="oe_view_nocontent_alias">%s</p>' % (
                    _('Add a new expense,'),
                    _('or send receipts by email to %s.') % (link),)
        return super(HrPlannedExpense, self).get_empty_list_help(help_message)

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_view_sheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.planned.expense.sheet',
            'target': 'current',
            'res_id': self.sheet_id.id
        }

    def action_submit_expenses(self):
        if any(expense.state != 'draft' or expense.sheet_id for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report."))

        todo = self.filtered(lambda x: x.payment_mode=='own_account') or self.filtered(lambda x: x.payment_mode=='company_account')
        return {
            'name': _('New Expense Report'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.planned.expense.sheet',
            'target': 'current',
            'context': {
                'default_expense_line_ids': todo.ids,
                'default_employee_id': self[0].employee_id.id,
                'default_name': todo[0].name if len(todo) == 1 else ''
            }
        }

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.planned.expense'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.planned.expense', 'default_res_id': self.id}
        return res

    # ----------------------------------------
    # Business
    # ----------------------------------------

    def refuse_expense(self, reason):
        self.write({'is_refused': True})
        self.sheet_id.write({'state': 'cancel'})
        self.sheet_id.message_post_with_view('hr_expense.hr_expense_template_refuse_reason',
                                             values={'reason': reason, 'is_sheet': False, 'name': self.name})


class HrPlannedExpenseSheet(models.Model):
    _name = "hr.planned.expense.sheet"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Planned Expense Report"
    _order = "accounting_date desc, id desc"

    name = fields.Char('Expense Report Summary', required=True)
    expense_line_ids = fields.One2many('hr.planned.expense', 'sheet_id', string='Expense Lines', states={'approve': [('readonly', True)], 'second_approve': [('readonly', True)]}, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('second_approve', 'BU Approved'),
        ('account_verified', 'Account Verified'),
        ('payment', 'Payment Approved'),
        ('paid', 'Paid'),
        ('cancel', 'Refused')
    ], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='draft', required=True, help='Expense Report State')
    employee_id = fields.Many2one('hr.employee', string="e-Zestian", required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    address_id = fields.Many2one('res.partner', string="Employee Home Address")
    payment_mode = fields.Selection([("own_account", "Cash"), ("company_account", "Bank/Online")], related='expense_line_ids.payment_mode', default='own_account', readonly=True, string="Pay Through")
    user_id = fields.Many2one('res.users', 'Manager', readonly=True, copy=False, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    total_amount = fields.Monetary('Total Amount', compute='_compute_amount', store=True, digits='Product Price')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="expense_line_ids.currency_id", string='Currency', readonly=True, states={'draft': [('readonly', False)]})
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')
    accounting_date = fields.Date("Date")
    department_id = fields.Many2one('hr.department', string='Department')
    is_multiple_currency = fields.Boolean("Handle lines with different currencies", compute='_compute_is_multiple_currency')
    can_reset = fields.Boolean('Can Reset', compute='_compute_can_reset')
    department_manager = fields.Many2one(related="expense_line_ids.department_manager", string="Department Manager")
    org_unit = fields.Many2one(related="employee_id.department_id", string="Cost Center")
    bank_account = fields.Many2one(string='Bank Account', related="employee_id.bank_account_id")
    payroll_location = fields.Char(string='Expense Location', compute="_get_payroll_loc")
    submit_date = fields.Date('Submit Date')
    approve_date = fields.Date('Approve Date')
    second_approve_date = fields.Date('Second Approve Date')
    post_date = fields.Date('Post Date')
    manager_id = fields.Many2one(related="employee_id.parent_id")

    @api.depends('employee_id')
    def _get_payroll_loc(self):
        self.payroll_location = self.employee_id.payroll_loc.name

    @api.depends('expense_line_ids.unit_amount')
    def _compute_amount(self):
        for sheet in self:
            sheet.total_amount = sum(sheet.expense_line_ids.mapped('unit_amount'))

    def _compute_attachment_number(self):
        for sheet in self:
            sheet.attachment_number = sum(sheet.expense_line_ids.mapped('attachment_number'))

    @api.depends('expense_line_ids.currency_id')
    def _compute_is_multiple_currency(self):
        for sheet in self:
            sheet.is_multiple_currency = len(sheet.expense_line_ids.mapped('currency_id')) > 1

    def _compute_can_reset(self):
        is_expense_user = self.user_has_groups('hr_expense.group_hr_expense_user')
        for sheet in self:
            sheet.can_reset = is_expense_user if is_expense_user else sheet.employee_id.user_id == self.env.user

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.address_id = self.employee_id.sudo().address_home_id
        self.department_id = self.employee_id.department_id
        self.user_id = self.employee_id.expense_manager_id or self.employee_id.parent_id.user_id

    @api.constrains('expense_line_ids', 'employee_id')
    def _check_employee(self):
        for sheet in self:
            employee_ids = sheet.expense_line_ids.mapped('employee_id')
            if len(employee_ids) > 1 or (len(employee_ids) == 1 and employee_ids != sheet.employee_id):
                raise ValidationError(_('You cannot add expenses of another employee.'))

    @api.model
    def create(self, vals):
        sheet = super(HrPlannedExpenseSheet, self.with_context(mail_create_nosubscribe=True)).create(vals)
        sheet.activity_update()
        return sheet

    def unlink(self):
        for expense in self:
            if expense.state in ['second_approve']:
                raise UserError(_('You cannot delete a BU Approved expense.'))
        super(HrPlannedExpenseSheet, self).unlink()

    # --------------------------------------------
    # Mail Thread
    # --------------------------------------------

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'approve':
            return 'hr_expense.mt_expense_approved'
        if 'state' in init_values and self.state == 'second_approve':
            return 'unity_expense.mt_expense_second_approved'
        elif 'state' in init_values and self.state == 'cancel':
            return 'hr_expense.mt_expense_refused'
        return super(HrPlannedExpenseSheet, self)._track_subtype(init_values)

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        res = super(HrPlannedExpenseSheet, self)._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get('employee_id'):
            employee = self.env['hr.employee'].browse(updated_values['employee_id'])
            if employee.user_id:
                res.append((employee.user_id.partner_id.id, subtype_ids, False))
        return res

    # --------------------------------------------
    # Actions
    # --------------------------------------------

    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.planned.expense'), ('res_id', 'in', self.expense_line_ids.ids)]
        res['context'] = {
            'default_res_model': 'hr.planned.expense.sheet',
            'default_res_id': self.id,
            'create': False,
            'edit': False,
        }
        return res

    # --------------------------------------------
    # Business
    # --------------------------------------------

    def action_submit_sheet(self):
        self.write({'state': 'submit'})
        self.activity_update()

    def approve_expense_sheets(self):
        responsible_id = self.user_id.id or self.env.user.id
        for line in self.expense_line_ids:
            if line.is_bill_client == 'yes' and line.bill_as == False:
                raise UserError(_('Must enter Billed As from expense line'))
        if not self.user_has_groups('unity_expense.group_hr_expense_user_manager'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))

        elif self.user_has_groups('hr_expense.group_hr_expense_manager') or self.user_has_groups('unity_expense.group_hr_expense_user_manager'):
            current_managers = self.employee_id.parent_id.user_id
            if current_managers and self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own expenses"))
            if current_managers and not self.env.user in current_managers:
                raise UserError(_("You can only approve your department expenses"))

        self.write({'approve_date': fields.Date.today()})
        if self.department_manager.id == self.user_id.id:
            self.state = 'second_approve'
            self.filtered(lambda hol: hol.state == 'second_approve').activity_feedback(['unity_expense.mail_act_expense_second_approval'])
        else:
            self.write({'state': 'approve', 'user_id': responsible_id})
            self.activity_update()

    def action_second_approve(self):
        if not self.user_has_groups('unity_expense.group_hr_expense_dept_manager'):
            raise UserError(_("Only Managers can approve expenses"))
        elif self.user_has_groups('hr_expense.group_hr_expense_manager') or self.user_has_groups('unity_expense.group_hr_expense_dept_manager'):
            current_managers = self.department_manager

            if current_managers and self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own expenses"))

            if current_managers and not self.env.user in current_managers:
                raise UserError(_("You can only approve your department expenses"))

        responsible_id = self.user_id.id or self.env.user.id
        self.write({'state': 'second_approve', 'user_id': responsible_id, 'second_approve_date': fields.Date.today()})
        self.filtered(lambda hol: hol.state == 'second_approve').activity_feedback(['unity_expense.mail_act_expense_second_approval'])
        get_account1 = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_account1')
        get_account2 = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_account2')
        for expenses in self.filtered(lambda hol: hol.state == 'second_approve'):
            if get_account1:
                self.activity_schedule(
                    'unity_expense.mail_act_expense_account',
                    user_id=int(get_account1) or self.env.user.id)
            if get_account2:
                self.activity_schedule(
                    'unity_expense.mail_act_expense_account',
                    user_id=int(get_account2) or self.env.user.id)
        template = self.env.ref('unity_expense.send_expense_email')
        template_values = {
            'email_from': 'unity@e-zest.in',
            'email_to': 'accounting@e-zest.in',
            'email_cc': False,
            'auto_delete': False,
            'partner_to': False,
            'scheduled_date': False,
        }
        template.write(template_values)
        with self.env.cr.savepoint():
            template.with_context(lang=self.user_id.lang).sudo().send_mail(self.user_id.id or self.env.user.id, force_send=True, raise_exception=False)

    def action_account_verified(self):
        get_account1 = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_account1')
        get_account2 = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_account2')
        if not int(get_account1) == self.env.user.id or int(get_account2) == self.env.user.id:
            raise UserError(_("Only Account Team can approve expenses"))

        self.write({'state': 'account_verified', 'user_id': self.user_id.id or self.env.user.id})
        self.filtered(lambda hol: hol.state == 'account_verified').activity_feedback(['unity_expense.mail_act_expense_account'])
        get_responsible_payment = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_payment')
        for expenses in self.filtered(lambda hol: hol.state == 'account_verified'):
            self.activity_schedule(
                'unity_expense.mail_act_expense_payment',
                user_id=int(get_responsible_payment) or self.env.user.id)

    def action_payment_approval(self):
        get_responsible_payment = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_payment')
        if not int(get_responsible_payment) == self.env.user.id:
            raise UserError(_("Only Manager can approve expenses"))
        get_account1 = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_account1')
        get_account2 = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_account2')
        self.write({'state': 'payment', 'user_id': self.user_id.id or self.env.user.id})
        self.filtered(lambda hol: hol.state == 'payment').activity_feedback(['unity_expense.mail_act_expense_payment'])
        for expenses in self.filtered(lambda hol: hol.state == 'payment'):
            if get_account1:
                self.activity_schedule(
                    'unity_expense.mail_act_expense_account',
                    user_id=int(get_account1) or self.env.user.id)
            if get_account2:
                self.activity_schedule(
                    'unity_expense.mail_act_expense_account',
                    user_id=int(get_account2) or self.env.user.id)

    def action_register_payment(self):
        get_account1 = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_account1')
        get_account2 = self.env['ir.config_parameter'].sudo().get_param('unity_expense.responsible_account2')
        if not int(get_account1) == self.env.user.id or int(get_account2) == self.env.user.id:
            raise UserError(_("Only Account Team can approve expenses"))
        self.write({'state': 'paid', 'user_id': self.user_id.id or self.env.user.id})
        for rec in self.expense_line_ids:
            rec.write({'state':'paid'})
        self.filtered(lambda hol: hol.state == 'paid').activity_feedback(['unity_expense.mail_act_expense_account'])
        # import pdb; pdb.set_trace()
        # return {
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'hr.expense.sheet.register.payment.wizard',
        #     'target': 'new',
        #     'context': {
        #         'default_amount': self.total_amount, 
        #         'partner_id': self.address_id.id
        #     }
        # }

    @api.constrains('expense_line_ids')
    def _check_project(self):
        for sheet in self:
            project_codes = sheet.expense_line_ids.mapped('project_code')
            if len(project_codes) > 1 and len(set(project_codes)) != 1:
                raise UserError(_('You cannot add expenses of another project.'))
            currency = sheet.expense_line_ids.mapped('currency_id')
            if len(currency) > 1 and len(set(currency)) != 1:
                raise UserError(_('You cannot add expenses of multiple currency.'))

    def refuse_sheet(self, reason):
        if not self.user_has_groups('hr_expense.group_hr_expense_user'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id

            if self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot refuse your own expenses"))

            if not self.env.user in current_managers:
                raise UserError(_("You can only refuse your department expenses"))

        self.write({'state': 'cancel'})
        for sheet in self:
            sheet.message_post_with_view('hr_expense.hr_expense_template_refuse_reason', values={'reason': reason, 'is_sheet': True, 'name': self.name})
        self.activity_update()

    def reset_expense_sheets(self):
        if not self.can_reset:
            raise UserError(_("Only HR Officers or the concerned employee can reset to draft."))
        self.mapped('expense_line_ids').write({'is_refused': False})
        self.write({'state': 'draft'})
        self.activity_update()
        return True

    def _get_responsible_for_approval(self):
        if self.user_id:
            return self.user_id
        elif self.employee_id.parent_id.user_id:
            return self.employee_id.parent_id.user_id
        elif self.employee_id.department_id.manager_id.user_id:
            return self.employee_id.department_id.manager_id.user_id
        return self.env['res.users']

    def activity_update(self):
        for expense_report in self.filtered(lambda hol: hol.state == 'submit'):
            self.activity_schedule(
                'hr_expense.mail_act_expense_approval',
                user_id=expense_report.sudo()._get_responsible_for_approval().id or self.env.user.id)
        self.filtered(lambda hol: hol.state == 'approve').activity_feedback(['hr_expense.mail_act_expense_approval'])
        self.filtered(lambda hol: hol.state == 'cancel').activity_unlink(['hr_expense.mail_act_expense_approval'])
        for expense_report in self.filtered(lambda hol: hol.state == 'approve'):
            self.activity_schedule(
                'unity_expense.mail_act_expense_second_approval',
                user_id=self.department_manager.id or self.env.user.id)
        self.filtered(lambda hol: hol.state == 'second_approve').activity_feedback(['unity_expense.mail_act_expense_second_approval'])
        self.filtered(lambda hol: hol.state == 'cancel').activity_unlink(['unity_expense.mail_act_expense_second_approval'])

