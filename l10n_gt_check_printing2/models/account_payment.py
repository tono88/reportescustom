# -*- coding: utf-8 -*-
from odoo import models

GT2_LAYOUTS = {
    "l10n_gt_check_printing2.check_top",
    "l10n_gt_check_printing2.check_middle",
    "l10n_gt_check_printing2.check_bottom",
}

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def do_print_checks(self):
        """Sobrecarga para usar nuestro layout/reporte cuando la empresa
        está configurada con cualquiera de los layouts GT2.
        """
        layouts = set(self.mapped("company_id.account_check_printing_layout"))
        if layouts and layouts.issubset(GT2_LAYOUTS):
            action = self.env.ref("l10n_gt_check_printing2.action_report_check_gt2")
            return action.report_action(self)
        return super().do_print_checks()

    def _get_checks_report_action(self):
        """En versiones nuevas, Odoo llama a esto internamente para el botón
        'Imprimir Cheque'. Mantenemos compatibilidad.
        """
        self.ensure_one()
        if self.company_id.account_check_printing_layout in GT2_LAYOUTS:
            return self.env.ref("l10n_gt_check_printing2.action_report_check_gt2")
        return super()._get_checks_report_action()
