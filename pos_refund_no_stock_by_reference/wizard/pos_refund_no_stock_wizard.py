# -*- coding: utf-8 -*-

import base64
import io
import logging
from uuid import uuid4

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except Exception:  # pragma: no cover - only depends on server packages
    openpyxl = None


class PosRefundNoStockWizard(models.TransientModel):
    _name = "pos.refund.no.stock.wizard"
    _description = "Crear reembolsos POS pagados sin inventario desde Excel"

    file_data = fields.Binary(string="Archivo Excel", required=True)
    file_name = fields.Char(string="Nombre del archivo")
    pos_session_id = fields.Many2one(
        "pos.session",
        string="Sesión POS destino opcional",
        domain=[("state", "=", "opened")],
        help=(
            "Si se deja vacío, el asistente buscará una sesión abierta del mismo punto de venta "
            "de cada orden original. Si se selecciona una sesión, se usará para todos los reembolsos."
        ),
    )
    skip_existing = fields.Boolean(
        string="Omitir órdenes que ya tengan reembolso creado",
        default=True,
        help="Evita crear dos reembolsos para la misma orden original.",
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("done", "Procesado")],
        default="draft",
        readonly=True,
    )
    result_message = fields.Text(string="Resultado", readonly=True)

    # -------------------------------------------------------------------------
    # Public action
    # -------------------------------------------------------------------------
    def action_process(self):
        self.ensure_one()
        references = self._read_references_from_excel()
        if not references:
            raise UserError(_("No se encontraron referencias válidas en la primera columna del Excel."))

        PosOrder = self.env["pos.order"].sudo()
        created = []
        not_found = []
        already_refunded = []
        no_session = []
        errors = []

        for ref in references:
            order = self._find_original_order(PosOrder, ref)
            if not order:
                not_found.append(ref)
                continue

            try:
                if self.skip_existing and self._has_existing_refund(order):
                    already_refunded.append(self._display_order(order))
                    continue

                session = self._get_target_session(order)
                if not session:
                    no_session.append(self._display_order(order))
                    continue

                refund_order = self._create_paid_refund_without_stock(order, session)
                created.append("%s  →  %s" % (self._display_order(order), self._display_order(refund_order)))
            except Exception as exc:  # keep processing the rest of the file
                _logger.exception("Error creating POS refund without stock for reference %s", ref)
                errors.append("%s: %s" % (ref, str(exc)))

        message = self._build_result_message(
            total=len(references),
            created=created,
            not_found=not_found,
            already_refunded=already_refunded,
            no_session=no_session,
            errors=errors,
        )
        self.write({"state": "done", "result_message": message})

        return {
            "type": "ir.actions.act_window",
            "name": _("Resultado reembolsos POS"),
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    # -------------------------------------------------------------------------
    # Excel helpers
    # -------------------------------------------------------------------------
    def _read_references_from_excel(self):
        if openpyxl is None:
            raise UserError(_("El servidor no tiene instalada la librería openpyxl. Instálala con: pip install openpyxl"))

        if self.file_name and not self.file_name.lower().endswith(".xlsx"):
            raise UserError(_("El archivo debe ser .xlsx"))

        try:
            content = base64.b64decode(self.file_data)
            workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            sheet = workbook.active
        except Exception as exc:
            raise UserError(_("No se pudo leer el Excel: %s") % str(exc))

        references = []
        seen = set()
        header_words = {
            "referencia",
            "ref",
            "ref.",
            "ref de la orden",
            "ref. de la orden",
            "orden",
            "pedido",
            "pos_reference",
        }

        for row_number, row in enumerate(sheet.iter_rows(min_col=1, max_col=1, values_only=True), start=1):
            value = row[0]
            if value is None:
                continue

            ref = str(value).strip()
            if not ref:
                continue

            # Permite encabezado en la primera fila.
            if row_number == 1 and ref.lower().strip() in header_words:
                continue

            if ref not in seen:
                references.append(ref)
                seen.add(ref)

        return references

    # -------------------------------------------------------------------------
    # Search / validation helpers
    # -------------------------------------------------------------------------
    def _find_original_order(self, PosOrder, reference):
        domain = ["|", ("pos_reference", "=", reference), ("name", "=", reference)]
        order = PosOrder.search(domain, limit=1, order="id desc")
        if order:
            return order

        # Respaldo: por si el Excel trae espacios dobles o un valor copiado con distinto formato.
        ref_like = reference.strip()
        if ref_like != reference:
            domain = ["|", ("pos_reference", "=", ref_like), ("name", "=", ref_like)]
            return PosOrder.search(domain, limit=1, order="id desc")
        return self.env["pos.order"]

    def _has_existing_refund(self, order):
        PosOrder = self.env["pos.order"].sudo()
        existing = PosOrder.search(
            [
                ("refund_origin_order_id", "=", order.id),
                ("state", "!=", "cancel"),
            ],
            limit=1,
        )
        if existing:
            return True

        # También detecta reembolsos creados por el POS estándar si las líneas quedaron relacionadas.
        PosLine = self.env["pos.order.line"].sudo()
        if "refunded_orderline_id" in PosLine._fields:
            existing_line = PosLine.search(
                [
                    ("refunded_orderline_id", "in", order.lines.ids),
                    ("order_id.state", "!=", "cancel"),
                ],
                limit=1,
            )
            return bool(existing_line)
        return False

    def _get_target_session(self, order):
        if self.pos_session_id:
            return self.pos_session_id

        config = order.session_id.config_id
        return self.env["pos.session"].sudo().search(
            [
                ("config_id", "=", config.id),
                ("state", "=", "opened"),
                ("company_id", "=", order.company_id.id),
            ],
            limit=1,
            order="id desc",
        )

    # -------------------------------------------------------------------------
    # Refund creation
    # -------------------------------------------------------------------------
    def _create_paid_refund_without_stock(self, order, session):
        PosOrder = self.env["pos.order"].sudo()
        PosLine = self.env["pos.order.line"].sudo()

        if not order.lines:
            raise UserError(_("La orden no tiene líneas de producto."))

        refund_order = PosOrder.create(self._prepare_refund_order_vals(order, session))

        created_lines = self.env["pos.order.line"]
        for line in order.lines:
            # Solo se reembolsan líneas vendidas. Si la orden original ya contiene líneas negativas,
            # no las duplicamos como ventas positivas.
            if line.qty <= 0:
                continue
            created_lines |= PosLine.create(self._prepare_refund_line_vals(line, refund_order))

        if not created_lines:
            raise UserError(_("La orden no tiene líneas positivas para reembolsar."))

        self._recompute_order_amounts_if_possible(refund_order)
        self._create_refund_payments(order, refund_order, session)
        self._set_order_paid_without_stock(refund_order)

        return refund_order

    def _prepare_refund_order_vals(self, order, session):
        PosOrder = self.env["pos.order"]

        # Partimos de copy_data() para conservar campos personalizados requeridos
        # que pueda tener la implementación del cliente. Luego limpiamos campos
        # que no deben copiarse a la orden de reembolso.
        try:
            vals = order.copy_data()[0]
        except Exception:
            vals = {}

        for field_name in [
            "id",
            "lines",
            "payment_ids",
            "statement_ids",
            "picking_ids",
            "picking_id",
            "account_move",
            "account_move_id",
            "procurement_group_id",
            "session_move_id",
            "move_id",
            "invoice_id",
            "refund_order_id",
            "refunded_order_ids",
            "create_uid",
            "create_date",
            "write_uid",
            "write_date",
        ]:
            vals.pop(field_name, None)

        def put(field_name, value):
            if field_name in PosOrder._fields:
                vals[field_name] = value

        put("name", self._next_pos_order_name(session, order))
        put("session_id", session.id)
        put("company_id", order.company_id.id)
        put("date_order", fields.Datetime.now())
        put("state", "draft")
        put("user_id", self.env.uid)
        put("employee_id", order.employee_id.id if "employee_id" in PosOrder._fields and order.employee_id else False)
        put("partner_id", order.partner_id.id if "partner_id" in PosOrder._fields and order.partner_id else False)
        put("pricelist_id", order.pricelist_id.id if "pricelist_id" in PosOrder._fields and order.pricelist_id else False)
        put("fiscal_position_id", order.fiscal_position_id.id if "fiscal_position_id" in PosOrder._fields and order.fiscal_position_id else False)
        put("currency_id", order.currency_id.id if "currency_id" in PosOrder._fields and order.currency_id else order.company_id.currency_id.id)
        put("to_invoice", False)
        put("pos_reference", self._unique_refund_reference(order))
        put("note", _("Reembolso automático sin movimiento de inventario de la orden: %s") % self._display_order(order))
        put("amount_tax", -order.amount_tax)
        put("amount_total", -order.amount_total)
        put("amount_paid", -order.amount_total)
        put("amount_return", 0.0)
        put("no_stock_refund", True)
        put("refund_origin_order_id", order.id)
        if "uuid" in PosOrder._fields:
            vals["uuid"] = str(uuid4())

        return vals

    def _prepare_refund_line_vals(self, line, refund_order):
        PosLine = self.env["pos.order.line"]

        # Igual que con la orden, copy_data() ayuda a conservar campos personalizados
        # requeridos por módulos del cliente. Luego ajustamos cantidades, importes y enlaces.
        try:
            vals = line.copy_data()[0]
        except Exception:
            vals = {}

        for field_name in [
            "id",
            "order_id",
            "pack_lot_ids",
            "create_uid",
            "create_date",
            "write_uid",
            "write_date",
        ]:
            vals.pop(field_name, None)

        def put(field_name, value):
            if field_name in PosLine._fields:
                vals[field_name] = value

        put("order_id", refund_order.id)
        put("product_id", line.product_id.id)
        put("company_id", refund_order.company_id.id if "company_id" in PosLine._fields and refund_order.company_id else False)
        put("qty", -abs(line.qty))
        put("price_unit", line.price_unit)
        put("discount", line.discount)
        put("price_subtotal", -abs(line.price_subtotal))
        put("price_subtotal_incl", -abs(line.price_subtotal_incl))
        put("full_product_name", getattr(line, "full_product_name", False) or line.product_id.display_name)
        put("customer_note", getattr(line, "customer_note", False))
        put("note", getattr(line, "note", False))
        put("price_extra", getattr(line, "price_extra", 0.0))
        put("product_uom_id", line.product_uom_id.id if "product_uom_id" in PosLine._fields and line.product_uom_id else False)
        put("refunded_orderline_id", line.id)

        if "tax_ids" in PosLine._fields:
            vals["tax_ids"] = [(6, 0, line.tax_ids.ids)]
        if "tax_ids_after_fiscal_position" in PosLine._fields:
            vals["tax_ids_after_fiscal_position"] = [(6, 0, line.tax_ids_after_fiscal_position.ids)]
        if "uuid" in PosLine._fields:
            vals["uuid"] = str(uuid4())

        return vals

    def _create_refund_payments(self, original_order, refund_order, session):
        Payment = self.env["pos.payment"].sudo()
        payment_methods = session.config_id.payment_method_ids
        if not payment_methods:
            raise UserError(_("La sesión destino no tiene métodos de pago configurados."))

        payment_vals = []
        original_payments = original_order.payment_ids.sorted("id")
        target_total = -original_order.amount_total

        for payment in original_payments:
            if float_is_zero(payment.amount, precision_rounding=original_order.currency_id.rounding):
                continue
            method = self._compatible_payment_method(payment.payment_method_id, payment_methods)
            payment_vals.append(self._prepare_payment_vals(refund_order, method, -payment.amount, payment))

        # Si por algún motivo no hay pagos legibles, se paga todo con el primer método de la sesión.
        if not payment_vals:
            payment_vals.append(self._prepare_payment_vals(refund_order, payment_methods[0], target_total))

        # Ajuste final para que la suma de pagos sea exactamente igual al total negativo del reembolso.
        total_payments = sum(vals["amount"] for vals in payment_vals)
        diff = target_total - total_payments
        if not float_is_zero(diff, precision_rounding=original_order.currency_id.rounding):
            payment_vals[-1]["amount"] += diff

        for vals in payment_vals:
            Payment.create(vals)

    def _prepare_payment_vals(self, refund_order, payment_method, amount, original_payment=None):
        Payment = self.env["pos.payment"]
        vals = {}

        def put(field_name, value):
            if field_name in Payment._fields:
                vals[field_name] = value

        put("pos_order_id", refund_order.id)
        put("amount", amount)
        put("payment_date", fields.Datetime.now())
        put("payment_method_id", payment_method.id)

        if original_payment:
            for optional_field in [
                "card_type",
                "cardholder_name",
                "transaction_id",
                "payment_status",
                "ticket",
            ]:
                if optional_field in Payment._fields and hasattr(original_payment, optional_field):
                    put(optional_field, getattr(original_payment, optional_field))

        return vals

    def _compatible_payment_method(self, original_method, session_methods):
        if original_method and original_method in session_methods:
            return original_method
        return session_methods[0]

    def _set_order_paid_without_stock(self, refund_order):
        """Marca la orden como pagada sin llamar a action_pos_order_paid().

        No se llama a los métodos estándar de validación/pago del POS porque esos métodos pueden
        crear pickings. Solo se actualiza el estado y el módulo deja la marca no_stock_refund=True.
        """
        refund_order.flush_recordset()
        self.env.cr.execute(
            """
                UPDATE pos_order
                   SET state = %s,
                       no_stock_refund = TRUE,
                       write_uid = %s,
                       write_date = (NOW() AT TIME ZONE 'UTC')
                 WHERE id = %s
            """,
            ["paid", self.env.uid, refund_order.id],
        )
        refund_order.invalidate_recordset()

    # -------------------------------------------------------------------------
    # Utility helpers
    # -------------------------------------------------------------------------
    def _next_pos_order_name(self, session, original_order):
        sequence = session.config_id.sequence_id
        if sequence:
            try:
                return sequence._next()
            except Exception:
                try:
                    return sequence.next_by_id()
                except Exception:
                    pass
        return _("Reembolso %s") % (original_order.name or original_order.pos_reference or original_order.id)

    def _unique_refund_reference(self, order):
        PosOrder = self.env["pos.order"].sudo()
        base = _("Reembolso %s") % (order.pos_reference or order.name or order.id)
        ref = base
        counter = 1
        while PosOrder.search_count([("pos_reference", "=", ref)]):
            counter += 1
            ref = "%s #%s" % (base, counter)
        return ref

    def _recompute_order_amounts_if_possible(self, refund_order):
        # Nombres utilizados por distintas versiones/customizaciones de POS.
        for method_name in ["_compute_amount_all", "_amount_all"]:
            method = getattr(refund_order, method_name, None)
            if method:
                try:
                    method()
                except Exception:
                    _logger.debug("Could not recompute POS order amounts with %s", method_name, exc_info=True)
        refund_order.flush_recordset()

    def _display_order(self, order):
        return order.pos_reference or order.name or str(order.id)

    def _build_result_message(self, total, created, not_found, already_refunded, no_session, errors):
        sections = [
            _("Referencias leídas: %s") % total,
            _("Reembolsos creados y pagados: %s") % len(created),
        ]

        if created:
            sections.append("\n" + _("Creados:") + "\n- " + "\n- ".join(created[:200]))
            if len(created) > 200:
                sections.append(_("... y %s más.") % (len(created) - 200))

        if already_refunded:
            sections.append("\n" + _("Omitidas por ya tener reembolso:") + "\n- " + "\n- ".join(already_refunded[:100]))

        if not_found:
            sections.append("\n" + _("No encontradas:") + "\n- " + "\n- ".join(not_found[:100]))

        if no_session:
            sections.append(
                "\n"
                + _("Sin sesión POS abierta compatible:")
                + "\n- "
                + "\n- ".join(no_session[:100])
            )

        if errors:
            sections.append("\n" + _("Errores:") + "\n- " + "\n- ".join(errors[:100]))

        sections.append(
            "\n"
            + _(
                "Nota: las órdenes originales no fueron canceladas. Los reembolsos quedaron pagados "
                "y marcados como 'Reembolso sin inventario', por lo que este módulo no genera pickings."
            )
        )
        return "\n".join(sections)
