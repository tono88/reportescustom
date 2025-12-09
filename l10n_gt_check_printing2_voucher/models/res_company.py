from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    # Agregamos nuevas opciones al dropdown de 'Diseño del cheque'
    # para la variante con voucher.
    account_check_printing_layout = fields.Selection(
        selection_add=[
            ("l10n_gt_check_printing2_voucher.check_top_voucher", "Cheque GT2 + Voucher - Top Stub"),
            ("l10n_gt_check_printing2_voucher.check_middle_voucher", "Cheque GT2 + Voucher - Middle Stub"),
            ("l10n_gt_check_printing2_voucher.check_bottom_voucher", "Cheque GT2 + Voucher - Bottom Stub"),
        ],
        ondelete={
            "l10n_gt_check_printing2_voucher.check_top_voucher": "set default",
            "l10n_gt_check_printing2_voucher.check_middle_voucher": "set default",
            "l10n_gt_check_printing2_voucher.check_bottom_voucher": "set default",
        },
    )
