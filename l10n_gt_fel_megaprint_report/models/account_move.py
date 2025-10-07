from odoo import api, fields, models
from math import modf
try:
    from num2words import num2words
except Exception:
    num2words = None

class AccountMove(models.Model):
    _inherit = "account.move"

    # Si ya existen en tu BD, estos add-ons no chocan; si ya los tienes en otro módulo,
    # puedes comentar estas líneas.
    firma_fel = fields.Char(string="Firma FEL / No. Autorización")
    serie_fel = fields.Char(string="Serie FEL")
    numero_fel = fields.Char(string="Número DTE")

    amount_total_gt_words = fields.Char(
        string="Total en letras (GT)",
        compute="_compute_amount_total_gt_words",
        store=False,
    )

    @api.depends("amount_total", "currency_id")
    def _compute_amount_total_gt_words(self):
        for move in self:
            amount = move.amount_total or 0.0
            # Quetzales y centavos como /100
            frac, entero = modf(amount)
            quetzales = int(entero)
            centavos = int(round(frac * 100.0))
            if centavos == 100:
                quetzales += 1
                centavos = 0

            if num2words:
                texto_entero = num2words(quetzales, lang="es")
            else:
                # Fallback simple en caso extremo (deberías tener num2words en Odoo)
                texto_entero = str(quetzales)

            # Formato requerido: "DIEZ QUETZALES CON 05/100"
            moneda = "QUETZALES" if quetzales != 1 else "QUETZAL"
            texto = f"{texto_entero} {moneda} CON {centavos:02d}/100"
            move.amount_total_gt_words = texto.upper()


    # === POS warehouse helper ===
    def _get_related_pos_order(self):
        """Return the POS order linked to this invoice if any.
        Tries common relations used by Odoo versions: account_move, invoice_id, move_id,
        and falls back to matching by reference/name.
        """
        self.ensure_one()
        PosOrder = self.env['pos.order'].sudo()
        order = PosOrder.search([('account_move', '=', self.id)], limit=1)
        if not order:
            order = PosOrder.search([('invoice_id', '=', self.id)], limit=1)
        if not order:
            order = PosOrder.search([('move_id', '=', self.id)], limit=1)
        if not order and (self.ref or self.payment_reference or self.invoice_origin):
            names = [x for x in [self.ref, self.payment_reference, self.invoice_origin] if x]
            order = PosOrder.search([('name', 'in', names)], limit=1)
        return order

    def get_wh_for_line(self, line):
        """Get the warehouse/location label for a given invoice line
        based on the related POS order line (if any). Returns '' if not found.
        This is designed to be called from QWeb: <t t-esc="o.get_wh_for_line(l)"/>
        """
        self.ensure_one()
        try:
            order = self._get_related_pos_order().sudo() if hasattr(self, '_get_related_pos_order') else False
        except Exception:
            order = False
        if not order:
            return ''
        # If the account.move.line has a direct link to a POS line, use it.
        if hasattr(line, 'pos_order_line_id') and getattr(line, 'pos_order_line_id'):
            wh = line.pos_order_line_id.stock_location_name or ''
            return wh or ''
        # Attempt to match by product and quantity
        try:
            lines = order.sudo().lines
        except Exception:
            lines = self.env['pos.order.line']
        if not lines:
            return ''
        # Strong match: product + qty + price_unit
        strong = lines.filtered(lambda ol: ol.product_id.id == line.product_id.id and float(getattr(ol, 'qty', 0.0)) == float(line.quantity) and float(getattr(ol, 'price_unit', 0.0)) == float(line.price_unit))
        if strong:
            return strong[0].stock_location_name or ''
        # Weaker match: product + qty
        weak = lines.filtered(lambda ol: ol.product_id.id == line.product_id.id and float(getattr(ol, 'qty', 0.0)) == float(line.quantity))
        if weak:
            return weak[0].stock_location_name or ''
        # Fallback: any line with same product
        prod_only = lines.filtered(lambda ol: ol.product_id.id == line.product_id.id)
        if prod_only:
            return prod_only[0].stock_location_name or ''
        return ''
