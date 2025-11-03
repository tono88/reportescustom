# -*- coding: utf-8 -*-
from odoo import api, models

INVOICE_TYPES = ("out_invoice", "in_invoice", "out_refund", "in_refund", "out_receipt", "in_receipt")

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _reconcile_orphan_invoices(self, limit=500):
        AML = self.env["account.move.line"]
        inv_lines = AML.search([
            ("company_id", "=", self.env.company.id),
            ("reconciled", "=", False),
            ("account_id.account_type", "in", ("asset_receivable", "liability_payable")),
            ("move_id.state", "=", "posted"),
            ("move_id.move_type", "in", INVOICE_TYPES),
        ], limit=limit)

        total = 0
        for inv_line in inv_lines:
            pay_lines = AML.search([
                ("company_id", "=", inv_line.company_id.id),
                ("reconciled", "=", False),
                ("partner_id", "=", inv_line.partner_id.id),
                ("account_id", "=", inv_line.account_id.id),
                ("move_id.state", "=", "posted"),
                ("move_id.move_type", "=", "entry"),
            ], order="date asc, id asc")
            for pl in pay_lines:
                try:
                    (pl | inv_line).reconcile()
                    if inv_line.reconciled:
                        total += 1
                        break
                except Exception:
                    continue
        return total

    @api.model
    def cron_fix_orphan_payments(self):
        self._reconcile_orphan_invoices(limit=500)
        return True

    def action_fix_orphan_payments(self):
        self.ensure_one()
        self._reconcile_orphan_invoices(limit=500)
        return True
