# -*- coding: utf-8 -*-
from odoo import models

RECEIVABLE_TYPES = ('asset_receivable',)
PAYABLE_TYPES = ('liability_payable',)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _is_inbound(self):
        """Fallback compatible check for inbound payments across builds."""
        # Prefer 'payment_type' field when available
        pt = getattr(self, 'payment_type', False)
        if pt:
            return pt in ('inbound', 'inbound_refund')
        # Fallback: if method exists on this build
        if hasattr(super(), 'is_inbound'):
            try:
                return super().is_inbound()
            except Exception:
                pass
        # As a last resort, assume inbound for 'receive' payment_direction
        pd = getattr(self, 'payment_direction', False)
        if pd:
            return pd in ('inbound', 'receive')
        return False

    # --- helpers ---
    def _partner_arap(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        return partner.property_account_receivable_id if self._is_inbound() else partner.property_account_payable_id

    def _fix_liquidity_only_entry(self):
        """If payment entry is liquidity-only (bank<->bank), convert one side to partner AR/AP and set partner."""
        for payment in self:
            journal = payment.journal_id
            if not getattr(journal, 'fix_liquidity_only_entry', True):
                continue
            move = payment.move_id
            if not move or move.state != 'posted':
                continue

            # Liquidity lines (cash/bank)
            liquidity_lines = move.line_ids.filtered(lambda l: l.account_id and l.account_id.account_type == 'asset_cash')
            if not liquidity_lines:
                continue
            # If there is already a receivable/payable line, nothing to repair
            has_arap = any(l.account_id and l.account_id.account_type in (RECEIVABLE_TYPES + PAYABLE_TYPES) for l in move.line_ids)
            if has_arap:
                continue
            # Need at least 2 liquidity lines to swap one side
            if len(liquidity_lines) < 2:
                continue

            arap = payment._partner_arap()
            if not arap or not arap.reconcile:
                continue

            # For inbound: credit should become AR; for outbound: debit should become AP
            target = None
            if payment._is_inbound():
                target = liquidity_lines.filtered(lambda l: l.balance < 0)[:1]
            else:
                target = liquidity_lines.filtered(lambda l: l.balance > 0)[:1]
            if not target:
                target = liquidity_lines[:1]
            target.write({
                'account_id': arap.id,
                'partner_id': payment.partner_id.commercial_partner_id.id,
            })

    # --- main hook ---
    def action_post(self):
        res = super().action_post()
        for payment in self:
            journal = payment.journal_id
            move = payment.move_id
            if not move or move.state != 'posted':
                continue

            # try to fix liquidity-only
            payment._fix_liquidity_only_entry()

            if not getattr(journal, 'instant_reconcile_on_post', True):
                continue

            partner = payment.partner_id.commercial_partner_id
            # lines on AR/AP not reconciled
            pay_lines = move.line_ids.filtered(
                lambda l: not l.reconciled and l.account_id and l.account_id.account_type in (RECEIVABLE_TYPES + PAYABLE_TYPES)
            )
            if not pay_lines:
                continue

            for pl in pay_lines:
                domain = [
                    ('company_id', '=', pl.company_id.id),
                    ('account_id', '=', pl.account_id.id),
                    ('partner_id', '=', partner.id),
                    ('reconciled', '=', False),
                    ('move_id.state', '=', 'posted'),
                    ('id', '!=', pl.id),
                ]
                # match opposite sign
                if pl.balance > 0:
                    domain.append(('balance', '<', 0))
                elif pl.balance < 0:
                    domain.append(('balance', '>', 0))
                counterparts = self.env['account.move.line'].search(domain, limit=500)
                if counterparts:
                    (pl + counterparts).reconcile()
        return res