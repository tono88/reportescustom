from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CurrentBalanceReportWizard(models.TransientModel):
    _name = "current.balance.report.wizard"
    _description = "Saldos por fecha de factura con estado actual"

    report_type = fields.Selection(
        [
            ("customer", "Clientes"),
            ("vendor", "Proveedores"),
        ],
        string="Tipo de reporte",
        required=True,
        default="customer",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string="Fecha de factura desde",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="Fecha de factura hasta",
        required=True,
        default=fields.Date.context_today,
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes / Proveedores",
        help="Déjelo vacío para incluir todos los terceros del periodo.",
    )
    include_paid = fields.Boolean(
        string="Incluir documentos ya pagados",
        default=True,
        help=(
            "Debe permanecer activado si desea que una factura del periodo que fue "
            "pagada posteriormente aparezca con saldo cero y estado Pagado."
        ),
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_("La fecha inicial no puede ser posterior a la fecha final."))

    def _get_move_types(self):
        self.ensure_one()
        if self.report_type == "customer":
            return ("out_invoice", "out_refund")
        return ("in_invoice", "in_refund")

    def _get_moves(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "posted"),
            ("move_type", "in", self._get_move_types()),
            ("invoice_date", ">=", self.date_from),
            ("invoice_date", "<=", self.date_to),
        ]
        if self.partner_ids:
            commercial_partner_ids = self.partner_ids.mapped("commercial_partner_id").ids
            domain.append(("commercial_partner_id", "in", commercial_partner_ids))
        if not self.include_paid:
            domain.append(("payment_state", "!=", "paid"))

        return self.env["account.move"].search(
            domain,
            order="commercial_partner_id, invoice_date, name, id",
        )

    def _payment_state_label(self, move):
        selection = dict(move._fields["payment_state"]._description_selection(self.env))
        return selection.get(move.payment_state, move.payment_state or "")

    def _signed_report_amounts(self, move):
        """Return total, paid and current residual in company currency.

        Invoices/bills are positive. Credit notes/refunds are negative so partner
        subtotals and the grand total remain meaningful.
        """
        sign = -1.0 if move.move_type in ("out_refund", "in_refund") else 1.0
        total = sign * abs(move.amount_total_signed)
        residual = sign * abs(move.amount_residual_signed)
        paid = total - residual
        return total, paid, residual

    def get_report_data(self):
        self.ensure_one()
        groups = defaultdict(lambda: {
            "partner": False,
            "lines": [],
            "total": 0.0,
            "paid": 0.0,
            "residual": 0.0,
        })

        grand_total = grand_paid = grand_residual = 0.0
        for move in self._get_moves():
            partner = move.commercial_partner_id or move.partner_id
            total, paid, residual = self._signed_report_amounts(move)
            key = partner.id or 0
            group = groups[key]
            group["partner"] = partner
            group["lines"].append({
                "move": move,
                "number": move.name,
                "reference": move.ref or "",
                "invoice_date": move.invoice_date,
                "due_date": move.invoice_date_due,
                "total": total,
                "paid": paid,
                "residual": residual,
                "payment_state": self._payment_state_label(move),
            })
            group["total"] += total
            group["paid"] += paid
            group["residual"] += residual
            grand_total += total
            grand_paid += paid
            grand_residual += residual

        ordered_groups = sorted(
            groups.values(),
            key=lambda g: (g["partner"].display_name or "").lower() if g["partner"] else "",
        )
        return {
            "groups": ordered_groups,
            "grand_total": grand_total,
            "grand_paid": grand_paid,
            "grand_residual": grand_residual,
            "move_count": sum(len(g["lines"]) for g in ordered_groups),
        }

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "current_invoice_balance_report.action_report_current_balance"
        ).report_action(self)

    def action_open_invoices(self):
        self.ensure_one()
        moves = self._get_moves()
        action_xmlid = (
            "account.action_move_out_invoice"
            if self.report_type == "customer"
            else "account.action_move_in_invoice"
        )
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        action["domain"] = [("id", "in", moves.ids)]
        action["context"] = {
            "allowed_company_ids": [self.company_id.id],
            "default_company_id": self.company_id.id,
        }
        return action
