from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..layout import BANKS, BANK_LABELS, HEIGHT, LAYOUTS, require_bank


class AccountPayment(models.Model):
    _inherit = "account.payment"

    lx350_layout_active = fields.Boolean(compute="_compute_lx350_layout_active")
    lx350_bank = fields.Selection(
        [("banrural", "Banrural"), ("gyt", "G&T Continental")],
        compute="_compute_lx350_layout_active",
    )

    @api.depends("journal_id.bank_check_printing_layout", "company_id.account_check_printing_layout")
    def _compute_lx350_layout_active(self):
        for payment in self:
            payment.lx350_layout_active = payment.journal_id._lx350_layout() in LAYOUTS if payment.journal_id else False
            payment.lx350_bank = BANKS.get(payment.journal_id._lx350_layout(), False) if payment.journal_id else False

    def _lx350_check_payments(self):
        self.check_access("read")
        if not self or len(self.journal_id) != 1 or len(self.company_id) != 1:
            raise UserError(_("Imprime cheques de una sola empresa y diario a la vez."))
        if self.journal_id._lx350_layout() not in LAYOUTS:
            raise UserError(_("Selecciona el diseño personal Banrural o G&T / LX-350 en el diario bancario."))
        for payment in self:
            if payment.payment_method_code != "check_printing" or payment.payment_type != "outbound":
                raise UserError(_("Este formato es para pagos salientes mediante cheque."))
            if payment.state in ("canceled", "cancel", "cancelled", "rejected"):
                raise UserError(_("No se puede imprimir un cheque de un pago anulado o rechazado."))
            if payment.currency_id.name != "GTQ":
                raise UserError(_("Este formato está diseñado para cheques en quetzales (GTQ)."))
        return self.journal_id._lx350_layout()

    def print_checks(self):
        action = super().print_checks()
        # Odoo's pre-numbered wizard builds a fresh context. Preserve only our
        # opt-in flag so USB printing still uses the normal numbering workflow.
        if self.env.context.get("lx350_direct") and action.get("res_model") == "print.prenumbered.checks":
            action["context"] = dict(action.get("context", {}), lx350_direct=True)
        return action

    def _lx350_print_for_bank(self, bank):
        self.ensure_one()
        layout = self._lx350_check_payments()
        try:
            require_bank(layout, bank)
        except ValueError as exc:
            raise UserError(str(exc)) from exc
        return self.with_context(lx350_direct=True).print_checks()

    def action_lx350_print_banrural_usb(self):
        return self._lx350_print_for_bank("banrural")

    def action_lx350_print_gyt_usb(self):
        return self._lx350_print_for_bank("gyt")

    def _lx350_report_action(self, direct=False):
        layout = self._lx350_check_payments()
        if any(not payment.check_number for payment in self):
            raise UserError(_("Usa primero Imprimir cheque para asignar el número preimpreso."))
        report = self.env.ref(layout)
        # Fail invalid content/geometry within the numbering transaction, before
        # handing control to the browser or desktop spooler.
        self.env["report." + report.report_name]._get_report_values(self.ids)
        action = report.report_action(self)
        action["lx350"] = {
            "direct": direct,
            "company_id": self.company_id.id,
            "width": LAYOUTS[layout],
            "height": HEIGHT,
            "bank_label": BANK_LABELS[layout],
        }
        return action

    def action_lx350_download_pdf(self):
        return self._lx350_report_action(direct=False)

    def action_lx350_reprint_usb(self):
        self.ensure_one()
        return self._lx350_report_action(direct=True)

    def do_print_checks(self):
        layouts = {payment.journal_id._lx350_layout() for payment in self}
        if layouts.intersection(LAYOUTS):
            action = self._lx350_report_action(direct=bool(self.env.context.get("lx350_direct")))
            self.write({"is_sent": True})
            return action
        return super().do_print_checks()
