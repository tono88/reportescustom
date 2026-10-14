from odoo import fields, models

from ..layout import COMMERCIAL, PERSONAL


class ResCompany(models.Model):
    _inherit = "res.company"

    account_check_printing_layout = fields.Selection(
        selection_add=[
            (PERSONAL, "Banrural / LX-350 — Personal 165.10 × 69.85 mm"),
            (COMMERCIAL, "Banrural / LX-350 — Comercial 190.50 × 69.85 mm"),
        ],
        ondelete={PERSONAL: "set default", COMMERCIAL: "set default"},
    )
