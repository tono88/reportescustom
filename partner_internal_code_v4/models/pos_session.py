# -*- coding: utf-8 -*-
from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_pos_ui_partner_fields(self):
        fields = super()._get_pos_ui_partner_fields()
        if 'internal_code' not in fields:
            fields.append('internal_code')
        return fields

    def _loader_params_res_partner(self):
        res = super()._loader_params_res_partner()
        search_params = res.get('search_params', {})
        fields = search_params.get('fields', [])
        if 'internal_code' not in fields:
            fields.append('internal_code')
        search_params['fields'] = fields
        res['search_params'] = search_params
        return res
