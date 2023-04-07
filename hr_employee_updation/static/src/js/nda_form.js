odoo.define('hr_employee_updation.NdaForm', function(require) {
    'use strict';

    var core = require('web.core');
    var KanbanController = require("web.KanbanController");
    var KanbanRenderer = require("web.KanbanRenderer");
    var AbstractRenderer = require("web.AbstractRenderer");
    var KanbanView = require("web.KanbanView");
    var viewRegistry = require('web.view_registry');

    var _t = core._t;
    var QWeb = core.qweb;

    var NdaFormController = KanbanController.extend({
        custom_events: _.extend({}, KanbanController.prototype.custom_events, {
            'get_controller': '_on_get_controller',
        }),
        renderButtons: function ($node) {
            if (this.renderer.unity_access) {
                if (!this.renderer.is_checklist) {
                    var controlPanel = this.__parentedChildren.filter(function(res){
                        if (res.$el) {
                            return res.$el.hasClass('o_cp_controller'); 
                        }
                    });
                    controlPanel[0].$el.hide();
                }
            }
            return this._super.apply(this, arguments)
        },
        _on_get_controller: function () {
            this.$('.o_cp_controller').show();
        }
    });

    var NdaFormRenderer = KanbanRenderer.extend({
        events: _.extend({}, KanbanRenderer.prototype.events, {
            'click .btn-agree':'_onClickBtnAgree',
        }),

        willStart: function () {
            var self = this;
            return this._rpc({
                model: 'hr.employee',
                method: 'get_nda_checklist',
                args: [[]],
            }).then(function (res) {
                self.is_checklist = res.checklist;
                self.has_checklist = res.checklist;
                self.unity_access = res.unity_access;
            });
        },

        _render: function () {
            var self = this;
            if (this.unity_access) {
                if (!this.is_checklist && !this.has_checklist) {
                    // $('#app-sidebar').hide()
                    $('.o_main_navbar').hide()
                    this.$el.removeClass('.o_kanban_badge')
                    this.$el.html(QWeb.render('KanbanView.NdaForm'));
                    this.has_checklist = true;
                } else {
                    // this.__parentedParent.$el.find('.o_cp_controller').show();
                    this.trigger_up('get_controller');
                    return this._super.apply(this, arguments)
                }
            } else {
                return this._super.apply(this, arguments)
            }
        },

        _onClickBtnAgree: function (ev) {
            var self= this;
            $(ev.currentTarget).remove()
            this._rpc({
                model: 'hr.employee',
                method: 'on_agree_nda',
                args: [[]],
            }).then(function () {
                // $('#app-sidebar').show()
                $('.o_main_navbar').show()
                self.do_action({
                    name: 'Certificate',
                    type: 'ir.actions.act_window',
                    res_model: 'gamification.badge',
                    views: [[false, 'kanban']],
                    view_mode: 'kanban',
                    target: 'current'
                });
            });
        }
    });

    var NdaFormView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: NdaFormController,
            Renderer: NdaFormRenderer,
        }),
    });

    viewRegistry.add('hr_nda_form', NdaFormView);

});
