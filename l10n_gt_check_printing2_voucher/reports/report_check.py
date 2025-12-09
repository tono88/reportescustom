# -*- coding: utf-8 -*-
from odoo import api, models, fields


class ReportCheckGT2Voucher(models.AbstractModel):
    _name = "report.l10n_gt_check_printing2_voucher.report_check"
    _description = "Report: Guatemala Check 2 + Voucher"

    # Reutilizamos la lógica del reporte base para monto en letras, fecha y anulado
    def _base_report(self):
        return self.env["report.l10n_gt_check_printing2.report_check"]

    def _amount_words_line(self, payment):
        return self._base_report()._amount_words_line(payment)

    def _fmt_date(self, d):
        return self._base_report()._fmt_date(d)

    def _is_void_payment(self, payment):
        return self._base_report()._is_void_payment(payment)

    # ==== Helpers específicos del voucher ====

    def _get_concept(self, payment):
        """Texto que saldrá como 'Concepto' en el voucher."""
        for field in ("ref", "communication", "narration"):
            if hasattr(payment, field):
                value = getattr(payment, field)
                if value:
                    return value
        return ""

    def _get_voucher_lines(self, payment):
        """Líneas contables a mostrar en el voucher."""
        move = getattr(payment, "move_id", False)
        if not move:
            return self.env["account.move.line"]
        # Normalmente serán 2 líneas: banco y cuenta por pagar, pero soporta más.
        return move.line_ids.filtered(lambda l: l.debit or l.credit)

    def _format_amount(self, amount):
        """Formateo estándar 0.00 para el voucher."""
        return "%0.2f" % (amount or 0.0)

    def _now_time(self):
        """Hora local del usuario para la parte inferior del voucher."""
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return now.strftime("%H:%M:%S")

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["account.payment"].browse(docids)
        return {
            "docs": docs,
            "amount_words_line": self._amount_words_line,
            "fmt_date": self._fmt_date,
            "upper": lambda s: (s or "").upper(),
            "is_void_payment": self._is_void_payment,
            # Helpers extra para el voucher
            "get_concept": self._get_concept,
            "get_voucher_lines": self._get_voucher_lines,
            "format_amount": self._format_amount,
            "now_time": self._now_time,
            "user": self.env.user,
            # NUEVO:
            "get_line_analytic": self._get_line_analytic,
        }
    def _get_line_analytic(self, line):
        """Devuelve el centro de costo/analítica de la línea si existe.
        Si no hay campo analítico, devuelve cadena vacía para no romper.
        """
        # Caso 1: base antigua con analytic_account_id M2O
        if 'analytic_account_id' in line._fields and line.analytic_account_id:
            return line.analytic_account_id.code or line.analytic_account_id.name

        # Caso 2: distribución analítica (Odoo nuevo)
        if 'analytic_distribution' in line._fields and line.analytic_distribution:
            dist = line.analytic_distribution
            # dist suele ser un dict {analytic_id: porcentaje}
            if isinstance(dist, dict) and dist:
                analytic_id = int(list(dist.keys())[0])
                analytic = self.env['account.analytic.account'].browse(analytic_id)
                if analytic:
                    return analytic.code or analytic.name

        # Si no hay nada analítico configurado
        return ""
