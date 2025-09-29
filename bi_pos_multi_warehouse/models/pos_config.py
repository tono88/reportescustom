from odoo import api, fields, models, tools,_

class PosConfigLocationwarehouse(models.Model):
	_inherit = 'pos.config'

	display_stock = fields.Boolean(string='Display stock in pos', help='Allow display stock in pos.')
	default_location_src_id = fields.Many2one(
		'stock.location', 'Default Stock Location',
		check_company=True)

	warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses', 
									 help="Show the routes that apply on selected warehouses." )
	picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True, copy=False)
	location_id = fields.Many2one(
		comodel_name='stock.location',
		related='picking_id.location_id',
		string="Stock Location", store=True,
		readonly=True,
	)
	stock_qty = fields.Selection([('qty_available', 'Available Quantity'),
								  ('virtual_available', 'Unreserved Quantity'),
								  ], 'Stock Type')
	Ready_state = fields.Boolean(string='Set Picking In Ready State', help='Allow display stock in ready state pos.')
	Negative_selling = fields.Boolean(string='Allow POS Order When Product is Out of Stock', help='Allow negative selling in pos.')