# -*- coding: utf-8 -*-
from odoo import models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        vals_list = super()._prepare_move_line_default_vals(write_off_line_vals)
        if self.journal_id.type not in ("bank", "cash"):
            return vals_list

        partner = self.partner_id.commercial_partner_id
        if not partner:
            return vals_list

        liquidity_account = self.journal_id.default_account_id
        if not liquidity_account:
            return vals_list

        partner_account = (
            partner.property_account_receivable_id
            if self.partner_type == "customer"
            else partner.property_account_payable_id
        )
        if not partner_account:
            return vals_list

        for v in vals_list:
            account_id = v.get("account_id")
            if account_id == liquidity_account.id:
                v["partner_id"] = False
            else:
                v["account_id"] = partner_account.id
                v["partner_id"] = partner.id
        return vals_list
