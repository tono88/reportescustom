# pos_internal_correlative/models/pos_config.py
from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    # Prefijo / secuencia para ÓRDENES FACTURADAS
    pos_series_prefix = fields.Char(
        string="Prefijo serie interna FACTURADAS",
        help="Prefijo para el correlativo interno del POS cuando la orden lleva factura (p.ej. 'A-').",
        default="A-",
        copy=False,
    )
    pos_internal_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Secuencia interna ventas POS (FACTURADAS)",
        readonly=True,
        copy=False,
        help="Secuencia usada para generar el correlativo interno cuando la orden POS se factura.",
    )

    # Prefijo / secuencia para ÓRDENES SIN FACTURA
    pos_series_prefix_no_invoice = fields.Char(
        string="Prefijo serie interna SIN FACTURA",
        help="Prefijo para el correlativo interno del POS cuando la orden NO lleva factura (p.ej. 'D-').",
        default="D-",
        copy=False,
    )
    pos_internal_sequence_no_invoice_id = fields.Many2one(
        "ir.sequence",
        string="Secuencia interna ventas POS (SIN FACTURA)",
        readonly=True,
        copy=False,
        help="Secuencia usada para generar el correlativo interno cuando la orden POS NO se factura.",
    )

    # Crea (si faltan) las secuencias propias de ESTE POS con los prefijos indicados
    def _ensure_internal_sequence(self):
        for config in self:
            # FACTURADAS
            if not config.pos_internal_sequence_id:
                seq = self.env["ir.sequence"].create({
                    "name": f"POS {config.display_name} Internal Seq (Facturadas)",
                    "implementation": "standard",
                    "prefix": (config.pos_series_prefix or "A-"),
                    "padding": 5,
                    "code": f"pos.internal.correlative.config_{config.id}",
                    "company_id": config.company_id.id,
                })
                config.pos_internal_sequence_id = seq.id

            # SIN FACTURA
            if not config.pos_internal_sequence_no_invoice_id:
                seq2 = self.env["ir.sequence"].create({
                    "name": f"POS {config.display_name} Internal Seq (Sin Factura)",
                    "implementation": "standard",
                    "prefix": (
                        config.pos_series_prefix_no_invoice
                        or config.pos_series_prefix
                        or "A-"
                    ),
                    "padding": 5,
                    "code": f"pos.internal.correlative.noinv.config_{config.id}",
                    "company_id": config.company_id.id,
                })
                config.pos_internal_sequence_no_invoice_id = seq2.id

    def write(self, vals):
        res = super().write(vals)
        # Si cambiaron el prefijo FACTURADAS, reflejarlo en la secuencia
        if "pos_series_prefix" in vals:
            for cfg in self:
                if cfg.pos_internal_sequence_id:
                    cfg.pos_internal_sequence_id.prefix = vals["pos_series_prefix"] or "A-"

        # Si cambiaron el prefijo SIN FACTURA, reflejarlo en la secuencia
        if "pos_series_prefix_no_invoice" in vals:
            for cfg in self:
                if cfg.pos_internal_sequence_no_invoice_id:
                    cfg.pos_internal_sequence_no_invoice_id.prefix = (
                        vals["pos_series_prefix_no_invoice"] or "D-"
                    )

        # Asegura que existan las dos secuencias
        self._ensure_internal_sequence()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # Autoselección A/B/C si no viene prefijo (1=A-, 2=B-, 3=C-, 4=A-, …)
        for vals in vals_list:
            if not vals.get("pos_series_prefix"):
                existing = self.search([], order="id asc")
                idx = len(existing) % 3
                vals["pos_series_prefix"] = ["A-", "B-", "C-"][idx]
            # Default para SIN FACTURA si no se indicó nada
            if not vals.get("pos_series_prefix_no_invoice"):
                vals["pos_series_prefix_no_invoice"] = "D-"
        records = super().create(vals_list)
        records._ensure_internal_sequence()
        return records
