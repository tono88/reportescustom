from odoo import api, fields, models, tools,_
import json
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare,format_datetime
from itertools import groupby

class WarehouseStockQty(models.Model):
    _inherit = 'stock.quant'

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    warehouse_quantity = fields.Char(compute='_get_quantity_warehouse_location', string='Quantity per warehouse')
    quantity_warehouse = fields.Char('Warehouse Qty')

    def _get_quantity_warehouse_location(self):
        for record in self:
            text = ''
            product_id = self.env['product.product'].sudo().search([('product_tmpl_id', '=', record.id)])
            if product_id:
                quant_ids = self.env['stock.quant'].sudo().search(
                    [('product_id', '=', product_id[0].id), ('location_id.usage', '=', 'internal')])
                res = {}
                for quant in quant_ids:
                    if quant.location_id:
                        if quant.location_id not in res:
                            res.update({quant.location_id: 0})
                        res[quant.location_id] += quant.quantity

                res1 = {}
                for location in res:
                    warehouse = False
                    location1 = location
                    while (not warehouse and location1):
                        warehouse_id = self.env['stock.warehouse'].sudo().search([('lot_stock_id', '=', location1.id)])
                        if len(warehouse_id) > 0:
                            warehouse = True
                        else:
                            warehouse = False
                        location1 = location1.location_id
                    if warehouse_id:
                        if warehouse_id.name not in res1:
                            res1.update({warehouse_id.name: 0})
                        res1[warehouse_id.name] += res[location]

                for item in res1:
                    if res1[item] != 0:
                        text = text + item + ': ' + str(res1[item]) + " "
                record.warehouse_quantity = text

    def warehouse_qty(self, warehouse_id, product, session,product_qty):  
        pos_session = self.env['pos.session'].browse(session) 
        selected_warehouses = pos_session.config_id.warehouse_ids

        loc_list = []  
        product_obj = self.env['product.product'].browse(int(product)) 
        for warehouse in warehouse_id: 
            warehouse_data = self.env['stock.warehouse'].browse(warehouse) 
            record_stock_location = warehouse_data.lot_stock_id 
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product_obj.id),
                ('warehouse_id', '=', warehouse_data.id)
            ]) 
            total_quantity = sum(quant.quantity for quant in quants)
            virtual_quantity = product_obj.with_context({'warehouse_id': warehouse_data.id}).virtual_available, 
            if product_qty == 'virtual_available':
                loc_list.append({
                    'quantity': virtual_quantity,
                    'location': warehouse_data.name,
                    'id': warehouse
                })
            if product_qty == 'qty_available':
                loc_list.append({
                    'quantity': total_quantity,
                    'location': warehouse_data.name,
                    'id': warehouse
                }) 
        return loc_list
