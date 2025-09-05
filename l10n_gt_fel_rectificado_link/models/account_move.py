# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    factura_original_id = fields.Many2one(
        comodel_name="account.move",
        string="Factura original FEL",
        help="Documento que está siendo rectificado (origen).",
        copy=True,
        readonly=True,
        store=True,
        compute="_compute_factura_original_id",
    )

    @api.depends("reversed_entry_id", "line_ids.balance")
    def _compute_factura_original_id(self):
        for move in self:
            if self.env.context.get("_skip_compute"):
                continue
            original = move.reversed_entry_id or getattr(move, "debit_origin_id", False)
            move.factura_original_id = original.id if original else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.factura_original_id:
                original = rec.reversed_entry_id or getattr(rec, "debit_origin_id", False)
                if original:
                    rec.sudo().write({"factura_original_id": original.id})
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if not rec.factura_original_id:
                original = rec.reversed_entry_id or getattr(rec, "debit_origin_id", False)
                if original:
                    rec.sudo().write({"factura_original_id": original.id})
        return res
