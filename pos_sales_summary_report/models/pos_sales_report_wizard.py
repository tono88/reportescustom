
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, time
import pytz

REPORT_XMLID = "pos_sales_summary_report.action_report_pos_sales_summary"
REPORT_NAME = "pos_sales_summary_report.report_pos_sales_summary"
REPORT_XLSX_XMLID = "pos_sales_summary_report.action_report_pos_sales_summary_xlsx"  # 👈 NUEVO

class PosSalesReportWizard(models.TransientModel):
    _name = "pos.sales.report.wizard"
    _description = "Asistente de Reporte de Ventas POS (rango fechas)"

    pos_config_id = fields.Many2one(
        "pos.config",
        string="Punto de venta",
        help="Si no seleccionas nada, se incluyen todos los puntos de venta."
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
        help="Si lo dejas vacío, se incluyen todos los clientes."
    )

    date_from = fields.Date(string="Desde", required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string="Hasta", required=True, default=lambda self: fields.Date.context_today(self))
    invoice_filter = fields.Selection([
        ("all", "Todos"),
        ("invoiced", "Solo Facturadas"),
        ("not_invoiced", "Solo NO Facturadas"),
    ], string="Facturación", required=True, default="all",
       help="Contado = pagos en efectivo. Crédito = otros métodos. El filtro limita qué órdenes se incluyen.")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for w in self:
            if w.date_to and w.date_from and w.date_to < w.date_from:
                raise models.ValidationError(_("La fecha 'Hasta' no puede ser menor a 'Desde'."))

    def _get_utc_bounds(self):
        self.ensure_one()
        user_tz = pytz.timezone(self.env.user.tz or "UTC")
        start_local = datetime.combine(self.date_from, time.min)
        end_local = datetime.combine(self.date_to, time.max)
        start_utc = user_tz.localize(start_local).astimezone(pytz.utc)
        end_utc = user_tz.localize(end_local).astimezone(pytz.utc)
        return start_utc.strftime("%Y-%m-%d %H:%M:%S"), end_utc.strftime("%Y-%m-%d %H:%M:%S")

    def _fallback_report_action(self):
        report = self.env["ir.actions.report"].sudo().search([("report_name", "=", REPORT_NAME)], limit=1)
        if not report:
            raise models.ValidationError(_("No se encontró la acción de reporte '%s'. Reinstale el módulo o cree la acción en Ajustes → Técnico → Acciones → Reportes.") % REPORT_NAME)
        return report

    def action_print_pdf(self):
        self.ensure_one()
        start_utc, end_utc = self._get_utc_bounds()
        data = {
            "date_from": str(self.date_from),
            "date_to": str(self.date_to),
            "invoice_filter": self.invoice_filter,
            "start_utc": start_utc,
            "end_utc": end_utc,
            # 👇 nuevo
            "pos_config_id": self.pos_config_id.id if self.pos_config_id else False,
            "pos_config_name": self.pos_config_id.display_name if self.pos_config_id else "Todos",
            # 👇 NUEVO: filtro por clientes
            "partner_ids": self.partner_ids.ids,
            "partner_names": ", ".join(self.partner_ids.mapped("display_name")) if self.partner_ids else "Todos",

       }
        Report = self.env["ir.actions.report"].sudo()    
        report = self.env.ref(REPORT_XMLID, raise_if_not_found=False) or self._fallback_report_action()
        # 2) Si no existe, buscar por nombre de reporte
        if not report:
            report = Report.search([
                ("report_name", "=", "pos_sales_summary_report.report_pos_sales_summary"),
                ("report_type", "=", "pdf"),
                ("model", "=", "pos.order"),
            ], limit=1)

        # 3) Si tampoco existe, crearlo en caliente
        if not report:
            report = Report.create({
                "name": "Reporte de Ventas POS",
                "model": "pos.order",
                "report_type": "pdf",
                "report_name": "pos_sales_summary_report.report_pos_sales_summary",
                "report_file": "pos_sales_summary_report.report_pos_sales_summary",
            })
        
        
        return report.report_action(None, data=data)

    def action_print_xlsx(self):
        self.ensure_one()
        start_utc, end_utc = self._get_utc_bounds()
        data = {
            "date_from": str(self.date_from),
            "date_to": str(self.date_to),
            "invoice_filter": self.invoice_filter,
            "start_utc": start_utc,
            "end_utc": end_utc,
            "pos_config_id": self.pos_config_id.id if self.pos_config_id else False,
            "pos_config_name": self.pos_config_id.display_name if self.pos_config_id else "Todos",
            # 👇 NUEVO: filtro por clientes
            "partner_ids": self.partner_ids.ids,
            "partner_names": ", ".join(self.partner_ids.mapped("display_name")) if self.partner_ids else "Todos",

        }
        Report = self.env["ir.actions.report"].sudo()

        # 1) Intentar por external id (si el XML sí se cargó)
        report = self.env.ref(REPORT_XLSX_XMLID, raise_if_not_found=False)

        # 2) Si no existe, buscar por nombre de reporte
        if not report:
            report = Report.search([
                ("report_name", "=", "pos_sales_summary_report.report_pos_sales_summary_xlsx"),
                ("report_type", "=", "xlsx"),
                ("model", "=", "pos.order"),
            ], limit=1)

        # 3) Si tampoco existe, crearlo en caliente
        if not report:
            report = Report.create({
                "name": "Reporte de Ventas POS (XLSX)",
                "model": "pos.order",
                "report_type": "xlsx",
                "report_name": "pos_sales_summary_report.report_pos_sales_summary_xlsx",
                "report_file": "pos_sales_summary_report.report_pos_sales_summary_xlsx",
            })
        return report.report_action(None, data=data)

