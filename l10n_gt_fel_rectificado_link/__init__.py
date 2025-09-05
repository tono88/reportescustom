from . import models

def post_init_set_original_links(env_or_cr, registry=None):
    """
    Hook post-instalación con firma flexible para Odoo 18.
    Odoo 18 llama con `env`; versiones previas con `(cr, registry)`.
    """
    from odoo.api import Environment, SUPERUSER_ID
    # Detectar si recibimos env o cr
    if registry is None:
        env = env_or_cr
    else:
        env = Environment(env_or_cr, SUPERUSER_ID, {})
    moves = env["account.move"].search([
        ("factura_original_id", "=", False),
        ("state", "!=", "cancel"),
        ("move_type", "in", ("out_refund", "in_refund", "out_invoice", "in_invoice")),
    ])
    for m in moves:
        original = m.reversed_entry_id or getattr(m, "debit_origin_id", False)
        if original:
            m.with_context(_skip_compute=True).write({"factura_original_id": original.id})
