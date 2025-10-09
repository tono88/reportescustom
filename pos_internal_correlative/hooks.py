from odoo import api, SUPERUSER_ID

def post_init_assign_existing_correlatives(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    seq = env.ref('pos_internal_correlative.seq_pos_internal_correlative', raise_if_not_found=False)
    if not seq:
        return
    # Asignar a órdenes sin valor, en orden por fecha
    domain = [('internal_correlative','=',False)]
    ids = env['pos.order'].search(domain, order='date_order asc', limit=1).ids
    # Procesar en lotes
    batch = 500
    offset = 0
    while True:
        orders = env['pos.order'].search(domain, order='date_order asc', offset=offset, limit=batch)
        if not orders:
            break
        for order in orders:
            order.internal_correlative = seq.next_by_id()
            # copiar a facturas relacionadas si existen
            if order.account_move and not order.account_move.pos_internal_correlative:
                order.account_move.pos_internal_correlative = order.internal_correlative
        offset += batch