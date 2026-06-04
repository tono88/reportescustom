# -*- coding: utf-8 -*-

from odoo import fields, models


class PosWarehouseSalesReportLine(models.TransientModel):
    _name = "pos.warehouse.sales.report.line"
    _description = "Detalle reporte ventas POS por almacén"
    _order = "date_order desc, order_id desc, product_id"

    wizard_id = fields.Many2one(
        "pos.warehouse.sales.report.wizard",
        string="Asistente",
        required=True,
        ondelete="cascade",
        readonly=True,
    )

    date_order = fields.Datetime(string="Fecha venta", readonly=True)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)

    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén", readonly=True)
    warehouse_display = fields.Char(string="Almacén", readonly=True)

    order_id = fields.Many2one("pos.order", string="Orden POS", readonly=True)
    order_line_id = fields.Many2one("pos.order.line", string="Línea POS", readonly=True)
    pos_reference = fields.Char(string="Referencia/recibo", readonly=True)
    session_id = fields.Many2one("pos.session", string="Sesión", readonly=True)
    config_id = fields.Many2one("pos.config", string="Punto de venta", readonly=True)
    cashier_id = fields.Many2one("res.users", string="Cajero", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)

    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    categ_id = fields.Many2one("product.category", string="Categoría", readonly=True)
    uom_id = fields.Many2one("uom.uom", string="UdM", readonly=True)

    qty = fields.Float(string="Cantidad", readonly=True)
    price_unit = fields.Monetary(string="Precio unitario", currency_field="currency_id", readonly=True)
    discount = fields.Float(string="Descuento %", readonly=True)
    price_subtotal = fields.Monetary(string="Subtotal sin impuesto", currency_field="currency_id", readonly=True)
    price_total = fields.Monetary(string="Total con impuesto", currency_field="currency_id", readonly=True)

    invoice_id = fields.Many2one("account.move", string="Factura", readonly=True)
    invoice_number = fields.Char(string="Número", readonly=True)
    invoice_numero_fel = fields.Char(string="Número DTE", readonly=True)
    invoice_status = fields.Selection(
        [
            ("invoiced", "Facturado"),
            ("not_invoiced", "No facturado"),
        ],
        string="Estado facturación",
        readonly=True,
    )
    order_state = fields.Char(string="Estado POS", readonly=True)
