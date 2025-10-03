
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class FelMegaprintPreviewWizard(models.TransientModel):
    _name = "fel.megaprint.preview.wizard"
    _description = "Previsualización del XML FEL antes de certificar"

    move_id = fields.Many2one("account.move", required=True)
    endpoint = fields.Char("Endpoint", readonly=True)
    xml_text = fields.Text("XML a enviar", readonly=True)

    def action_open(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Previsualización XML FEL"),
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def action_confirm_send(self):
        """Usuario confirmó enviar: ejecutamos certificación real y cerramos."""
        self.ensure_one()
        # Ejecutar ahora sí la certificación con 'preview_confirmed=True'
        self.move_id._fel_certify_with_capture(preview_mode=True, preview_confirmed=True)
        return {"type": "ir.actions.act_window_close"}
