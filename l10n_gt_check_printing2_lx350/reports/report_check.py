from num2words import num2words

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..layout import BANK_LABELS, GYT, HEIGHT, PERSONAL, amount_parts, fit_font


class ReportCheckPersonal(models.AbstractModel):
    _name = "report.l10n_gt_check_printing2_lx350.check_personal"
    _description = "Cheque Banrural personal"
    _check_width = 165.10
    _check_layout = PERSONAL
    _calibration = False

    def _line(self, key, text, positions, journal):
        x, y, width = positions[key]
        try:
            font = fit_font(text, width, journal.lx350_font_size)
        except ValueError as exc:
            raise UserError(f"{key}: {exc}") from exc
        return {
            "text": text,
            "style": (
                f"position:absolute;left:{x}mm;top:{y}mm;width:{width}mm;"
                f"font-size:{font}pt;line-height:1;white-space:nowrap;"
                + ("text-align:right;" if key == "amount" else "")
            ),
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        model = "account.journal" if self._calibration else "account.payment"
        docs = self.env[model].browse(docids).exists()
        docs.check_access("read")
        if not docs or len(docs) != len(set(docids)):
            raise UserError(_("No se encontraron todos los documentos solicitados."))
        if not self._calibration:
            docs._lx350_check_payments()
            if any(not p.check_number or not p.partner_id or p.state == "draft" for p in docs):
                raise UserError(_("El pago debe estar confirmado, con beneficiario y número de cheque."))
        rows = []
        for doc in docs:
            journal = doc if self._calibration else doc.journal_id
            if journal._lx350_layout() != self._check_layout:
                raise UserError(_("El banco del reporte no coincide con el diseño seleccionado en el diario."))
            positions = journal._lx350_geometry(self._check_width)
            date = fields.Date.context_today(journal) if self._calibration else doc.date
            amount = 1234.56 if self._calibration else doc.currency_id.round(doc.amount)
            try:
                integer, cents = amount_parts(amount)
            except ValueError as exc:
                raise UserError(str(exc)) from exc
            texts = {
                "date": f"{(journal.lx350_city or '').upper()}, {date.strftime('%d/%m/%Y')}",
                "amount": f"{integer:,}.{cents:02d}",
                "payee": "BENEFICIARIO DE PRUEBA" if self._calibration else doc.partner_id.name.upper(),
                "words": f"{num2words(integer, lang='es').upper()} CON {cents:02d}/100",
            }
            rows.append({
                "lines": [self._line(key, text, positions, journal) for key, text in texts.items()],
                "company": journal.company_id,
            })
        return {
            "doc_ids": docs.ids,
            "doc_model": model,
            "docs": docs,
            "rows": rows,
            "width": self._check_width,
            "height": HEIGHT,
            "calibration": self._calibration,
            "bank_label": BANK_LABELS[self._check_layout],
        }


class ReportCheckGyt(models.AbstractModel):
    _name = "report.l10n_gt_check_printing2_lx350.check_gyt"
    _inherit = "report.l10n_gt_check_printing2_lx350.check_personal"
    _description = "Cheque G&T Continental personal"
    _check_layout = GYT


class ReportCalibrationPersonal(models.AbstractModel):
    _name = "report.l10n_gt_check_printing2_lx350.calibration_personal"
    _inherit = "report.l10n_gt_check_printing2_lx350.check_personal"
    _description = "Calibración cheque personal con datos ficticios"
    _calibration = True


class ReportCalibrationGyt(models.AbstractModel):
    _name = "report.l10n_gt_check_printing2_lx350.calibration_gyt"
    _inherit = "report.l10n_gt_check_printing2_lx350.check_gyt"
    _description = "Calibración cheque G&T personal con datos ficticios"
    _calibration = True
