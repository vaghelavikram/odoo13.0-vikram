odoo.define('project_role.open_form_edit', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var ListRenderer = ListRenderer.extend({

        /**
         * @private
         * @param {MouseEvent} event
         */
        _onRowClicked: function (ev) {
            if (!ev.target.closest('.o_list_record_selector') && !$(ev.target).prop('special_click')) {
                var id = $(ev.currentTarget).data('id');
                var data_val = _.filter(this.state.data, function(val){if(val.id==id){return val.data}})
                if (id && data_val.length && data_val[0].data.state == 'draft') {
                    this.trigger_up('open_record', {
                        id: id,
                        target: ev.target,
                        mode: 'edit'
                    });
                } else {
                    this._super.apply(this, arguments);
                }
            }
        },
    });

    // open form in list view using (viewRegistry) which is js_class
    var ListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Renderer: ListRenderer,
        }),
    });

    viewRegistry.add('open_form_edit', ListView);

});
