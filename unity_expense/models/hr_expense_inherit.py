# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError


class HrExpenseInherit(models.Model):
    _inherit = 'hr.expense'

    payment_mode = fields.Selection([
        ("own_account", "Cash"),
        ("company_account", "Bank/Online")
    ], default='own_account', states={'done': [('readonly', True)], 'approved': [('readonly', True)], 'reported': [('readonly', True)]}, string="Paid Through")
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('reported', 'Submitted'),
        ('approved', 'Approved'),
        ('second_approved', 'BU Approved'),
        ('done', 'Paid'),
        ('refused', 'Refused')
    ], compute='_compute_state', track_visibility='onchange', string='Status', copy=False, index=True, readonly=True, store=True, help="Status of the expense.")
    unit_amount = fields.Float("Unit Price", required=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, digits='Product Price', track_visibility='onchange')
    reference = fields.Char("Bill Reference", track_visibility='onchange')
    date = fields.Date(readonly=True, track_visibility='onchange', states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, default=fields.Date.context_today, string="Date")
    project_id = fields.Many2one('project.project', readonly=False, string='Project Name', track_visibility='onchange',)
    project_code = fields.Char(string='Whizible ID', track_visibility='onchange', readonly=False)
    is_bill_client = fields.Selection([('yes','YES'),('no','No')], default="no", required=1, string='Is Billable to Client', track_visibility='onchange',)
    bill_as = fields.Selection([('debit_note', 'Debit Note'), ('sale_invoice', 'Sales Invoice No.')], string='To be Billed As', track_visibility='onchange',)
    debit_note = fields.Char(string='Debit No./Sales Invoice No.', track_visibility='onchange')
    department_manager = fields.Many2one('res.users', string="Department Manager", compute="_compute_parent_department_manager")
    planned_expense_id = fields.Many2one('hr.planned.expense', string="Related Planned Expense", readonly=False)
    is_same_planned_amount = fields.Boolean('Is Same Amount as Planned Amount')
    org_unit = fields.Many2one(related="employee_id.department_id", string="Cost Center")
    is_advance = fields.Boolean(string="Advance Required?",)
    advance_amount = fields.Float(related="planned_expense_id.advance_amount", string="Advance Amount")
    is_manager = fields.Boolean(string='Is Manager', compute="_compute_is_manager")

    @api.depends('employee_id')
    def _compute_is_manager(self):
        manager = self.employee_id.parent_id.user_id if self.employee_id.parent_id else self.employee_id.user_id
        check_group = manager.user_has_groups('unity_expense.group_hr_expense_user_manager') or manager.user_has_groups('unity_expense.group_hr_expense_dept_manager') or manager.user_has_groups('unity_expense.group_hr_expense_manager')
        if check_group:
            self.is_manager = True

    @api.onchange('planned_expense_id')
    def _onchange_planned_expense(self):
        if self.planned_expense_id:
            self.name = self.planned_expense_id.name
            self.product_id = self.planned_expense_id.product_id
            self.unit_amount = self.planned_expense_id.unit_amount
            self.project_id = self.planned_expense_id.project_id
            self.project_code = self.planned_expense_id.project_code
            self.description = self.planned_expense_id.description
            self.is_bill_client = self.planned_expense_id.is_bill_client
            self.currency_id = self.planned_expense_id.currency_id
            self.org_unit = self.planned_expense_id.org_unit
            if self.planned_expense_id.is_bill_client == 'yes':
                self.bill_as = self.planned_expense_id.bill_as
            else:
                self.bill_as = ''
        else:
            self.name =''
            self.product_id =''
            self.unit_amount =''
            self.project_id =''
            self.project_code =''
            self.description = self.planned_expense_id.description
            self.is_bill_client =''
            self.currency_id =''
            self.org_unit =''
            self.bill_as =''


    @api.model
    def create(self, vals):
        if vals.get('planned_expense_id'):
            planned_expense = self.env['hr.planned.expense'].browse(vals.get('planned_expense_id'))
            if vals.get('unit_amount') > planned_expense.unit_amount:
                vals['is_same_planned_amount'] = False
            else:
                vals['is_same_planned_amount'] = True
        sheet = super(HrExpenseInherit, self).create(vals)
        return sheet

    def write(self, vals):
        if vals.get('planned_expense_id') or vals.get('unit_amount'):
            planned_expense_amount = self.env['hr.planned.expense'].browse(vals.get('planned_expense_id')) if vals.get('planned_expense_id') else self.planned_expense_id
            unit_amount = vals.get('unit_amount') or self.unit_amount
            if unit_amount > planned_expense_amount.unit_amount:
                self.is_same_planned_amount = False
            else:
                self.is_same_planned_amount = True
        sheet = super(HrExpenseInherit, self).write(vals)
        return sheet

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

    @api.depends('sheet_id', 'sheet_id.account_move_id', 'sheet_id.state')
    def _compute_state(self):
        res = super(HrExpenseInherit, self)._compute_state()
        for expense in self:
            if expense.sheet_id.state == "second_approve":
                expense.state = "second_approved"
        return res


