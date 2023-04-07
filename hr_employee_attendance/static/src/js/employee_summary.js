odoo.define('hr_employee_attendance.EmployeeSummary', function (require) {
"use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var qweb = core.qweb;

    var SummaryListController = ListController.extend({
        buttons_template: 'SummaryListView.buttons',
        /**
         * Extends the renderButtons function of ListView by adding an event listener
         * on the bill upload button.
         *
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments); // Possibly sets this.$buttons
            if (this.$buttons) {
                var self = this;
                this.$buttons.on('click', '.o_employee_summary_button', function () {
                    var state = self.model.get(self.handle, {raw: true});
                    var context = state.getContext()
                    return self._rpc({
                    	model: 'employee.attendance.leave.summary',
		                method: 'action_summary_report',
		                args: [[]]
		            }).then(function(action){
		            	action.views = [[false, 'form']];
		            	self.do_action(action);
		            });
                });
                // this.$buttons.on('click', '.o_employee_reg_button', function () {
                //     return self.do_action({
                //         name: 'Regularization',
                //         type: 'ir.actions.act_window',
                //         res_model: 'attendance.regular',
                //         target: 'current',
                //         views: [[false, 'form']],
                //     });
                // });
                this.$buttons.on('click', '.o_employee_timesheet_button', function () {
                    var state = self.model.get(self.handle, {raw: true});
                    var context = state.getContext()
                    return self._rpc({
                        model: 'employee.summary.report',
                        method: 'open_timesheet',
                        args: [[]]
                    }).then(function(action){
                        action.views = [[false, 'form']];
                        self.do_action(action);
                    });
                });
                // this.$buttons.on('click', '.o_employee_timesheet_button', function () {
                //     return self.do_action({
                //         name: 'TImesheet',
                //         type: 'ir.actions.act_window',
                //         res_model: 'account.analytic.line',
                //         target: 'current',
                //         view_id: self.env.ref('hr_timesheet.hr_timesheet_line_form').id,
                //         views: [[false, 'form']],
                //     });
                // });
                this.$buttons.on('click', '.o_employee_reg_view_button', function () {
                    return self.do_action({
                        name: 'Regularization',
                        type: 'ir.actions.act_window',
                        res_model: 'attendance.regular',
                        target: 'current',
                        views: [[false, 'list'], [false, 'form']],
                        context: {'search_default_my_reg':1},
                    });
                });
            }
        }
    });

    var LeaveSummaryListController = ListController.extend({
        buttons_template: 'LeaveSummaryListView.buttons',
        /**
         * Extends the renderButtons function of ListView by adding an event listener
         * on the bill upload button.
         *
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments); // Possibly sets this.$buttons
            if (this.$buttons) {
                var self = this;
                this.$buttons.on('click', '.o_employee_summary_button', function () {
                    var state = self.model.get(self.handle, {raw: true});
                    var context = state.getContext()
                    return self._rpc({
                        model: 'employee.attendance.leave.summary',
                        method: 'action_summary_report',
                        args: [[]]
                    }).then(function(action){
                        action.views = [[false, 'form']];
                        self.do_action(action);
                    });
                });
                this.$buttons.on('click', '.o_employee_leave_request', function () {
                    return self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'hr.leave',
                        target: 'current',
                        views: [[false, 'form']],
                    });
                });
            }
        }
    });

    var SummaryListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: SummaryListController,
        }),
    });

    var LeaveSummaryListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: LeaveSummaryListController,
        }),
    });

    viewRegistry.add('employee_summary_tree', SummaryListView);
    viewRegistry.add('leave_employee_summary_tree', LeaveSummaryListView);
});
