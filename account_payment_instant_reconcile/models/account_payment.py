# -*- coding: utf-8 -*-
from odoo import api, models

RECEIVABLE_TYPES = ('asset_receivable',)
PAYABLE_TYPES = ('liability_payable',)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        res = super().action_post()
        for payment in self:
            journal = payment.journal_id
            if not journal.instant_reconcile_on_post:
                continue

            move = payment.move_id
            if not move or move.state != "posted":
                continue

            partner = payment.partner_id.commercial_partner_id

            # Lines on receivable/payable not reconciled
            pay_lines = move.line_ids.filtered(
                lambda l: not l.reconciled and l.account_id and l.account_id.account_type in (RECEIVABLE_TYPES + PAYABLE_TYPES)
            )
            if not pay_lines:
                continue

            for pl in pay_lines:
                # Build domain for opposite open items for same partner/account
                domain = [
                    ('company_id', '=', pl.company_id.id),
                    ('account_id', '=', pl.account_id.id),
                    ('partner_id', '=', partner.id),
                    ('reconciled', '=', False),
                    ('move_id.state', '=', 'posted'),
                    ('id', '!=', pl.id),
                ]
                # Opposite sign criterion using balance
                if pl.balance > 0:
                    domain.append(('balance', '<', 0))
                elif pl.balance < 0:
                    domain.append(('balance', '>', 0))
                counterpart_lines = self.env['account.move.line'].search(domain, limit=500)
                if counterpart_lines:
                    (pl + counterpart_lines).with_context(skip_full_reconcile_check=False).reconcile()
        return res