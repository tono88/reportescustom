/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    shouldDownloadInvoice() {
        return false;
    },
    async _postPushOrderResolve(order, order_server_ids) {
        const [savedOrder] = await this.pos.data.searchRead(
            "pos.order",
            [["id", "in", order_server_ids]],
            [
                "firma_fel",
                "serie_fel",
                "numero_fel",
                "certificador_fel",
            ],
        );

        if (savedOrder && savedOrder.firma_fel) {
            order.firma_fel = savedOrder.firma_fel;
            order.serie_fel = savedOrder.serie_fel;
            order.numero_fel = savedOrder.numero_fel;
            order.certificador_fel = savedOrder.certificador_fel;

            let precio_total_descuento = 0;
            let precio_total_positivo = 0;

            order.get_orderlines().forEach(function(linea) {
                if (linea.price * linea.quantity > 0) {
                    precio_total_positivo += linea.price * linea.quantity;
                } else if (linea.price * linea.quantity < 0) {
                    precio_total_descuento += Math.abs(linea.price * linea.quantity);
                }
            });

            order.precio_total_descuento = precio_total_descuento;
            
            let descuento_porcentaje_fel = precio_total_descuento / precio_total_positivo;
            order.get_orderlines().forEach(function(linea) {
                if (linea.price * linea.quantity > 0) {
                    linea.descuento_porcentaje_fel = descuento_porcentaje_fel * 100;
                    linea.descuento_nominal_fel = linea.price * linea.quantity * descuento_porcentaje_fel;
                } else if (linea.price * linea.quantity < 0) {
                    linea.descuento_porcentaje_fel = 100;
                    linea.descuento_nominal_fel = linea.price * linea.quantity;
                }
            });
        }
        return super._postPushOrderResolve(...arguments);
    },
});