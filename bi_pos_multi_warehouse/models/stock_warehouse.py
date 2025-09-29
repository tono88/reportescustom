from odoo import api, fields, models, tools,_

class WarehouseQty(models.Model):
    _inherit = 'stock.warehouse'
    
    quantity = fields.Integer('quantity')

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = data['pos.config']['data'][0]['config_id']
        return [['id', 'in', config_id.warehouse_ids.ids]]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id','name']

    def _load_pos_data(self, data):
        domain = []
        fields = self._load_pos_data_fields(data)
        data = self.search_read(domain, fields, load=False, )
        return {
            'data': data,
            'fields': fields
        }


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def _load_pos_data_fields(self, config_id):
        return []

    def _load_pos_data(self, data):
        domain = []
        fields = self._load_pos_data_fields(data)
        data = self.search_read(domain, fields, load=False, )
        return {
            'data': data,
            'fields': fields
        }