from odoo import fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    # If your database already has a bank_reference field on the wizard, remove this line.
    bank_reference = fields.Char(string="Bank Reference")

    def _find_bank_reference_duplicates(self, bank_reference, company_id):
        if not bank_reference:
            return self.env["account.payment"]
        domain = [
            ("company_id", "=", company_id),
            ("bank_reference", "=", bank_reference),
            ("state", "!=", "cancel"),
        ]
        return self.env["account.payment"].search(domain)

    def _open_dup_bank_reference_wizard(self, duplicates):
        self.ensure_one()
        wiz = self.env["account.dup.bank.reference.wizard"].create({
            "origin_model": "register",
            "origin_register_id": self.id,
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

    def action_create_payments(self):
        """Before creating payments from invoice wizard, warn if bank_reference exists."""
        self.ensure_one()

        if not self.env.context.get("skip_bank_reference_dup_check"):
            duplicates = self._find_bank_reference_duplicates(self.bank_reference, self.company_id.id)
            if duplicates:
                return self._open_dup_bank_reference_wizard(duplicates)

        return super().action_create_payments()

    def _create_payment_vals_from_batch(self, batch_result):
        """Pass bank_reference to created account.payment records."""
        vals = super()._create_payment_vals_from_batch(batch_result)
        vals["bank_reference"] = self.bank_reference
        return vals
