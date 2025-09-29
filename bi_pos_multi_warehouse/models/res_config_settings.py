from odoo import api, fields, models, tools,_

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	pos_display_stock = fields.Boolean(related='pos_config_id.display_stock',string='Display stock in pos', help='Allow display stock in pos.',readonly=False)
	pos_default_location_src_id = fields.Many2one(related='pos_config_id.default_location_src_id',check_company=True, string='Default Stock Location',readonly=False)

	pos_warehouse_ids = fields.Many2many(related='pos_config_id.warehouse_ids',string='Warehouses', 
									 help="Show the routes that apply on selected warehouses." ,readonly=False)
	pos_picking_id = fields.Many2one(related='pos_config_id.picking_id', string='Picking',  copy=False,readonly=False)
	pos_location_id = fields.Many2one(
		related='pos_config_id.location_id', 
		string="Stock Location", store=True,
		readonly=False,
	)
	pos_stock_qty = fields.Selection(related='pos_config_id.stock_qty', string='Stock Type',required=True,readonly=False)
	pos_Ready_state = fields.Boolean(related='pos_config_id.Ready_state',string='Set Picking In Ready State', help='Allow display stock in ready state pos.',readonly=False)
	pos_Negative_selling = fields.Boolean(related='pos_config_id.Negative_selling',string='Allow POS Order When Product is Out of Stock', help='Allow negative selling in pos.',readonly=False)