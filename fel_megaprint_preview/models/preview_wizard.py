
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class FelMegaprintPreviewWizard(models.TransientModel):
    _name = "fel.megaprint.preview.wizard"
    _description = "Previsualización del XML FEL"

    move_id = fields.Many2one("account.move", required=True)
    endpoint = fields.Char("Endpoint", readonly=True)
    xml_text = fields.Text("XML (solo lectura)", readonly=True)

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
