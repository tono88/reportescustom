# pos_internal_correlative/models/pos_config.py
from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    pos_series_prefix = fields.Char(
        string="Prefijo de serie interna (A/B/C)",
        help="Prefijo para el correlativo interno del POS, p.ej. 'A-'",
        default="A-",
        copy=False,
    )
    pos_internal_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Secuencia interna de ventas POS",
        readonly=True,
        copy=False,
        help="Secuencia usada para generar el correlativo interno por orden POS.",
    )

    # Crea (si falta) la secuencia propia de ESTE POS con el prefijo indicado
    def _ensure_internal_sequence(self):
        for config in self:
            if not config.pos_internal_sequence_id:
                seq = self.env["ir.sequence"].create({
                    "name": f"POS {config.display_name} Internal Seq",
                    "implementation": "standard",
                    "prefix": (config.pos_series_prefix or "A-"),
                    "padding": 5,
                    "code": f"pos.internal.correlative.config_{config.id}",
                    "company_id": config.company_id.id,
                })
                config.pos_internal_sequence_id = seq.id

    def write(self, vals):
        res = super().write(vals)
        # Si cambiaron el prefijo, reflejarlo en la secuencia
        if 'pos_series_prefix' in vals:
            for cfg in self:
                if cfg.pos_internal_sequence_id:
                    cfg.pos_internal_sequence_id.prefix = vals['pos_series_prefix'] or "A-"
        # Asegura que exista la secuencia
        self._ensure_internal_sequence()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # Autoselección A/B/C si no viene prefijo (1=A-, 2=B-, 3=C-, 4=A-, …)
        for vals in vals_list:
            if not vals.get('pos_series_prefix'):
                existing = self.search([], order='id asc')
                idx = len(existing) % 3
                vals['pos_series_prefix'] = ['A-', 'B-', 'C-'][idx]
        records = super().create(vals_list)
        records._ensure_internal_sequence()
        return records
