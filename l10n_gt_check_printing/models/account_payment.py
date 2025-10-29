# -*- coding: utf-8 -*-
from odoo import models

GT_LAYOUTS = {
    "l10n_gt_check_printing.check_top",
    "l10n_gt_check_printing.check_middle",
    "l10n_gt_check_printing.check_bottom",
}

class AccountPayment(models.Model):
    _inherit = "account.payment"

    # Wizard clásico: imprime con nuestro reporte si el layout de la compañía es GT
    def do_print_checks(self):
        layouts = set(self.mapped("company_id.account_check_printing_layout"))
        if layouts and layouts.issubset(GT_LAYOUTS):
            action = self.env.ref("l10n_gt_check_printing.action_report_check_gt")
            return action.report_action(self)
        return super().do_print_checks()

    # Ruta alternativa (Odoo 18) para obtener la acción del reporte
    def _get_checks_report_action(self):
        self.ensure_one()
        if self.company_id.account_check_printing_layout in GT_LAYOUTS:
            return self.env.ref("l10n_gt_check_printing.action_report_check_gt")
        return super()._get_checks_report_action()

