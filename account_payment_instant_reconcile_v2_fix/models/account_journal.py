# -*- coding: utf-8 -*-
from odoo import fields, models

class AccountJournal(models.Model):
    _inherit = "account.journal"

    instant_reconcile_on_post = fields.Boolean(
        string="Reconciliar pago al validar",
        help="Si está activo, al validar un pago en este diario se intentará reconciliar "
             "inmediatamente contra las facturas abiertas del partner.",
        default=True,
    )

    fix_liquidity_only_entry = fields.Boolean(
        string="Corregir asiento liquidez↔liquidez",
        help="Si el asiento del pago solo contiene cuentas de liquidez (banco/caja), "
             "convertir automáticamente la contrapartida a CxC/CxP del partner antes de conciliar.",
        default=True,
    )