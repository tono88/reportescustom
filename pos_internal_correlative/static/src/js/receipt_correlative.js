/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, "pos_internal_correlative_fixed", {
    export_for_printing() {
        const res = this._super(...arguments);
        // If backend has set internal correlative on the order, try to read it
        if (this.backendId && this.backendOrder && this.backendOrder.internal_correlative) {
            res.pos_internal_correlative = this.backendOrder.internal_correlative;
        }
        // Fallback if any custom field exists on the front-end order
        if (!res.pos_internal_correlative && this.internal_correlative) {
            res.pos_internal_correlative = this.internal_correlative;
        }
        return res;
    },
});