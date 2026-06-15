/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";
import { registry } from "@web/core/registry";

patch(Order.prototype, "pos_internal_correlative_export", {
    export_for_printing() {
        const result = super.export_for_printing();
        // Incluir el correlativo si está presente en backend
        if (this.backendId && this.pos) {
            // La info detallada ya viene inyectada por _export_for_printing backend;
            // como red de seguridad, propagamos desde order fields si existe.
            if (!result.internal_correlative && this.server_id) {
                result.internal_correlative = this.server_id.internal_correlative;
            }
        }
        // También intentar desde el json del pedido si existe
        if (!result.internal_correlative && this.internal_correlative) {
            result.internal_correlative = this.internal_correlative;
        }
        return result;
    },
});