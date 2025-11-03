# -*- coding: utf-8 -*-
from odoo import models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    # Firma compatible con posibles kwargs extra en tu stack
    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None, existing_lines=None, **kwargs):
        vals_list = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
            existing_lines=existing_lines,
            **kwargs
        )

        journal = self.journal_id
        if journal.type not in ("bank", "cash"):
            return vals_list

        partner = self.partner_id.commercial_partner_id
        if not partner:
            return vals_list

        liquidity_account = journal.default_account_id
        if not liquidity_account:
            return vals_list

        partner_account = (
            partner.property_account_receivable_id
            if self.partner_type == "customer"
            else partner.property_account_payable_id
        )
        if not partner_account:
            return vals_list

        # Forzar que la contrapartida sea AR/AP y dejar la línea de liquidez limpia
        for v in vals_list:
            if v.get("account_id") == liquidity_account.id:
                v["partner_id"] = False
            else:
                v["account_id"] = partner_account.id
                v["partner_id"] = partner.id

        return vals_list
