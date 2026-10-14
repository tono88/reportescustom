from odoo import _, fields, models
from odoo.exceptions import UserError

from ..layout import COMMERCIAL, HEIGHT, LAYOUTS, MODULE, validate_geometry


class AccountJournal(models.Model):
    _inherit = "account.journal"

    lx350_city = fields.Char(string="Lugar del cheque", default="PALÍN")
    lx350_offset_x = fields.Float(string="Desplazamiento horizontal (mm)", help="Negativo: izquierda. Positivo: derecha.")
    lx350_offset_y = fields.Float(string="Desplazamiento vertical (mm)", help="Positivo: abajo. Negativo: arriba.")
    lx350_font_size = fields.Float(string="Letra (pt)", default=9)
    lx350_date_x = fields.Float(string="Fecha: izquierda (mm)", default=18)
    lx350_date_y = fields.Float(string="Fecha: arriba (mm)", default=24)
    lx350_date_width = fields.Float(string="Fecha: ancho (mm)", default=110)
    lx350_amount_x = fields.Float(string="Monto: izquierda (mm)", default=139)
    lx350_amount_y = fields.Float(string="Monto: arriba (mm)", default=24)
    lx350_amount_width = fields.Float(string="Monto: ancho (mm)", default=23)
    lx350_payee_x = fields.Float(string="Beneficiario: izquierda (mm)", default=18)
    lx350_payee_y = fields.Float(string="Beneficiario: arriba (mm)", default=31)
    lx350_payee_width = fields.Float(string="Beneficiario: ancho (mm)", default=144)
    lx350_words_x = fields.Float(string="Letras: izquierda (mm)", default=18)
    lx350_words_y = fields.Float(string="Letras: arriba (mm)", default=38)
    lx350_words_width = fields.Float(string="Letras: ancho (mm)", default=144)

    def _lx350_layout(self):
        self.ensure_one()
        return self.bank_check_printing_layout or self.company_id.account_check_printing_layout

    def _lx350_geometry(self, width):
        self.ensure_one()
        positions = {
            key: (
                self[f"lx350_{key}_x"] + self.lx350_offset_x,
                self[f"lx350_{key}_y"] + self.lx350_offset_y,
                self[f"lx350_{key}_width"],
            )
            for key in ("date", "amount", "payee", "words")
        }
        try:
            validate_geometry(width, positions, self.lx350_font_size)
        except ValueError as exc:
            raise UserError(str(exc)) from exc
        return positions

    def action_lx350_configure_printer(self):
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.client",
            "tag": MODULE + ".configure_printer",
            "params": {"company_id": self.company_id.id},
        }

    def action_lx350_calibration(self):
        self.ensure_one()
        self.check_access("read")
        layout = self._lx350_layout()
        if layout not in LAYOUTS:
            raise UserError(_("Selecciona primero un diseño Banrural / LX-350 en este diario."))
        self._lx350_geometry(LAYOUTS[layout])
        suffix = "commercial" if layout == COMMERCIAL else "personal"
        action = self.env.ref(MODULE + ".action_calibration_" + suffix).report_action(self)
        action["lx350"] = {
            "direct": bool(self.env.context.get("lx350_direct")),
            "company_id": self.company_id.id,
            "width": LAYOUTS[layout],
            "height": HEIGHT,
            "calibration": True,
        }
        return action

    def action_lx350_calibration_usb(self):
        return self.with_context(lx350_direct=True).action_lx350_calibration()
