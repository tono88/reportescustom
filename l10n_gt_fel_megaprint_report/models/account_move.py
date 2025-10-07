# -*- coding: utf-8 -*-
from odoo import models, fields, api
from urllib.parse import quote_plus

class AccountMove(models.Model):
    _inherit = 'account.move'

    fel_qr_encoded = fields.Char(
        string="FEL QR Encoded",
        compute="_compute_fel_qr",
        store=False
    )

    @api.depends('firma_fel', 'amount_total', 'company_id.vat', 'partner_id.vat')
    def _compute_fel_qr(self):
        base = "https://felpub.c.sat.gob.gt/verificador-web/publico/vistas/verificacionDte.jsf"
        for move in self:
            numero = (getattr(move, 'firma_fel', '') or '').strip()
            # Limpieza básica de NIT (remueve prefijo GT y guiones)
            emisor = (move.company_id.vat or '').replace('GT', '').replace('-', '').strip()
            receptor = (move.partner_id.vat or '').replace('GT', '').replace('-', '').strip()
            monto = f"{(move.amount_total or 0.0):.2f}"

            full_url = (
                f"{base}?tipo=autorizacion"
                f"&numero={numero}"
                f"&emisor={emisor}"
                f"&receptor={receptor}"
                f"&monto={monto}"
            )
            move.fel_qr_encoded = quote_plus(full_url)