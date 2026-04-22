from odoo import api, fields, models
from odoo.tools.misc import formatLang


class AccountDupBankReferenceWizard(models.TransientModel):
    _name = "account.dup.bank.reference.wizard"
    _description = "Duplicate Bank Reference Confirmation"

    origin_model = fields.Selection(
        [("payment", "Payment"), ("register", "Register Payment")],
        required=True,
        readonly=True,
    )
    origin_payment_id = fields.Many2one("account.payment", readonly=True)
    origin_register_id = fields.Many2one("account.payment.register", readonly=True)

    bank_reference = fields.Char(readonly=True)
    duplicate_payment_ids = fields.Many2many(
        "account.payment",
        string="Pagos existentes con la misma referencia",
        readonly=True,
    )

    duplicates_html = fields.Html(
        string="Pagos encontrados",
        compute="_compute_duplicates_html",
        readonly=True,
        sanitize=False,
    )

    @api.depends("duplicate_payment_ids")
    def _compute_duplicates_html(self):
        for wiz in self:
            if not wiz.duplicate_payment_ids:
                wiz.duplicates_html = ""
                continue

            rows = []
            for p in wiz.duplicate_payment_ids:
                # Relative URL works fine inside Odoo
                href = f"#id={p.id}&model=account.payment&view_type=form"
                amount_str = formatLang(
                    wiz.env,
                    p.amount,
                    currency_obj=p.currency_id,
                )
                rows.append(
                    f"""<tr>
                        <td><a href="{href}">{p.display_name}</a></td>
                        <td>{(p.partner_id.display_name or "")}</td>
                        <td>{(p.date or "")}</td>
                        <td style="text-align:right">{amount_str}</td>
                        <td>{(p.state or "")}</td>
                    </tr>"""
                )

            table = f"""

            <div class="o_row">
              <table class="table table-sm table-hover">
                <thead>
                  <tr>
                    <th>Pago</th>
                    <th>Proveedor/Cliente</th>
                    <th>Fecha</th>
                    <th style="text-align:right">Importe</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {''.join(rows)}
                </tbody>
              </table>
            </div>
            """
            wiz.duplicates_html = table

    def action_proceed(self):
        """Retry original action but skipping the duplicate check."""
        self.ensure_one()
        ctx = dict(self.env.context, skip_bank_reference_dup_check=True)

        if self.origin_model == "payment" and self.origin_payment_id:
            return self.origin_payment_id.with_context(ctx).action_post()

        if self.origin_model == "register" and self.origin_register_id:
            return self.origin_register_id.with_context(ctx).action_create_payments()

        return {"type": "ir.actions.act_window_close"}
