odoo.define('project_role.OpenAllocation', function (require) {
"use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var qweb = core.qweb;

    var AllocationListController = ListController.extend({
        buttons_template: 'allocationListView.buttons',
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
                // this.$buttons.on('click', '.o_open_allocation_button', function () {
                //     var state = self.model.get(self.handle, {raw: true});
                //     var context = state.getContext()
                //     return self._rpc({
                //         model: 'employee.attendance.leave.summary',
                //         method: 'action_summary_report',
                //         args: [[]]
                //     }).then(function(action){
                //         action.views = [[false, 'form']];
                //         self.do_action(action);
                //     });
                // });
                this.$buttons.on('click', '.o_open_allocation_button', function () {
                    return self.do_action({
                        name: 'Allocation',
                        type: 'ir.actions.act_window',
                        res_model: 'project.assignment',
                        target: 'current',
                        views: [[false, 'form']],
                    });
                });
            }
        }
    });

    var AllocationListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: AllocationListController,
        }),
    });

    viewRegistry.add('open_allocation_tree', AllocationListView);
});
