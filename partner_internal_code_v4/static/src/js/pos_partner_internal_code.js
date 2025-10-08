/** @odoo-module **/

import { PosDB } from 'point_of_sale.DB';
import { patch } from '@web/core/utils/patch';

// Log para confirmar que el asset cargó
console.log('[PIC] pos_partner_internal_code.js cargado');

patch(PosDB.prototype, 'partner_internal_code_search', {
    _partner_search_string(partner) {
        const base = this._super ? this._super(partner) : (
            (partner.name || '') + '|' +
            (partner.barcode || '') + '|' +
            (partner.phone || '') + '|' +
            (partner.mobile || '') + '|' +
            (partner.email || '') + '|' +
            (partner.vat || '') + '\n'
        );
        const code = partner.internal_code || '';
        if (!code) return base;
        return base.endsWith('\n') ? base.slice(0, -1) + '|' + code + '\n' : base + '|' + code;
    },
});
