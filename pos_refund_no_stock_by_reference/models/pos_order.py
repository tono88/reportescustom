# -*- coding: utf-8 -*-

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    no_stock_refund = fields.Boolean(
        string="Reembolso sin inventario",
        help="Marcador técnico: esta orden POS fue creada como reembolso pagado sin generar movimientos de inventario.",
        copy=False,
        default=False,
    )
    refund_origin_order_id = fields.Many2one(
        "pos.order",
        string="Orden POS original del reembolso",
        copy=False,
        index=True,
        readonly=True,
    )

    def _create_order_picking(self):
        """Evita pickings para reembolsos creados por este módulo.

        En Odoo, los movimientos de inventario del POS normalmente se generan al validar/pagar
        una orden. Estos reembolsos se marcan con `no_stock_refund=True`, por lo que si algún
        proceso estándar intenta crear pickings posteriormente, se omiten para esas órdenes.
        """
        normal_orders = self.filtered(lambda order: not order.no_stock_refund)
        if normal_orders:
            return super(PosOrder, normal_orders)._create_order_picking()
        return True
