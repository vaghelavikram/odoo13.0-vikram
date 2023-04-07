# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError

# import datetime
import calendar
import base64
from random import choice
from string import digits

GENDER_SELECTION = [('male', 'Male'),
                    ('female', 'Female'),
                    ('other', 'Other')]


class HrEmployeeContractName(models.Model):
    """This class is to add emergency contact table"""

    _name = 'hr.emergency.contact'
    _description = 'HR Emergency Contact'

    relation = fields.Char(string='Contact Name', help='Contact Name')
    number = fields.Char(string='Contact Number', help='Contact Number')
    employee_obj = fields.Many2one('hr.employee', "e-Zestian Object")
    relationship = fields.Selection([('father', 'Father'),
                                    ('mother', 'Mother'),
                                    ('daughter', 'Daughter'),
                                    ('son', 'Son'),
                                    ('wife', 'Wife'),
                                    ('husband', 'Husband'),
                                    ('brother', 'Brother'),
                                    ('sister', 'Sister')], string='Relationship',
                                    help='Relationship with employee')


class HrEmployeeFamilyInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.family'
    _description = 'HR Employee Family'

    member_name = fields.Char(string='Name', related='employee_ref.name', store=True)
    employee_ref = fields.Many2one('hr.employee', string="Is Employee",
                                   help='If family member currently is an employee of same company, '
                                        'then please tick this field')
    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee',
                                  invisible=1)
    relation = fields.Selection([('father', 'Father'),
                                 ('mother', 'Mother'),
                                 ('daughter', 'Daughter'),
                                 ('son', 'Son'),
                                 ('wife', 'Wife')], string='Relationship', help='Relation with employee')
    member_contact = fields.Char(string='Contact No', related='employee_ref.personal_mobile', store=True)


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
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)


class HrEmployeeDeptMov(models.Model):
    _name = 'hr.emp.dept.move'
    _description = 'HR Employee Department Movement'

    @api.depends('employee_id')
    def _compute_max_date(self):
        for rec in self:
            max_date = max([d.mov_date for d in self.search([('employee_id', '=', rec.employee_id.id)]) if d.mov_date])
            if max_date == rec.mov_date:
                rec.is_max_date = True
            else:
                rec.is_max_date = False

    prev_dept_id = fields.Many2one('hr.department', string="Last Department")
    current_dept_id = fields.Many2one('hr.department', string="Current Department")
    mov_date = fields.Date(string="Movement Date")
    employee_id = fields.Many2one('hr.employee', string="e-Zestian")
    company_id = fields.Many2one(related="employee_id.company_id", string="Company", store=True)
    last_project_id = fields.Many2one('project.project', string="Last Project")
    current_project_id = fields.Many2one('project.project', string="Current Project")
    manager_id = fields.Many2one('hr.employee', string="Manager")
    is_max_date = fields.Boolean(string="Is Max Date", compute='_compute_max_date')


class DepartmentInherit(models.Model):
    _inherit = 'hr.department'

    custom_manager_id = fields.Many2one('hr.employee', string="Custom Manager")


