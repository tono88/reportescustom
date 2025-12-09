# -*- coding: utf-8 -*-
from odoo import models

GT2_LAYOUTS = {
    "l10n_gt_check_printing2.check_top",
    "l10n_gt_check_printing2.check_middle",
    "l10n_gt_check_printing2.check_bottom",
}

GT2_VOUCHER_LAYOUTS = {
    "l10n_gt_check_printing2_voucher.check_top_voucher",
    "l10n_gt_check_printing2_voucher.check_middle_voucher",
    "l10n_gt_check_printing2_voucher.check_bottom_voucher",
}

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def do_print_checks(self):
        """Sobrecarga para usar nuestro layout/reporte cuando la empresa
        está configurada con cualquiera de los layouts GT2 con voucher.

        Si no coincide, caemos al super(), que será el método de
        l10n_gt_check_printing2 o el de Odoo base.
        """
        layouts = set(self.mapped("company_id.account_check_printing_layout"))
        if layouts and layouts.issubset(GT2_VOUCHER_LAYOUTS):
            action = self.env.ref("l10n_gt_check_printing2_voucher.action_report_check_gt2_voucher")
            return action.report_action(self)
        return super().do_print_checks()

    def _get_checks_report_action(self):
        """En versiones nuevas, Odoo llama a esto internamente para el botón
        'Imprimir Cheque'. Mantenemos compatibilidad.
        """
        self.ensure_one()
        if self.company_id.account_check_printing_layout in GT2_VOUCHER_LAYOUTS:
            return self.env.ref("l10n_gt_check_printing2_voucher.action_report_check_gt2_voucher")
        return super()._get_checks_report_action()
