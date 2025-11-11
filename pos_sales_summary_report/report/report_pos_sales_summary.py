
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ReportPosSalesSummary(models.AbstractModel):
    _name = "report.pos_sales_summary_report.report_pos_sales_summary"
    _description = "Reporte PDF: Resumen de ventas POS"

    def _is_cash_method(self, method):
        if not method:
            return False
        # Método efectivo (POS v18: flag is_cash_count)
        if getattr(method, "is_cash_count", False):
            return True
        jrnl = getattr(method, "journal_id", False)
        if jrnl and getattr(jrnl, "is_cash_count", False):
            return True
        t = getattr(method, "type", None)
        return isinstance(t, str) and t.lower() == "cash"

    def _split_payments(self, order):
        contado = 0.0
        credito = 0.0
        for p in order.payment_ids:
            # <<< AÑADE ESTAS LÍNEAS >>>
            amt = p.amount or 0.0
            if amt <= 0:
                continue
            # ---------------------------
            if self._is_cash_method(getattr(p, "payment_method_id", False)):
                contado += p.amount or 0.0
            else:
                credito += p.amount or 0.0
        return contado, credito

    def _fmt_amount(self, amt, currency):
        amt = amt or 0.0
        text = "{:,.2f}".format(amt)
        if not currency:
            return text
        if getattr(currency, "position", "before") == "before":
            return f"{currency.symbol} {text}"
        return f"{text} {currency.symbol}"

    def _line_from_order(self, order, currency):
        partner = order.partner_id.name or _("Consumidor Final")
        move = getattr(order, "account_move", False)
        #factura = move.name if move else "-"
        firma = "-"
        if move:
            # usa firma_fel si existe; si no, cae al nombre (número) de la factura
            firma = getattr(move, "firma_fel", False) or move.name or "-"

        contado, credito = self._split_payments(order)
        total = order.amount_total or 0.0
        return {
            "partner": partner,
            "correlative": getattr(order, "internal_correlative", "") or "-",
            #"invoice": factura,
            "invoice": firma,          # <--- aquí
            "contado": contado,
            "credito": credito,
            "total": total,
            "contado_fmt": self._fmt_amount(contado, currency),
            "credito_fmt": self._fmt_amount(credito, currency),
            "total_fmt": self._fmt_amount(total, currency),
            "order_name": order.name,
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        start_utc = data.get("start_utc")
        end_utc = data.get("end_utc")
        invoice_filter = data.get("invoice_filter", "all")

        domain = [
            ("state", "in", ["paid", "done", "invoiced"]),
            ("state", "!=", "cancel"),   # ⬅️ añade esta línea
            ("date_order", ">=", start_utc),
            ("date_order", "<=", end_utc),
        ]
        if invoice_filter == "invoiced":
            domain += [("account_move", "!=", False)]
        elif invoice_filter == "not_invoiced":
            domain += [("account_move", "=", False)]

        orders = self.env["pos.order"].search(domain, order="partner_id, date_order, name")
        # --- EXCLUIR ORDENES ORIGEN QUE TENGAN UN REEMBOLSO EN EL RANGO ---
        # Detectar reembolsos por nombre "REEMBOLSO DE …" y excluir su orden original
        refund_domain = [
            ("state", "in", ["paid", "done", "invoiced"]),
            ("date_order", ">=", start_utc),
            ("date_order", "<=", end_utc),
            ("amount_total", "<", 0),  # reembolsos suelen tener total negativo
        ]
        refund_orders = self.env["pos.order"].search(refund_domain)

        # Extraer nombres originales desde "REEMBOLSO DE <NOMBRE-ORIGINAL>"
        orig_names = []
        for r in refund_orders:
            n = (r.name or "").strip()
            if n.upper().startswith("REEMBOLSO DE "):
                orig_names.append(n.split("REEMBOLSO DE ", 1)[1].strip())

        # Filtrar fuera esas órdenes originales del conjunto a reportar
        if orig_names:
            orders = orders.filtered(lambda o: o.name not in orig_names)
        # --- FIN EXCLUSION ---

        currency = self.env.company.currency_id
        lines = []
        invs = []
        for o in orders:
            L = self._line_from_order(o, currency)
            if L["contado"] == 0 and L["credito"] == 0:
                continue
            lines.append(L)
            

            if L["invoice"] and L["invoice"] != "-":
                invs.append(L["invoice"])

        total_contado = sum(l["contado"] for l in lines)
        total_credito = sum(l["credito"] for l in lines)
        total_general = sum(l["total"] for l in lines)

        # Agrupar por partner
        grouped_map = {}
        for l in lines:
            grouped_map.setdefault(l["partner"], []).append(l)
        grouped_list = [{"partner": k, "lines": v} for k, v in grouped_map.items()]
        grouped_list.sort(key=lambda g: g["partner"] or "")

        first_inv = invs[0] if invs else "-"
        last_inv = invs[-1] if invs else "-"

        now_dt = fields.Datetime.context_timestamp(self.env.user, fields.Datetime.now())
        return {
            "doc_ids": docids,
            "doc_model": "pos.order",
            "data": data,
            "grouped": grouped_list,
            "total_contado": total_contado,
            "total_credito": total_credito,
            "total_general": total_general,
            "total_contado_fmt": self._fmt_amount(total_contado, currency),
            "total_credito_fmt": self._fmt_amount(total_credito, currency),
            "total_general_fmt": self._fmt_amount(total_general, currency),
            "first_invoice": first_inv,
            "last_invoice": last_inv,
            "user_label": self.env.user.name,
            "now_label": now_dt.strftime("%d/%m/%Y %I:%M:%S %p"),
            "company": self.env.company,
        }
