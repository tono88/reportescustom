# -*- coding: utf-8 -*-
from odoo import models, _

class PosSalesSummaryXlsx(models.AbstractModel):
    _name = "report.pos_sales_summary_report.report_pos_sales_summary_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Reporte XLSX: Resumen de ventas POS"

    def generate_xlsx_report(self, workbook, data, orders):
        """Genera el Excel usando la misma lógica del reporte PDF."""
        # Reusar la lógica del reporte PDF
        pdf_report = self.env["report.pos_sales_summary_report.report_pos_sales_summary"]
        vals = pdf_report._get_report_values(docids=None, data=data or {})

        grouped = vals.get("grouped", [])
        lines_linear = vals.get("lines_linear") or []
        order_by_correlative = bool(vals.get("order_by_internal_correlative"))    
        
        total_contado = vals.get("total_contado") or 0.0
        total_credito = vals.get("total_credito") or 0.0
        total_general = vals.get("total_general") or 0.0

        sheet = workbook.add_worksheet(_("Ventas POS")[:31])

        # Formatos
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})

        # Ancho de columnas
        sheet.set_column("A:A", 30)  # Cliente
        sheet.set_column("B:B", 18)  # Correlativo
        sheet.set_column("C:C", 28)  # Factura/Firma FEL
        sheet.set_column("D:F", 14)  # Montos

        row = 0

        # Título y rango de fechas
        sheet.write(row, 0, _("Reporte de Ventas POS"), bold)
        row += 1
        date_from = vals.get("data", {}).get("date_from", "")
        date_to = vals.get("data", {}).get("date_to", "")
        sheet.write(row, 0, _("Del: %s  Al: %s") % (date_from, date_to))
        row += 2

        # Encabezados
        headers = [
            _("Cliente"),
            _("Correlativo"),
            _("Factura/Firma FEL"),
            _("Contado"),
            _("Crédito"),
            _("Total"),
        ]
        for col, h in enumerate(headers):
            sheet.write(row, col, h, bold)
        row += 1
        if order_by_correlative:
            # Modo lineal: usamos la lista ya ordenada por correlativo
            for line in lines_linear:
                sheet.write(row, 0, line.get("partner") or "")
                sheet.write(row, 1, line.get("correlative") or "")
                sheet.write(row, 2, line.get("invoice") or "")
                sheet.write_number(row, 3, line.get("contado") or 0.0, money)
                sheet.write_number(row, 4, line.get("credito") or 0.0, money)
                sheet.write_number(row, 5, line.get("total") or 0.0, money)
                row += 1
        else:
            # Detalle por cliente
            for group in grouped:
                partner_name = group.get("partner") or ""
                for line in group.get("lines", []):
                    sheet.write(row, 0, partner_name)
                    sheet.write(row, 1, line.get("correlative") or "")
                    sheet.write(row, 2, line.get("invoice") or "")
                    sheet.write_number(row, 3, line.get("contado") or 0.0, money)
                    sheet.write_number(row, 4, line.get("credito") or 0.0, money)
                    sheet.write_number(row, 5, line.get("total") or 0.0, money)
                    row += 1

        # Totales generales
        row += 1
        sheet.write(row, 2, _("Totales"), bold)
        sheet.write_number(row, 3, total_contado, money)
        sheet.write_number(row, 4, total_credito, money)
        sheet.write_number(row, 5, total_general, money)
