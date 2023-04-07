# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime, timedelta, date
from dateutil. relativedelta import relativedelta

class BirthdayAnniversary(models.Model):
    _name = 'birthday.anni'
    _description = "Birthday and Anniversary"


    def _cron_mail_birth_anni(self):
        employees = self.env['hr.employee'].sudo().search([])
        # employees = self.env['hr.employee'].sudo().search([('joining_date', '=', True)])
        today = datetime.today().date()
        next_day = today + relativedelta(days=1)
        if employees:
            message_body = 'Joining Anniversary List For : %s <br/>' %(next_day)
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">' \
                            '<th>' + 'Sr. No.' + '</th>' \
                            '<th>' + 'Employee Name' + '</th>' \
                            '<th>' + 'Joining Date' + '</th>' \
                            '<th>' + 'Years Completed' + '</th>' \
                            '<th>' + 'Team Member Category' + '</th>' \
                            '<th>' + 'Exit Date' + '</th>' \
                            '</tr>'
            count = 1
            for emp in employees:
                if emp.joining_date:
                    days_diff = next_day - emp.joining_date
                    years_diff = ((days_diff.days + days_diff.seconds/86400)/365)//1
                    if next_day.strftime('%d-%m') == emp.joining_date.strftime('%d-%m'):
                        message_body += '<tr style="text-align:center;">' \
                                            '<td>' + str(count) + '</td>'\
                                            '<td>' + str(emp.name) + '</td>'\
                                            '<td>' + str(emp.joining_date) + '</td>'\
                                            '<td>' + str(years_diff) + '</td>'\
                                            '<td>' + str(emp.employee_category.name) + '</td>'\
                                            '<td>' + str(emp.exit_date) + '</td>'\
                                        '</tr>'
                        count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            template_values = {
                'subject': 'Joining Anniversay Employee List for "%s"'%(next_day),
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': 'hrd@e-zest.in',
                'email_cc': 'unity@e-zest.in',
                'auto_delete': True,
            }
            self.env['mail.mail'].create(template_values).sudo().send()

            message_body1 = 'Birthday List For : %s <br/>' % (next_day)
            message_body1 += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body1 += '<tr style="text-align:center;">' \
                                 '<th>' + 'Sr. No.' + '</th>' \
                                 '<th>' + 'Employee Name' + '</th>' \
                                 '<th>' + 'Birthdate' + '</th>' \
                                 '<th>' + 'Team Member Category' + '</th>' \
                                 '<th>' + 'Exit Date' + '</th>' \
                             '</tr>'
            count1 = 1
            for emp1 in employees:
                if emp1.birthday and next_day.strftime('%d-%m') == emp1.birthday.strftime('%d-%m'):
                    message_body1 += '<tr style="text-align:center;">' \
                                         '<td>' + str(count) + '</td>' \
                                         '<td>' + str(emp1.name) + '</td>' \
                                         '<td>' + str(emp1.birthday) + '</td>' \
                                         '<td>' + str(emp1.employee_category.name) + '</td>' \
                                         '<td>' + str(emp1.exit_date) + '</td>' \
                                     '</tr>'
                    count1 += 1
            message_body1 += '</table>' + '<br/>' + '<br/>'
            template_values1 = {
                'subject': 'Birthday Employee List for "%s"' % (next_day),
                'body_html': message_body1,
                'email_from': 'unity@e-zest.in',
                'email_to': 'hrd@e-zest.in',
                'email_cc': 'unity@e-zest.in',
                'auto_delete': True,
            }
            self.env['mail.mail'].create(template_values1).sudo().send()









