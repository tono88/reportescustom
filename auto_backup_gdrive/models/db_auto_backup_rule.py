# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import requests
import tempfile
from datetime import datetime, timedelta
from werkzeug import urls

from odoo.addons.auto_backup_gdrive.models import db
from odoo import _, api, fields, models
from odoo.tools import config
from odoo.exceptions import ValidationError


class DatabaseAutoBackupRule(models.Model):
    _name = 'db.auto.backup.rule'
    _description = 'Database Automatic Backup Rule'

    def default_backup_filename(self):
        return self.env.cr.dbname

    name = fields.Char(required=True)
    db_backup_destinations = fields.Many2many('db.backup.destination', string='Backup Destinations', required=True)
    interval_number = fields.Integer(required=True, default=1, help="Repeat every x.")
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Unit', required=True, default='months')
    cron_id = fields.Many2one('ir.cron', string='Cron Job', readonly=True, store=True)
    delete_old_backups = fields.Boolean(default=True)
    delete_days = fields.Integer(string='Delete backups older than [days]', default=30)
    backup_type = fields.Selection([('dump', 'Database Without Filestore'), ('zip', 'Database With Filestore')], string='Backup Type', required=True)
    backup_filename = fields.Char(required=True, default=default_backup_filename)

    # odoo server settings
    limit_time_cpu = fields.Integer(string='CPU Time/Request(seconds)',
                                    compute='compute_odoo_settings', inverse='set_odoo_settings')
    limit_time_real = fields.Integer(string='Real Time/Request(seconds)',
                                     compute='compute_odoo_settings', inverse='set_odoo_settings')
    limit_time_real_cron = fields.Integer(
        string='Real Time/Cron Job(seconds)',
        compute='compute_odoo_settings', inverse='set_odoo_settings')

    def compute_odoo_settings(self):
        self.limit_time_cpu = config['limit_time_cpu']
        self.limit_time_real = config['limit_time_real']
        self.limit_time_real_cron = config['limit_time_real_cron']

    def set_odoo_settings(self):
        config['limit_time_cpu'] = self.limit_time_cpu
        config['limit_time_real'] = self.limit_time_real
        config['limit_time_real_cron'] = self.limit_time_real_cron
        config.save()

    @api.constrains('delete_days')
    def constrains_delete_days(self):
        for record in self:
            if record.delete_old_backups:
                if record.delete_days is False or record.delete_days < 1:
                    raise ValidationError(_('Minimum delete days should be 1'))

    @api.model_create_multi
    def create(self, vals):
        rules = super(DatabaseAutoBackupRule, self).create(vals)
        for rule in rules:
            ir_vals = {
                'name': 'Automatic Database Backup - %s' % rule.name,
                'model_id': self.env['ir.model'].search([('model', '=', 'db.auto.backup.rule')]).id,
                'interval_number': rule.interval_number,
                'interval_type': rule.interval_type,
                'state': 'code',
                'code': 'model._db_backup_cron(%s)' % rule.id,
                'active': True,
                'db_auto_backup_rule': rule.id
            }
            cron_id = self.env['ir.cron'].create(ir_vals)
            rule.cron_id = cron_id.id
        return rules

    def unlink(self):
        self.cron_id.with_context({'force_backup_unlink': True}).unlink()
        return super(DatabaseAutoBackupRule, self).unlink()

    def create_db_backup(self, check=False):
        filename = ''
        if check is False:
            backup_binary = db.custom_dump_db(self.env.cr.dbname, None, self.backup_type)
        else:
            backup_binary = tempfile.TemporaryFile()
            backup_binary.write(str.encode('Dummy File'))
            backup_binary.seek(0)

        for dest in self.db_backup_destinations:
            if dest.backup_destination == 'gdrive':
                if not dest.gdrive_access_token:
                    return

                filename = self.backup_filename + '_' + str(datetime.now()).split('.')[0].replace(':', '_') + '.' + self.backup_type

                auth_header = {
                    "Authorization": "Bearer " + dest.gdrive_access_token,
                }

                encoded_params = urls.url_encode({
                    'scope': 'drive',
                    'q': "mimeType = 'application/vnd.google-apps.folder' and name = 'Odoo Databse Backups'",
                    'fields': 'nextPageToken, files(id, name, trashed)',
                    'pageToken': None,
                })

                response = requests.get('https://www.googleapis.com/drive/v3/files?' + encoded_params, headers=auth_header).json()
                folder_id = False
                for folder in response.get('files', dict()):
                    folder_id = folder['id']
                    if folder.get('trashed'):
                        restore_url = f'https://www.googleapis.com/drive/v3/files/{folder_id}'
                        patch_headers = {
                            'Content-Type': 'application/json',
                        }
                        patch_headers.update(auth_header)
                        request_body = {
                            'trashed': False
                        }
                        response = requests.patch(restore_url, headers=patch_headers, json=request_body)
                    break
                if not folder_id:
                    params = dict(
                        uploadType='multipart',
                        name='Odoo Databse Backups',
                        mimeType='application/vnd.google-apps.folder',
                    )
                    response = requests.post('https://www.googleapis.com/drive/v3/files', headers=auth_header, json=params).json()
                    folder_id = response['id']

                mimetype = 'application/zip' if (self.backup_type == 'zip') else 'application/octet-stream'
                params = {
                    "name": filename,
                    "mimeType": mimetype,
                    "parents": [folder_id],
                }
                r = requests.post(
                    "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
                    headers=auth_header,
                    json=params,
                )
                location = r.headers['Location']
                headers = {"Content-Range": "bytes 0-*/*"}
                r = requests.put(location, headers=headers, data=backup_binary)

                if self.delete_old_backups:
                    encoded_params = urls.url_encode({
                        'scope': 'drive',
                        'q': "'%s' in parents and modifiedTime < '%s'" % (folder_id, str((datetime.now() - timedelta(days=self.delete_days)).date())),
                    })
                    response = requests.get('https://www.googleapis.com/drive/v3/files?' + encoded_params, headers=auth_header).json()
                    for file in response['files']:
                        requests.delete('https://www.googleapis.com/drive/v3/files/' + file['id'], headers=auth_header)

                if check:
                    delete_id = r.json()['id']
                    requests.delete('https://www.googleapis.com/drive/v3/files/' + delete_id, headers=auth_header)

        backup_binary.close()

    @api.model
    def _db_backup_cron(self, rule_id):
        try:
            rule = self.env['db.auto.backup.rule'].browse(int(rule_id))
            rule.create_db_backup()
        except Exception as e:
            pass
