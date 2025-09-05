# -*- coding: utf-8 -*-
from odoo import api, models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        res = super().action_post()
        # Reconciliation logic: for each posted payment, if the journal flag is enabled,
        # reconcile receivable/payable lines immediately with open items of the partner.
        for payment in self:
            journal = payment.journal_id
            if not journal.instant_reconcile_on_post:
                continue

            # Only attempt for posted moves
            move = payment.move_id
            if not move or move.state != "posted":
                continue

            company = payment.company_id
            partner = payment.partner_id.commercial_partner_id

            # Collect payment lines on receivable/payable that are not reconciled
            pay_lines = move.line_ids.filtered(
                lambda l: l.account_id.internal_type in ('receivable', 'payable') and not l.reconciled
            )
            if not pay_lines:
                continue

            # For each payment line, find opposite open items for the same partner/account/company
            for pl in pay_lines:
                sign = 1 if pl.balance > 0 else -1
                domain = [
                    ('company_id', '=', company.id),
                    ('account_id', '=', pl.account_id.id),
                    ('partner_id', '=', partner.id),
                    ('reconciled', '=', False),
                    ('move_id.state', '=', 'posted'),
                    # opposite sign (allow tiny rounding)
                    ('balance', '<', 0) if pl.balance > 0 else ('balance', '>', 0),
                ]
                counterpart_lines = self.env['account.move.line'].search(domain, limit=200)
                if counterpart_lines:
                    # Try to reconcile payment line with the found counterpart lines
                    # Odoo's reconcile supports partials if amounts don't match exactly.
                    (pl + counterpart_lines).with_context(skip_full_reconcile_check=False).reconcile()
        return res