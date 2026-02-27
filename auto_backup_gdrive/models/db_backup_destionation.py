# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import json
import requests
from werkzeug import urls

from odoo import api, fields, models


class DBBackupDestination(models.Model):
    _name = 'db.backup.destination'
    _description = 'Database Backup Destination'

    name = fields.Char(required=True)
    backup_destination = fields.Selection([('gdrive', 'Google Drive')], string='Backup Storage')

    gdrive_client_id = fields.Char(required=True)
    gdrive_client_secret = fields.Char(required=True)
    gdrive_redirect_uri = fields.Char(required=True)
    gdrive_refresh_token = fields.Char()
    gdrive_access_token = fields.Char()

    def name_get(self):
        result = []
        for dest in self:
            dest_name = ''
            if dest.backup_destination == 'gdrive':
                dest_name = 'Google Drive'
            name = dest.name + '(%s)' % dest_name
            result.append((dest.id, name))
        return result

    def authorize_and_get_token(self):
        self.ensure_one()
        encoded_params = urls.url_encode({
            'scope': 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.file',
            'redirect_uri': self.gdrive_redirect_uri,
            'client_id': self.gdrive_client_id,
            'response_type': 'code',
            'state': self.id,
            'prompt': 'consent',
            'access_type': 'offline'
        })
        target_url = '%s?%s' % ('https://accounts.google.com/o/oauth2/auth', encoded_params)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': target_url,
        }

    @api.model
    def RefereshToken(self):
        backup_configs = self.env['db.backup.destination'].search([('gdrive_client_id', '!=', False), ('gdrive_client_secret', '!=', False), ('gdrive_refresh_token', '!=', False)])
        if backup_configs:
            for backup_config in backup_configs:
                payload = {
                    'client_id': backup_config.gdrive_client_id,
                    'refresh_token': backup_config.gdrive_refresh_token,
                    'client_secret': backup_config.gdrive_client_secret,
                    'grant_type': 'refresh_token',
                    'access_type': "offline"
                }
                headers = {"Content-type": "application/x-www-form-urlencoded"}
                r = requests.post('https://accounts.google.com/o/oauth2/token', data=payload, headers=headers)
                if r.status_code != 200:
                    return False
                bearer_raw = json.loads(r.text)

                if bearer_raw.get('access_token'):
                    backup_config.gdrive_access_token = str(bearer_raw.get('access_token').strip())

                if bearer_raw.get('refresh_token'):
                    backup_config.gdrive_refresh_token = str(bearer_raw.get('refresh_token').strip())