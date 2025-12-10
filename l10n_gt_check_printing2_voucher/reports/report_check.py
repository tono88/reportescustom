# -*- coding: utf-8 -*-
from odoo import api, models, fields


class ReportCheckVoucher(models.AbstractModel):
    _name = "report.l10n_gt_check_printing2_voucher.report_check"
    _description = "Guatemala Check 2 + Voucher"

    # ===================== HELPERS VOUCHER =====================

    def _get_concept(self, payment):
        """Texto que saldrá como 'Concepto' en el voucher."""
        for field_name in ("ref", "communication", "narration"):
            if hasattr(payment, field_name):
                value = getattr(payment, field_name)
                if value:
                    return value
        return ""

    def _get_voucher_lines(self, payment):
        """Líneas contables a mostrar en el voucher."""
        move = getattr(payment, "move_id", False)
        if not move:
            return self.env["account.move.line"]
        # normalmente serán 2 líneas: banco y cuenta por pagar
        return move.line_ids.filtered(lambda l: l.debit or l.credit)

    def _format_amount(self, amount):
         """Formateo estándar con miles y 2 decimales: 1,234.56."""
        amt = amount or 0.0
        return f"{amt:,.2f}"

    def _now_time(self):
        """Hora local del usuario para la parte inferior del voucher."""
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return now.strftime("%H:%M:%S")

    # ===================== VALORES PARA QWEB =====================

    @api.model
    def _get_report_values(self, docids, data=None):
        """Usa la lógica del módulo base y añade los helpers del voucher."""
        docs = self.env["account.payment"].browse(docids)
        base = self.env["report.l10n_gt_check_printing2.report_check"]

        #return {
        #    "docs": docs,
        #    # helpers del módulo original
        #    "amount_words_line": base._amount_words_line,
        #    "fmt_date": base._fmt_date,
        #    "upper": lambda s: (s or "").upper(),
        #    "is_void_payment": base._is_void_payment,
        #    # helpers extra para el voucher
        #    "get_concept": self._get_concept,
        #    "get_voucher_lines": self._get_voucher_lines,
        #    "format_amount": self._format_amount,
        #    "now_time": self._now_time,
        #    "user": self.env.user,
        #    # MUY IMPORTANTE: este helper ya NO usa ningún campo analítico
        #    "get_line_analytic": lambda line: "",
        #}
        
        return {
            "docs": docs,
            "amount_words_line": base._amount_words_line,
            "fmt_date": base._fmt_date,
            "upper": self._upper_fixed,        # <-- usa el helper nuevo
            "is_void_payment": base._is_void_payment,
            "get_concept": self._get_concept,
            "get_voucher_lines": self._get_voucher_lines,
            "format_amount": self._format_amount,
            "now_time": self._now_time,
            "user": self.env.user,
            "fix_text": self._fix_encoding,    # <-- para usarlo directo en QWeb
        }

    def _fix_encoding(self, text):
        """Corrige cadenas mal guardadas tipo PALÃN -> PALÍN.
        Si el texto ya está bien, lo deja igual.
        """
        if not text:
            return ""
        # Si viniera en bytes
        if isinstance(text, bytes):
            for enc in ("utf-8", "latin-1"):
                try:
                    return text.decode(enc)
                except Exception:
                    continue
            return text.decode("utf-8", errors="ignore")

        # Aquí ya es str: probamos el caso típico PALÃN / DescripciÃ³n
        try:
            return text.encode("latin-1").decode("utf-8")
        except Exception:
            # Si no es ese caso, lo dejamos como venía
            return text

    def _upper_fixed(self, text):
        """upper() que primero corrige acentos mal codificados."""
        return self._fix_encoding(text).upper()

