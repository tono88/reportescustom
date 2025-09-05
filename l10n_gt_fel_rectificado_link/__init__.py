from . import models

def post_init_set_original_links(cr, registry):
    """Backfill del campo en documentos existentes."""
    from odoo.api import Environment, SUPERUSER_ID
    env = Environment(cr, SUPERUSER_ID, {})
    moves = env["account.move"].search([
        ("factura_original_id", "=", False),
        ("state", "!=", "cancel"),
        ("move_type", "in", ("out_refund", "in_refund", "out_invoice", "in_invoice")),
    ])
    for m in moves:
        original = m.reversed_entry_id or getattr(m, "debit_origin_id", False)
        if original:
            m.with_context(_skip_compute=True).write({"factura_original_id": original.id})