class ResPartnerBankInherit(models.Model):
    _inherit = "res.partner.bank"

    @api.model
    def create(self, vals):
        acc_number = vals.get('acc_number')
        if not acc_number.isdigit():
            raise UserError(_("In account number fill numeric value only."))
        res = super(ResPartnerBankInherit, self).create(vals)
        return res

    loc_bank_id = fields.Many2one('hr.location.work', string="Work Location")


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Team Member'

    def name_get(self):
        res = []
        for emp in self:
            if self._context.get('show_detail'):
                skill = emp.skills.name if emp.skills else False
                allocate = emp.allocate and emp.allocate or False
                project_assign_till = emp.project_assign_till and emp.project_assign_till.strftime('%d-%b-%Y') or False
                total_billability = emp.total_billability and emp.total_billability or 0
                total_exp = emp.total_exp and emp.total_exp or 0.0
                c_name = emp.consultancy_name.name if emp.consultancy_name else ''
                if emp.employee_category.name == 'Contractor':
                    name = emp.name + ' (' + 'Skills-' + str(skill) + ', ' + \
                            'Allocate-' + str(allocate) + '%' + ', ' + \
                            'Assign Till-' + str(project_assign_till) + ', ' + \
                            'Total Billability-' + str(total_billability) +'%'+ ', ' +  \
                            'Total Exp-' + str(total_exp) + \
                            'Consultancy-' + str(c_name) + ')'
                else:
                    name = emp.name + ' (' + 'Skills-' + str(skill) + ', ' + \
                            'Allocate-' + str(allocate) + '%' + ', ' + \
                            'Assign Till-' + str(project_assign_till) + ', ' + \
                            'Total Billability-' + str(total_billability) +'%'+ ', ' +  \
                            'Total Exp-' + str(total_exp) + ')'
                res.append((emp.id, name))
            else:
                res.append((emp.id, emp.name))
        if self._context.get('show_inactive_user'):
            res = []
            self._cr.execute('''SELECT id, name, identification_id FROM hr_employee''')
            all_emp = self._cr.fetchall()
            for rec in all_emp:
                if rec and rec[1] and rec[2]:
                    name = rec[1] + '-' + rec[2]
                else:
                    name = rec[1]
                res.append((rec[0], name))
        return res

    # def toggle_active(self):
    #     res = super(HrEmployee, self).toggle_active()
    #     self.user_id.sudo().write({'active': False})
    #     self.user_id.partner_id.write({'active': False})
    #     return res

    def toggle_active(self):
        res = super(HrEmployee, self).toggle_active()
        applicant1 = self.env['hr.applicant'].sudo().search([('feedback_technical1', 'in', self.id)])
        applicant2 = self.env['hr.applicant'].sudo().search([('feedback_technical2', 'in', self.id)])
        applicant3 = self.env['hr.applicant'].sudo().search([('feedback_technical3', 'in', self.id)])
        for rec in applicant1:
            rec.sudo().feedback_technical1_inactive = self.id
        for rec in applicant2:
            rec.sudo().feedback_technical2_inactive = self.id
        for rec in applicant3:
            rec.sudo().feedback_technical3_inactive = self.id
        # when archive employee
        if res:
            self.user_id.sudo().write({'active': False})
            self.user_id.partner_id.sudo().write({'active': False})
        # when unarchive employee
        if not res:
            self.user_id.sudo().write({'active': True})
            self.user_id.partner_id.sudo().write({'active': True})
            employee_exit = self.env['hr.exit.process'].sudo().search([('employee_id', '=', self.id)])
            if employee_exit and employee_exit.employee_id and employee_exit.employee_id.employee_category.name in ['Contractor', 'Intern']:
                employee_exit.active = False
                if employee_exit.employee_id.exit_date:
                    employee_exit.employee_id.exit_date = False
        return res

    def _get_probation_form(self, employees):
        survey_days = self.env['ir.config_parameter'].sudo().get_param('hr_employee_updation.survey_days')
        today_date = datetime.today().date()
        for employee in employees:
            existing_survey = self.env['hr.probation.survey'].search([('employee_id','=',employee.id)])
            if employee.confirmation_status != 'confirmed' and employee.joining_date and not employee.resign_date:
                join_date = employee.joining_date
                confrm_period = employee.confirmation_period
                confirm_date = join_date + timedelta(days=confrm_period)
                confirm_date_extend = False
                if not employee.is_extend:
                    survey_date = join_date + timedelta(days=confrm_period - (int(survey_days) or 10))
                elif employee.is_extend:
                    extend_period_sum = sum([int(i) for i in employee.extend_period.split('+')])
                    extend_confirm_period = confrm_period + extend_period_sum
                    survey_date = join_date + timedelta(days=extend_confirm_period - (int(survey_days) or 10))
                    if today_date == confirm_date or (today_date == confirm_date_extend and employee.confirmation_status == 'extended'):
                        # if HR not confirm in time then again same mail sended to user for extended 
                        # print("send email to user that your probation is extend with extend_period .........................")
                        template = self.env.ref('hr_employee_updation.send_extend_period_email')
                        template_values = {
                            'email_to': employee.user_id.login or False,
                            'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
                            'email_from': 'unity@e-zest.in',
                            'auto_delete': False,
                            'partner_to': False,
                            'scheduled_date': False,
                        }
                        template.write(template_values)
                        if not employee.user_id.login:
                            raise UserError(_("Cannot send email: user %s has no email address.") % employee.user_id.name)
                        with self.env.cr.savepoint():
                            template.with_context(lang=employee.user_id.lang).send_mail(employee.user_id.id, force_send=True, raise_exception=False)

                        # user_extend_days = int(employee.extend_period.split('+')[-2]) or int(employee.extend_period)
                        # user_mail_extend_days = int(employee.extend_period.split('+')[-1])
                        # confirm_date_extend = join_date + timedelta(days=confrm_period + user_extend_days)
                    elif existing_survey and (today_date == survey_date) and employee.confirmation_status == "extended":
                        existing_survey.show_button_manager = True
                        if self.is_extend:
                            existing_survey.sudo().write({
                                'is_extend': True,
                                'extend_period': self.extend_period,
                                'extend_reason': self.extend_reason
                            })
                        existing_survey.activity_update()
                        login = employee.responsible_hr.related_hr[0].work_email if employee.responsible_hr else False
                        # login_list =[i.work_email for i in employee.responsible_hr.related_hr if employee.responsible_hr]
                        template = self.env.ref('hr_employee_updation.send_confirm_due_email_hr')
                        template_values = {
                            # 'email_to': ", ".join((x) for x in login_list) or False,
                            'email_to': login or False,
                            'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
                            'email_from': 'unity@e-zest.in',
                            'auto_delete': False,
                            'partner_to': False,
                            'scheduled_date': False,
                        }
                        template.write(template_values)
                        with self.env.cr.savepoint():
                            template.with_context(lang=employee.user_id.lang).send_mail(employee.user_id.id, force_send=True, raise_exception=False)

                        # template = self.env.ref('hr_employeeoyee_updation.send_extend_notification_manager')
                        # login_list =[i.work_email for i in employee.responsible_hr.related_hr if employee.responsible_hr]
                        # login_list.append('hrd@e-zest.in')
                        # login_list.append('unity@-ezest.in')
                        # template_values = {
                        #     'email_to': employee.parent_id.user_id.login,
                        #     'email_cc': ", ".join((x) for x in login_list),
                        #     'auto_delete': False,
                        #     'partner_to': False,
                        #     'scheduled_date': False,
                        # }
                        # template.write(template_values)
                        # if not employee.user_id.login:
                        #     raise UserError(_("Cannot send email: user %s has no email address.") % employee.user_id.name)
                        # with self.env.cr.savepoint():
                        #     template.with_context(lang=employee.user_id.lang).send_mail(employee.user_id.id, force_send=True, raise_exception=False)
                if not existing_survey and (today_date == survey_date or survey_date < today_date) and employee.confirmation_status != "confirmed":
                    employee.confirmation_status = "in_progress"
                    # print("send email manager for survey.....")
                    checklist = self.env['employee.checklist'].search([('name', '=', 'Confirmation Evaluation Form')])
                    survey = self.env['hr.probation.survey'].create({
                        'employee_id': employee.id,
                        'checklist_id': checklist.id if checklist else False,
                        'date': employee.joining_date + timedelta(days=employee.confirmation_period),
                        'confirmation_status': 'in_progress'
                    })
                    survey.show_button_manager = True
                    login = employee.responsible_hr.related_hr[0].work_email if employee.responsible_hr else False
                    # login_list =[i.work_email for i in employee.responsible_hr.related_hr if employee.responsible_hr]
                    template = self.env.ref('hr_employee_updation.send_confirm_due_email_hr')
                    template_values = {
                        # 'email_to': ", ".join((x) for x in login_list) or False,
                        'email_to': login or False,
                        'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
                        'email_from': 'unity@e-zest.in',
                        'auto_delete': False,
                        'partner_to': False,
                        'scheduled_date': False,
                    }
                    template.write(template_values)
                    with self.env.cr.savepoint():
                        template.with_context(lang=employee.user_id.lang).send_mail(employee.user_id.id, force_send=True, raise_exception=False)

            # if employee.confirmation_date and datetime.today().date() == employee.confirmation_date and employee.confirmation_status == 'confirmed':
            #     # send confirmation email to user after 90 days
            #     template = self.env.ref('hr_employee_updation.send_confirm_period_email_user')
            #     template_values = {
            #         'email_to': employee.user_id.login or False,
            #         'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
            #         'email_from': 'unity@e-zest.in',
            #         'auto_delete': False,
            #         'partner_to': False,
            #         'scheduled_date': False,
            #     }
            #     template.write(template_values)
            #     if not employee.user_id.login:
            #         raise UserError(_("Cannot send email: user %s has no email address.") % employee.user_id.name)
            #     with self.env.cr.savepoint():
            #         template.with_context(lang=employee.user_id.lang).send_mail(employee.user_id.id, force_send=True, raise_exception=False)

    def _cron_probation_period(self):
        employees = self.search([('employee_category', '=', 'eZestian'), ('company_id', '=', 'e-Zest Solutions Ltd.')])
        self._get_probation_form(employees)

    def _cron_missing_salary_details(self):
        employees = self.search([('joining_date', '!=', False)])
        emp_dic = {}
        for emp in employees:
            if emp.emp_wage == 0.00 and emp.user_id:
                if emp.responsible_hr.related_hr[0] in emp_dic:
                    emp_dic[emp.responsible_hr.related_hr[0]].append(emp)
                else:
                    emp_dic[emp.responsible_hr.related_hr[0]] = [emp]
        for hr, emp_list in emp_dic.items():
            login_list = [i.work_email for i in emp.responsible_hr.related_hr if emp.responsible_hr]
            body = 'Dear {0},\
                        <br/><p>Below team members remuneration details are not updated in UNITY. \
                        Kindly update the details to avoid any inconvenience in operational \
                        activities</p><br/><p><b>Team Member Names:</b></p>'.format(hr.name)
            for empl in emp_list:
                body += '<p>'
                body += empl.name
                body += '</p>'
            body += '<br/><br/>\
                    Thanks,\
                    <br/>\
                    Team Unity\
                    <p><br></p>'
            self.env['mail.mail'].create({
                'subject': 'Team members remuneration details in UNITY',
                'email_from': 'unity@e-zest.in',
                'email_to': ','.join(login_list),
                'email_cc': 'unity@e-zest.in,hrd@e-zest.in,vishant.sarodia@e-zest.in,devendra.deshmukh@e-zest.in',
                'auto_delete': False,
                'body_html': body,
            }).sudo().send()

    def action_confirmation_period(self):
        employee = self.env['hr.employee'].search([('employee_category', '=', 'eZestian'),('id','=',self.id),('company_id', '=', 'e-Zest Solutions Ltd.')])
        if not employee:
            raise UserError(_("Confirmation is generated only for 'e-Zestian' Category"))
        existing_survey = self.env['hr.probation.survey'].search([('employee_id','=',employee.id)])
        today_date = datetime.today().date()
        if not self.extend_period:
            self.confirmation_period = (today_date - self.joining_date).days
        elif self.extend_period and self.confirmation_status == 'extended':
            confrm_date = self.joining_date + timedelta(days=self.confirmation_period)
            self.extend_period = (today_date - confrm_date).days
        if existing_survey:
            if self.is_extend:
                existing_survey.sudo().write({
                    'is_extend': True,
                    'extend_period': self.extend_period,
                    'extend_reason': self.extend_reason
                })
            existing_survey.show_button_manager = True
            existing_survey.activity_update()
            login = employee.responsible_hr.related_hr[0].work_email if employee.responsible_hr else False
            # login_list =[i.work_email for i in employee.responsible_hr.related_hr if employee.responsible_hr]
            template = self.env.ref('hr_employee_updation.send_confirm_due_email_hr')
            template_values = {
                # 'email_to': ", ".join((x) for x in login_list) or False,
                'email_to': login or False,
                'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
                'email_from': 'unity@e-zest.in',
                'auto_delete': False,
                'partner_to': False,
                'scheduled_date': False,
            }
            template.write(template_values)
            with self.env.cr.savepoint():
                template.with_context(lang=employee.user_id.lang).send_mail(employee.user_id.id, force_send=True, raise_exception=False)
        if not existing_survey:
            employee.confirmation_status = "in_progress"
            checklist = self.env['employee.checklist'].search([('name', '=', 'Confirmation Evaluation Form')])
            survey = self.env['hr.probation.survey'].create({
                'employee_id': employee.id,
                'checklist_id': checklist.id if checklist else False,
                'date': employee.joining_date + timedelta(days=employee.confirmation_period),
                'confirmation_status': 'in_progress'
            })
            survey.show_button_manager = True
            login = employee.responsible_hr.related_hr[0].work_email if employee.responsible_hr else False
            # login_list =[i.work_email for i in employee.responsible_hr.related_hr if employee.responsible_hr]
            template = self.env.ref('hr_employee_updation.send_confirm_due_email_hr')
            template_values = {
                # 'email_to': ", ".join((x) for x in login_list) or False,
                'email_to': login or False,
                'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
                'email_from': 'unity@e-zest.in',
                'auto_delete': False,
                'partner_to': False,
                'scheduled_date': False,
            }
            template.write(template_values)
            with self.env.cr.savepoint():
                template.with_context(lang=employee.user_id.lang).send_mail(employee.user_id.id, force_send=True, raise_exception=False)

    def action_clearance(self):
        self.env['hr.resignation']._create_sep_feedback(self)

    def _cron_new_onboarded_ezestian_daily(self):
        today = fields.Date.today()
        last_date = calendar.monthrange(today.year, today.month)[1]
        week_start = today - timedelta(days=today.weekday())
        week_end = today - timedelta(days=today.weekday()) + (timedelta(days=6))
        month_start = today + relativedelta(day=1)
        month_end = (month_start + relativedelta(months=2)) - relativedelta(days=1)
        if today.weekday() < 5:
            # exec_email = self.env['ir.config_parameter'].sudo().get_param('helpdesk.exec_email')
            exec_email = self.env['bod.mail.config'].sudo().search([]).mapped('user_id.login')
            exec_email = list(set(exec_email))
            # New joinee logic report
            planned_joined_employees = [i for i in self.search([]) if i.planned_join_date and i.planned_join_date == today]
            planned_not_joined_employees = [i for i in self.search([]) if i.planned_join_date and i.planned_join_date == today and not i.joining_date]
            planned_join_week = self.search([('planned_join_date', '>=', week_start), ('planned_join_date', '<=', week_end), ('joining_date', '=', False), ('is_ezestian', '=', False)])
            planned_join_month = self.search([('planned_join_date', '>=', month_start), ('planned_join_date', '<=', month_end), ('joining_date', '=', False), ('is_ezestian', '=', False)])
            joined_employees = self.search([('joining_date', '=', today), ('is_ezestian', '=', True)])
            joined_no_employees = self.search([('planned_join_date','<=', today),('joining_date', '<=', today), ('is_ezestian', '=', False)])
            # exit ezestian logic report
            archive_employee = self.env['hr.employee'].search([('active', '=', False)])
            # submit_resignation = self.env['hr.resignation'].search([('state', '=', 'confirm')])
            total_resignation_approved = [i for i in self.env['hr.resignation'].search([('state', '=', 'approved'), ('employee_id', 'not in', archive_employee.ids)])]
            total_resign = [i for i in self.env['hr.employee'].search([('joining_date', '!=', False), ('resign_date', '!=', False)])]
            planned_exit_employees = [i for i in self.env['hr.resignation'].search([('resign_confirm_date', '=', today), ('state', '=', 'confirm')])]
            exit_confirm_employees = [i for i in self.env['hr.resignation'].search([('state', '=', 'approved'), ('approved_date', '=', today)])]
            exit_employees = [i for i in self.env['hr.resignation'].search([('state', '=', 'approved'), ('approved_revealing_date', '=', today)])]
            confirmed_resignation = [i for i in self.env['hr.resignation'].search([('state', '=', 'confirm')])]
            planned_count = 1
            planned_exit_count = 1
            joined_count = 1
            joined_no_count = 1
            exit_confirm_count = 1
            exit_count = 1
            message_body = '<h5>' + 'Overview:' + '<h5/>'
            message_body += '<table border="1" width="50%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                        '<td colspan="2">' + '<strong>Joining Summary</strong>' + '</td>'\
                                    '</tr>'
            message_body += '<tr style="text-align:center;">'\
                            '<td>' + 'Expected joining today' + '</td>'\
                            '<td>' + str(len(planned_joined_employees)) + '</td>'\
                            '</tr>'
            message_body += '<tr style="text-align:center;">'\
                            '<td>' + "Actual joined today" + '</td>'\
                            '<td>' + str(len(joined_employees)) + '</td>'\
                            '</tr>'
            message_body += '<tr style="text-align:center;">'\
                            '<td>' + 'Expected joining this week' + '</td>'\
                            '<td>' + str(len(planned_join_week)) + '</td>'\
                            '</tr>'
            message_body += '<tr style="text-align:center;">'\
                            '<td>' + 'Expected joining this month' + '</td>'\
                            '<td>' + str(len(planned_join_month)) + '</td>'\
                            '</tr>'
            message_body += '</table>' + '<br/>' + '<br/>'
            message_body += '<table border="1" width="50%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                        '<td colspan="2">' + '<strong>Exit Summary </strong>' + '</td>'\
                                    '</tr>'
            message_body += '<tr style="text-align:center;">'\
                            '<td>' + "Exit today" + '</td>'\
                            '<td>' + str(len(exit_employees)) + '</td>'\
                            '</tr>'
            message_body += '<tr style="text-align:center;">'\
                            '<td>' + 'Pending approval for resignation' + '</td>'\
                            '<td>' + str(len(confirmed_resignation)) + '</td>'\
                            '</tr>'
            message_body += '<tr style="text-align:center;">'\
                            '<td>' + 'Resignation approved till date' + '</td>'\
                            '<td>' + str(len(total_resignation_approved)) + '</td>'\
                            '</tr>'
            message_body += '<tr style="text-align:center;">'\
                            '<td>' + 'Total Resignations' + '</td>'\
                            '<td>' + str(len(total_resign)) + '</td>'\
                            '</tr>'
            message_body += '</table>' + '<br/>'
            # if planned_joined_employees or joined_employees or joined_no_employees:
            # message_body += 'Today %s e-Zestian/s is/are planning to join. %s e-Zestian/s have joined and %s e-Zestian/s exited.' % (len(planned_joined_employees), len(joined_employees), len(exit_employees)) + '<br/>' + '<br/>'
            if planned_not_joined_employees or joined_employees or planned_exit_employees or exit_employees or joined_no_employees or exit_confirm_employees:
                message_body += '<h5> Detailed Report:' + '<h5/>'
                if planned_not_joined_employees or joined_employees:
                    message_body += "<h5 style='color:black;''>e-Zest's Joining report of the day:</h5>"
                    message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
                    message_body += '<tr style="text-align:center;">'\
                                        '<th>' + 'Sr. No.' + '</th>'\
                                        '<th>' + 'e-Zestian Name' + '</th>'\
                                        '<th>' + 'Company' + '</th>'\
                                        '<th>' + 'Designation' + '</th>'\
                                        '<th>' + 'Skills' + '</th>'\
                                        '<th>' + 'Yrs of experience' + '</th>'\
                                        '<th>' + 'Department' + '</th>'\
                                        '<th>' + 'SBU' + '</th>'\
                                        '<th>' + 'Reporting Manager' + '</th>'\
                                        '<th>' + 'Planned Project' + '</th>'\
                                        '<th>' + 'Payroll Location' + '</th>'\
                                        '<th>' + 'Work Location' + '</th>'\
                                        '<th>' + 'Expected Joining Date' + '</th>'\
                                        '<th>' + 'Date of Joining' + '</th>'\
                                        '<th>' + 'Source of Hiring' + '</th>'\
                                        '<th>' + 'Sub-Source' + '</th>'\
                                        '<th>' + 'Recruiter' + '</th>'\
                                        '<th>' + 'Responsible HR' + '</th>'\
                                        '<th>' + 'Comments' + '</th>'\
                                        '<th>' + 'Joining Category' + '</th>'\
                                    '</tr>'
                if joined_employees:
                    message_body += '<tr style="text-align:center;">'\
                                        '<td colspan="17">' + '<strong>Actual Joined today</strong>' + '</td>'\
                                    '</tr>'
                    for employee in joined_employees:
                        applicant = self.env['hr.applicant'].search([('partner_mobile', '=', employee.mobile_phone)], limit=1)
                        project_name = applicant.job_id.project_id.name if applicant.job_id.project_id else ''
                        total_exp = applicant.total_exp if applicant.total_exp else ''
                        vacancy_type = applicant.job_id.vacancy_type.capitalize() if applicant.job_id.vacancy_type else ''
                        recruiter_feedback = applicant.recruiter_feedback if applicant.recruiter_feedback else ''
                        source = applicant.medium_id.name if applicant.medium_id else ''
                        if source == 'Team Reference' and applicant.ref_employee_id:
                            sub_source = applicant.applicant.ref_employee_id.name
                        else:
                            sub_source = ''
                        job_id = employee.job_id.name if employee.job_id else ''
                        skills = employee.skills.name if employee.skills else ''
                        department_id = employee.department_id.name if employee.department_id else ''
                        sbu_id = employee.sbu_id.name if employee.sbu_id else ''
                        payroll_loc = employee.payroll_loc.name if employee.payroll_loc else ''
                        work_loc = employee.location_work.name if employee.location_work else ''
                        manager_id = employee.parent_id.name if employee.parent_id else ''
                        work_email = employee.work_email if employee.work_email else ''
                        planned_join = str(employee.planned_join_date.strftime('%d-%b-%Y')) if employee.planned_join_date else ''
                        joining_date = str(employee.joining_date.strftime('%d-%b-%Y')) if employee.joining_date else ''
                        recruiter = ' '.join([i.name for i in employee.responsible_recruiter]) if employee.responsible_recruiter else ''
                        responsible_hr = employee.responsible_hr.related_hr.name if employee.responsible_hr and employee.responsible_hr.related_hr else ''
                        message_body += '<tr style="text-align:center;">'\
                                            '<td>' + str(joined_count) + '</td>'\
                                            '<td>' + employee.name + '</td>'\
                                            '<td>' + employee.company_id.name + '</td>'\
                                            '<td>' + job_id + '</td>'\
                                            '<td>' + skills + '</td>'\
                                            '<td>' + str(total_exp) + '</td>'\
                                            '<td>' + department_id + '</td>'\
                                            '<td>' + sbu_id + '</td>'\
                                            '<td>' + manager_id + '</td>'\
                                            '<td>' + project_name + '</td>'\
                                            '<td>' + payroll_loc + '</td>'\
                                            '<td>' + work_loc + '</td>'\
                                            '<td>' + planned_join + '</td>'\
                                            '<td>' + str(joining_date) + '</td>'\
                                            '<td>' + source + '</td>'\
                                            '<td>' + sub_source + '</td>'\
                                            '<td>' + recruiter + '</td>'\
                                            '<td>' + responsible_hr + '</td>'\
                                            '<td>' + recruiter_feedback + '</td>'\
                                            '<td>' + vacancy_type + '</td>'\
                                        '</tr>'
                        joined_count += 1
                    # message_body += '</table>' + '<br/>' + '<br/>'
                if not planned_not_joined_employees:
                    message_body += '<tr style="text-align:center;">'\
                                        '<td colspan="17">' + '<strong>None</strong>' + '</td>'\
                                    '</tr>'
                if planned_not_joined_employees:
                    message_body += '<tr style="text-align:center;">'\
                                        '<td colspan="17">' + '<strong>Expected to join today but did not show up</strong>' + '</td>'\
                                    '</tr>'
                    for employee in planned_not_joined_employees:
                        applicant = self.env['hr.applicant'].search([('partner_mobile', '=', employee.mobile_phone)], limit=1)
                        project_name = applicant.job_id.project_id.name if applicant.job_id.project_id else ''
                        total_exp = applicant.total_exp if applicant.total_exp else ''
                        source = applicant.medium_id.name if applicant.medium_id else ''
                        if source == 'Team Reference' and applicant.ref_employee_id:
                            sub_source = applicant.applicant.ref_employee_id.name
                        else:
                            sub_source = ''
                        vacancy_type = applicant.job_id.vacancy_type.capitalize() if applicant.job_id and applicant.job_id.vacancy_type else ''
                        recruiter_feedback = applicant.recruiter_feedback if applicant.recruiter_feedback else ''
                        job_id = employee.job_id.name if employee.job_id else ''
                        skills = employee.skills.name if employee.skills else ''
                        department_id = employee.department_id.name if employee.department_id else ''
                        sbu_id = employee.sbu_id.name if employee.sbu_id else ''
                        payroll_loc = employee.payroll_loc.name if employee.payroll_loc else ''
                        work_loc = employee.location_work.name if employee.location_work else ''
                        manager_id = employee.parent_id.name if employee.parent_id else ''
                        joining_date = str(employee.joining_date.strftime('%d-%b-%Y')) if employee.joining_date else ''
                        recruiter = ' '.join([i.name for i in employee.responsible_recruiter]) if employee.responsible_recruiter else ''
                        responsible_hr = employee.responsible_hr.related_hr.name if employee.responsible_hr and employee.responsible_hr.related_hr else ''
                        if employee.planned_join_date:
                            message_body += '<tr style="text-align:center;">'\
                                                '<td>' + str(planned_count) + '</td>'\
                                                '<td>' + employee.name + '</td>'\
                                                '<td>' + employee.company_id.name + '</td>'\
                                                '<td>' + job_id + '</td>'\
                                                '<td>' + skills + '</td>'\
                                                '<td>' + str(total_exp) + '</td>'\
                                                '<td>' + department_id + '</td>'\
                                                '<td>' + sbu_id + '</td>'\
                                                '<td>' + manager_id + '</td>'\
                                                '<td>' + project_name + '</td>'\
                                                '<td>' + payroll_loc + '</td>'\
                                                '<td>' + work_loc + '</td>'\
                                                '<td>' + str(employee.planned_join_date.strftime('%d-%b-%Y')) + '</td>'\
                                                '<td>' + str(joining_date) + '</td>'\
                                                '<td>' + source + '</td>'\
                                                '<td>' + sub_source + '</td>'\
                                                '<td>' + recruiter + '</td>'\
                                                '<td>' + responsible_hr + '</td>'\
                                                '<td>' + recruiter_feedback + '</td>'\
                                                '<td>' + vacancy_type + '</td>'\
                                            '</tr>'
                        planned_count += 1
                    # message_body += '</table>' + '<br/>' + '<br/>'
                # if joined_no_employees:
                #     message_body += '<tr style="text-align:center;">'\
                #                         '<td colspan="17">' + '<strong>Joined but no access</strong>' + '</td>'\
                #                     '</tr>'
                #     for employee in joined_no_employees:
                #         applicant = self.env['hr.applicant'].search([('partner_mobile', '=', employee.mobile_phone)], limit=1)
                #         project_name = applicant.job_id.project_id.name if applicant.job_id.project_id else ''
                #         total_exp = applicant.total_exp if applicant.total_exp else ''
                #         vacancy_type = applicant.job_id.vacancy_type.capitalize() if applicant.job_id.vacancy_type else ''
                #         source = applicant.medium_id.name if applicant.medium_id else ''
                #         job_id = employee.job_id.name if employee.job_id else ''
                #         skills = employee.skills.name if employee.skills else ''
                #         department_id = employee.department_id.name if employee.department_id else ''
                #         sbu_id = employee.sbu_id.name if employee.sbu_id else ''
                #         payroll_loc = employee.payroll_loc.name if employee.payroll_loc else ''
                #         work_loc = employee.location_work.name if employee.location_work else ''
                #         manager_id = employee.parent_id.name if employee.parent_id else ''
                #         work_email = employee.work_email if employee.work_email else ''
                #         planned_join = str(employee.planned_join_date.strftime('%d-%b-%Y')) if employee.planned_join_date else ''
                #         joining_date = str(employee.joining_date.strftime('%d-%b-%Y')) if employee.joining_date else ''
                #         recruiter = ' '.join([i.name for i in employee.responsible_recruiter]) if employee.responsible_recruiter else ''
                #         responsible_hr = employee.responsible_hr.related_hr.name if employee.responsible_hr and employee.responsible_hr.related_hr else ''
                #         message_body += '<tr style="text-align:center;">'\
                #                             '<td>' + str(joined_no_count) + '</td>'\
                #                             '<td>' + employee.name + '</td>'\
                #                             '<td>' + employee.company_id.name + '</td>'\
                #                             '<td>' + job_id + '</td>'\
                #                             '<td>' + skills + '</td>'\
                #                             '<td>' + str(total_exp) + '</td>'\
                #                             '<td>' + department_id + '</td>'\
                #                             '<td>' + sbu_id + '</td>'\
                #                             '<td>' + manager_id + '</td>'\
                #                             '<td>' + project_name + '</td>'\
                #                             '<td>' + payroll_loc + '</td>'\
                #                             '<td>' + work_loc + '</td>'\
                #                             '<td>' + planned_join + '</td>'\
                #                             '<td>' + joining_date + '</td>'\
                #                             '<td>' + source + '</td>'\
                #                             '<td>' + recruiter + '</td>'\
                #                             '<td>' + responsible_hr + '</td>'\
                #                         '</tr>'
                #         joined_no_count += 1
                message_body += '</table>' + '<br/>' + '<br/>'
                message_body += "<h5 style='color:black;''>e-Zest's exit report of the day:</h5>"
                message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
                if exit_employees:
                    message_body += '<tr style="text-align:center;">'\
                                    '<th>' + 'Sr. No.' + '</th>'\
                                    '<th>' + 'e-Zestian Name' + '</th>'\
                                    '<th>' + 'Company' + '</th>'\
                                    '<th>' + 'Designation' + '</th>'\
                                    '<th>' + 'Skills' + '</th>'\
                                    '<th>' + 'Years of experience' + '</th>'\
                                    '<th>' + 'Department' + '</th>'\
                                    '<th>' + 'SBU' + '</th>'\
                                    '<th>' + 'Reporting Manager' + '</th>'\
                                    '<th>' + 'Experience in e-Zest' + '</th>'\
                                    '<th>' + 'Payroll Location' + '</th>'\
                                    '<th>' + 'Date of Resignation' + '</th>'\
                                    '<th>' + 'Date of Joining' + '</th>'\
                                    '<th>' + 'Exit Date' + '</th>'\
                                    '<th>' + 'Responsible HR' + '</th>'\
                                '</tr>'
                if not exit_employees:
                    message_body += '<tr style="text-align:center;">'\
                                    "No exits today </tr>"
                if exit_employees:
                    message_body += '<tr style="text-align:center;">'\
                                        '<td colspan="15">' + '<strong>Today Exit e-Zestians</strong>' + '</td>'\
                                    '</tr>'
                    for resign in exit_employees:
                        resign_date = resign.resign_confirm_date.strftime('%d-%b-%Y') if resign.resign_confirm_date else ''
                        exit_date = resign.approved_revealing_date.strftime('%d-%b-%Y') if resign.approved_revealing_date else ''
                        job_id = resign.employee_id.job_id.name if resign.employee_id.job_id else ''
                        skills = resign.employee_id.skills.name if resign.employee_id.skills else ''
                        department_id = resign.employee_id.department_id.name if resign.employee_id.department_id else ''
                        sbu_id = resign.employee_id.sbu_id.name if resign.employee_id.sbu_id else ''
                        payroll_loc = resign.employee_id.payroll_loc.name if resign.employee_id.payroll_loc else ''
                        manager_id = resign.employee_id.parent_id.name if resign.employee_id.parent_id else ''
                        work_email = resign.employee_id.work_email if resign.employee_id.work_email else ''
                        total_exp_after_join = resign.employee_id.relevant_exp_aftr_join if resign.employee_id.relevant_exp_aftr_join else ''
                        total_exp = resign.employee_id.total_exp if resign.employee_id.total_exp else ''
                        joining_date = resign.employee_id.joining_date.strftime('%d-%b-%Y') if resign.employee_id.joining_date else ''
                        responsible_hr = resign.employee_id.responsible_hr.related_hr.name if resign.employee_id.responsible_hr and resign.employee_id.responsible_hr.related_hr else ''
                        message_body += '<tr style="text-align:center;">'\
                                            '<td>' + str(exit_count) + '</td>'\
                                            '<td>' + resign.employee_id.name + '</td>'\
                                            '<td>' + resign.employee_id.company_id.name + '</td>'\
                                            '<td>' + job_id + '</td>'\
                                            '<td>' + skills + '</td>'\
                                            '<td>' + str(total_exp) + '</td>'\
                                            '<td>' + department_id + '</td>'\
                                            '<td>' + sbu_id + '</td>'\
                                            '<td>' + manager_id + '</td>'\
                                            '<td>' + total_exp_after_join + '</td>'\
                                            '<td>' + payroll_loc + '</td>'\
                                            '<td>' + resign_date + '</td>'\
                                            '<td>' + joining_date + '</td>'\
                                            '<td>' + exit_date + '</td>'\
                                            '<td>' + responsible_hr + '</td>'\
                                        '</tr>'
                        exit_count += 1
                    # message_body += '</table>' + '<br/>' + '<br/>'
                # if exit_confirm_employees:
                #     message_body += '<tr style="text-align:center;">'\
                #                         '<td colspan="15">' + '<strong>Resignation Approved</strong>' + '</td>'\
                #                     '</tr>'
                #     for resign in exit_confirm_employees:
                #         resign_date = resign.resign_confirm_date.strftime('%d-%b-%Y') if resign.resign_confirm_date else ''
                #         exit_date = resign.approved_revealing_date.strftime('%d-%b-%Y') if resign.approved_revealing_date else ''
                #         job_id = resign.employee_id.job_id.name if resign.employee_id.job_id else ''
                #         skills = resign.employee_id.skills.name if resign.employee_id.skills else ''
                #         department_id = resign.employee_id.department_id.name if resign.employee_id.department_id else ''
                #         sbu_id = resign.employee_id.sbu_id.name if resign.employee_id.sbu_id else ''
                #         payroll_loc = resign.employee_id.payroll_loc.name if resign.employee_id.payroll_loc else ''
                #         manager_id = resign.employee_id.parent_id.name if resign.employee_id.parent_id else ''
                #         work_email = resign.employee_id.work_email if resign.employee_id.work_email else ''
                #         total_exp_after_join = resign.employee_id.relevant_exp_aftr_join if resign.employee_id.relevant_exp_aftr_join else ''
                #         total_exp = resign.employee_id.total_exp if resign.employee_id.total_exp else ''
                #         joining_date = resign.employee_id.joining_date.strftime('%d-%b-%Y') if resign.employee_id.joining_date else ''
                #         responsible_hr = resign.employee_id.responsible_hr.related_hr.name if resign.employee_id.responsible_hr and resign.employee_id.responsible_hr.related_hr else ''
                #         message_body += '<tr style="text-align:center;">'\
                #                             '<td>' + str(exit_confirm_count) + '</td>'\
                #                             '<td>' + resign.employee_id.name + '</td>'\
                #                             '<td>' + resign.employee_id.company_id.name + '</td>'\
                #                             '<td>' + job_id + '</td>'\
                #                             '<td>' + skills + '</td>'\
                #                             '<td>' + str(total_exp) + '</td>'\
                #                             '<td>' + department_id + '</td>'\
                #                             '<td>' + sbu_id + '</td>'\
                #                             '<td>' + manager_id + '</td>'\
                #                             '<td>' + total_exp_after_join + '</td>'\
                #                             '<td>' + payroll_loc + '</td>'\
                #                             '<td>' + resign_date + '</td>'\
                #                             '<td>' + joining_date + '</td>'\
                #                             '<td>' + exit_date + '</td>'\
                #                             '<td>' + responsible_hr + '</td>'\
                #                         '</tr>'
                #         exit_confirm_count += 1
                # if planned_exit_employees:
                #     message_body += '<tr style="text-align:center;">'\
                #                         '<td colspan="15">' + '<strong>Resignation - To be Approved </strong>' + '</td>'\
                #                     '</tr>'
                #     for resign in planned_exit_employees:
                #         resign_date = resign.resign_confirm_date.strftime('%d-%b-%Y') if resign.resign_confirm_date else ''
                #         exit_date = resign.approved_revealing_date.strftime('%d-%b-%Y') if resign.approved_revealing_date else ''
                #         job_id = resign.employee_id.job_id.name if resign.employee_id.job_id else ''
                #         skills = resign.employee_id.skills.name if resign.employee_id.skills else ''
                #         department_id = resign.employee_id.department_id.name if resign.employee_id.department_id else ''
                #         sbu_id = resign.employee_id.sbu_id.name if resign.employee_id.sbu_id else ''
                #         payroll_loc = resign.employee_id.payroll_loc.name if resign.employee_id.payroll_loc else ''
                #         manager_id = resign.employee_id.parent_id.name if resign.employee_id.parent_id else ''
                #         work_email = resign.employee_id.work_email if resign.employee_id.work_email else ''
                #         total_exp_after_join = resign.employee_id.relevant_exp_aftr_join if resign.employee_id.relevant_exp_aftr_join else ''
                #         total_exp = resign.employee_id.total_exp if resign.employee_id.total_exp else ''
                #         joining_date = resign.employee_id.joining_date.strftime('%d-%b-%Y') if resign.employee_id.joining_date else ''
                #         responsible_hr = resign.employee_id.responsible_hr.related_hr.name if resign.employee_id.responsible_hr and resign.employee_id.responsible_hr.related_hr else ''
                #         message_body += '<tr style="text-align:center;">'\
                #                             '<td>' + str(planned_exit_count) + '</td>'\
                #                             '<td>' + resign.employee_id.name + '</td>'\
                #                             '<td>' + resign.employee_id.company_id.name + '</td>'\
                #                             '<td>' + job_id + '</td>'\
                #                             '<td>' + skills + '</td>'\
                #                             '<td>' + str(total_exp) + '</td>'\
                #                             '<td>' + department_id + '</td>'\
                #                             '<td>' + sbu_id + '</td>'\
                #                             '<td>' + manager_id + '</td>'\
                #                             '<td>' + total_exp_after_join + '</td>'\
                #                             '<td>' + payroll_loc + '</td>'\
                #                             '<td>' + resign_date + '</td>'\
                #                             '<td>' + joining_date + '</td>'\
                #                             '<td>' + exit_date + '</td>'\
                #                             '<td>' + responsible_hr + '</td>'\
                #                         '</tr>'
                #         planned_exit_count += 1
                    # message_body += '</table>' + '<br/>' + '<br/>'
                message_body += '</table>' + '<br/>' + '<br/>'
            message_body += 'Thank you' + '<br/>' + 'Unity'
            self.env['mail.mail'].create({
                'subject': 'Joining and Exit Summary - %s' % today.strftime("%d-%b-%Y"),
                'body_html': message_body,
                'auto_delete': False,
                'email_from': 'unity@e-zest.in',
                # 'email_to': 'unity@e-zest.in,hrd@e-zest.in,shailesh.kulkarni@e-zest.com,girish.chandra@e-zest.com,mandar.garge@e-zest.in,ameet@e-zest.in,%s' % (str(exec_email))
                'email_to': ",".join(x for x in exec_email) if exec_email else 'unity@e-zest.in',
                'email_cc': 'unity@e-zest.in,exec@e-zest.in',
            }).sudo().send()

    def _cron_fnf(self):
        self._cr.execute('''SELECT id FROM hr_employee''')
        employees = self._cr.fetchall()
        # fnf_days = self.env['ir.config_parameter'].sudo().get_param('hr_employee_updation.employee_fnf_days')
        for employee in employees:
            employee = self.search([('id','=',employee[0])])
            if employee.exit_date and employee.responsible_hr:
                logins = employee.responsible_hr.related_hr
                login_list =[i.work_email for i in employee.responsible_hr.related_hr if employee.responsible_hr]
                date = employee.exit_date + timedelta(days=int(employee.fnf_days) or 40)
                if date == datetime.today().date():
                    employee.is_exp_letter = True
                    template = self.env.ref('hr_employee_updation.send_fnf_email')
                    template_values = {
                        'email_from': 'unity@e-zest.in',
                        'email_to': login_list or 'hrd@e-zest.in',
                        'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
                        'auto_delete': False,
                        'partner_to': False,
                        'scheduled_date': False,
                    }
                    template.write(template_values)
                    with self.env.cr.savepoint():
                        template.with_context(lang=employee.user_id.lang).sudo().send_mail(employee.user_id.id, force_send=True, raise_exception=False)

    def action_send_exp_letter(self):
        self._cr.execute('''SELECT id FROM hr_employee''')
        employees = self._cr.fetchall()
        for employee in employees:
            employee = self.sudo().search([('id', '=', employee[0])])
            if employee.is_exp_letter and employee.responsible_hr:
                logins = employee.responsible_hr.related_hr
                login_list = [i.work_email for i in employee.responsible_hr.related_hr if employee.responsible_hr]
                login_list.append('hrd@e-zest.in')
                login_list.append('unity@-ezest.in')
                REPORT_ID = 'hr_employee_updation.employee_experience_letter'
                pdf = self.env.ref(REPORT_ID).render_qweb_pdf(employee.id)
                # pdf result is a list
                b64_pdf = base64.b64encode(pdf[0])
                ATTACHMENT_NAME = employee.name.lower() + '_experience_letter'
                template = self.env.ref('hr_employee_updation.send_experience_letter_email')
                attachment = {'name': ATTACHMENT_NAME + '.pdf',
                            'description': ATTACHMENT_NAME,
                            'type': 'binary',
                            'datas': b64_pdf,
                            'store_fname': ATTACHMENT_NAME,
                            'res_model': self._name,
                            'res_id': employee.id,
                            'mimetype': 'application/x-pdf'}
                template_values = {
                    'email_from': 'unity@e-zest.in',
                    'email_to': employee.personal_email if employee.personal_email else False,
                    'email_cc': ", ".join((x) for x in login_list),
                    'auto_delete': False,
                    'partner_to': False,
                    'scheduled_date': False,
                    'attachment_ids': [(0, 0, attachment)]
                    }
                template.write(template_values)
                with self.env.cr.savepoint():
                    template.with_context(lang=employee.user_id.lang).sudo().send_mail(employee.user_id.id, force_send=True, raise_exception=False)

    def action_clear_roles(self):
        self.user_id.sudo().write({'groups_id': False})
        internal_group = self.env['res.groups'].search([('name', '=', 'Internal User')])
        self.user_id.sudo().write({'groups_id': [(4, internal_group.id)]})

    def action_give_roles(self):
        return {
            'name': _('Groups'),
            'view_mode': 'tree',
            'res_model': 'res.groups',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False, 'default_user_id': self.user_id.id},
            'domain': [('name', 'ilike', 'Role')],
            'target': 'new',
        }

    # def _cron_inter_bu_movement_report(self):
    #     prev_month = fields.Date.today() - relativedelta(months=1)
    #     count = 1
    #     message_body = 'Last Month Inter-BU Movement:'
    #     message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
    #     message_body += '<tr style="text-align:center;">'\
    #                     '<th>' + 'Sr. No.' + '</th>'\
    #                     '<th>' + 'e-Zestian Name' + '</th>'\
    #                     '<th>' + 'Date of Transfer' + '</th>'\
    #                     '<th>' + 'Last Project' + '</th>'\
    #                     '<th>' + 'Last Department (BU)' + '</th>'\
    #                     '<th>' + 'Current Project' + '</th>'\
    #                     '<th>' + 'Current Department (BU)' + '</th>'\
    #                 '</tr>'
    #     for rec in self.search([]):
    #         if rec.dept_change_date and rec.joining_date and rec.dept_change_date > rec.joining_date and rec.dept_change_date.month == prev_month.month:
    #             prev_allocs = [(a.end_date, a) for a in rec.allocation_ids if a.end_date < fields.Date.today()]
    #             current_allocs = [(a.allocation_percentage, a) for a in rec.allocation_ids if a.end_date >= fields.Date.today() and a.start_date <= fields.Date.today()]
    #             prev_allocs.sort()
    #             current_allocs.sort()
    #             last_project = prev_allocs[0][1].project_id.name if prev_allocs and prev_allocs[0] and prev_allocs[0][1] else ''
    #             current_project = current_allocs[0][1].project_id.name if current_allocs and current_allocs[0] and current_allocs[0][1] else ''
    #             message_body += '<tr style="text-align:center;">'\
    #                             '<td>' + str(count) + '</td>'\
    #                             '<td>' + str(rec.name) + '</td>'\
    #                             '<td>' + str(rec.dept_change_date) + '</td>'\
    #                             '<td>' + last_project + '</td>'\
    #                             '<td>' + str(rec.prev_department_id.name) + '</td>'\
    #                             '<td>' + str(current_project) + '</td>'\
    #                             '<td>' + str(rec.department_id.name) + '</td>'\
    #                         '</tr>'
    #             count += 1
    #     message_body += '</table>' + '<br/>' + '<br/>'
    #     message_body += 'Thank you' + '<br/>' + 'Unity'
    #     self.env['mail.mail'].create({
    #         'subject': 'Inter-BU Movement Report',
    #         'body_html': message_body,
    #         'email_from': 'unity@e-zest.in',
    #         'email_to': 'hrd@e-zest.in',
    #         'auto_delete': False,
    #     }).sudo().send()

    def _cron_contract_expiry_remainder(self):
        for rec in self.search([('employee_category','in', ['Contractor', 'Intern'])]):
            if rec and rec.exit_date:
                prior_contractor_10 = rec.exit_date - timedelta(days=10)
                prior_contractor_5 = rec.exit_date - timedelta(days=5)
                prior_contractor_2 = rec.exit_date - timedelta(days=2)
                prior_contractor_1 = rec.exit_date - timedelta(days=1)
                if prior_contractor_10 == fields.Date.today() or prior_contractor_5 == fields.Date.today() or prior_contractor_2 == fields.Date.today() or prior_contractor_1 == fields.Date.today():
                    bu_head = False
                    responsible_hr = 'HR SPOC'
                    if rec.department_id and rec.department_id.custom_manager_id:
                        bu_head = rec.department_id.custom_manager_id.work_email
                    if rec.responsible_hr and rec.responsible_hr.related_hr:
                        responsible_hr = rec.responsible_hr.related_hr[0].work_email
                    body = 'Dear {0},\
                        <p>Contract date of {1} is going to end on {2}.</p><br/>\
                        <p>Get in touch with your {3}  if the contract period is to be extended.</p><br/>\
                        <p>Kindly Ignore the email if the contract period is not be  extended.</p><br/>\
                        <br/>\
                        <br/><br/>\
                        Thanks,\
                        <br/>\
                        Team Unity\
                        <p><br></p>'.format(rec.parent_id.name, rec.name, rec.exit_date.strftime("%d-%b-%Y"), responsible_hr)
                    self.env['mail.mail'].create({
                        'subject': 'End of contract period - %s' % (rec.name),
                        'email_from': 'unity@e-zest.in',
                        'email_to': rec.parent_id.work_email if rec.parent_id else False,
                        'email_cc': 'unity@e-zest.in,hrd@e-zest.in,%s' % bu_head,
                        'auto_delete': False,
                        'body_html': body,
                    }).sudo().send()

    # @api.model
    # def create(self, vals):
    #     res = super(HrEmployee, self).create(vals)
    #     if not res.employee_category:
    #         raise UserError(_("Fill Team member category in Work Information (Fellow e-Zestian's Profile)"))
    #     elif not res.job_id:
    #         raise UserError(_("Fill Designation in Work Information (Fellow e-Zestian's Profile)"))
    #     elif not res.is_technical:
    #         raise UserError(_("Fill Is technical in HR Settings (Fellow e-Zestian's Profile)"))
    #     elif not res.payroll_loc:
    #         raise UserError(_("Fill Payroll Location in HR Settings (Fellow e-Zestian's Profile)"))
    #     elif not res.joining_date:
    #         raise UserError(_("Fill Joining date in HR Settings (Fellow e-Zestian's Profile)"))
    #     user_id = self.env['res.users'].sudo().create({
    #         'name': res.name,
    #         'login': vals.get('work_email') or vals.get('personal_email'),
    #         'company_id': res.company_id.id,
    #     })
    #     res.user_id = user_id
    #     res.personal_email = vals.get('work_email')
    #     res.address_home_id = user_id.partner_id.id
    #     return res

    def write(self, vals):
        for rec in self:
            existing_survey = self.env['hr.probation.survey'].search([('employee_id', '=', rec.id)])
            if existing_survey and (vals.get('confirmation_status') or vals.get('is_extend') or vals.get('extend_period') or vals.get('extend_reason') or vals.get('confirmation_checklist')):
                existing_survey.confirmation_status = vals.get('confirmation_status') or rec.confirmation_status
                existing_survey.is_extend = vals.get('is_extend') or rec.is_extend
                existing_survey.extend_period = vals.get('extend_period') or rec.extend_period
                existing_survey.extend_reason = vals.get('extend_reason') or rec.extend_reason
                existing_survey.confirmation_checklist = vals.get('confirmation_checklist') or rec.confirmation_checklist
            # commented confirmation email from here because sending from probation
            # if rec.confirmation_date and vals.get('confirmation_status') == 'confirmed':
            #     # send cofirmation email to employee
            #     # REPORT_ID = 'hr_employee_updation.employee_confirmation_letter'
            #     # pdf = self.env.ref(REPORT_ID).render_qweb_pdf(self.id)
            #     # pdf result is a list
            #     # b64_pdf = base64.b64encode(pdf[0])
            #     # ATTACHMENT_NAME = self.name.lower() + '_confirmation_letter'
            #     template = self.env.ref('hr_employee_updation.send_confirm_period_email_user')
            #     # attachment = {'name': ATTACHMENT_NAME + '.pdf',
            #     #             'description': ATTACHMENT_NAME,
            #     #             'type': 'binary',
            #     #             'datas': b64_pdf,
            #     #             'store_fname': ATTACHMENT_NAME,
            #     #             'res_model': self._name,
            #     #             'res_id': self.id,
            #     #             'mimetype': 'application/x-pdf'}
            #     template_values = {
            #         'email_to': rec.user_id.login or False,
            #         'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
            #         'email_from': 'unity@e-zest.in',
            #         'auto_delete': False,
            #         'partner_to': False,
            #         'scheduled_date': False,
            #         # 'attachment_ids': [(0, 0, attachment)]
            #     }
            #     template.write(template_values)
            #     if not rec.user_id.login:
            #         raise UserError(_("Cannot send email: user %s has no email address.") % rec.user_id.name)
            #     with self.env.cr.savepoint():
            #         template.with_context(lang=rec.user_id.lang).send_mail(rec.user_id.id, force_send=True, raise_exception=False)
            if vals.get('is_fired'):
                # send fired email to employee
                template = self.env.ref('hr_employee_updation.send_employee_fired_email')
                template_values = {
                    'email_to': rec.user_id.login or False,
                    'email_cc': 'hrd@e-zest.in,unity@e-zest.in',
                    'email_from': 'unity@e-zest.in',
                    'auto_delete': False,
                    'partner_to': False,
                    'scheduled_date': False,
                }
                template.write(template_values)
                if not rec.user_id.login:
                    raise UserError(_("Cannot send email: user %s has no email address.") % rec.user_id.name)
                with self.env.cr.savepoint():
                    template.with_context(lang=rec.user_id.lang).send_mail(rec.user_id.id, force_send=True, raise_exception=False)
            if vals.get('department_id'):
                if rec.joining_date and fields.Date.today() > rec.joining_date and rec.is_ezestian:
                    prev_allocs = [(a.end_date, a) for a in rec.allocation_ids if a.end_date < fields.Date.today()]
                    current_allocs = [(a.allocation_percentage, a) for a in rec.allocation_ids if a.end_date >= fields.Date.today() and a.start_date <= fields.Date.today()]
                    prev_allocs.sort()
                    current_allocs.sort()
                    last_project = prev_allocs[0][1].project_id.id if prev_allocs and prev_allocs[0] and prev_allocs[0][1] else False
                    current_project = current_allocs[0][1].project_id.id if current_allocs and current_allocs[0] and current_allocs[0][1] else False
                    self.env['hr.emp.dept.move'].sudo().create({
                        'prev_dept_id': rec.department_id.id,
                        'current_dept_id': vals.get('department_id'),
                        'employee_id': rec.id,
                        'manager_id': rec.parent_id.id or False,
                        'mov_date': fields.Date.today(),
                        'last_project_id': last_project,
                        'current_project_id': current_project
                    })
                    # rec.prev_department_id = rec.department_id.id
                    # rec.dept_change_date = fields.Date.today()
            # if vals.get('work_email'):
            #     rec.user_id.write({'login': vals.get('work_email')})
            #     rec.user_id.partner_id.write({'email': vals.get('work_email')})
            if vals.get('job_id'):
                for resume in rec.resume_line_ids:
                    if resume.line_type_id.name == 'Experience' and resume.name == rec.company_id.name and resume.employee_id.id == rec.id:
                        resume.sudo().write({
                            'description': self.env['hr.job'].browse(vals.get('job_id')).name
                        })
            if vals.get('is_ezestian'):
                if not self.skills and not vals.get('skills'):
                    raise UserError(_("Primary Skills can not be blank."))
            if vals.get('active') is False:
                for child in self.child_ids:
                    child.parent_id = self.parent_id.id
            if vals.get('parent_id'):
                manager = self.env['hr.employee'].search([('id', '=', vals.get('parent_id'))])
                if rec.parent_id:
                    activity = self.env['mail.activity'].search([('user_id', '=', rec.parent_id.user_id.id)])
                    regular = self.env['attendance.regular'].search([('state_select', '=', 'requested'), ('employee', '=', rec.id)])
                    leave = self.env['hr.leave'].search([('state', '=', 'confirm'), ('employee_id', '=', rec.id)])
                    for act in activity:
                        model = self.env[act.res_model].search([('id', '=', act.res_id)])
                        if act.res_model == 'attendance.regular':
                            if model.employee and model.employee.name == rec.name:
                                act.sudo().write({'user_id': manager.user_id.id})
                            if regular:
                                for reg in regular:
                                    reg.sudo().write({
                                        'manager_id': vals.get('parent_id')
                                    })
                        if act.res_model == 'hr.leave':
                            if model.employee_id and model.employee_id.name == rec.name:
                                act.sudo().write({'user_id': manager.user_id.id})
                            if leave:
                                for leav in leave:
                                    leav.sudo().write({
                                        'manager_id': vals.get('parent_id')
                                    })
                        # if act.res_model == 'hr.resignation':
                        #     if model.employee_id and model.employee_id.name == rec.name:
                        #         act.sudo().write({'user_id': manager.user_id.id})
        return super(HrEmployee, self).write(vals)

    @api.onchange('father_ins', 'mother_ins')
    def _onchange_insurance_details(self):
        for emp in self:
            if emp.sudo().single_parent:
                if not emp.sudo().father_ins and not emp.sudo().mother_ins:
                    emp.sudo().single_parent = False

    @api.constrains('single_parent')
    def _check_single_parent_mediclaim_details(self):
        for emp in self:
            if emp.sudo().single_parent:
                if not emp.sudo().father_ins and not emp.sudo().mother_ins:
                    raise ValidationError(_('Please select either Mother or Father in Mediclaim details'))

    @api.depends('joining_date')
    def _compute_experience(self):
        for rec in self:
            current_date = datetime.now().date()
            # current_date = date.today()
            if rec.exit_date and rec.exit_date < current_date:
                rdelta = relativedelta(rec.exit_date, rec.joining_date)
            else:
                rdelta = relativedelta(current_date, rec.joining_date)
            # if rdelta.days:
            #     rec.relevant_exp_aftr_join = "{} days".format(rdelta.days)
            if rdelta.months:
                rec.relevant_exp_aftr_join = "{} months".format(rdelta.months)
            if rdelta.years >= 1:
                if rdelta.years == 1:
                    rec.relevant_exp_aftr_join = "{} year".format(rdelta.years)
                if rdelta.years > 1:
                    rec.relevant_exp_aftr_join = "{} years".format(rdelta.years)
            # if rdelta.months and rdelta.days:
            #     rec.relevant_exp_aftr_join = "{} months {} days".format(rdelta.months,rdelta.days)
            if rdelta.years and rdelta.months:
                rec.relevant_exp_aftr_join = "{} years {} months".format(rdelta.years,rdelta.months)
            # if rdelta.years and rdelta.days:
            #     rec.relevant_exp_aftr_join = "{} years {} days".format(rdelta.years,rdelta.days)
            # if rdelta.years and rdelta.months and rdelta.days:
            #     rec.relevant_exp_aftr_join = "{} years {} months {} days".format(rdelta.years,rdelta.months,rdelta.days)
            # if not rdelta.years and not rdelta.months and not rdelta.days:
            #     rec.relevant_exp_aftr_join = ""
            if not rdelta.years and not rdelta.months:
                rec.relevant_exp_aftr_join = ""

    def mail_reminder(self):
        """Sending expiry date notification for ID and Passport"""
        now = datetime.now() + timedelta(days=1)
        date_now = now.date()
        match = self.search([])
        for i in match:
            if i.id_expiry_date:
                exp_date = fields.Date.from_string(i.id_expiry_date) - timedelta(days=14)
                if date_now >= exp_date:
                    mail_content = "  Hello  " + i.name + ",<br>Your ID " + i.identification_id + "is going to expire on " + \
                                   str(i.id_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('ID-%s Expired On %s') % (i.identification_id, i.id_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()
        match1 = self.search([])
        for i in match1:
            if i.passport_expiry_date:
                exp_date1 = fields.Date.from_string(i.passport_expiry_date) - timedelta(days=180)
                if date_now >= exp_date1:
                    mail_content = "  Hello  " + i.name + ",<br>Your Passport " + i.passport_id + "is going to expire on " + \
                                   str(i.passport_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('Passport-%s Expired On %s') % (i.passport_id, i.passport_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()

    def _compute_show_details(self):
        show_details = self.env['res.users'].has_group('hr.group_hr_user')
        # user see his/her own info and hr can see.
        for employee in self:
            if show_details or employee.user_id == self.env.user:
                employee.show_details = True
            else:
                employee.show_details = False

    def _compute_show_skills(self):
        other_role = self.env['res.users'].has_group('hr_employee_updation.group_vp_operation')
        # user see his/her own info and hr can see.
        for employee in self:
            if other_role or employee.user_id == self.env.user:
                employee.show_skills = True
            else:
                employee.show_skills = False

    @api.depends('joining_date', 'confirmation_period', 'extend_period', 'confirmation_status')
    # @api.depends('joining_date', 'confirmation_period', 'extend_period')
    def _compute_confirm_date(self):
        for rec in self:
            if rec.joining_date:
                now = datetime.now().date()
                if rec.is_extend and rec.extend_period:
                    extend_period = sum([int(i) for i in rec.extend_period.split('+')])
                    confirm_date = rec.joining_date + timedelta(days=extend_period+rec.confirmation_period)
                else:
                    confirm_date = rec.joining_date + timedelta(days=rec.confirmation_period)
                # if now >= confirm_date or rec.confirmation_status == "confirmed":
                #     rec.confirmation_status = "confirmed"
                #     rec.confirmation_date = confirm_date
                # import pdb; pdb.set_trace()
                if rec.confirmation_status == "confirmed":
                    rec.confirmation_date = confirm_date
                else:
                    rec.confirmation_date = False
            else:
                rec.confirmation_date = False

    @api.onchange('is_extend')
    def _onchange_extend(self):
        if self.is_extend:
            self.confirmation_status = "extended"

    @api.onchange('employee_category')
    def _onchange_employee_category(self):
        if self.employee_category and self.employee_category.name in ['eZestian', 'Intern']:
            self.contractor_type = ''
            self.vendor_name = ''
        employee_category = self.env['hr.contract.type'].search([('name', '=', 'Contractor')])
        employee_category_intern = self.env['hr.contract.type'].search([('name', '=', 'Intern')])
        employee_category_employee = self.env['hr.contract.type'].search([('name', '=', 'eZestian')])
        if self.employee_category.id == employee_category.id or self.employee_category.id == employee_category_intern.id:
            self.confirmation_status = ''
            self.confirmation_period = 0
        elif self.employee_category.id == employee_category_employee.id and not self.confirmation_date:
            self.confirmation_status = 'due'

    @api.onchange('confirmation_status')
    def _onchange_confirmation_status(self):
        for rec in self:
            if rec.confirmation_status == 'confirmed' and rec.confirmation_date:
                rec.notice_period = 60
            else:
                rec.notice_period = 60

    @api.onchange('current_address_copy')
    def _onchange_currnt_addrss_copy(self):
        for rec in self:
            if rec.current_address_copy:
                if rec.street_c or rec.street2_c or rec.city_c or rec.state_c or rec.zip_c or rec.country_c:
                    rec.street_p = rec.street_c
                    rec.street2_p = rec.street2_c
                    rec.city_p = rec.city_c
                    rec.state_p = rec.state_c
                    rec.zip_p = rec.zip_c
                    rec.country_p = rec.country_c
            else:
                rec.street_p = False
                rec.street2_p = False
                rec.city_p = False
                rec.state_p = False
                rec.zip_p = False
                rec.country_p = False

    def _cron_change_NP(self):
        emp = self.env['hr.employee'].search([])
        for e in emp:
            given_date = datetime(2021, 11, 26)
            given_date1 = given_date.strftime("%Y-%m-%d")
            # print('------------',given_date1)
            # print('-----------',e.joining_date)
            new_jd = str(e.joining_date)
            if given_date1 <= new_jd and e.notice_period != 60:
                 e.notice_period = 60

    @api.depends('notice_period', 'is_fired', 'is_abscond')
    def _get_exit_date(self):
        for rec in self:
            if rec.is_fired:
                rec.exit_date = fields.Date.today()
            elif rec.is_abscond:
                rec.abscond = fields.Date.today()
            else:
                rec.exit_date = False

    def confirmation_view(self):
        self.ensure_one()
        domain = [
            ('employee_id', '=', self.id)]
        return {
            'name': _('Confirmation'),
            'domain': domain,
            'res_model': 'hr.probation.survey',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Confirmation
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_id': '%s'}" % self.id
        }

    def get_nda_checklist(self):
        checklist = self.env['employee.checklist'].search([('name', '=', 'NDA Agreement')])
        employee = self.search([('user_id', '=', self.env.user.id)])
        emp_checklist = [emp.id for emp in employee.entry_checklist]
        if employee.is_ezestian:
            if checklist.id in emp_checklist:
                return ({'unity_access': True, 'checklist': True})
            else:
                return ({'unity_access': True, 'checklist': False, 'nda_signed_off': False})
        else:
            return ({'unity_access': False, 'checklist': False, 'nda_signed_off': False})


    def get_coc_checklist(self):
        checklist = self.env['employee.checklist'].search([('name', '=', 'Code of Conduct')])
        employee = self.search([('user_id', '=', self.env.user.id)])
        emp_checklist = [emp.id for emp in employee.entry_checklist]
        if employee.is_ezestian:
            if checklist.id in emp_checklist:
                return ({'unity_access': True, 'checklist': True})
            else:
                return ({'unity_access': True, 'checklist': False, 'coc_signed_off': False})
        else:
            return ({'unity_access': False, 'checklist': False, 'coc_signed_off': False})

    def _check_nda(self, user_id):
        checklist = self.env['employee.checklist'].search([('name', '=', 'NDA Agreement')])
        antisexual_checklist = self.env['employee.checklist'].search([('name', '=', 'Anti-Sexual Harassment Policy')])
        coc_checklist = self.env['employee.checklist'].search([('name', '=', 'Code of Conduct')])
        employee = self.search([('user_id', '=', user_id)], limit=1)
        emp_checklist = [emp.id for emp in employee.entry_checklist]
        # print("Got the result!!!!")
        if employee.is_ezestian:
            if checklist.id in emp_checklist and antisexual_checklist.id in emp_checklist and coc_checklist.id in emp_checklist and employee.employee_category.name in ['eZestian', 'Contractor', 'Intern'] and employee.company_id.name == 'e-Zest Solutions Ltd.':
            # if (checklist.id in emp_checklist or antisexual_checklist.id in emp_checklist or coc_checklist.id in emp_checklist) and employee.employee_category.name in ['eZestian', 'Contractor', 'Intern', 'Employee'] and employee.company_id.name == 'e-Zest Solutions Ltd.':
                return True
            elif checklist.id in emp_checklist and employee.company_id.name != 'e-Zest Solutions Ltd.':
                return True
        else:
            return False

    def on_agree_nda(self):
        checklist = self.env['employee.checklist'].search([('name', '=', 'NDA Agreement')])
        employee = self.search([('user_id', '=', self.env.user.id)])
        employee.sudo().write({
            'entry_checklist': [(4, checklist.id)],
            'nda_signed_off': fields.Date.today()})
        REPORT_ID = 'hr_employee_updation.employee_agreement_letter'
        pdf = self.env.ref(REPORT_ID).render_qweb_pdf(employee.id)
        # pdf result is a list
        b64_pdf = base64.b64encode(pdf[0])
        # save pdf as attachment
        ATTACHMENT_NAME = employee.name.lower() + '_agreement' 
        return self.env['ir.attachment'].sudo().create({
            'description': ATTACHMENT_NAME,
            'type': 'binary',
            'datas': b64_pdf,
            'name': ATTACHMENT_NAME + '.pdf',
            'store_fname': ATTACHMENT_NAME,
            'res_model': self._name,
            'res_id': employee.id,
            'mimetype': 'application/x-pdf'
        })

    def on_agree_coc(self):
        checklist = self.env['employee.checklist'].search([('name', '=', 'Code of Conduct')])
        employee = self.search([('user_id', '=', self.env.user.id)])
        employee.sudo().write({
            'entry_checklist': [(4, checklist.id)],
            'coc_signed_off': fields.Date.today()})
        REPORT_ID = 'hr_employee_updation.employee_coc_pdf'
        pdf = self.env.ref(REPORT_ID).render_qweb_pdf(employee.id)
        # pdf result is a list
        b64_pdf = base64.b64encode(pdf[0])
        # save pdf as attachment
        ATTACHMENT_NAME = employee.name.lower() + '_code_of_conduct'
        return self.env['ir.attachment'].sudo().create({
            'description': ATTACHMENT_NAME,
            'type': 'binary',
            'datas': b64_pdf,
            'name': ATTACHMENT_NAME + '.pdf',
            'store_fname': ATTACHMENT_NAME,
            'res_model': self._name,
            'res_id': employee.id,
            'mimetype': 'application/x-pdf'
        })

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.employee'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.employee', 'default_res_id': self.id}
        return res

    @api.onchange('empl_shift')
    def _onchange_empl_shift(self):
        calendar_client_id = self.env['resource.calendar'].search([('name','=','Client 45 Hours/Week')])
        calendar_id = self.env['resource.calendar'].search([('name','=','e-Zest 45 Hours/Week')])
        if self.empl_shift:
            self.write({'resource_calendar_id': calendar_client_id.id})
        else:
            self.write({'resource_calendar_id': calendar_id.id})

    def action_identification_id(self):
        for rec in self:
            if not rec.employee_category:
                raise UserError(_("Fill Team member category in Work Information (Fellow e-Zestian's Profile)"))
            elif not rec.job_id:
                raise UserError(_("Fill Designation in Work Information (Fellow e-Zestian's Profile)"))
            elif not rec.parent_id:
                raise UserError(_("Fill Manager in Work Information (Fellow e-Zestian's Profile)"))
            elif not rec.is_technical and rec.company_id.name == 'e-Zest Solutions Ltd.':
                raise UserError(_("Fill Is technical in HR Settings (Fellow e-Zestian's Profile)"))
            elif not rec.payroll_loc and rec.company_id.name == 'e-Zest Solutions Ltd.':
                raise UserError(_("Fill Payroll Location in HR Settings (Fellow e-Zestian's Profile)"))
            elif not rec.joining_date:
                raise UserError(_("Fill Joining date in HR Settings (Fellow e-Zestian's Profile)"))
            elif rec.company_id.name == 'e-Zest Solutions Ltd.' and rec.identification_id == 'New':
                if rec.employee_category.name == 'eZestian':
                    rec.identification_id = rec.env['ir.sequence'].next_by_code('hr.employee.identification.id') or _('New')
                if rec.employee_category.name == 'Contractor':
                    rec.identification_id = rec.env['ir.sequence'].next_by_code('hr.employee.contract.identification.id') or _('New')
            elif rec.company_id.name == 'e-Zest Solutions Inc.' and rec.identification_id == 'New':
                if rec.employee_category.name == 'eZestian':
                    rec.identification_id = rec.env['ir.sequence'].next_by_code('hr.employee.identification.inc.id') or _('New')
                if rec.employee_category.name == 'Contractor':
                    rec.identification_id = rec.env['ir.sequence'].next_by_code('hr.employee.contract.identification.inc.id') or _('New')
            # elif rec.company_id.name == 'e-Zest Solutions Ltd, Zweigniederlassung Österreich' and rec.identification_id == 'New':
            #     if rec.employee_category.name == 'eZestian':
            #         rec.identification_id = rec.env['ir.sequence'].next_by_code('hr.employee.identification.austria.id') or _('New')
            #     if rec.employee_category.name == 'Contractor':
            #         rec.identification_id = rec.env['ir.sequence'].next_by_code('hr.employee.contract.identification.austria.id') or _('New')

    def _default_random_barcode(self):
        barcode = None
        while not barcode or self.env['hr.employee'].search([('barcode', '=', barcode)]):
            barcode = "".join(choice(digits) for i in range(8))
        return barcode

    def action_information_agree(self):
        view_id = self.env.ref('hr_employee_updation.employee_information_agree_form').id
        return {
            'name': _('Information Agree'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'employee.information.agree',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
            }
        }

    def action_change_emp_category(self):
        view_id = self.env.ref('hr_employee_updation.employee_change_category_form').id
        return {
            'name': _('Change Team Member Category'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'employee.change.category.wizard',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
            }
        }

    def contractor_document_view(self):
        view_id = self.env.ref('oh_employee_check_list.employee_contractor_document_tree_view').id
        return {
            'name': _('Contactor Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.document',
            'view_mode': 'tree',
            'view_id': view_id,
            'target': 'current',
            'domain': [('employee_ref', '=', self.id)],
            'context': {
                'default_employee_ref': self.id,
            }
        }

    @api.constrains('image_1920', 'mobile_phone', 'aadhar_no', 'name_aadhar_card', 'pan_no', 'name_pan_card',
        'date_of_leaving', 'blood_group', 'street_c', 'city_c', 'state_c', 'zip_c', 'country_c', 'street_p',
        'city_p', 'state_p', 'zip_p', 'country_p', 'country_id', 'gender', 'birthday', 'fathers_name', 'spouse_complete_name', 'emp_emergency_contact', 'personal_bnk_name', 'personal_name', 'personal_acc_no', 'personal_bnk_add', 'personal_bnk_ifsc', 'pf_uan', 'prev_pf_address', 'prev_pension_no', 'prev_epf_no', 'paytm_amt', 'paytm_contact', 'marital', 'personal_email', 'cancel_check', 'is_ezestian', 'pf_opt', 'permit_no', 'is_account_info')
    def _validate_required_information(self):
        if not self.is_ezestian:
            if self.user_id.id == self.env.user.id:
                if not self.personal_email:
                    raise UserError(_("Fill Personal Email in Personal Information (Fellow e-Zestian's Profile)"))
                if not self.image_1920:
                    raise UserError(_("Upload Image"))
                if not self.street_c:
                    raise UserError(_("Fill Current Address in Personal Information (Fellow e-Zestian's Profile)"))
                if not self.city_c:
                    raise UserError(_("Fill Current City in Personal Information (Fellow e-Zestian's Profile)"))
                if not self.zip_c:
                    raise UserError(_("Fill Current Zip in Personal Information (Fellow e-Zestian's Profile)"))
                if not self.country_c:
                    raise UserError(_("Fill Current Country in Personal Information (Fellow e-Zestian's Profile)"))
                if not self.street_p:
                    raise UserError(_("Fill Permanent Address in Personal Information (Fellow e-Zestian's Profile)"))
                if not self.city_p:
                    raise UserError(_("Fill Permanent City in Personal Information (Fellow e-Zestian's Profile)"))
                if not self.zip_p:
                    raise UserError(_("Fill Permanent Zip in Personal Information (Fellow e-Zestian's Profile)"))
                if not self.country_p:
                    raise UserError(_("Fill Permanent Country in Personal Information (Fellow e-Zestian's Profile)"))
                if self.company_id.name in ['e-Zest Solutions Ltd, Zweigniederlassung Österreich', 'e-Zest Solutions Ltd.']:
                    if not self.country_id:
                        raise UserError(_("Fill Nationality (Country) in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.gender:
                        raise UserError(_("Fill Gender in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.birthday:
                        raise UserError(_("Fill Date of Birth in Personal Information (Fellow e-Zestian's Profile)"))
                    if self.marital == 'single':
                        if not self.fathers_name:
                            raise UserError(_("Fill Father Name in Personal Information (Fellow e-Zestian's Profile)"))
                    if self.marital == 'married':
                        if not self.fathers_name:
                            raise UserError(_("Fill Father Name in Personal Information (Fellow e-Zestian's Profile)"))
                        if not self.spouse_complete_name:
                            raise UserError(_("Fill Spouse Complete Name in Personal Information (Fellow e-Zestian's Profile)"))
                    if len(self.emp_emergency_contact) == 0:
                        raise UserError(_("Fill Emergency Contact in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.mobile_phone:
                        raise UserError(_("Fill Personal Mobile in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.personal_email:
                        raise UserError(_("Fill Personal Email in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.marital:
                        raise UserError(_("Fill Marital Status in Personal Information (Fellow e-Zestian's Profile)"))
                    if (self.is_account_info and self.employee_category.name == 'Contractor') or self.employee_category.name == 'e-Zestian' or self.employee_category.name == 'Intern':
                        if not self.personal_bnk_name:
                            raise UserError(_("Fill Personal Bank Name in Account Info (Fellow e-Zestian's Profile)"))
                        if not self.personal_name:
                            raise UserError(_("Fill Personal Your Name as per Bank records in Account Info (Fellow e-Zestian's Profile)"))
                        if not self.personal_acc_no:
                            raise UserError(_("Fill Personal Personal Account Number in Account Info (Fellow e-Zestian's Profile)"))
                        if not self.personal_acc_no.isdigit():
                            raise UserError(_("Fill numeric value only in Personal Account Number. in Account Info (Fellow e-Zestian's Profile)"))
                        if not self.personal_bnk_add:
                            raise UserError(_("Fill Personal Branch Name & Address in Account Info (Fellow e-Zestian's Profile)"))
                if self.company_id.name == 'e-Zest Solutions Ltd, Zweigniederlassung Österreich':
                    if not self.permit_no:
                        raise UserError(_("Fill Work Permit No. in Personal Information (Fellow e-Zestian's Profile)"))
                if self.company_id.name == 'e-Zest Solutions Ltd.':
                    if not self.aadhar_no:
                        raise UserError(_("Fill Aadhar Number in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.name_aadhar_card:
                        raise UserError(_("Fill Name as per Aadhar Card in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.pan_no:
                        raise UserError(_("Fill Pan Number in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.name_pan_card:
                        raise UserError(_("Fill Name As Per PAN Card in Personal Information (Fellow e-Zestian's Profile)"))
                    if self.is_date_leaving:
                        if not self.date_of_leaving:
                            raise UserError(_("Fill Date of Leaving of prev. org. in Personal Information (Fellow e-Zestian's Profile)"))
                        if self.date_of_leaving >= fields.Date.today():
                            raise UserError(_("Prev. org. Leaving date must be less than todays date in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.blood_group:
                        raise UserError(_("Fill Blood Group in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.state_c:
                        raise UserError(_("Fill Current State in Personal Information (Fellow e-Zestian's Profile)"))
                    if not self.state_p:
                        raise UserError(_("Fill Permanent State in Personal Information (Fellow e-Zestian's Profile)"))
                    if (self.is_account_info and self.employee_category.name == 'Contractor') or self.employee_category.name == 'e-Zestian' or self.employee_category.name == 'Intern':
                        if not self.personal_bnk_ifsc:
                            raise UserError(_("Fill Personal IFSC Code in Account Info (Fellow e-Zestian's Profile)"))
                    if not self.cancel_check:
                        raise UserError(_("Fill Cancel Cheque in Account Info (Fellow e-Zestian's Profile)"))
                    if self.pf_acc:
                        if not self.pf_uan:
                            raise UserError(_("Fill UAN Number in Account Info (Fellow e-Zestian's Profile)"))
                        if not self.prev_pf_address:
                            raise UserError(_("Fill Prev. Pf Address in Account Info (Fellow e-Zestian's Profile)"))
                        # if not self.prev_pension_no:
                        #     raise UserError(_("Fill Prev. Pension No. in Account Info (Fellow e-Zestian's Profile)"))
                        # if not self.prev_epf_no:
                        #     raise UserError(_("Fill Prev. EPF No. in Account Info (Fellow e-Zestian's Profile)"))
                    if not self.pf_acc:
                        if not self.pf_opt:
                            raise UserError(_("Fill Do you to opt from pf account in Account Info (Fellow e-Zestian's Profile)"))
                    if self.paytm_acc:
                        if not self.paytm_amt:
                            raise UserError(_("Fill Paytm Amount in Account Info (Fellow e-Zestian's Profile)"))
                        if not self.paytm_contact:
                            raise UserError(_("Fill Paytm Contact Number in Account Info (Fellow e-Zestian's Profile)"))
                    if len(self.resume_line_ids) == 0:
                        raise UserError(_("Fill Resume and Skill in Resume (Fellow e-Zestian's Profile)"))
                # if not self.passport_id:
                #     raise UserError(_("Fill Passport Number"))
                # if not self.date_of_leaving:
                #     raise UserError(_("Fill Date of Leaving of prev. org."))

    @api.depends('responsible_hr', 'is_exp_letter')
    def _get_responsible_hrs(self):
        current_user = self.env.user
        for employee in self:
            employee.show_exp_button = True
            employee.can_edit = False
            if (employee.responsible_hr and current_user.employee_id.id in employee.responsible_hr.related_hr.ids) or current_user.user_has_groups('base.group_system'):
                employee.can_edit = True
                if not employee.is_exp_letter and employee.show_exp_button:
                    employee.show_exp_button = False
                elif employee.is_exp_letter and employee.show_exp_button:
                    employee.show_exp_button = True
            else:
                employee.show_exp_button = False

    @api.depends('user_id')
    def _get_user_roles(self):
        for rec in self:
            rec.group_ids = self.env['res.groups'].search([
                ('name', 'ilike', 'Role:'),
                ('users', '=', rec.user_id.id)])

    @api.onchange('department_id')
    def _onchange_department(self):
        if self.department_id:
            resp_hr = self.env['hr.employee.group'].search([('department_ids', '=', self.department_id.id)])
            self.responsible_hr = resp_hr.id

    @api.onchange('set_of_parent')
    def _onchange_set_of_parent(self):
        if self.set_of_parent:
            self.mother_ins = True
            self.father_ins = True
        else:
            self.mother_ins = False
            self.father_ins = False

    @api.depends('department_id')
    def _get_parent_dept(self):
        for rec in self:
            rec.sbu_id = False
            if rec.department_id and ' Operations ' in rec.department_id.display_name.split('/'):
                department = rec.department_id
                if department.parent_id:
                    while department.parent_id.name != 'Operations':
                        department = department.parent_id
                    if department.parent_id.name == 'Operations':
                        rec.sbu_id = department.id

    @api.depends('joining_date', 'is_ezestian')
    def _compute_joining_month(self):
        for rec in self:
            rec.spouse_age = 0
            rec.child1_age = 0
            rec.child2_age = 0
            if rec.spouse_birth_date:
                today = fields.Date.today()
                diff = relativedelta(today, rec.spouse_birth_date)
                if not diff.years and diff.months:
                    if diff.months > 9:
                        rec.spouse_age = float('0.' + str(diff.months))
                    elif diff.months <= 9:
                        rec.spouse_age = float('0.0' + str(diff.months))
                elif diff.years and not diff.months:
                    rec.spouse_age = float(str(diff.years) + '.00')
                elif diff.years and diff.months:
                    if diff.years <= 0 and diff.months <= 0:
                        rec.spouse_age = 0.0
                    if diff.years >= 0 and diff.months > 9:
                        rec.spouse_age = float(str(diff.years) + '.' + str(diff.months))
                    if diff.years >= 0 and diff.months >= 0 and diff.months <= 9:
                        rec.spouse_age = float(str(diff.years) + '.0' + str(diff.months))
            if rec.child1_birth_date:
                today = fields.Date.today()
                diff = relativedelta(today, rec.child1_birth_date)
                if not diff.years and diff.months:
                    if diff.months > 9:
                        rec.child1_age = float('0.' + str(diff.months))
                    elif diff.months <= 9:
                        rec.child1_age = float('0.0' + str(diff.months))
                elif diff.years and not diff.months:
                    rec.child1_age = float(str(diff.years) + '.00')
                elif diff.years and diff.months:
                    if diff.years <= 0 and diff.months <= 0:
                        rec.child1_age = 0.0
                    if diff.years >= 0 and diff.months > 9:
                        rec.child1_age = float(str(diff.years) + '.' + str(diff.months))
                    if diff.years >= 0 and diff.months >= 0 and diff.months <= 9:
                        rec.child1_age = float(str(diff.years) + '.0' + str(diff.months))
            if rec.child2_birth_date:
                today = fields.Date.today()
                diff = relativedelta(today, rec.child2_birth_date)
                if not diff.years and diff.months:
                    if diff.months > 9:
                        rec.child2_age = float('0.' + str(diff.months))
                    elif diff.months <= 9:
                        rec.child2_age = float('0.0' + str(diff.months))
                elif diff.years and not diff.months:
                    rec.child2_age = float(str(diff.years) + '.00')
                elif diff.years and diff.months:
                    if diff.years <= 0 and diff.months <= 0:
                        rec.child2_age = 0.0
                    if diff.years >= 0 and diff.months > 9:
                        rec.child2_age = float(str(diff.years) + '.' + str(diff.months))
                    if diff.years >= 0 and diff.months >= 0 and diff.months <= 9:
                        rec.child2_age = float(str(diff.years) + '.0' + str(diff.months))
            if rec.joining_date:
                rec.joining_month = str(rec.joining_date.month)
            else:
                rec.joining_month = False

    @api.depends('direct_badge_ids', 'user_id.badge_ids.employee_id')
    def _compute_unique_badges(self):
        for employee in self:
            badge_ids = employee.badge_ids.mapped('badge_id')
            employee.uniq_badge_ids = badge_ids

    def _search_relevant_exp_aftr(self, operator, value):
        employee_exp_domain = []
        for rec in self.env['hr.employee'].search([]):
            if rec.relevant_exp_aftr_join and operator == 'ilike' and value.lower() in rec.relevant_exp_aftr_join.lower():
                employee_exp_domain.append(('id', '=', rec.id))
            if rec.relevant_exp_aftr_join and operator == 'not like' and value.lower() in rec.relevant_exp_aftr_join.lower():
                employee_exp_domain.append(('id', '=', rec.id))
            if rec.relevant_exp_aftr_join and operator == '=' and value.lower() in rec.relevant_exp_aftr_join.lower():
                employee_exp_domain.append(('id', '=', rec.id))
            if rec.relevant_exp_aftr_join and operator == '!=' and value.lower() in rec.relevant_exp_aftr_join.lower():
                employee_exp_domain.append(('id', '=', rec.id))
            else:
                employee_exp_domain.append(('id', '=', None))
        for rec in range(0, len(employee_exp_domain) - 1):
            employee_exp_domain.insert(rec, '|')
        return employee_exp_domain

    def action_show_org(self):
        self.sudo().show_org_chart = True
        # return {
        #     'name': _("Org Chart"),
        #     'type': 'ir.actions.act_url',
        #     'url': '/hr/get_org_chart?%(employee_id)s' % {'employee_id': self.id},
        # }

    def update_show_org_chart(self):
        self.sudo().show_org_chart = False

    def action_image_download(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        active_ids = self._context.get('active_ids')
        return {
            'name': _("Bulk Image Download"),
            'type': 'ir.actions.act_url',
            'url': base_url + '/image_download/zip?file_ids=%s' % active_ids,
        }

    @api.onchange('father_ins', 'mother_ins', 'single_parent', 'set_of_parent')
    def _onchange_mediclaim_details(self):
        if self.single_parent:
            self.single_parent_amt1 = False
            self.set_of_parent = False
            self.set_of_parent_amt1 = False
        elif not self.single_parent:
            self.single_parent_amt1 = False
            self.father_ins = False
            self.mother_ins = False
        elif self.set_of_parent:
            self.set_of_parent_amt1 = False
            self.father_ins = False
            self.mother_ins = False
            self.single_parent = False
        elif not self.set_of_parent:
            self.set_of_parent_amt1 = False

    def _get_default_company_currency(self):
        return self.env.company.currency_id.id

    @api.model
    @api.onchange('next_appraisal')
    def _compute_revise_salary_visible(self):
        for rec in self:
            if not rec.next_appraisal:
                rec.sudo().is_revise_salary_visible = True
                rec.sudo().is_revise_salary = False
            if rec.next_appraisal:
                rec.sudo().is_revise_salary_visible = False

    personal_mobile = fields.Char(string='Mobile', related='address_home_id.mobile')
    personal_email = fields.Char(string='Personal Email', store=True, track_visibility="onchange")
    emp_emergency_contact = fields.One2many('hr.emergency.contact', 'employee_obj', string='e-Zestian Emergency Contact', copy=True)
    joining_date = fields.Date(string='Joining Date', track_visibility="onchange")
    id_expiry_date = fields.Date(string='Expiry Date', help='Expiry date of Identification ID')
    passport_expiry_date = fields.Date(string='Passport Expiry Date', help='Expiry date of Passport ID')
    id_attachment_id = fields.Many2many('ir.attachment', 'id_attachment_rel', 'id_ref', 'attach_ref',
                                        string="Attachment", help='You can attach the copy of your Id')
    passport_attachment_id = fields.Many2many('ir.attachment', 'passport_attachment_rel', 'passport_ref', 'attach_ref1',
                                              string="Passport Attachment", help='You can attach the copy of Passport')
    fam_ids = fields.One2many('hr.employee.family', 'employee_id', string='Family', help='Family Information')
    aadhar_no = fields.Char('Aadhar Number', size=12, track_visibility="onchange")
    pan_no = fields.Char('PAN Number', size=10, track_visibility="onchange")
    business_entities = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, string='Business Entities', track_visibility="onchange")
    relevant_exp_aftr_join = fields.Char(string='Relevant Experience Joining', compute='_compute_experience', search='_search_relevant_exp_aftr')
    skills = fields.Many2one('hr.primary.skill', string='Primary Skills')
    account = fields.Many2one('hr.account', string='Deployability', track_visibility="onchange")
    blood_group = fields.Selection([
        ('o+', "O+"), ('o-', "O-"), ('a+', "A+"), ('a-', "A-"), ('b+', "B+"),
        ('b-', "B-"), ('ab+', "AB+"), ('ab-', "AB-")], string="Blood Group", track_visibility="onchange")
    band_grade = fields.Many2one('hr.band', string='Band/Grade', track_visibility="onchange")
    payroll_loc = fields.Many2one('hr.payroll.location', track_visibility="onchange", string='Payroll Location')
    show_details = fields.Boolean(string='Show Details', compute='_compute_show_details')
    show_skills = fields.Boolean(string='Show Skills', compute='_compute_show_skills')
    confirmation_period = fields.Integer(string='Confirmation Period', default=90, track_visibility="onchange")
    confirmation_date = fields.Date(string='Confirmation Date', compute="_compute_confirm_date", store=True, track_visibility="onchange")
    exit_date = fields.Date(string='Exit Date', track_visibility='onchange', compute="_get_exit_date", readonly=False, store=True)
    street_c = fields.Char('Current Address Street', tracking=True)
    street2_c = fields.Char('Current Address street2', tracking=True)
    city_c = fields.Char('Current Address City', tracking=True)
    country_c = fields.Many2one('res.country', 'Current Address Country', tracking=True)
    state_c = fields.Many2one('res.country.state', 'Current Address State', domain="[('country_id', '=?', country_c)]", tracking=True)
    zip_c = fields.Char('Current Address ZIP', tracking=True)
    street_p = fields.Char('Permanent Address Street', tracking=True)
    street2_p = fields.Char('Permanent Address street2', tracking=True)
    city_p = fields.Char('Permanent Address City', tracking=True)
    country_p = fields.Many2one('res.country', 'Permanent Address Country', tracking=True)
    state_p = fields.Many2one('res.country.state', 'Permanent Address State', domain="[('country_id', '=?', country_p)]", tracking=True)
    zip_p = fields.Char('Permanent Address ZIP', tracking=True)
    social_facebook = fields.Char('Facebook Account', tracking=True)
    social_linkedin = fields.Char('LinkedIn Account', tracking=True)
    social_twitter = fields.Char('Twitter Account', tracking=True)
    social_instagram = fields.Char('Instagram Account', tracking=True)
    social_googleplus = fields.Char('Google+ Account', tracking=True)
    social_personal_website = fields.Char('Person Website/Blog Website Account', tracking=True)
    social_whatsapp = fields.Char('Whatsapp Account')
    question11 = fields.Text(string='Qualities?', tracking=True)
    question1 = fields.Text(string='Where are your roots from - your native place?', tracking=True)
    question2 = fields.Text(string='Extra-curricular activities that keeps you engaged after work - your hobbies?', tracking=True)
    question3 = fields.Text(string='Taste buds calling - what is your favorite Food Item?', tracking=True)
    question4 = fields.Text(string='Now something about Music. You like Music – which type?', tracking=True)
    question5 = fields.Text(string='Place(s) you love Travelling to?', tracking=True)
    question6 = fields.Text(string='Now some literature - any favorite Books?', tracking=True)
    question7 = fields.Text(string='In which Attire you love to see yourself in?', tracking=True)
    question8 = fields.Text(string='What do you do when there is nothing to do – your Favorite Pastime Activity?', tracking=True)
    question9 = fields.Text(string='Who inspires you - your Role Model?', tracking=True)
    question10 = fields.Text(string='Slogan you swear by?', tracking=True)
    kotak_acc = fields.Boolean(string="Have existing Kotak Bank Account?", tracking=True)
    kotak_acc_no = fields.Integer(string="Account Number", tracking=True)
    kotak_acc_brn = fields.Char(string="Branch Name", tracking=True)
    kotak_acc_active = fields.Date(string="Active Since", tracking=True)
    personal_bnk_name = fields.Char(string="Bank Name", tracking=True)
    personal_name = fields.Char(string="Your Name as per Bank records", tracking=True)
    personal_acc_no = fields.Char(string="Personal Account Number", size=16, tracking=True)
    personal_bnk_add = fields.Char(string="Branch Name & Address", tracking=True)
    personal_bnk_ifsc = fields.Char(string="IFSC Code", tracking=True)
    cancel_check = fields.Binary(string="Cancel Cheque")
    pf_acc = fields.Boolean(string="Did you have a PF account with previous organization?", tracking=True)
    pf_acc_status = fields.Char(string="If Yes, Previous PF account Status", tracking=True)
    pf_uan = fields.Char(string="UAN Number", size=20, tracking=True)
    pf_opt = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="If no PF account, Do you want to opt for a PF account?", tracking=True)
    paytm_acc = fields.Boolean(string="Want to opt?", tracking=True)
    paytm_amt = fields.Selection([('1100', '1100'), ('2200', '2200')], string="Select Amount?", tracking=True)
    hr_name = fields.Char(string='Ref. HR Name')
    hr_designation = fields.Char(string='Ref. HR Designation')
    hr_email = fields.Char(string='Ref. HR Email')
    hr_contact = fields.Char(string='Ref. HR Contact')
    manager_name = fields.Char(string='Ref. Manager Name')
    manager_designation = fields.Char(string='Ref. Manager Designation')
    manager_email = fields.Char(string='Ref. Manager Email')
    manager_contact = fields.Char(string='Ref. Manager Contact')
    ref_name = fields.Char(string='Name of your Friend/Family')
    ref_contact = fields.Char(string='Phone No.')
    ref_email = fields.Char(string='e-mail Id')
    ref_skill = fields.Char(string='Technology / Skill')
    empl_shift = fields.Boolean(string="Rotational Shift", default=False, tracking=True)
    current_address_copy = fields.Boolean(string='Copy Current Address')
    is_extend = fields.Boolean(string='Is Confirmation Extend', track_visibility="onchange")
    is_fired = fields.Boolean(string='Is Fired', track_visibility="onchange")
    extend_period = fields.Char(string="Extended Period", track_visibility="onchange", help="Add extend days with previous extend days (eg: 30 + 30)")
    extend_reason = fields.Text(string="Extend Reason", track_visibility="onchange")
    fired_reason = fields.Text(string="Fired Reason", track_visibility="onchange")
    notice_period = fields.Integer(string="Notice Period", track_visibility="onchange", default=60)
    employee_category = fields.Many2one("hr.contract.type", track_visibility="onchange", string="Team Member Category")
    location_work = fields.Many2one("hr.location.work", track_visibility="onchange", string="e-Zestian Work Location")
    is_abscond = fields.Boolean(string="Is Abscond", track_visibility="onchange")
    abscond = fields.Date(string="Abscond Date", track_visibility="onchange")
    resign_date = fields.Date('Resign Date', readonly=True, track_visibility="onchange", help="This is the e-Zestian resignation date")
    confirmation_status = fields.Selection([('due','Due'),('in_progress','In Progress'),('extended','Extend'),('confirmed','Confirmed')], track_visibility="onchange", default="due")
    lwf = fields.Boolean(string="Is LWF", track_visibility="onchange")
    ltc = fields.Boolean(string="Is LTC", track_visibility="onchange")
    ltc_amount = fields.Float(string="LTC Amount", track_visibility="onchange")
    paytm_contact = fields.Char(string="Paytm Contact", track_visibility="onchange")
    is_technical = fields.Selection([('technical','Technical'),('non_technical','Non-Technical')], track_visibility="onchange")
    pf_status = fields.Selection([('transfer','Transfer'),('withdrawal','Withdrawal')], track_visibility="onchange")
    fathers_name = fields.Char(string="Father's Name", track_visibility="onchange")
    nda_signed_off = fields.Date(string="NDA Signed Date",tracking=True)
    coc_signed_off = fields.Date(string="Code of Conduct Signed Date",tracking=True)
    anti_sexual_signed_off = fields.Date(string="Anti-sexual harassment policy acknowledgement date", tracking=True)
    name_aadhar_card = fields.Char(string="Name As Per Aadhar Card",tracking=True)
    name_pan_card = fields.Char(string="Name As Per PAN Card",tracking=True)
    prev_pf_address = fields.Char(string="Prev. Pf Address",tracking=True)
    prev_pension_no = fields.Char(string="Prev. Pension No.",tracking=True)
    prev_epf_no = fields.Char(string="Prev. EPF No.",tracking=True)
    date_of_leaving = fields.Date(string="Date of Leaving of prev. org.",tracking=True)
    passport_validity_date = fields.Date(string="Passport Validity Date",tracking=True)
    passport_country_id = fields.Many2one('res.country', string="Passport Issued Country",tracking=True)
    is_exp_letter = fields.Boolean(string="Is Exp Letter", track_visibility="onchange")
    is_submit = fields.Boolean(string="Is Submit")
    is_confirmation_check = fields.Boolean(string="Is Confirmation Check")
    show_exp_button = fields.Boolean(string="Show Experience Button", compute="_get_responsible_hrs")
    can_edit = fields.Boolean(string="Responsible HR Can Edit", compute="_get_responsible_hrs")
    is_hr_verified = fields.Boolean(string="HR Verified")
    fnf_days = fields.Char(string="FNF Days", default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_employee_updation.employee_fnf_days'))
    group_ids = fields.Many2many('res.groups', string="Roles", compute="_get_user_roles")
    is_date_leaving = fields.Boolean(string="Is Date of Leaving?", tracking=True)
    is_watermark = fields.Boolean(string="Print with LetterHead ?", tracking=True)
    single_parent = fields.Boolean(string="Single parent/ in-laws", track_visibility="onchange")
    single_parent_amt = fields.Integer(string="Single Parent/in-law Rs.(OLD)", track_visibility="onchange")
    single_parent_amt1 = fields.Selection([('2', '2 Lac'), ('3', '3 Lac')], string="Sum Insured", track_visibility="onchange")
    set_of_parent = fields.Boolean(string="Set of parents/in- laws", track_visibility="onchange")
    set_of_parent_amt = fields.Integer(string="Set of Parents/in-laws Rs.(OLD)", track_visibility="onchange")
    set_of_parent_amt1 = fields.Selection([('2', '2 Lac'), ('3', '3 Lac')], string="Sum Insured", track_visibility="onchange")
    father_n_law = fields.Char(string="Father/ Father in law's name", track_visibility="onchange")
    father_n_dob = fields.Date(string="Father/ Father in law's DOB", track_visibility="onchange")
    mother_n_law = fields.Char(string="Mother/ Mother in law's name", track_visibility="onchange")
    mother_n_dob = fields.Date(string="Mother/ Mother in law's DOB", track_visibility="onchange")
    father_ins = fields.Boolean(string="For Father/ Father in law's", tracking=True)
    mother_ins = fields.Boolean(string="For Mother/ Mother in law's", tracking=True)
    employee = fields.Many2one('hr.employee')
    responsible_recruiter_ids = fields.One2many('hr.employee', 'employee', string="Responsible Recruiter(Not in User)", tracking=True)
    responsible_recruiter = fields.Many2many('hr.employee', 'employee_rel', 'employee_id', string="Responsible Recruiter", tracking=True)
    prev_department_id = fields.Many2one('hr.department', string="Prev Department")
    dept_change_date = fields.Date(string="Dept change date")
    sbu_id = fields.Many2one('hr.department', string="SBU", compute="_get_parent_dept", store=True, compute_sudo=True)
    joining_month = fields.Selection([('1','January'),('2','February'),('3','March'),('4','April'),
                    ('5','May'),('6','June'),('7','July'),('8','August'),('9','September'),('10','October'),
                    ('11','November'),('12','December')], compute="_compute_joining_month", compute_sudo=True, store=True)
    consultant_salary = fields.Char(string="Salary Details", tracking=True)
    applicant_id = fields.Many2one('hr.applicant', string="Applicant")
    contractor_type = fields.Selection([('direct','Direct'),('third_party', 'Third Party')], string="Type of contractor")
    vendor_name = fields.Char(string="Vendor Name(Char)")
    vendor_id = fields.Many2one('hr.vendor', string="Vendor Name", tracking=True)
    is_invitation = fields.Boolean(string="Is Inviation")
    consultancy_name = fields.Many2one('hr.job.consultancy', string="Consultancy Name", tracking=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', default=_get_default_company_currency)
    emp_wage = fields.Monetary(string="Monthly CTC", currency_field='company_currency_id', tracking=True)
    annual_bonus = fields.Monetary(string="Annual Bonus", currency_field='company_currency_id', tracking=True)
    lin = fields.Char(string="LIN")
    uniq_badge_ids = fields.One2many('gamification.badge', 'employee_id', string="Unique Badges", compute="_compute_unique_badges")
    show_org_chart = fields.Boolean(string="Show Org Chart", default=False)
    # hr base field inherit
    address_id = fields.Many2one('res.partner', 'Work Address', track_visibility="onchange")
    work_email = fields.Char(related='user_id.login', string='Work Email')
    department_id = fields.Many2one('hr.department', 'Department', track_visibility="onchange")
    parent_id = fields.Many2one('hr.employee', 'Manager', track_visibility="onchange")
    category_ids = fields.Many2many('hr.employee.category', 'employee_category_rel', 'emp_id', 'category_id',
        string='Tags', track_visibility="onchange")
    job_title = fields.Char(string="Designation Prev", track_visibility="onchange")
    job_id = fields.Many2one('hr.job', 'Designation', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('is_designation','in',['in_employee', 'both'])]")
    mobile_phone = fields.Char('Personal Mobile', track_visibility="onchange")
    address_home_id = fields.Many2one(
        'res.partner', 'Private Address', help='Enter here the private address of the e-Zestian, not the one linked to your company.'
    )
    is_address_home_a_company = fields.Boolean(
        'The e-Zestian adress has a company linked',
        compute='_compute_is_address_home_a_company',
    )
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', track_visibility="onchange")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], track_visibility="onchange")
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', default='single', track_visibility="onchange")
    birthday = fields.Date('Date of Birth', track_visibility="onchange")
    identification_id = fields.Char(string='Identification No', track_visibility="onchange", default='New')
    # identification_id = fields.Char(string='Identification No', track_visibility="onchange")
    passport_id = fields.Char('Passport No', track_visibility="onchange")
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Kotak Bank Details',
        domain="[('partner_id', '=', address_home_id)]",
        help='e-Zestian bank salary account', track_visibility="onchange")
    permit_no = fields.Char('Work Permit No', track_visibility="onchange")
    visa_no = fields.Char('Visa No', track_visibility="onchange")
    visa_expire = fields.Date('Visa Expire Date', track_visibility="onchange")
    spouse_name = fields.Char(string="Spouse Name", default="NA", required=True, tracking=True)
    chlid1_name = fields.Char(string="Child1 Name", default="NA", required=True, tracking=True)
    chlid2_name = fields.Char(string="Child2 Name", default="NA", required=True, tracking=True)
    spouse_age = fields.Float(string="Spouse Age", tracking=True, compute="_compute_joining_month")
    child1_age = fields.Float(string="Child1 Age", tracking=True, compute="_compute_joining_month")
    child2_age = fields.Float(string="Child2 Age", tracking=True, compute="_compute_joining_month")
    spouse_birth_date = fields.Date(string="Spouse Birth Date", tracking=True)
    child1_birth_date = fields.Date(string="Child1 Birth Date", tracking=True)
    child2_birth_date = fields.Date(string="child2 Birth Date", tracking=True)
    responsible_hr = fields.Many2one('hr.employee.group', string="Responsible HR", tracking=True)
    planned_join_date = fields.Date(string="Planned Joining Date", track_visibility='onchange')
    barcode = fields.Char(string="Badge ID", help="ID used for e-Zestian identification.", default=_default_random_barcode, copy=False)
    is_account_info = fields.Boolean(string="Is Account Info Required", help="If it is checked then Personal Savings Bank Details are required.")
    is_revise_salary = fields.Boolean('Revise Salary', default=False)
    is_revise_salary_visible = fields.Boolean('Revise Salary', default=False)
    revised_salary_effective_from = fields.Date(string="Revised salary Effective From", tracking=True)
    next_appraisal = fields.Date(string="Next Appraisal Date", tracking=True, compute='_compute_revise_salary_visible', readonly=False)


class GroupsInherit(models.Model):
    _inherit = "res.groups"

    def give_group_user(self):
        if self.env.context.get('default_user_id'):
            self.sudo().write({'users': [(4, int(self.env.context.get('default_user_id')))]})
            self.is_group_access = True
            return {
                'name': _('Groups'),
                'view_mode': 'tree',
                'res_model': 'res.groups',
                'type': 'ir.actions.act_window',
                'context': {'create': False, 'delete': False, 'default_user_id': self.env.context.get('default_user_id')},
                'domain': [('name', 'ilike', 'Role')],
                'target': 'new',
            }

    def remove_group_user(self):
        if self.env.context.get('default_user_id'):
            self.sudo().write({'users': [(3, int(self.env.context.get('default_user_id')))]})
            self.is_group_access = False
            return {
                'name': _('Groups'),
                'view_mode': 'tree',
                'res_model': 'res.groups',
                'type': 'ir.actions.act_window',
                'context': {'create': False, 'delete': False, 'default_user_id': self.env.context.get('default_user_id')},
                'domain': [('name', 'ilike', 'Role')],
                'target': 'new',
            }

    def _compute_access(self):
        for rec in self:
            if self.env.context.get('default_user_id'):
                user = self.env['res.users'].browse(int(self.env.context.get('default_user_id')))
                if rec.id in user.groups_id.ids:
                    rec.is_group_access = True
                else:
                    rec.is_group_access = False
            else:
                rec.is_group_access = False

    is_group_access = fields.Boolean(string="Group Access", compute="_compute_access")


class GamificationBadgeInherit(models.Model):
    _inherit = "gamification.badge"

    employee_id = fields.Many2one('hr.employee', string="Employee")

class HrJobInherit(models.Model):
    _inherit = "hr.job"

    is_designation = fields.Selection([
        ('in_job', 'In Job Position'),
        ('in_employee', 'In Designation'),
        ('both', 'Both')], string="Show Designation", default="both")
