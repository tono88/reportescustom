from odoo import api, fields, models
from math import modf
try:
    from num2words import num2words
except Exception:
    num2words = None

class AccountMove(models.Model):
    _inherit = "account.move"

    # Si ya existen en tu BD, estos add-ons no chocan; si ya los tienes en otro módulo,
    # puedes comentar estas líneas.
    firma_fel = fields.Char(string="Firma FEL / No. Autorización")
    serie_fel = fields.Char(string="Serie FEL")
    numero_fel = fields.Char(string="Número DTE")

    amount_total_gt_words = fields.Char(
        string="Total en letras (GT)",
        compute="_compute_amount_total_gt_words",
        store=False,
    )

    @api.depends("amount_total", "currency_id")
    def _compute_amount_total_gt_words(self):
        for move in self:
            amount = move.amount_total or 0.0
            # Quetzales y centavos como /100
            frac, entero = modf(amount)
            quetzales = int(entero)
            centavos = int(round(frac * 100.0))
            if centavos == 100:
                quetzales += 1
                centavos = 0

            if num2words:
                texto_entero = num2words(quetzales, lang="es")
            else:
                # Fallback simple en caso extremo (deberías tener num2words en Odoo)
                texto_entero = str(quetzales)

            # Formato requerido: "DIEZ QUETZALES CON 05/100"
            moneda = "QUETZALES" if quetzales != 1 else "QUETZAL"
            texto = f"{texto_entero} {moneda} CON {centavos:02d}/100"
            move.amount_total_gt_words = texto.upper()
