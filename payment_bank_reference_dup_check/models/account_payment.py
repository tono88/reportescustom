from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _find_bank_reference_duplicates(self, bank_reference):
        """Return payments in same company with same bank_reference (excluding self, excluding cancelled)."""
        self.ensure_one()
        if not bank_reference:
            return self.env["account.payment"]

        domain = [
            ("id", "not in", self.ids),
            ("company_id", "=", self.company_id.id),
            ("bank_reference", "=", bank_reference),
            ("state", "!=", "cancel"),
        ]
        return self.search(domain)

    def _open_dup_bank_reference_wizard(self, duplicates):
        self.ensure_one()
        wiz = self.env["account.dup.bank.reference.wizard"].create({
            "origin_model": "payment",
            "origin_payment_id": self.id,
            "bank_reference": self.bank_reference,
            "duplicate_payment_ids": [(6, 0, duplicates.ids)],
        })
        return {
            "type": "ir.actions.act_window",
            "name": "Referencia bancaria duplicada",
            "res_model": "account.dup.bank.reference.wizard",
            "view_mode": "form",
            "res_id": wiz.id,
            "target": "new",
        }

    def action_post(self):
        """When user posts a payment, warn if bank_reference already exists."""
        if not self.env.context.get("skip_bank_reference_dup_check"):
            for pay in self:
                duplicates = pay._find_bank_reference_duplicates(pay.bank_reference)
                if duplicates:
                    return pay._open_dup_bank_reference_wizard(duplicates)

        return super().action_post()
