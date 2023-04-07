# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class ProbationSurveyForm(models.Model):
    _name = 'hr.probation.survey'
    _description = 'Confirmation Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    def action_submit(self):
        self.show_button_manager = False
        self.show_button_hr = True
        if not (self.user_has_groups('hr.group_hr_user') or self.user_has_groups('hr_employee_updation.group_hr_conf_manager')):
            raise UserError(_("Only Managers and HR Officers can approve your confirmation"))
        elif self.user_has_groups('hr_employee_updation.group_hr_conf_manager') or self.user_has_groups('hr.group_hr_user'):
            current_managers = self.employee_id.parent_id.user_id
            if current_managers and self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own confirmation"))

        if not self.question12:
            raise UserError(_("Fill Conduct at Workplace"))
        if not self.question13:
            raise UserError(_("Fill Teamwork"))
        if not self.question14:
            raise UserError(_("Fill Dedication"))
        if not self.question15:
            raise UserError(_("Fill Logical and Analytical Skills"))
        if not self.question16:
            raise UserError(_("Fill Technical Work"))
        if not self.question17:
            raise UserError(_("Fill Competency"))
        if not self.question18:
            raise UserError(_("Fill Participation in HR Activities"))
        if not self.question10:
            raise UserError(_("Fill Probation Status"))

        if self.question10 == 'extended':
            self.sudo().write({
                'state': 'submit',
                'confirmation_status': 'extended',
                'is_extend': True,
                'extend_reason': self.question2,
            })
        elif self.question10 == 'confirmed':
            self.sudo().write({
                'state': 'submit',
                'confirmation_status': 'confirmed'
            })
        elif self.question10 == 'cancelled':
            self.sudo().write({
                'state': 'cancel'
            })
            self.employee_id.sudo().write({
                'confirmation_status': self.confirmation_status
            })

        self.filtered(lambda hol: hol.state == 'submit').activity_feedback(['hr_employee_updation.act_mail_confirmation'])
        work_location = self.employee_id.responsible_hr.related_hr
        if work_location:
            for conf_form in self.filtered(lambda hol: hol.state == 'submit'):
                for hr in work_location:
                    conf_form.activity_schedule(
                        'hr_employee_updation.act_conf_email_hr', #send confirmation form to hr after submitting from manager
                        user_id=hr.user_id.id or self.env.user.id)
        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Successfull! Confirmation Evaluation Form is submitted.'),
                'img_url': '/web/image/%s/%s/image_1024' % (self.employee_id._name, self.employee_id.id) if self.employee_id.image_1024 else '/web/static/src/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def action_hr_submit(self):
        self.show_button_hr = False
        current_user = self.env.user.employee_id
        responsible_hr = self.employee_id.responsible_hr
        if not (self.user_has_groups('hr.group_hr_user') or self.user_has_groups('hr_employee_updation.group_hr_conf_manager')):
            raise UserError(_("Only Managers and HR Officers can approve your confirmation"))
        elif responsible_hr and current_user.id not in responsible_hr.related_hr.ids:
            raise UserError(_("Only responsible HR can approve"))
        if self.confirmation_status == 'in_progress':
            raise UserError(_("You need to change confirmation status"))
        elif self.confirmation_status == 'extended':
            if not self.is_extend:
                raise UserError(_("Check the Is Confirmation Extend"))
            if self.is_extend and not self.extend_period: 
                raise UserError(_("Fill extend period"))
            self.sudo().write({'state': 'extend'})
            self.employee_id.sudo().write({
                'is_extend': self.is_extend,
                'extend_period': self.extend_period,
                'extend_reason': self.extend_reason,
                'confirmation_status': self.confirmation_status,
                'confirmation_checklist': [(6, 0, self.confirmation_checklist.ids)]
            })
            self.show_button_hr = True
            # email send to user for extended
            msg_body = '<p>Dear {0}</p>\
                    <br/>\
                    <p>Your confirmation period is extended by {1} days.\
                    <br/>\
                    <p>Extend Reason: {2}</p>\
                    <br/><br/><br/>\
                    Thanks,\
                    <br/>\
                    Team Unity\
                    <p><br></p>'.format(self.employee_id.name, str(self.extend_period.split('+')[-1]), self.extend_reason)
            self.env['mail.mail'].create({
                'subject': 'Extended Probation Period for %s' % (self.employee_id.name),
                'email_from': 'unity@e-zest.in',
                'email_to': self.employee_id.work_email or False,
                'email_cc': 'unity@e-zest.in,hrd@e-zest.in',
                'auto_delete': False,
                'body_html': msg_body,
                'scheduled_date': False,
            }).sudo().send()
        elif self.confirmation_status == 'confirmed':
            # checklist = self.env['employee.checklist'].search_count([('document_type', '=', 'confirmation')])
            # emp_checklist = self.confirmation_checklist
            # if len(emp_checklist) != checklist:
            #     raise UserError(_("Confirmation checklist not marked"))
            self.sudo().write({'state': 'confirm'})
            self.employee_id.sudo().write({
                'confirmation_status': self.confirmation_status,
                'notice_period': 60,
                'confirmation_checklist': [(6, 0, self.confirmation_checklist.ids)]
            })
            template = self.env.ref('hr_employee_updation.send_confirm_period_email_user')
            # attachment = {'name': ATTACHMENT_NAME + '.pdf',
            #             'description': ATTACHMENT_NAME,
            #             'type': 'binary',
            #             'datas': b64_pdf,
            #             'store_fname': ATTACHMENT_NAME,
            #             'res_model': self._name,
            #             'res_id': self.id,
            #             'mimetype': 'application/x-pdf'}
            template_values = {
                'email_from': 'unity@e-zest.in',
                'email_to': self.employee_id.user_id.login or False,
                'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
                'auto_delete': False,
                'partner_to': False,
                'scheduled_date': False,
                # 'attachment_ids': [(0, 0, attachment)]
            }
            template.write(template_values)
            if not self.employee_id.user_id.login:
                raise UserError(_("Cannot send email: user %s has no email address.") % self.employee_id.user_id.name)
            with self.env.cr.savepoint():
                template.with_context(lang=self.employee_id.user_id.lang).send_mail(self.employee_id.user_id.id, force_send=True, raise_exception=False)
        elif self.confirmation_status == 'due':
            self.employee_id.sudo().write({
                'confirmation_status': self.confirmation_status,
                'confirmation_checklist': [(6, 0, self.confirmation_checklist.ids)]
            })
        if self.confirmation_checklist: 
            self.employee_id.sudo().write({'confirmation_checklist':[(6,0,self.confirmation_checklist.ids)]})

        self.filtered(lambda hol: hol.state == 'confirm').activity_feedback(['hr_employee_updation.act_conf_email_hr'])
        self.filtered(lambda hol: hol.state == 'extend').activity_feedback(['hr_employee_updation.act_conf_email_hr'])
        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Successfully! HR Evaluation is submitted.'),
                'img_url': '/web/image/%s/%s/image_1024' % (self.employee_id._name, self.employee_id.id) if self.employee_id.image_1024 else '/web/static/src/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def action_cancel(self):
        if self.env.user.employee_id.id == self.employee_id.id:
            raise UserError(_("You cannot cancel your own confirmation"))
        self.sudo().write({'state':'cancel'})
        activity = self.env['mail.activity'].search([('res_model', '=', 'hr.probation.survey'), ('res_id', '=', self.id)])
        if activity:
            activity.sudo().unlink()

    @api.model
    def create(self, vals):
        res = super(ProbationSurveyForm, self).create(vals)
        if res.employee_id.joining_date:
            res.date = res.employee_id.joining_date + timedelta(days=res.employee_id.confirmation_period)
        res.activity_update()
        return res

    # def write(self, vals):
    #     res = super(ProbationSurveyForm, self).write(vals)
    #     employee = vals.get('employee_id')
    #     if employee:
    #         employee_id = self.env['hr.employee'].search([('id','=',employee)])
    #         self.date = (employee_id.joining_date + timedelta(days=employee_id.confirmation_period)) if employee_id.joining_date else ''
    #     return res

    def _get_responsible_for_conf_submit(self):
        return self.employee_id.parent_id.user_id or self.env.user

    def activity_update(self):
        for expense_report in self.filtered(lambda hol: hol.state == 'draft'):
            if expense_report.employee_id.gender == 'female':
                gender = 'her'
            else:
                gender = 'his'
            note = '<p>Dear {8}</p>\
                    <p>{0} has completed {7} probation period, kindly evaluate {7} performance and submit the confirmation feedback sheet.\
                    <br/><br/>\
                    <p>PFB the details:</p>\
                    {0} - {1}<br/>\
                    Designation - {2}<br/>\
                    Date of Joining - {3}<br/>\
                    Probation Period - {4}<br/>\
                    <br/><br/>\
                    <p>You are requested to submit the same on or before probation period completed.</p>\
                    <p>Kindly click on \
                    <a href="/web#id={5}&amp;model={6}&amp;view_type=form"\
                    target="_blank" style="background-color: #875A7B; padding: 8px 16px 8px 16px;\
                    text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">View Confirmation Evaluation Form</a> for further process.</p>\
                    <br/><br/><br/>\
                    Thanks,\
                    <br/>\
                    Team Unity\
                    <p><br></p>'.format(expense_report.employee_id.name, expense_report.employee_id.identification_id,
                    expense_report.employee_id.job_id.name, expense_report.employee_id.joining_date.strftime('%d-%b-%Y'),
                    expense_report.employee_id.confirmation_period, expense_report.id, expense_report._name, gender, expense_report.employee_id.parent_id.name)
            subject = 'Probation period of %s is going to complete' % (expense_report.employee_id.name)
            self.activity_schedule(
                'hr_employee_updation.act_mail_confirmation',
                user_id=expense_report.sudo()._get_responsible_for_conf_submit().id or self.env.user.id, note=note, summary=subject)
        for extend_probation in self.filtered(lambda hol: hol.state == 'extend'):
            if extend_probation.employee_id.gender == 'female':
                gender = 'her'
            else:
                gender = 'his'
            note = '<p>Dear {0}</p>\
                    <p>The confirmation for {1}, was extended and is now completed, kindly re-evaluate {2} performance and submit the confirmation evaluation sheet.\
                    <br/><br/><br/>\
                    Thanks,\
                    <br/>\
                    Team Unity\
                    <p><br></p>'.format(extend_probation.employee_id.parent_id.name, extend_probation.employee_id.name, gender)
            subject = 'Confirmation re-evaluation form for {}'.format(extend_probation.employee_id.name)
            self.activity_schedule(
                'hr_employee_updation.act_mail_confirmation',
                user_id=extend_probation.sudo()._get_responsible_for_conf_submit().id or self.env.user.id, note=note, summary=subject)

    employee_id = fields.Many2one('hr.employee', string='e-Zestian Name')
    identification_id = fields.Char(related='employee_id.identification_id', string='e-Zestian ID')
    manager_id = fields.Many2one(related='employee_id.parent_id', string='Manager', tracking=True)
    job_id = fields.Many2one(related='employee_id.job_id', string='Designation', tracking=True)
    employee_category = fields.Many2one(related='employee_id.employee_category', track_visibility="onchange", string="Team Member Category")
    department_id = fields.Many2one(related='employee_id.department_id', string='Department', tracking=True)
    responsible_hr = fields.Many2one(related='employee_id.responsible_hr', string='Responsible HR', tracking=True)
    state = fields.Selection([('draft', 'Evaluation requested'),('submit', 'Evaluation submitted'), ('confirm', 'Confirmed'), ('extend', 'Extended'), ('cancel', 'Cancelled')], default='draft', string='State', tracking=True)

    confirmation_checklist = fields.Many2many('employee.checklist', string='Confirmation Checklist', tracking=True)
    joining_date = fields.Date(related='employee_id.joining_date', string="Joining Date")
    confirmation_status = fields.Selection([('due','Due'),('in_progress','In Progress'),('extended','Extend'),('confirmed','Confirmed')], track_visibility="onchange")
    is_extend = fields.Boolean(string="Is Confirmation Extend", tracking=True)
    extend_period = fields.Char(string='Extended Period', tracking=True)
    extend_reason = fields.Text(string='Extend Reason', tracking=True)
    show_button_manager = fields.Boolean(string="Show Button Manager?")
    show_button_hr = fields.Boolean(string="Show Button HR?")
    # designation = fields.Char(related='employee_id.job_title', string='e-Zestian ID')
    date = fields.Date(string='Confirmation Due Date', tracking=True)
    question1 = fields.Text(string='Question 1', tracking=True)
    question2 = fields.Text(string='Question 2', tracking=True)
    question3 = fields.Text(string='Question 3', tracking=True)
    question4 = fields.Text(string='Question 4', tracking=True)
    question5 = fields.Text(string='Question 5', tracking=True)
    question6 = fields.Text(string='Question 6', tracking=True)
    question7 = fields.Text(string='Question 7', tracking=True)
    question8 = fields.Text(string='Question 8', tracking=True)
    question9 = fields.Text(string='Question 9', tracking=True)
    question21 = fields.Text(string='Question 10', tracking=True)
    question22 = fields.Text(string='Question 11', tracking=True)
    question10 = fields.Selection([('confirmed', 'To be Confirmed'),('extended', 'To be Extended'),('cancelled', 'To be Cancelled')], string='Probation Status', tracking=True)
    question11 = fields.Selection([('1', '1 Month'),('2', '2 Month'),('3', '3 Month')], string='Extended for', tracking=True)
    question12 = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'), ('satisfactory', 'Satisfactory'), ('average', 'Average'), ('unsatisfactory', 'Unsatisfactory')], string='Conduct at Workplace', tracking=True)
    question13 = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'), ('satisfactory', 'Satisfactory'), ('average', 'Average'), ('unsatisfactory', 'Unsatisfactory')], string='Teamwork', tracking=True)
    question14 = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'), ('satisfactory', 'Satisfactory'), ('average', 'Average'), ('unsatisfactory', 'Unsatisfactory')], string='Dedication', tracking=True)
    question15 = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'), ('satisfactory', 'Satisfactory'), ('average', 'Average'), ('unsatisfactory', 'Unsatisfactory')], string='Logical and Analytical Skills', tracking=True)
    question16 = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'), ('satisfactory', 'Satisfactory'), ('average', 'Average'), ('unsatisfactory', 'Unsatisfactory')], string='Technical Work', tracking=True)
    question17 = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'), ('satisfactory', 'Satisfactory'), ('average', 'Average'), ('unsatisfactory', 'Unsatisfactory')], string='Competency', tracking=True)
    question18 = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'), ('satisfactory', 'Satisfactory'), ('average', 'Average'), ('unsatisfactory', 'Unsatisfactory')], string='Participation in HR Activities', tracking=True)
    question19 = fields.Selection([('0', '0'),('1','1'),('2', '2'),('3', '3'),('4', '4'),('5', '5')], string="OLIVZ Rating", tracking=True)
    question20 = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'), ('satisfactory', 'Satisfactory'), ('average', 'Average'), ('unsatisfactory', 'Unsatisfactory')], string='Question 2', tracking=True)
    checklist_id = fields.Many2one('employee.checklist', string='Checklist Name', tracking=True)
    question23 = fields.Selection([('0', '0'),('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5')], tracking=True)
    question24 = fields.Selection([('0', '0'),('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5')], tracking=True)
    question25 = fields.Selection([('0', '0'),('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5')], tracking=True)
    question26 = fields.Selection([('0', '0'),('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5')], tracking=True)
    image = fields.Binary(related="employee_id.image_1920")
    image_medium = fields.Binary(related="employee_id.image_1024")
    image_small = fields.Binary(related="employee_id.image_256")
    active = fields.Boolean('Active', default=True, store=True, readonly=False)
