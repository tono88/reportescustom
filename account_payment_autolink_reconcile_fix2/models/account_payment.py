# -*- coding: utf-8 -*-
from odoo import models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        res = super().action_post()
        self._auto_reconcile_related_invoices()
        return res

    def _auto_reconcile_related_invoices(self):
        AccountMoveLine = self.env["account.move.line"]
        for pay in self:
            if pay.state != "posted" or not pay.move_id:
                continue

            pay_lines = pay.move_id.line_ids.filtered(
                lambda l: not l.reconciled
                and l.partner_id == pay.partner_id
                and l.account_id.internal_type in ("receivable", "payable")
            )
            if not pay_lines:
                continue

            for pl in pay_lines:
                domain = [
                    ("company_id", "=", pay.company_id.id),
                    ("partner_id", "=", pay.partner_id.id),
                    ("reconciled", "=", False),
                    ("account_id", "=", pl.account_id.id),
                    ("move_id.state", "=", "posted"),
                    ("move_id.is_invoice", "=", True),
                ]
                candidates = AccountMoveLine.search(domain, order="date asc, id asc")
                for inv_line in candidates:
                    if inv_line.reconciled:
                        continue
                    try:
                        (pl | inv_line).reconcile()
                        if pl.reconciled:
                            break
                    except Exception:
                        continue
