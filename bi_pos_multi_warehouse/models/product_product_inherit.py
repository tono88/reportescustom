# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools,_
from odoo.tools import float_is_zero, float_compare,format_datetime
from collections import defaultdict
import json

class ProductTemplate(models.Model):
    _inherit = "product.template"

    warehouse_quantity = fields.Char(compute='_get_quantity_warehouse_location', string='Quantity per warehouse')
    warehouse_id = fields.Many2one(compute='_get_quantity_warehouse_forcast_location', string='Warehouse Name')


    def _get_quantity_warehouse_location(self):
        for record in self:
            text = ''
            product_id = self.env['product.product'].sudo().search([('product_tmpl_id', '=', record.id)])
            if product_id:
                quant_ids = self.env['stock.quant'].sudo().search([('product_id','=',product_id[0].id),('location_id.usage','=','internal')])
                res = {}
                for quant in quant_ids:
                    if quant.location_id:
                        if quant.location_id not in res:
                            res.update({quant.location_id:0})
                        res[quant.location_id] += quant.quantity

                res1 = {}
                for location in res:
                    warehouse = False
                    location1 = location
                    while (not warehouse and location1):
                        warehouse_id = self.env['stock.warehouse'].sudo().search([('lot_stock_id','=',location1.id)])
                        if len(warehouse_id) > 0:
                            warehouse = True
                        else:
                            warehouse = False
                        location1 = location1.location_id
                    if warehouse_id:
                        if warehouse_id.name not in res1:
                            res1.update({warehouse_id.name:0})
                        res1[warehouse_id.name] += res[location]

                for item in res1:
                    if res1[item] != 0:
                        text = text + item + ': ' + str(res1[item])
                record.warehouse_quantity = text


    def _get_quantity_warehouse_forcast_location(self):
        for record in self:
            text = ''
            product_id = self.env['product.product'].sudo().search([('product_tmpl_id', '=', record.id)])
            if product_id:
                quant_ids = self.env['stock.quant'].sudo().search([('product_id','=',product_id[0].id),('location_id.usage','=','internal')])
                res = {}
                for quant in quant_ids:
                    if quant.location_id:
                        if quant.location_id not in res:
                            res.update({quant.location_id:0})
                        res[quant.location_id] += quant.virtual_available

                res1 = {}
                for location in res:
                    warehouse = False
                    location1 = location
                    while (not warehouse and location1):
                        warehouse_id = self.env['stock.warehouse'].sudo().search([('lot_stock_id','=',location1.id)])
                        if len(warehouse_id) > 0:
                            warehouse = True
                        else:
                            warehouse = False
                        location1 = location1.location_id
                    if warehouse_id:
                        if warehouse_id.name not in res1:
                            res1.update({warehouse_id.name:0})
                        res1[warehouse_id.name] += res[location]

                for item in res1:
                    if res1[item] != 0:
                        text = text + item + ': ' + str(res1[item])
                record.warehouse_quantity = text


class PosOrderLinePicking(models.Model):
    _inherit = 'pos.order.line'

    stock_location_name = fields.Char('Warehouse')

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += ['stock_location_name']
        return fields


class PosOrderPicking(models.Model):
    _inherit = 'pos.order'

    stock_location_name = fields.Char('Warehouse')

    def _create_order_picking(self):
        self.ensure_one()
        if self.shipping_date:
            self.sudo().lines._launch_stock_rule_from_pos_order_lines()
        else:
            if self._should_create_picking_real_time():
                picking_type = self.config_id.picking_type_id
                if self.partner_id.property_stock_customer:
                    destination_id = self.partner_id.property_stock_customer.id
                elif not picking_type or not picking_type.default_location_dest_id:
                    destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
                else:
                    destination_id = picking_type.default_location_dest_id.id

                different = self.lines.filtered(lambda l: l.stock_location_name)

                if different:
                    for line in different:
                        picking_type = self.env['stock.picking.type'].search(
                            [('warehouse_id.name', '=', line.stock_location_name), ('code', '=', 'outgoing'),
                             ('sequence_code', '=', 'POS')])

                        diff_pick = self.env['stock.picking'].with_context(diff_loc=line.stock_location_name)._create_picking_from_pos_order_lines(destination_id, line, picking_type, self.partner_id)
                        diff_pick.write({'pos_session_id': self.session_id.id, 'pos_order_id': self.id,'pos_order_id': self.id, 'origin': self.name})

                else:
                    pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(destination_id, self.lines, picking_type, self.partner_id)
                    pickings.write({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})


class Product(models.Model):
    _inherit = 'product.product'


    quant_ids = fields.One2many("stock.quant", "product_id", string="Quants",
                                domain=[('location_id.usage', '=', 'internal')])

    quant_text = fields.Text('Quant Qty', compute='_compute_avail_locations', store=True)

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += ['type','quant_ids','quant_text','qty_available','incoming_qty','outgoing_qty','virtual_available','name','product_variant_count']
        return fields

    @api.depends('stock_quant_ids', 'stock_quant_ids.product_id', 'stock_quant_ids.location_id',
                 'stock_quant_ids.quantity')
    def _compute_avail_locations(self):
        notifications = []
        for rec in self:
            final_data = {}
            rec.quant_text = json.dumps(final_data)
            if rec.type == 'consu':
                quants = self.env['stock.quant'].sudo().search(
                    [('product_id', 'in', rec.ids), ('location_id.usage', '=', 'internal')])
                outgoing = self.env['stock.move'].sudo().search(
                    [('product_id', '=', rec.id), ('state', 'not in', ['done','cancel']),
                     ('location_id.usage', '=', 'internal'),
                     ('picking_id.picking_type_code', 'in', ['outgoing'])])
                incoming = self.env['stock.move'].sudo().search(
                    [('product_id', '=', rec.id), ('state', 'not in', ['done','cancel']),
                     ('location_dest_id.usage', '=', 'internal'),
                     ('picking_id.picking_type_code', 'in', ['incoming'])])
                for quant in quants:
                    loc = quant.location_id.id
                    if loc in final_data:
                        last_qty = final_data[loc][0]
                        final_data[loc][0] = last_qty + quant.quantity
                    else:
                        final_data[loc] = [quant.quantity, 0, 0]

                for out in outgoing:
                    loc = out.location_id.id
                    if loc in final_data:
                        last_qty = final_data[loc][1]
                        final_data[loc][1] = last_qty + out.product_qty
                    else:
                        final_data[loc] = [0, out.product_qty, 0]

                for inc in incoming:
                    loc = inc.location_dest_id.id
                    if loc in final_data:
                        last_qty = final_data[loc][2]
                        final_data[loc][2] = last_qty + inc.product_qty
                    else:
                        final_data[loc] = [0, 0, inc.product_qty]
                rec.quant_text = json.dumps(final_data)
        return True