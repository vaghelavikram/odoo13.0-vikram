# -*- coding: utf-8 -*-

import base64
import zipfile
import io
import logging
import os
import hashlib
import mimetypes

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request, STATIC_CACHE, content_disposition
from odoo.tools import pycompat
from odoo.tools.mimetypes import guess_mimetype

logger = logging.getLogger(__name__)


class DownloadFile(http.Controller):

    def _binary_record_content(
            self, record, record_name, field='doc_attachment_id', filename=None,
            filename_field='name', default_mimetype='application/octet-stream'):

        model = record._name
        mimetype = 'mimetype' in record and record.mimetype or False
        content = None
        filehash = 'checksum' in record and record['checksum'] or False
        field_def = record._fields[field]
        if field_def.type == 'many2many':
            field_attachment = request.env['ir.attachment'].sudo().search_read(domain=[('res_model', '=', model), ('name', 'in', record_name)], fields=['datas', 'mimetype', 'checksum', 'name'])
            # for multi record as it is many2many field, by this it will not raise error
            for rec in field_attachment:
                if field_attachment:
                    mimetype = rec['mimetype']
                    content = rec['datas']
                    filehash = rec['checksum']

                # if not content:
                #     content = record[field] or ''

                # filename
                if not filename:
                    filename = rec.get('name')

                if not mimetype:
                    mimetype = guess_mimetype(base64.b64decode(content), default=default_mimetype)

                # extension
                _, existing_extension = os.path.splitext(filename)
                if not existing_extension:
                    extension = mimetypes.guess_extension(mimetype)
                    if extension:
                        filename = "%s%s" % (filename, extension)

                if not filehash:
                    filehash = '"%s"' % hashlib.md5(pycompat.to_text(content).encode('utf-8')).hexdigest()

                status = 200 if content else 404
                return status, content, filename, mimetype, filehash

    def _binary_set_headers(self, status, content, filename, mimetype, unique, filehash=None, download=False):
        headers = [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff')]
        # cache
        etag = bool(request) and request.httprequest.headers.get('If-None-Match')
        status = status or 200
        if filehash:
            headers.append(('ETag', filehash))
            if etag == filehash and status == 200:
                status = 304
        headers.append(('Cache-Control', 'max-age=%s' % (STATIC_CACHE if unique else 0)))
        # content-disposition default name
        if download:
            headers.append(('Content-Disposition', content_disposition(filename)))

        return (status, headers, content)

    def binary_content(self, id, env=None, field='doc_attachment_id', share_id=None, share_token=None,
                       download=False, unique=False, filename_field='name'):
        env = env or request.env
        record = env['hr.employee.document'].browse(int(id))
        record_name = record.doc_attachment_id.mapped('name')

        filehash = None

        if not record:
            return (404, [], None)

        #check access right
        try:
            last_update = record['__last_update']
        except AccessError:
            return (404, [], None)

        mimetype = False
        status, content, filename, mimetype, filehash =self._binary_record_content(
            record, record_name, field=field, filename=None, filename_field=filename_field,
            default_mimetype='application/octet-stream')
        status, headers, content = self._binary_set_headers(
            status, content, filename, mimetype, unique, filehash=filehash, download=download)

        return status, headers, content

    def _get_file_response(self, id, field='doc_attachment_id', share_id=None, share_token=None):
        status, headers, content = self.binary_content(
            id, field=field, share_id=share_id, share_token=share_token, download=True)

        content_base64 = base64.b64decode(content)
        headers.append(('Content-Length', len(content_base64)))
        response = request.make_response(content_base64, headers)

        return response

    @http.route(['/documents/content/<int:id>'], type='http', auth='public')
    def document_content(self, id, debug=None):
        return self._get_file_response(id)

############################### Zip files ####################################
    def _make_zip(self, name, documents):
        """returns zip files for the Document Inspector and the portal.

        :param name: the name to give to the zip file.
        :param documents: files (hr.employee.document) to be zipped.
        :return: a http response to download a zip file.
        """
        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                for document in documents:
                    # for Binary field download zip
                    if document.attach1:
                        filename = document.document_name.name + '_front' 
                        doc_zip.writestr(filename, base64.b64decode(document.attach1),
                                        compress_type=zipfile.ZIP_DEFLATED)
                        if document.attach2:
                            filename = document.document_name.name + '_back'
                            doc_zip.writestr(filename, base64.b64decode(document.attach2),
                                        compress_type=zipfile.ZIP_DEFLATED)

                    # for Many2many field download zip

                    # if len(document.doc_attachment_id.ids) > 1:
                    #     for attachment_id in document.doc_attachment_id:
                    #         if attachment_id.type != 'binary':
                    #             continue
                    #         filename = attachment_id.name
                    #         doc_zip.writestr(filename, base64.b64decode(attachment_id.datas),
                    #                          compress_type=zipfile.ZIP_DEFLATED)
                    # else:
                    #     if document.doc_attachment_id.type != 'binary':
                    #         continue
                    #     filename = document.doc_attachment_id.name
                    #     doc_zip.writestr(filename, base64.b64decode(document.doc_attachment_id.datas),
                    #                      compress_type=zipfile.ZIP_DEFLATED)

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

    @http.route(['/document/zip'], type='http', auth='user')
    def get_zip(self, file_ids, zip_name, model_name, token=None):
        """route to get the zip file of the selection in the document's List view.
        :param file_ids: if of the files to zip.
        :param zip_name: name of the zip file.
        """
        ids_list = [int(x) for x in file_ids.split(',')]
        env = request.env
        response = self._make_zip(zip_name, env[model_name].browse(ids_list))
        if token:
            response.set_cookie('fileToken', token)
        return response
