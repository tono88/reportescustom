from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    account_check_printing_layout = fields.Selection(
        selection_add=[
            ("l10n_gt_check_printing.check_top", "Cheque GT - Top Stub"),
            ("l10n_gt_check_printing.check_middle", "Cheque GT - Middle Stub"),
            ("l10n_gt_check_printing.check_bottom", "Cheque GT - Bottom Stub"),
        ],
        ondelete={
            "l10n_gt_check_printing.check_top": "set default",
            "l10n_gt_check_printing.check_middle": "set default",
            "l10n_gt_check_printing.check_bottom": "set default",
        },
    )
