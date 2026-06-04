# -*- coding: utf-8 -*-

from datetime import datetime, time

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class PosWarehouseSalesReportWizard(models.TransientModel):
    _name = "pos.warehouse.sales.report.wizard"
    _description = "Asistente reporte ventas POS por almacén"

    date_from = fields.Date(
        string="Fecha inicial",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_to = fields.Date(
        string="Fecha final",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    company_ids = fields.Many2many(
        "res.company",
        string="Compañías",
        default=lambda self: self.env.companies,
        help="Si se dejan vacías, se usarán las compañías activas del usuario.",
    )
    partner_id = fields.Many2one("res.partner", string="Cliente")
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén")
    invoice_filter = fields.Selection(
        [
            ("all", "Todos"),
            ("invoiced", "Solo facturados"),
            ("not_invoiced", "Solo no facturados"),
        ],
        string="Facturación",
        required=True,
        default="all",
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise UserError(_("La fecha inicial no puede ser mayor que la fecha final."))

    def _get_utc_datetime_bounds(self):
        """Return UTC naive datetimes for the selected local date range."""
        self.ensure_one()
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

    def _get_invoice_field_name(self):
        PosOrder = self.env["pos.order"]
        for field_name in ("account_move", "account_move_id", "invoice_id"):
            if field_name in PosOrder._fields:
                return field_name
        return False

    def _get_invoice_move(self, order):
        invoice_field = self._get_invoice_field_name()
        if invoice_field:
            invoice = order[invoice_field]
            if invoice and invoice._name == "account.move":
                return invoice
        return self.env["account.move"]

    def _invoice_has_related_credit_note(self, invoice):
        """Return True when the invoice has a posted related customer credit note.

        The report must not rely on ``payment_state`` because some invoices can
        be marked as reversed/paid/partial depending on reconciliations. The
        business rule requested for this report is simpler: exclude the sale
        only when the invoice has a related credit note. In standard Odoo this
        relation is stored with ``reversed_entry_id`` / ``reversal_move_ids``.
        """
        if not invoice or not invoice.exists():
            return False

        AccountMove = self.env["account.move"].sudo()

        def _is_active_customer_credit_note(move):
            return (
                move.exists()
                # Only posted credit notes are final/valid for excluding the
                # original invoice. Draft reversals/credit notes must not remove
                # the invoice from the sales report.
                and ("state" not in move._fields or move.state == "posted")
                and ("move_type" not in move._fields or move.move_type == "out_refund")
            )

        if "reversal_move_ids" in invoice._fields:
            related_credit_notes = invoice.reversal_move_ids.filtered(_is_active_customer_credit_note)
            if related_credit_notes:
                return True

        if "reversed_entry_id" in AccountMove._fields:
            domain = [("reversed_entry_id", "=", invoice.id)]
            if "state" in AccountMove._fields:
                domain.append(("state", "=", "posted"))
            if "move_type" in AccountMove._fields:
                domain.append(("move_type", "=", "out_refund"))
            if AccountMove.search_count(domain):
                return True

        return False

    def _get_valid_invoice_move(self, order):
        """Return the linked invoice only when it is valid for the sales report.

        A POS order can remain with state ``invoiced`` even if the linked invoice
        is missing, cancelled or already has a related credit note. Those cases
        must not be counted as valid invoiced sales.
        """
        invoice = self._get_invoice_move(order)
        if not invoice or not invoice.exists():
            return self.env["account.move"]
        if "state" in invoice._fields and invoice.state == "cancel":
            return self.env["account.move"]
        if "move_type" in invoice._fields and invoice.move_type == "out_refund":
            return self.env["account.move"]
        if self._invoice_has_related_credit_note(invoice):
            return self.env["account.move"]
        return invoice

    def _line_passes_invoice_rules(self, line):
        """Apply invoice filters using only valid, non-cancelled invoices.

        If the POS order says it is invoiced but the invoice is missing or
        cancelled, the line is ignored in every filter because the sale should
        not be counted as a valid invoiced POS sale.
        """
        order = line.order_id
        valid_invoice = self._get_valid_invoice_move(order)

        if order.state == "invoiced" and not valid_invoice:
            return False

        if self.invoice_filter == "invoiced":
            return bool(valid_invoice)

        if self.invoice_filter == "not_invoiced":
            return not valid_invoice and order.state != "invoiced"

        return True

    def _get_selection_label(self, record, field_name):
        if field_name not in record._fields:
            return ""
        value = record[field_name]
        selection = dict(record._fields[field_name]._description_selection(self.env))
        return selection.get(value, value or "")

    def _find_warehouse_by_location(self, location, company):
        if not location:
            return self.env["stock.warehouse"]

        domain = []
        if company:
            domain = [("company_id", "in", [False, company.id])]

        warehouses = self.env["stock.warehouse"].search(domain)
        for warehouse in warehouses:
            candidate_locations = warehouse.lot_stock_id | warehouse.view_location_id
            for candidate in candidate_locations:
                if not candidate:
                    continue
                if location == candidate:
                    return warehouse
                if location.parent_path and candidate.parent_path and location.parent_path.startswith(candidate.parent_path):
                    return warehouse
        return self.env["stock.warehouse"]

    def _resolve_line_warehouse(self, line):
        """Resolve the warehouse used by the POS line.

        The external module stores the selected warehouse name in
        pos.order.line.stock_location_name. If that value is missing, this falls
        back to the POS picking type/default source location.
        """
        order = line.order_id
        company = order.company_id
        Warehouse = self.env["stock.warehouse"]

        warehouse_name = ""
        if "stock_location_name" in line._fields and line.stock_location_name:
            warehouse_name = line.stock_location_name.strip()
            domain = [("name", "=", warehouse_name)]
            if company:
                domain = expression.AND([domain, [("company_id", "in", [False, company.id])]])
            warehouse = Warehouse.search(domain, limit=1)
            if warehouse:
                return warehouse, warehouse.name
            return Warehouse, warehouse_name

        picking_type = order.config_id.picking_type_id
        if picking_type and picking_type.warehouse_id:
            return picking_type.warehouse_id, picking_type.warehouse_id.name

        default_location = False
        if "default_location_src_id" in order.config_id._fields:
            default_location = order.config_id.default_location_src_id
        warehouse = self._find_warehouse_by_location(default_location, company)
        if warehouse:
            return warehouse, warehouse.name

        return Warehouse, _("Sin almacén definido")

    def _build_line_domain(self):
        self.ensure_one()
        start_dt, end_dt = self._get_utc_datetime_bounds()
        companies = self.company_ids or self.env.companies

        domain = [
            ("order_id.date_order", ">=", fields.Datetime.to_string(start_dt)),
            ("order_id.date_order", "<=", fields.Datetime.to_string(end_dt)),
            ("order_id.company_id", "in", companies.ids),
            ("order_id.state", "!=", "cancel"),
        ]

        if self.partner_id:
            domain.append(("order_id.partner_id", "=", self.partner_id.id))

        invoice_field = self._get_invoice_field_name()
        if self.invoice_filter == "invoiced":
            if invoice_field:
                domain.append((f"order_id.{invoice_field}", "!=", False))
            else:
                domain.append(("order_id.state", "=", "invoiced"))
        elif self.invoice_filter == "not_invoiced":
            domain.append(("order_id.state", "!=", "invoiced"))
            if invoice_field:
                domain.append((f"order_id.{invoice_field}", "=", False))

        return domain

    def _prepare_report_line_values(self, line):
        order = line.order_id
        warehouse, warehouse_display = self._resolve_line_warehouse(line)
        invoice = self._get_valid_invoice_move(order)
        invoice_status = "invoiced" if bool(invoice) else "not_invoiced"

        currency = order.company_id.currency_id
        if "currency_id" in order._fields and order.currency_id:
            currency = order.currency_id

        product = line.product_id
        return {
            "wizard_id": self.id,
            "date_order": order.date_order,
            "company_id": order.company_id.id,
            "currency_id": currency.id,
            "warehouse_id": warehouse.id if warehouse else False,
            "warehouse_display": warehouse_display or _("Sin almacén definido"),
            "order_id": order.id,
            "order_line_id": line.id,
            "pos_reference": order.pos_reference if "pos_reference" in order._fields else order.name,
            "session_id": order.session_id.id,
            "config_id": order.config_id.id,
            "cashier_id": order.user_id.id if "user_id" in order._fields and order.user_id else False,
            "partner_id": order.partner_id.id,
            "product_id": product.id,
            "categ_id": product.categ_id.id,
            "uom_id": product.uom_id.id,
            "qty": line.qty,
            "price_unit": line.price_unit,
            "discount": line.discount if "discount" in line._fields else 0.0,
            "price_subtotal": line.price_subtotal if "price_subtotal" in line._fields else line.qty * line.price_unit,
            "price_total": line.price_subtotal_incl if "price_subtotal_incl" in line._fields else line.qty * line.price_unit,
            "invoice_id": invoice.id if invoice else False,
            "invoice_number": invoice.name if invoice and "name" in invoice._fields else "",
            "invoice_numero_fel": invoice.numero_fel if invoice and "numero_fel" in invoice._fields else "",
            "invoice_status": invoice_status,
            "order_state": self._get_selection_label(order, "state"),
        }

    def _generate_report_lines(self):
        self.ensure_one()
        ReportLine = self.env["pos.warehouse.sales.report.line"]
        ReportLine.search([("create_uid", "=", self.env.uid)]).unlink()

        pos_lines = self.env["pos.order.line"].search(self._build_line_domain())
        values = []
        for line in pos_lines:
            if not self._line_passes_invoice_rules(line):
                continue
            warehouse, _warehouse_display = self._resolve_line_warehouse(line)
            if self.warehouse_id and warehouse != self.warehouse_id:
                continue
            values.append(self._prepare_report_line_values(line))

        if values:
            ReportLine.create(values)
        return len(values)

    def action_view_report(self):
        self.ensure_one()
        total_lines = self._generate_report_lines()
        if not total_lines:
            raise UserError(_("No se encontraron ventas POS con los filtros seleccionados."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Ventas POS por almacén"),
            "res_model": "pos.warehouse.sales.report.line",
            "view_mode": "list,pivot,graph",
            "domain": [("wizard_id", "=", self.id)],
            "context": {
                "search_default_group_by_warehouse": 1,
                "search_default_group_by_product": 2,
            },
            "target": "current",
        }

    @api.model
    def _normalize_menu_label(self, value):
        """Normalize menu labels for safe technical menu detection."""
        return (value or "").strip().lower().replace("ó", "o").replace("á", "a").replace("é", "e").replace("í", "i").replace("ú", "u")

    @api.model
    def _safe_menu_name(self, menu):
        """Read menu name without using the user's possibly invalid language."""
        try:
            return menu.with_context(lang="en_US").name or ""
        except Exception:
            return ""

    @api.model
    def _find_pos_root_menu(self):
        """Return the real POS root menu when possible."""
        Menu = self.env["ir.ui.menu"].sudo()
        for xmlid in (
            "point_of_sale.menu_point_root",
            "point_of_sale.menu_point_of_sale",
            "point_of_sale.menu_pos_root",
        ):
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                return menu.sudo()

        # Fallback: infer the POS root from any menu that opens POS orders.
        Action = self.env["ir.actions.act_window"].sudo()
        order_actions = Action.search([("res_model", "=", "pos.order")])
        action_refs = ["ir.actions.act_window,%s" % action.id for action in order_actions]
        if action_refs:
            order_menu = Menu.search([("action", "in", action_refs)], order="sequence,id", limit=1)
            current = order_menu
            while current.parent_id:
                current = current.parent_id
            if current:
                return current
        return Menu.browse()

    @api.model
    def _find_direct_child_menu(self, parent, expected_labels):
        """Find a direct child menu by English/source label safely."""
        if not parent:
            return self.env["ir.ui.menu"].sudo().browse()
        expected = {self._normalize_menu_label(label) for label in expected_labels}
        children = self.env["ir.ui.menu"].sudo().search([
            ("parent_id", "=", parent.id),
            ("active", "=", True),
        ], order="sequence,id")
        for child in children:
            label = self._normalize_menu_label(self._safe_menu_name(child))
            if label in expected:
                return child
        return self.env["ir.ui.menu"].sudo().browse()

    @api.model
    def _find_pos_orders_dropdown_menu(self):
        """Return the visible POS 'Orders/Órdenes' dropdown menu.

        The previous versions attached the report under a menu found by action.
        Some databases have several POS order menus, so Odoo showed the menu as
        installed in technical info but not in the visible top navigation. This
        version first anchors to the POS root and then finds its direct Orders
        child using a safe English context, avoiding the invalid es_ES issue.
        """
        Menu = self.env["ir.ui.menu"].sudo()
        Action = self.env["ir.actions.act_window"].sudo()
        root = self._find_pos_root_menu()

        # 1) Preferred target: the direct top navigation item Orders/Órdenes.
        orders_parent = self._find_direct_child_menu(root, ["Orders", "Órdenes", "Ordenes"])
        if orders_parent:
            return orders_parent

        # 2) Find a visible menu that opens pos.order and whose parent belongs to
        # the POS root. Return its parent, because that is the dropdown container.
        order_actions = Action.search([("res_model", "=", "pos.order")])
        action_refs = ["ir.actions.act_window,%s" % action.id for action in order_actions]
        if action_refs:
            order_menus = Menu.search([("action", "in", action_refs), ("active", "=", True)], order="sequence,id")
            for menu in order_menus:
                path_ids = [int(item) for item in (menu.parent_path or "").split("/") if item.isdigit()]
                if root and root.id in path_ids:
                    return menu.parent_id or menu
            for menu in order_menus:
                if menu.parent_id:
                    return menu.parent_id
            if order_menus:
                return order_menus[0]

        # 3) Fallback: attach directly to POS root so the report is still visible.
        return root or Menu.browse()

    @api.model
    def _ensure_pos_warehouse_sales_report_menu(self):
        """Create/update the POS menu used to open this report.

        This is intentionally executed from XML data so it also runs when the
        module is upgraded, not only on first installation.
        """
        module = "pos_multi_warehouse_sales_report"
        menu_xmlid = "menu_pos_warehouse_sales_report"
        action = self.env.ref("%s.action_pos_warehouse_sales_report_wizard" % module, raise_if_not_found=False)
        if not action:
            return False

        Menu = self.env["ir.ui.menu"].sudo()
        parent = self._find_pos_orders_dropdown_menu()
        action_ref = "ir.actions.act_window,%s" % action.id

        imd = self.env["ir.model.data"].sudo().search([
            ("module", "=", module),
            ("name", "=", menu_xmlid),
            ("model", "=", "ir.ui.menu"),
        ], limit=1)
        menu = Menu.browse(imd.res_id).exists() if imd else Menu.browse()

        # Recover a menu created previously without XML ID, if any.
        if not menu:
            menu = Menu.search([("action", "=", action_ref), ("name", "=", "Ventas por almacén")], limit=1)

        values = {
            "name": "Ventas por almacén",
            "parent_id": parent.id if parent else False,
            "action": action_ref,
            "sequence": 45,
            "active": True,
            # Do not set menu-specific groups. The parent POS menu and model ACLs
            # already control access; this avoids hiding it from administrators.
            "groups_id": [(5, 0, 0)],
        }

        if menu:
            menu.write(values)
        else:
            menu = Menu.create(values)

        if imd:
            imd.write({"res_id": menu.id, "noupdate": False})
        else:
            self.env["ir.model.data"].sudo().create({
                "module": module,
                "name": menu_xmlid,
                "model": "ir.ui.menu",
                "res_id": menu.id,
                "noupdate": False,
            })

        # Clear menu caches so the new entry appears after browser refresh.
        Menu.clear_caches()
        return True

