# models/res_config_settings.py
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Relacionados correctos (editables)
    account_check_printing_margin_top = fields.Float(
        related="company_id.account_check_printing_margin_top", readonly=False
    )
    account_check_printing_margin_left = fields.Float(
        related="company_id.account_check_printing_margin_left", readonly=False
    )
    account_check_printing_margin_right = fields.Float(
        related="company_id.account_check_printing_margin_right", readonly=False
    )
