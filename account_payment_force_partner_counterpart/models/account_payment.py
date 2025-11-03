# -*- coding: utf-8 -*-
from odoo import models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    # Normalizamos la contrapartida en el valor final del move, sin importar overrides previos.
    def _generate_move_vals(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        move_vals = super()._generate_move_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
            line_ids=line_ids,
        )

        journal = self.journal_id
        if journal.type not in ("bank", "cash"):
            return move_vals

        partner = self.partner_id.commercial_partner_id
        if not partner:
            return move_vals

        liquidity_account = journal.default_account_id
        if not liquidity_account:
            return move_vals

        partner_account = (
            partner.property_account_receivable_id
            if self.partner_type == "customer"
            else partner.property_account_payable_id
        )
        if not partner_account:
            return move_vals

        # move_vals['line_ids'] es formato (0,0,vals) / (1,id,vals) etc.
        new_line_ids = []
        for tup in move_vals.get("line_ids", []):
            if not isinstance(tup, (list, tuple)) or len(tup) < 3:
                new_line_ids.append(tup)
                continue
            cmd, _id, vals = tup
            if not isinstance(vals, dict):
                new_line_ids.append(tup)
                continue

            acc_id = vals.get("account_id")
            if acc_id == liquidity_account.id:
                # limpiar partner en la línea de banco
                vals = dict(vals, partner_id=False)
            else:
                # forzar AR/AP y partner
                vals = dict(vals, account_id=partner_account.id, partner_id=partner.id)

            new_line_ids.append((cmd, _id, vals))

        move_vals["line_ids"] = new_line_ids
        return move_vals
