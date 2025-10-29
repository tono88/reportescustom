from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Exponemos márgenes de impresión de cheque (ya existen en res.company)
    account_check_printing_margin_top = fields.Float(
        related="company_id.account_check_printing_margin_top", readonly=False
    )
    account_check_printing_margin_left = fields.Float(
        related="company_id.account_check_printing_margin_left", readonly=False
    )
    account_check_printing_margin_right = fields.Float(
        related="company_id.account_check_printing_margin_right", readonly=False
    )
