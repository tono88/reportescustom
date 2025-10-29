# -*- coding: utf-8 -*-
from odoo import api, models

class ReportCheckGT(models.AbstractModel):
    _name = "report.l10n_gt_check_printing.report_check"
    _description = "Report: Guatemala Check"

    def _amount_words_line(self, payment):
        """Devuelve el monto en letras y los centavos en la MISMA línea.
        Ejemplo: 'Quinientos Con 25/100'
        """
        amount = payment.amount or 0.0
        integer = int(amount)
        cents = int(round((amount - integer) * 100))

        # Palabras del entero usando la propia moneda (respeta localización si existe)
        try:
            try:
                words = payment.currency_id.amount_to_text(integer, lang=self.env.user.lang)
            except TypeError:
                # Algunas implementaciones de amount_to_text no aceptan lang
                words = payment.currency_id.amount_to_text(integer)
        except Exception:
            words = str(integer)

        if isinstance(words, str):
            words = words.strip()
            if words:
                # Capitaliza la primera letra
                words = words[0].upper() + words[1:]
            # ' y ' -> ' Con '
            words = words.replace(" y ", " Con ")

        return f"{words} {cents:02d}/100"

    def _fmt_date(self, d):
        """Devuelve la fecha dd/mm/YYYY"""
        return d.strftime("%d/%m/%Y") if d else ""

    def _is_void_payment(self, payment):
        """True si el pago/asiento está anulado (cancelled/cancel)."""
        st = (getattr(payment, "state", "") or "").lower()
        if st in {"canceled", "cancelled", "cancel"}:
            return True

        move = getattr(payment, "move_id", False)
        if move and (getattr(move, "state", "") or "").lower() in {"cancel", "canceled", "cancelled"}:
            return True

        return False

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["account.payment"].browse(docids)
        return {
            "docs": docs,
            "amount_words_line": self._amount_words_line,  # monto en letras + centavos en una línea
            "fmt_date": self._fmt_date,                    # fecha dd/mm/YYYY
            "upper": lambda s: (s or "").upper(),        # helper para mayúsculas
            "is_void_payment": self._is_void_payment,      # cheque anulado
        }
