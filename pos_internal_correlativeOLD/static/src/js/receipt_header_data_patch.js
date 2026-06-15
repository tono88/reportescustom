/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

/**
 * Patch PosStore.getReceiptHeaderData to inject the pos internal correlative
 * so it can be shown in the ReceiptHeader component.
 */
patch(PosStore.prototype, "pos_internal_correlative_headerdata", {
    getReceiptHeaderData(order) {
        const data = super.getReceiptHeaderData(order);
        let corr = null;

        // Try to read from the order model directly
        if (order && order.internal_correlative) {
            corr = order.internal_correlative;
        }

        // Fallback: read from export_for_printing payload if available
        if (!corr && order && typeof order.export_for_printing === "function") {
            try {
                const exported = order.export_for_printing();
                corr = exported && exported.internal_correlative ? exported.internal_correlative : null;
            } catch (e) {
                // ignore
            }
        }

        if (corr) {
            data.internal_correlative = corr;
        }
        return data;
    },
});
