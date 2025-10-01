/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.diario_factura_nombre = this.config.diario_factura_nombre
        result.diario_factura_direccion = this.config.diario_factura_direccion
        result.diario_factura_tel = this.config.diario_factura_tel
        return result;
    },
})
