# -*- coding: utf-8 -*-
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    amount_payment_cash = fields.Monetary(
        string='Efectivo',
        compute='_compute_amounts_by_method',
        currency_field='currency_id',
        store=True,
    )
    amount_payment_cuenta = fields.Monetary(
        string='Cuenta',
        compute='_compute_amounts_by_method',
        currency_field='currency_id',
        store=True,
    )

    @api.depends(
        'payment_ids.amount',
        'payment_ids.payment_method_id.name',
        'payment_ids.payment_method_id.is_cash_count',
    )
    def _compute_amounts_by_method(self):
        for order in self:
            cash = 0.0
            cuenta = 0.0
            for p in order.payment_ids:
                method = p.payment_method_id
                # Efectivo: métodos con control de caja
                if getattr(method, 'is_cash_count', False):
                    cash += p.amount
                # Cuenta: nombre del método contiene "Cuenta" (insensible a mayúsculas)
                if 'cuenta' in (method.name or '').lower():
                    cuenta += p.amount
            order.amount_payment_cash = cash
            order.amount_payment_cuenta = cuenta