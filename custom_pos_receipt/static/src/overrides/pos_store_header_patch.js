/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

function firstDefined(arr) {
    for (let i=0;i<arr.length;i++) if (arr[i]) return arr[i];
    return null;
}

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const base = super.getReceiptHeaderData(...arguments);
        const correlative = firstDefined([
            order?.backendOrder?.internal_correlative,
            order?.backendOrder?.pos_internal_seq,
            order?.internal_correlative,
            order?.pos_internal_seq,
            order?.internal_pos_sequence,
        ]);
        return {
            ...base,
            partner: order?.partner_id ?? base.partner,
            correlative: correlative ? String(correlative) : base.correlative,
        };
    },
});
