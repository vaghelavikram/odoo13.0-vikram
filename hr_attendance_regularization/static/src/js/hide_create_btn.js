odoo.define('attendance_reg.hide_edit_btn', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var FormController = require('web.FormController');
    var session = require('web.session');
    var core = require('web.core');
    var _t = core._t;

    FormController.include({

        /**
         * @private
         */
        _updateButtons: function () {
            var self = this;
            this._super.apply(this, arguments);
            if (this.$buttons && this.mode === 'readonly') {
                var attrs = this.renderer.arch.attrs;
                var action_edit = ['edit', 'create'];
                _.each(action_edit, function (action) {
                    var expr = attrs['rp_' + action];
                    var res = expr ? self._evalExpression(expr) : self.activeActions[action];
                    self.$buttons.find('.o_form_button_' + action).toggleClass('o_hidden', !res);
                });
            }
        },

        _evalExpression: function (expr) {
            //https://openerp-web-v7.readthedocs.io/en/stable/#convert-js
            var tokens = py.tokenize(expr);
            var tree = py.parse(tokens);
            var evalcontext = this.renderer.state.evalContext
            var expr_eval = py.evaluate(tree, evalcontext);
            return py.PY_isTrue(expr_eval);
        }
    });
    
    var RegListController = ListController.extend({

        willStart: function () {
            var self = this;
            this.self_model = 'attendance.regular'
            var get_details = this._rpc({
                model: 'hr.employee',
                method: 'search_read',
                domain: [['user_id', '=', session.uid]],
                fields: ['account'],
            }).then(function (res) {
                if (res[0] && res[0]['account'] && ['Deployable - Billable', 'Temporarily - Deployable'].includes(res[0]['account'][1])) {
                    self.show_create = false
                } else {
                    self.show_create = true
                }
            });
            return Promise.all([
                this._super.apply(this, arguments),
                get_details
            ]);
        }
    });

    var RegListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: RegListController,
        }),
    });

    viewRegistry.add('reg_create_tree', RegListView);
});
