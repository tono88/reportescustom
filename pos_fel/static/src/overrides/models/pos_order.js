/** @odoo-module */

import { uuidv4 } from "@point_of_sale/utils";
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);

        const max = 999999999;
        const min = 100000000;
        this.numero_acceso_fel = Math.floor(Math.random() * (max - min + 1) + min);
        this.uuid_pos_fel = uuidv4();
    },
    wait_for_push_order() {
        return true;
    },
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        result.fel = {}
        result.fel['firma_fel'] = this.firma_fel;
        result.fel['serie_fel'] = this.serie_fel;
        result.fel['numero_fel'] = this.numero_fel;
        result.fel['certificador_fel'] = this.certificador_fel;
        result.fel['numero_acceso_fel'] = this.numero_acceso_fel;
        result.fel['contingencia_fel'] = this.contingencia_fel;
        result.fel['precio_total_descuento'] = this.precio_total_descuento || 0;
        return result;
    },
})