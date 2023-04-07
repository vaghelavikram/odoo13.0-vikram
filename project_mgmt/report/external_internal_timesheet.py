# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class TimesheetAttendance(models.Model):
    _name = 'hr.external.internal.timesheet.report'
    _auto = False
    _description = 'External Internal Timesheet Report'

    user_id = fields.Many2one('res.users')
    date = fields.Date()
    total_external_timesheet = fields.Float()
    total_internal_timesheet = fields.Float()
    total_difference = fields.Float()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""CREATE OR REPLACE VIEW %s AS (
            SELECT
                max(id) AS id,
                t.user_id,
                t.date,
                coalesce(sum(t.int_timesheet), 0) AS total_internal_timesheet,
                coalesce(sum(t.ext_timesheet), 0) AS total_external_timesheet,
                coalesce(sum(t.int_timesheet), 0) - coalesce(sum(t.ext_timesheet), 0) as total_difference
            FROM (
                SELECT
                    its.id AS id,
                    its.user_id AS user_id,
                    its.unit_amount AS int_timesheet,
                    NULL AS ext_timesheet,
                    its.date AS date
                FROM account_analytic_line AS its
                WHERE its.project_id IS NOT NULL AND its.external_timesheet IS NOT True AND its.project_id != 2
            UNION ALL
                SELECT
                    ts.id AS id,
                    ts.user_id AS user_id,
                    NULL AS int_timesheet,
                    ts.unit_amount AS ext_timesheet,
                    ts.date AS date
                FROM account_analytic_line AS ts
                WHERE ts.project_id IS NOT NULL AND ts.external_timesheet IS True
            ) AS t
            GROUP BY t.user_id, t.date
            ORDER BY t.date
        )
        """ % self._table)
