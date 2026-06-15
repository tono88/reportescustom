/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/models/order";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { useService } from "@web/core/utils/hooks";

/**
 * 1) Inyectar el correlativo en el diccionario que usa el recibo
 *    (export_for_printing es lo que leen los templates del recibo).
 */
patch(Order.prototype, "pos_internal_correlative_export", {
    export_for_printing() {
        const res = super.export_for_printing(...arguments);
        res.internal_correlative = this.internal_correlative || null;
        return res;
    },
});

/**
 * 2) En la pantalla de Recibo, si ya existe backendId (el pedido ya se creó
 *    en el servidor) pero el POS aún no conoce el correlativo, lo leemos por RPC
 *    y lo guardamos en el Order; al guardarlo, el recibo se re-renderiza.
 */
patch(ReceiptScreen.prototype, "pos_internal_correlative_fetch", {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    async onMounted() {
        await super.onMounted?.();
        try {
            const order = this.currentOrder;
            // Si el pedido ya está en el servidor y no tenemos el correlativo en el cliente
            if (order?.backendId && !order.internal_correlative) {
                const [[vals]] = await this.orm.read(
                    "pos.order",
                    [order.backendId],
                    ["internal_correlative"]
                );
                if (vals?.internal_correlative) {
                    order.internal_correlative = vals.internal_correlative;
                    // Forzar re-render para que el template muestre el nuevo dato
                    this.render(true);
                }
            }
        } catch (e) {
            // No rompemos el flujo del POS si falla; solo seguimos con el nombre de la orden
            console.warn("No se pudo leer internal_correlative para el recibo:", e);
        }
    },
});
