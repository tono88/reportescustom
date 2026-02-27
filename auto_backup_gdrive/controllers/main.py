# -*- coding: utf-8 -*-

import json
import requests
import werkzeug
from six.moves.urllib.parse import urlencode

from odoo import http
from odoo.http import request


class GoogleAuthentication(http.Controller):

    def getToken(self, CLIENT_ID, CLIENT_SECRET, AUTH_CODE, REDIRECT_URI):
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        payload = {
            'code': AUTH_CODE,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code',
        }
        r = requests.post('https://accounts.google.com/o/oauth2/token', data=payload, headers=headers)
        if r.status_code != 200:
            return r.text
        data = json.loads(r.text)
        return data

    @http.route('/web/gdrive/redirect', auth='user', type='http', csrf=False)
    def google_drive_auth(self, **kwargs):
        if kwargs.get('state') and kwargs.get('code'):
            backup_config = request.env['db.backup.destination'].sudo().browse(int(kwargs['state']))
            token_info = self.getToken(backup_config.gdrive_client_id, backup_config.gdrive_client_secret, kwargs['code'], backup_config.gdrive_redirect_uri)
            backup_config.gdrive_access_token = token_info.get('access_token')
            backup_config.gdrive_refresh_token = token_info.get('refresh_token')
            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
            end_point = urlencode({'id': str(kwargs['state']), 'view_type': 'form', 'model': 'db.backup.destination'})
            ConfigUrl = base_url + '/web#' + end_point
            return werkzeug.utils.redirect(ConfigUrl)
        return werkzeug.utils.redirect('/web')
