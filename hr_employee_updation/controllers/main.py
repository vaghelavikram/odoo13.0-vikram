# -*- coding: utf-8 -*-

import io
import base64
import zipfile
from odoo import http
from odoo.http import request, content_disposition
from odoo.addons.hr_org_chart.controllers.hr_org_chart import HrOrgChartController

import logging
logger = logging.getLogger(__name__)


class HrOrgChartControllerInherit(HrOrgChartController):

    @http.route('/hr/get_org_chart', type='json', auth='user')
    def get_org_chart(self, employee_id, **kw):

        employee = self._check_employee(employee_id, **kw)
        hr_employee = request.env['hr.employee'].browse(int(employee_id))
        if not employee:  # to check
            return {
                'managers': [],
                'children': [],
            }
        if hr_employee and not hr_employee.show_org_chart:
            return {
                'managers': [],
                'children': [],
            }
        # compute employee data for org chart
        ancestors, current = request.env['hr.employee.public'].sudo(), employee.sudo()
        while current.parent_id and len(ancestors) < self._managers_level+1:
            ancestors += current.parent_id
            current = current.parent_id

        values = dict(
            self=self._prepare_employee_data(employee),
            managers=[
                self._prepare_employee_data(ancestor)
                for idx, ancestor in enumerate(ancestors)
                if idx < self._managers_level
            ],
            managers_more=len(ancestors) > self._managers_level,
            children=[self._prepare_employee_data(child) for child in employee.child_ids],
        )
        values['managers'].reverse()
        return values


class DownloadFile(http.Controller):

    def _make_zip(self, name, documents):
        """returns zip files for the Document Inspector and the portal.

        :param name: the name to give to the zip file.
        :param documents: files (hr.employee) to be zipped.
        :return: a http response to download a zip file.
        """
        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                for document in documents:
                    # for Binary field download zip
                    if document.image_512:
                        filename = document.name
                        doc_zip.writestr(filename, base64.b64decode(document.image_512),
                                        compress_type=zipfile.ZIP_DEFLATED)
        except zipfile.BadZipfile:
            logger.exception("BadZipfile exception")

        content = stream.getvalue()
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(name))
        ]
        return request.make_response(content, headers)

    @http.route(['/image_download/zip'], type='http', auth='user')
    def get_zip(self, file_ids, token=None):
        """route to get the zip file of the selection in the document's List view.
        :param file_ids: if of the files to zip.
        :param zip_name: name of the zip file.
        """
        file_ids = eval(file_ids)
        ids_list = [int(x) for x in file_ids]
        env = request.env
        zip_name = 'ezestian_images'
        model_name = 'hr.employee'
        response = self._make_zip(zip_name, env[model_name].browse(ids_list))
        if token:
            response.set_cookie('fileToken', token)
        return response
