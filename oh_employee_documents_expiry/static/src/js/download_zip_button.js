odoo.define('oh_employee_documents_expiry.download_zip', function (require) {
"use strict";
    var BasicModel = require('web.BasicModel');
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var Sidebar = require('web.Sidebar');

    var _t = core._t;
    var session = require('web.session');
    var qweb = core.qweb;

    /*BasicModel.include({
        downloadZip: function (recordIds) {
            var self= this;
            var records = _.map(recordIds, function (id) { return self.localData[id]; });
            var ids = [];
            _.each(records, function(record) {ids.push(record.res_id)});
            return ids;
        },
    });*/

    var DownloadZipListController = ListController.extend({
        /**
         * Extends the renderSidebar function of ListView by adding an button on
         * side to download zip file.
         *
         * @override
         * @param {jQuery Node} $node
         */
        renderSidebar: function ($node) {
            var self = this;
            if (this.hasSidebar) {
                var other = [{
                    label: _t("Export"),
                    callback: this._onExportData.bind(this)
                }];
                other.push({
                    label: ("Download Zip File"),
                    callback: this._onDownloadFile.bind(this, false)
                });
                if (this.is_action_enabled('delete')) {
                    other.push({
                        label: _t('Delete'),
                        callback: this._onDeleteSelectedRecords.bind(this)
                    });
                }
                this.sidebar = new Sidebar(this, {
                    editable: this.is_action_enabled('edit'),
                    env: {
                        context: this.model.get(this.handle, {raw: true}).getContext(),
                        activeIds: this.getSelectedIds(),
                        model: this.modelName,
                    },
                    actions: _.extend(this.toolbarActions, {other: other}),
                });
                return this.sidebar.appendTo($node).then(function() {
                    self._toggleSidebar();
                });
            }
            return Promise.resolve();
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * prepare url for selected resIds
         *
         * @private
         * @param {array} [resIDs]
         */
        _onDownloadZipFile: function (resIDs, recordName, recordModel) {
            if (resIDs.length === 1) {
                window.location = '/documents/content/' + resIDs[0];
            } else {
                var timestamp = moment().format('YYYY-MM-DD');
                session.get_file({
                    url: '/document/zip',
                    data: {
                        file_ids: resIDs,
                        zip_name: recordName + '-documents-' + timestamp + '.zip',
                        model_name: recordModel,
                    },
                });
            }
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Calls when select record and click on download button
         *
         * @private
         */
        _onDownloadFile: function () {
            /*var ids = this.selectedRecords;
            var recordIds = this.model.downloadZip(ids);*/
            var recordIds = this.renderer.state.res_ids;
            var recordName = this.renderer.state.data[0].data.employee_ref.data.display_name.split(' ')[0].toLowerCase()
            var recordModel = this.renderer.state.model;
            this._onDownloadZipFile(recordIds, recordName, recordModel);
        },
    });

    var DownloadZipListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: DownloadZipListController,
        }),
    });

    viewRegistry.add('download_zip_button', DownloadZipListView);

});