class HrExpenseSheetInherit(models.Model):
    _inherit = "hr.expense.sheet"

    @api.depends('employee_id')
    def _get_payroll_loc(self):
        self.payroll_location = self.employee_id.payroll_loc.name

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('second_approve', 'BU Approved'),
        ('post', 'Posted'),
        ('done', 'Paid'),
        ('cancel', 'Refused')
    ], string='Status', index=True, track_visibility='onchange', readonly=True, copy=False, default='draft', required=True, help='Expense Report State')
    department_manager = fields.Many2one(related="expense_line_ids.department_manager", string="Department Manager")
    bank_account = fields.Many2one(string='Bank Account', related="employee_id.bank_account_id")
    payroll_location = fields.Char(string='Expense Location', compute="_get_payroll_loc")
    submit_date = fields.Date('Submit Date')
    approve_date = fields.Date('Approve Date')
    second_approve_date = fields.Date('Second Approve Date')
    post_date = fields.Date('Post Date')
    org_unit = fields.Many2one(related="employee_id.department_id", string="Cost Center")
    check_planned_amount = fields.Boolean('Is Same as Planned Amount')

    def action_sheet_move_create(self):
        self.write({'post_date': fields.Date.today()})
        return super(HrExpenseSheetInherit, self).action_sheet_move_create()

    def _get_responsible_for_second_approval(self):
        if self.department_manager:
            return self.department_manager

    def action_submit_sheet(self):
        if self.expense_line_ids:
            get_total_advance = []
            for rec in self.expense_line_ids:
                get_total_advance.append(rec.advance_amount)
            if self.total_amount > sum(get_total_advance):
                self.write({'check_planned_amount':False})
            else:
                self.write({'check_planned_amount':True})
        if self.check_planned_amount:
            self.write({'state': 'second_approve', 'submit_date': fields.Date.today(),'user_id': self.department_manager.id, 'second_approve_date': fields.Date.today()})
            self.filtered(lambda hol: hol.state == 'second_approve').activity_feedback(['unity_expense.mail_act_expense_second_approval'])
            if self.expense_line_ids:
                for rec in self.expense_line_ids:
                    if rec.planned_expense_id:
                        rec.planned_expense_id.write({'state':'done'})
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
        else:
            self.write({'state': 'submit', 'submit_date': fields.Date.today()})
            self.activity_update()

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'second_approve':
            return 'unity_expense.mt_expense_second_approved'
        return super(HrExpenseSheetInherit, self)._track_subtype(init_values)

    def approve_expense_sheets(self):
        for line in self.expense_line_ids:
            if line.is_bill_client == 'yes' and line.bill_as == False:
                raise UserError(_('Must enter Billed As from expense line'))
        if not self.user_has_groups('unity_expense.group_hr_expense_user_manager'):
            raise UserError(_("Only Managers can approve expenses"))

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
        res =  super(HrExpenseSheetInherit, self).approve_expense_sheets()
        return res

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
        if self.expense_line_ids:
            for rec in self.expense_line_ids:
                if rec.planned_expense_id:
                    rec.planned_expense_id.write({'state':'done'})
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

    def activity_update(self):
        super(HrExpenseSheetInherit, self).activity_update()
        for expense_report in self.filtered(lambda hol: hol.state == 'approve'):
            self.activity_schedule(
                'unity_expense.mail_act_expense_second_approval',
                user_id=self.department_manager.id or self.env.user.id)
        self.filtered(lambda hol: hol.state == 'second_approve').activity_feedback(['unity_expense.mail_act_expense_second_approval'])
        self.filtered(lambda hol: hol.state == 'cancel').activity_unlink(['unity_expense.mail_act_expense_second_approval'])

    @api.constrains('expense_line_ids')
    def _check_project(self):
        for sheet in self:
            project_codes = sheet.expense_line_ids.mapped('project_code')
            if len(project_codes) > 1 and len(set(project_codes)) != 1:
                raise UserError(_('You cannot add expenses of another project.'))
            # planned_expense = sheet.expense_line_ids.mapped('planned_expense_id')
            # if len(planned_expense) > 1 and len(set(planned_expense)) != 1:
            #     raise 
            currency = sheet.expense_line_ids.mapped('currency_id')
            if len(currency) > 1 and len(set(currency)) != 1:
                raise UserError(_('You cannot add multiple currency expenses.'))
