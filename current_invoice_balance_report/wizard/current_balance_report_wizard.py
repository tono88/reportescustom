# -*- coding: utf-8 -*-
import base64
from collections import defaultdict
from datetime import datetime, time
from io import BytesIO

import pytz
import xlsxwriter

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


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
    invoice_filter = fields.Selection(
        [
            ("all", "Facturados y no facturados"),
            ("invoiced", "Solo facturados"),
            ("not_invoiced", "Solo no facturados"),
        ],
        string="Facturación",
        required=True,
        default="invoiced",
        help=(
            "Para clientes, los facturados se toman de facturas contables y los no "
            "facturados de pedidos de Punto de Venta. Para proveedores solo aplica Facturados."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        domain=lambda self: [("id", "in", self.env.companies.ids)],
    )
    use_oldest_date = fields.Boolean(
        string="Usar fecha más antigua automáticamente",
        default=False,
        help=(
            "Al activarlo, el reporte busca automáticamente la fecha más antigua "
            "que exista para los filtros seleccionados. Solo necesita indicar la fecha final."
        ),
    )
    date_from = fields.Date(
        string="Fecha desde",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="Fecha hasta",
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
            "pagada posteriormente aparezca con saldo cero."
        ),
    )
    excel_file = fields.Binary(string="Archivo Excel", readonly=True, attachment=False)
    excel_filename = fields.Char(string="Nombre Excel", readonly=True)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_("La fecha inicial no puede ser posterior a la fecha final."))

    @api.onchange(
        "use_oldest_date",
        "report_type",
        "invoice_filter",
        "company_id",
        "date_to",
        "partner_ids",
        "include_paid",
    )
    def _onchange_automatic_oldest_date(self):
        for wizard in self:
            if wizard.use_oldest_date and wizard.company_id and wizard.date_to:
                wizard._refresh_automatic_date_from()

    @api.constrains("company_id")
    def _check_company_allowed(self):
        allowed_ids = set(self.env.companies.ids)
        for wizard in self:
            if wizard.company_id and wizard.company_id.id not in allowed_ids:
                raise ValidationError(_("No tiene acceso a la compañía seleccionada."))

    @api.onchange("report_type")
    def _onchange_report_type(self):
        if self.report_type == "vendor":
            self.invoice_filter = "invoiced"
        if self.use_oldest_date and self.company_id and self.date_to:
            self._refresh_automatic_date_from()

    def _effective_invoice_filter(self):
        self.ensure_one()
        return "invoiced" if self.report_type == "vendor" else self.invoice_filter

    def _oldest_invoice_date(self):
        """Fecha fiscal más antigua que cumple los filtros actuales hasta date_to."""
        self.ensure_one()
        if not self.company_id or not self.date_to:
            return False

        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "posted"),
            ("move_type", "in", self._get_move_types()),
            ("invoice_date", "!=", False),
            ("invoice_date", "<=", self.date_to),
        ]
        if self.partner_ids:
            commercial_partner_ids = self.partner_ids.mapped("commercial_partner_id").ids
            domain.append(("commercial_partner_id", "in", commercial_partner_ids))
        if not self.include_paid:
            domain.append(("amount_residual", "!=", 0))

        move = self.env["account.move"].search(
            domain,
            order="invoice_date asc, id asc",
            limit=1,
        )
        return move.invoice_date if move else False

    def _get_utc_end_datetime(self):
        """Fin de date_to convertido a UTC-naive, sin depender de date_from."""
        self.ensure_one()
        tz_name = self.env.user.tz or "UTC"
        try:
            user_tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.UTC
        end_local = user_tz.localize(datetime.combine(self.date_to, time.max))
        return end_local.astimezone(pytz.UTC).replace(tzinfo=None)

    def _oldest_uninvoiced_pos_date(self):
        """Fecha POS más antigua no facturada que cumple los filtros hasta date_to."""
        self.ensure_one()
        if self.report_type != "customer" or not self.company_id or not self.date_to:
            return False

        PosOrder = self.env["pos.order"].sudo()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "!=", "cancel"),
            ("date_order", "<=", fields.Datetime.to_string(self._get_utc_end_datetime())),
        ]

        invoice_field = next(
            (name for name in ("account_move", "account_move_id", "invoice_id") if name in PosOrder._fields),
            False,
        )
        if invoice_field:
            domain.append((invoice_field, "=", False))
        if "state" in PosOrder._fields:
            domain.append(("state", "!=", "invoiced"))
        if self.partner_ids:
            commercial_ids = self.partner_ids.mapped("commercial_partner_id").ids
            domain.append(("partner_id.commercial_partner_id", "in", commercial_ids))

        # Se consulta por bloques para no cargar todo el historial solo para hallar
        # la primera orden válida; se saltan reembolsos/orígenes reembolsados.
        offset = 0
        batch_size = 200
        while True:
            orders = PosOrder.search(
                domain,
                order="date_order asc, id asc",
                limit=batch_size,
                offset=offset,
            )
            if not orders:
                return False
            for order in orders:
                if self._order_is_refund_or_refunded_origin(order):
                    continue
                if not self.include_paid and not self._pos_current_residual(order):
                    continue
                return self._local_pos_date(order)
            if len(orders) < batch_size:
                return False
            offset += batch_size

    def _get_oldest_available_date(self):
        """Calcula la fecha inicial automática según el tipo/modo del reporte."""
        self.ensure_one()
        mode = self._effective_invoice_filter()
        candidates = []
        if mode in ("all", "invoiced"):
            invoice_date = self._oldest_invoice_date()
            if invoice_date:
                candidates.append(invoice_date)
        if mode in ("all", "not_invoiced") and self.report_type == "customer":
            pos_date = self._oldest_uninvoiced_pos_date()
            if pos_date:
                candidates.append(pos_date)
        return min(candidates) if candidates else False

    def _refresh_automatic_date_from(self):
        """Actualiza date_from cuando el check automático está activo."""
        self.ensure_one()
        if not self.use_oldest_date:
            return self.date_from
        oldest = self._get_oldest_available_date()
        # Si no hay registros hasta la fecha final, mantener un rango válido.
        self.date_from = oldest or self.date_to
        return self.date_from

    def _ensure_report_date_range(self):
        """Sincroniza la fecha automática antes de cualquier consulta/exportación."""
        self.ensure_one()
        if self.use_oldest_date:
            self._refresh_automatic_date_from()
        if not self.date_from or not self.date_to:
            raise ValidationError(_("Debe indicar un rango de fechas válido."))
        if self.date_from > self.date_to:
            raise ValidationError(_("La fecha inicial no puede ser posterior a la fecha final."))
        return self.date_from, self.date_to

    def _get_move_types(self):
        self.ensure_one()
        if self.report_type == "customer":
            return ("out_invoice", "out_refund")
        return ("in_invoice", "in_refund")

    def _get_moves(self):
        """Facturas del periodo fiscal; su saldo es el residual ACTUAL."""
        self.ensure_one()
        self._ensure_report_date_range()
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
            domain.append(("amount_residual", "!=", 0))

        return self.env["account.move"].search(
            domain,
            order="invoice_date, commercial_partner_id, name, id",
        )

    def _signed_report_amounts(self, move):
        """Total, pagado actual y residual actual en moneda de compañía."""
        sign = -1.0 if move.move_type in ("out_refund", "in_refund") else 1.0
        total = sign * abs(move.amount_total_signed)
        residual = sign * abs(move.amount_residual_signed)
        paid = total - residual
        return total, paid, residual

    def _get_utc_datetime_bounds(self):
        """Límites UTC-naive correspondientes al rango de fechas en la zona del usuario."""
        self.ensure_one()
        self._ensure_report_date_range()
        tz_name = self.env.user.tz or "UTC"
        try:
            user_tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.UTC

        start_local = user_tz.localize(datetime.combine(self.date_from, time.min))
        end_local = user_tz.localize(datetime.combine(self.date_to, time.max))
        return (
            start_local.astimezone(pytz.UTC).replace(tzinfo=None),
            end_local.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    def _local_pos_date(self, order):
        if not order.date_order:
            return False
        return fields.Datetime.context_timestamp(self, order.date_order).date()

    def _order_is_refund_or_refunded_origin(self, order):
        """Misma regla del reporte POS previo: omitir reembolso y orden origen reembolsada."""
        if not order or not order.exists():
            return False

        if "refunded_order_id" in order._fields and order.refunded_order_id:
            return True
        if order.lines and "refunded_orderline_id" in order.lines._fields and order.lines.filtered("refunded_orderline_id"):
            return True
        if "refund_orders_count" in order._fields and order.refund_orders_count:
            return True
        if order.lines and "refund_orderline_ids" in order.lines._fields and order.lines.filtered("refund_orderline_ids"):
            return True
        return False

    def _pos_actual_paid(self, order):
        """Importe realmente cobrado en POS, sin contar "Cuenta de cliente/Pay Later" como pago.

        Odoo incluye el método pay_later dentro de amount_paid para poder validar
        la orden POS. Para un reporte de saldos eso no significa dinero cobrado:
        ese importe sigue siendo una cuenta por cobrar del cliente.
        """
        if not order or not order.exists():
            return 0.0
        if "payment_ids" not in order._fields:
            return order.amount_paid or 0.0
        paid = 0.0
        for payment in order.payment_ids:
            method = payment.payment_method_id
            method_type = method.type if method and "type" in method._fields else False
            if method_type == "pay_later":
                continue
            paid += payment.amount or 0.0
        return paid

    def _pos_current_residual(self, order):
        currency = order.currency_id or order.company_id.currency_id
        residual = (order.amount_total or 0.0) - self._pos_actual_paid(order)
        return 0.0 if currency.is_zero(residual) else residual

    def _get_uninvoiced_pos_orders(self):
        """Pedidos POS no facturados, usando fecha POS y reglas del reporte anterior."""
        self.ensure_one()
        self._ensure_report_date_range()
        if self.report_type != "customer":
            return self.env["pos.order"]

        start_dt, end_dt = self._get_utc_datetime_bounds()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "!=", "cancel"),
            ("date_order", ">=", fields.Datetime.to_string(start_dt)),
            ("date_order", "<=", fields.Datetime.to_string(end_dt)),
        ]

        PosOrder = self.env["pos.order"]
        invoice_field = next(
            (name for name in ("account_move", "account_move_id", "invoice_id") if name in PosOrder._fields),
            False,
        )
        if invoice_field:
            domain.append((invoice_field, "=", False))
        if "state" in PosOrder._fields:
            domain.append(("state", "!=", "invoiced"))
        if self.partner_ids:
            commercial_ids = self.partner_ids.mapped("commercial_partner_id").ids
            domain.append(("partner_id.commercial_partner_id", "in", commercial_ids))

        orders = PosOrder.sudo().search(domain, order="date_order, id")
        orders = orders.filtered(lambda order: not self._order_is_refund_or_refunded_origin(order))

        if not self.include_paid:
            orders = orders.filtered(lambda order: bool(self._pos_current_residual(order)))
        return orders

    def _text_value(self, record, field_names):
        """Lee el primer campo existente/no vacío sin depender de un módulo FEL concreto."""
        if not record:
            return ""
        for name in field_names:
            if name not in record._fields:
                continue
            value = record[name]
            if not value:
                continue
            if getattr(record._fields[name], "type", "") in ("many2one",):
                return value.display_name or ""
            if getattr(record._fields[name], "type", "") in ("many2many", "one2many"):
                return ", ".join(value.mapped("display_name"))
            return str(value)
        return ""

    def _get_dte_fel(self, move=False, order=False):
        candidates = (
            "numero_fel",
            "numero_dte",
            "dte_fel",
            "fel_numero",
            "numero_autorizacion",
            "fel_numero_autorizacion",
        )
        value = self._text_value(move, candidates) if move else ""
        return value or (self._text_value(order, candidates) if order else "")

    def _get_pos_order_display(self, order):
        if not order:
            return ""
        # En la instalación actual el correlativo A-xxxxx proviene de pos_internal_correlative.
        if "internal_correlative" in order._fields and order.internal_correlative:
            return order.internal_correlative
        return order.name or (order.pos_reference if "pos_reference" in order._fields else "") or ""

    def _map_moves_to_pos_orders(self, moves):
        """Vincula facturas con POS usando vínculo estándar y fallbacks ya usados en reportes previos."""
        self.ensure_one()
        result = {}
        if self.report_type != "customer" or not moves:
            return result

        PosOrder = self.env["pos.order"].sudo()
        invoice_field = next(
            (name for name in ("account_move", "account_move_id", "invoice_id") if name in PosOrder._fields),
            False,
        )
        if invoice_field:
            orders = PosOrder.search([
                ("company_id", "=", self.company_id.id),
                (invoice_field, "in", moves.ids),
            ])
            for order in orders:
                move = order[invoice_field]
                if move:
                    result.setdefault(move.id, order)

        missing = moves.filtered(lambda move: move.id not in result)
        if missing and "internal_correlative" in PosOrder._fields and "internal_correlative" in moves._fields:
            corr_to_move = {
                move.internal_correlative: move
                for move in missing
                if move.internal_correlative
            }
            if corr_to_move:
                orders = PosOrder.search([
                    ("company_id", "=", self.company_id.id),
                    ("internal_correlative", "in", list(corr_to_move)),
                ])
                for order in orders:
                    move = corr_to_move.get(order.internal_correlative)
                    if move:
                        result.setdefault(move.id, order)

        missing = moves.filtered(lambda move: move.id not in result)
        ref_to_move = {move.ref: move for move in missing if move.ref}
        if ref_to_move:
            orders = PosOrder.search([
                ("company_id", "=", self.company_id.id),
                ("name", "in", list(ref_to_move)),
            ])
            for order in orders:
                move = ref_to_move.get(order.name)
                if move:
                    result.setdefault(move.id, order)
        return result

    def _prepare_invoiced_rows(self):
        self.ensure_one()
        moves = self._get_moves()
        order_by_move = self._map_moves_to_pos_orders(moves)
        rows = []
        for move in moves:
            partner = move.commercial_partner_id or move.partner_id
            order = order_by_move.get(move.id)
            total, paid, residual = self._signed_report_amounts(move)
            rows.append({
                "source": "invoice",
                "record": move,
                "date": move.invoice_date,
                "partner": partner,
                "partner_name": partner.display_name if partner else _("Sin cliente"),
                "pos_order": self._get_pos_order_display(order),
                "dte_fel": self._get_dte_fel(move=move, order=order),
                "total": total,
                "paid": paid,
                "residual": residual,
            })
        return rows

    def _prepare_uninvoiced_rows(self):
        self.ensure_one()
        rows = []
        for order in self._get_uninvoiced_pos_orders():
            partner = order.partner_id.commercial_partner_id if order.partner_id else False
            total = order.amount_total or 0.0
            paid = self._pos_actual_paid(order)
            residual = self._pos_current_residual(order)
            rows.append({
                "source": "pos",
                "record": order,
                "date": self._local_pos_date(order),
                "partner": partner,
                "partner_name": partner.display_name if partner else _("Consumidor Final"),
                "pos_order": self._get_pos_order_display(order),
                "dte_fel": self._get_dte_fel(order=order),
                "total": total,
                "paid": paid,
                "residual": residual,
            })
        return rows

    def get_report_rows(self):
        self.ensure_one()
        self._ensure_report_date_range()
        mode = self._effective_invoice_filter()
        rows = []
        if mode in ("all", "invoiced"):
            rows.extend(self._prepare_invoiced_rows())
        if mode in ("all", "not_invoiced"):
            rows.extend(self._prepare_uninvoiced_rows())
        rows.sort(key=lambda row: (row["date"] or fields.Date.from_string("1900-01-01"), (row["partner_name"] or "").lower(), row["pos_order"] or ""))
        return rows

    def get_report_data(self):
        self.ensure_one()
        rows = self.get_report_rows()
        return {
            "rows": rows,
            "grand_total": sum(row["total"] for row in rows),
            "grand_paid": sum(row["paid"] for row in rows),
            "grand_residual": sum(row["residual"] for row in rows),
            "row_count": len(rows),
        }

    def action_print_pdf(self):
        self.ensure_one()
        self._ensure_report_date_range()
        return self.env.ref(
            "current_invoice_balance_report.action_report_current_balance"
        ).report_action(self)

    def action_export_xlsx(self):
        """Descarga XLSX con las columnas solicitadas exactamente en el orden indicado."""
        self.ensure_one()
        rows = self.get_report_rows()
        if not rows:
            raise UserError(_("No se encontraron registros con los filtros seleccionados."))

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Saldos")

        header_fmt = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })
        text_fmt = workbook.add_format({"border": 1})
        date_fmt = workbook.add_format({"border": 1, "num_format": "dd/mm/yyyy"})
        money_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00;[Red]-#,##0.00"})
        total_label_fmt = workbook.add_format({"bold": True, "border": 1, "align": "right"})
        total_money_fmt = workbook.add_format({"bold": True, "border": 1, "num_format": "#,##0.00;[Red]-#,##0.00"})

        partner_header = "Cliente" if self.report_type == "customer" else "Proveedor"
        headers = [
            "Fecha factura",
            partner_header,
            "Orden POS",
            "DTE FEL",
            "Total factura",
            "Total pagado",
            "Saldo pendiente",
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_fmt)

        for row_idx, row in enumerate(rows, start=1):
            if row["date"]:
                dt_value = datetime.combine(row["date"], time.min)
                sheet.write_datetime(row_idx, 0, dt_value, date_fmt)
            else:
                sheet.write_blank(row_idx, 0, None, date_fmt)
            sheet.write_string(row_idx, 1, row["partner_name"] or "", text_fmt)
            sheet.write_string(row_idx, 2, row["pos_order"] or "", text_fmt)
            sheet.write_string(row_idx, 3, row["dte_fel"] or "", text_fmt)
            sheet.write_number(row_idx, 4, row["total"] or 0.0, money_fmt)
            sheet.write_number(row_idx, 5, row["paid"] or 0.0, money_fmt)
            sheet.write_number(row_idx, 6, row["residual"] or 0.0, money_fmt)

        total_row = len(rows) + 1
        sheet.merge_range(total_row, 0, total_row, 3, "TOTAL", total_label_fmt)
        sheet.write_number(total_row, 4, sum(r["total"] for r in rows), total_money_fmt)
        sheet.write_number(total_row, 5, sum(r["paid"] for r in rows), total_money_fmt)
        sheet.write_number(total_row, 6, sum(r["residual"] for r in rows), total_money_fmt)

        sheet.set_column(0, 0, 14)
        sheet.set_column(1, 1, 46)
        sheet.set_column(2, 2, 18)
        sheet.set_column(3, 3, 20)
        sheet.set_column(4, 6, 18)
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, len(rows), len(headers) - 1)

        workbook.close()
        output.seek(0)

        mode = self._effective_invoice_filter()
        filename = "Saldos_%s_%s_%s_%s.xlsx" % (
            self.report_type,
            mode,
            self.date_from,
            self.date_to,
        )
        self.write({
            "excel_file": base64.b64encode(output.read()),
            "excel_filename": filename,
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content?model=%s&id=%s&field=excel_file&filename_field=excel_filename&download=true" % (
                self._name,
                self.id,
            ),
            "target": "self",
        }

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

    def action_open_pos_orders(self):
        self.ensure_one()
        if self.report_type != "customer":
            raise UserError(_("El reporte de proveedores no utiliza pedidos POS."))
        orders = self._get_uninvoiced_pos_orders()
        return {
            "type": "ir.actions.act_window",
            "name": _("Pedidos POS no facturados"),
            "res_model": "pos.order",
            "view_mode": "list,form",
            "domain": [("id", "in", orders.ids)],
            "context": {
                "allowed_company_ids": [self.company_id.id],
            },
            "target": "current",
        }
