# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrPlanActivityTypeInherit(models.Model):
    _inherit = 'hr.plan.activity.type'

    topic = fields.Char('Topic')
    tentative_training_date = fields.Date('Tentative training date')
    trainer = fields.Many2one('hr.employee', 'Trainer')
    training_proposed = fields.Many2one('hr.employee', 'Training Proposed By')
    courses = fields.Many2one('slide.channel', string="Courses")


class HrPlanInherit(models.Model):
    _inherit = 'hr.plan'

    plan_type = fields.Selection([('generic', 'Generic'), ('training', 'Training')], string="Plan Type", default="training")


class HrPlanWizardInherit(models.TransientModel):
    _inherit = 'hr.plan.wizard'

    def action_launch(self):
        if self.plan_id.plan_type == 'training':
            for activity_type in self.plan_id.plan_activity_type_ids:
                responsible = activity_type.get_responsible_id(self.employee_id)
                if activity_type.courses:
                    note = activity_type.summary + 'Link: <a href="{0}">{1}</a>'.format(activity_type.courses.website_url, activity_type.courses.name)
                else:
                    note = activity_type.summary
                if self.env['hr.employee'].with_user(self.employee_id.user_id).check_access_rights('read', raise_exception=False):
                    # schedule activity to trainer
                    self.env['mail.activity'].create({
                        'res_id': self.employee_id.id,
                        'res_model_id': self.env['ir.model']._get('hr.employee').id,
                        'summary': activity_type.topic,
                        'note': note,
                        'activity_type_id': activity_type.activity_type_id.id,
                        # 'user_id': self.employee_id.user_id.id,
                        'user_id': activity_type.trainer.user_id.id if activity_type.trainer.user_id else self.employee_id.user_id.id,
                    })
        else:
            return super(HrPlanWizardInherit, self).action_launch()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'name': self.employee_id.display_name,
            'view_mode': 'form',
            'views': [(False, "form")],
        }
