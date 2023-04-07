odoo.define('hr_employee_updation.OrgChartLoad', function (require) {
"use strict";

var FieldOrgChart = require('web.OrgChart');
var core = require('web.core');
var session = require('web.session');

var QWeb = core.qweb;
var _t = core._t;

FieldOrgChart.include({
    _render: function () {
        if (!this.recordData.id) {
            return this.$el.html(QWeb.render("hr_org_chart", {
                managers: [],
                children: [],
            }));
        }
        else if (!this.employee) {
            // the widget is either dispayed in the context of a hr.employee form or a res.users form
            this.employee = this.recordData.employee_ids !== undefined ? this.recordData.employee_ids.res_ids[0] : this.recordData.id;
        }

        var self = this;
        return this._getOrgData().then(function (orgData) {
            if (_.isEmpty(orgData)) {
                orgData = {
                    managers: [],
                    children: [],
                }
            }
            orgData.view_employee_id = self.recordData.id;
            self.$el.html(QWeb.render("hr_org_chart", orgData));
            self.$('[data-toggle="popover"]').each(function () {
                $(this).popover({
                    html: true,
                    title: function () {
                        var $title = $(QWeb.render('hr_orgchart_emp_popover_title', {
                            employee: {
                                name: $(this).data('emp-name'),
                                id: $(this).data('emp-id'),
                            },
                        }));
                        $title.on('click',
                            '.o_employee_redirect', _.bind(self._onEmployeeRedirect, self));
                        return $title;
                    },
                    container: this,
                    placement: 'left',
                    trigger: 'focus',
                    content: function () {
                        var $content = $(QWeb.render('hr_orgchart_emp_popover_content', {
                            employee: {
                                id: $(this).data('emp-id'),
                                name: $(this).data('emp-name'),
                                direct_sub_count: parseInt($(this).data('emp-dir-subs')),
                                indirect_sub_count: parseInt($(this).data('emp-ind-subs')),
                            },
                        }));
                        $content.on('click',
                            '.o_employee_sub_redirect', _.bind(self._onEmployeeSubRedirect, self));
                        return $content;
                    },
                    template: QWeb.render('hr_orgchart_emp_popover', {}),
                });
            });
            self._rpc({
                model: 'hr.employee',
                method: 'update_show_org_chart',
                args: [self.employee],
            })
        });
    },
});
});