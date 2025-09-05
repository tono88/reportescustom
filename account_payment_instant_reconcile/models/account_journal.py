# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountJournal(models.Model):
    _inherit = "account.journal"

    instant_reconcile_on_post = fields.Boolean(
        string="Reconciliar pago al validar",
        help="Si está activo, al validar un pago en este diario se intentará "
             "reconciliar inmediatamente contra las facturas abiertas del partner.",
        default=True
    )