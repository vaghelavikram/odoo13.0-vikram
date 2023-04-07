
from odoo import fields, models, api
import os
import random

import logging
import base64
import zipfile

from odoo.modules.module import get_resource_path
from odoo.modules.module import get_module_resource
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageChops
import io
from datetime import datetime
import numpy as np
from odoo import http


logger = logging.getLogger(__name__)


class BirthdayTemplate(models.Model):
    _name = 'birthday.template'
    _description = 'e-Zestian Birthday Greeting'

    name = fields.Char(string="File Name")
    birthday_greeting = fields.Binary(string="Birthday Greeting")
    employee_id = fields.Many2one('hr.employee', string="e-Zestian")
    creation_date = fields.Date(string="Created On")

    def _cron_birthday_greeting(self):
        today =  datetime.today().date()
        employees = self.env['hr.employee'].search([])
        path = self.env['birthday.template.template'].search([]).mapped('image_1920')
        if employees and path:
            for employee in employees:
                emp_name = employee.name
                emp_image = employee.image_1920
                emp_dob = employee.birthday
                if emp_image and emp_dob and emp_dob.day == today.day and emp_dob.month == today.month:
                    exists_employee = self.search([('employee_id','=',employee.id)])
                    if not exists_employee:
                        # path = get_resource_path('greeting', 'data/Birthday')
                        # birthday_temp = random.choice(os.listdir(path))
                        # greeting_img = Image.open(os.path.join(path, birthday_temp))
                        birthday_random_template = random.choice(path)
                        decoded_random_template = base64.b64decode(birthday_random_template)
                        Image1 = Image.open(io.BytesIO(decoded_random_template))
                        Image1copy = Image1.copy()
                        W,H = Image1.size
                        
                        # employee image
                        photo_data = base64.b64decode(emp_image)
                        Image2 = Image.open(io.BytesIO(photo_data))
                        Image2 = Image2.resize((400,400)) 
                        Image2copy = Image2.copy() 
                        position = ((W - 400) // 2, (H - 400) // 2)
                        # image pasted
                        Image1copy.paste(Image2copy, position)
                        # text above image
                        draw = ImageDraw.Draw(Image1copy)
                        font = get_resource_path('greeting', 'static/lib/fonts/Lobster-Regular.ttf')
                        font_obj = ImageFont.truetype(font, 65)
                        wish = emp_name
                        color = 'rgb(255, 255, 255)'
                        # draw.text((int(W//2.4),int(H//1.3)), wish, fill=color, font=font_obj, align="center")
                        width_text, height_text = draw.textsize(str(wish), font_obj)
                        position = ((W - width_text) / 2, (H - height_text) / 1.4)

                        draw.text(position, wish, font=font_obj, fill=color)
                        text_font = ImageFont.truetype(font, 50)
                        text = emp_dob.strftime("%d %B")
                        width_text, height_text = draw.textsize(text, text_font)
                        position = ((W - width_text) / 2, (H - height_text) / 1.3)

                        draw.text(position, text, font=text_font, fill=color)

                        text = "Created by Unity"
                        text_font = ImageFont.truetype(font, 35)
                        width_text, height_text = draw.textsize(text, text_font)
                        position = ((W - width_text) / 1.1, (H - height_text))
                        draw.text(position, text, font=text_font, fill=color)
                        # coping_image = photo.resize((280, 280))

                        # copied_img = greeting_img.copy()
                        # np_image = np.array(coping_image)
                        # h, w = coping_image.size

                        # # Create same size alpha leastyer with circle
                        # alpha = Image.new('L', coping_image.size)
                        # draw = ImageDraw.Draw(alpha)
                        # draw.pieslice([1, 1, h, w], 0, 360, fill=255)

                        # # Convert alpha Image to numpy array
                        # np_alpha = np.array(alpha)
                        # # Add alpha layer to RGB
                        # np_image = np.dstack((np_image, np_alpha))
                        # new_im = Image.fromarray(np_image.astype(np.uint8))
                        # copied_img.paste(new_im, (345, 460))

                        # img_with_border = ImageOps.expand(copied_img, border=(15, 12), fill='#C5B358')
                        # img_with_bord                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   er = img_with_border.filter(ImageFilter.SMOOTH_MORE)

                        # # writing text on greetings
                        # d = ImageDraw.Draw(img_with_border)
                        # wish = (emp_name)
                        # color = 'rgb(255, 255, 255)' #C5B358' #'#FFD700'
                        # # Make sure we have at least size=1
                        # size = max(1, 40)
                        # font = get_resource_path('greeting', 'static/lib/fonts/Monotype Corsiva.ttf')
                        # # Initialize font
                        # font_obj = ImageFont.truetype(font, size)
                        # d.text((348, 630), wish, fill=color, font=font_obj)
                        file_name = emp_name.split(' ')[0].lower() + '_' + str(emp_dob) + '.png'  # format(count)
                        birthday_output = get_resource_path('greeting', 'data/OutputImages/Birthday')
                        image_path = birthday_output + '/'+ file_name
                        Image1copy.save(image_path)
                        # img_with_border.save(image_path, quality=95)
                        # image_path = get_module_resource('greeting', 'data/OutputImages/Birthday/' + file_name)
                        # image_path = birthday_output + '/'+ file_name
                        self.sudo().create({
                            'birthday_greeting': base64.b64encode(open(image_path, 'rb').read()),
                            'employee_id': employee.id,
                            'name': file_name,
                            'creation_date': fields.Date.today()
                        })
                        path_remove = os.path.join(image_path)
                        os.remove(path_remove)
            for rec in self:
                if not (rec.employee_id and rec.birthday_greeting):
                    rec.unlink()
        return

    
    def _make_zip(self, name, documents):
        """returns zip files for the Document Inspector and the portal.

        :param name: the name to give to the zip file.
        :param documents: files (hr.employee.document) to be zipped.
        :return: a http response to download a zip file.
        """
        logger.info("Inside _make_zip function")
        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                for document in documents:
                    # for Binary field download zip
                    if document.birthday_greeting:
                        filename = document.employee_id.name
                        doc_zip.writestr(filename, base64.b64decode(document.birthday_greeting),
                                        compress_type=zipfile.ZIP_DEFLATED)

        except zipfile.BadZipfile:
            logger.exception("BadZipfile exception")

        content = stream.getvalue()
        return content


    def _get_zip(self, zip_name, file_ids, token=None):
        """route to get the zip file of the selection in the document's List view.
        :param file_ids: if of the files to zip.
        :param zip_name: name of the zip file.
        """
        model = self.env[self._name]
        ids_list = [int(x) for x in file_ids.ids]
        if ids_list:
            response = self._make_zip(zip_name, model.browse(ids_list))
            if token:
                response.set_cookie('fileToken', token)
            ATTACHMENT_NAME = 'Birthday Greeting'
            b64_pdf = base64.b64encode(response)
            attachment = {
                'name': ATTACHMENT_NAME + '.zip',
                'description': ATTACHMENT_NAME,
                'type': 'binary',
                'datas': b64_pdf,
                'store_fname': ATTACHMENT_NAME,
                'res_model': model,
                'mimetype': 'application/zip'
            }
            mail_values = {
                'body_html': "Please find the e-Zestian Birthday Greeting",
                'subject': "Today's Birthday Greeting",
                'email_from': 'unity@e-zest.in',
                'email_to': 'hrd@e-zest.in',
                'attachment_ids': [(0, 0, attachment)]
            }
            self.env['mail.mail'].sudo().create(mail_values).send(self.env.user.id)
        return

    def cron_birthday_make_zip(self):
        zip_name = "Birthday.zip"
        file_ids = self.search([('creation_date', '=', fields.Date.today())])
        if file_ids:
            self._get_zip(zip_name,file_ids)

    def download_image(self):
        return {
            'type': "ir.actions.act_url",
            'url': '/web/content?model=%s&download=True&field=birthday_greeting&id=%s&filename=%s' %
                   (self._name, self.id, 'Birthday %s' % self.employee_id.name),
            'target': 'self',
        }


class TemplateTemplate(models.Model):
    _name = 'birthday.template.template'
    _description = 'All Birthday Templates'


    name = fields.Char(string="File Name")
    image_1920 = fields.Binary(string="Greeting")
