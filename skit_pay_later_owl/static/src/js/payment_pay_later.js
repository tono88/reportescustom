/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";

const STORAGE_KEY = "skit_pay_later_orders_v1";

function loadStoredOrders() {
    try {
        const data = window.localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch (e) {
        console.warn("SKIT Pay Later: cannot read localStorage", e);
        return [];
    }
}

function saveStoredOrders(orders) {
    try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(orders));
    } catch (e) {
        console.warn("SKIT Pay Later: cannot write localStorage", e);
    }
}

patch(PaymentScreen.prototype, "skit_pay_later_payment", {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    async onClickPayLater() {
        const order = this.pos.get_order();

        if (!order) return;
        if (!order.get_orderlines().length) {
            this.showPopup("ErrorPopup", {
                title: this.env._t("Orden vacía"),
                body: this.env._t("Agregue al menos un producto antes de diferir el pago."),
            });
            return;
        }
        if (!order.get_partner()) {
            this.showPopup("ErrorPopup", {
                title: this.env._t("Cliente requerido"),
                body: this.env._t("Seleccione un cliente para poder 'Pagar después'."),
            });
            return;
        }

        // Export order JSON to be recalled later
        const exported = order.export_as_JSON();
        exported.skit_pay_later = true;
        exported.skit_pay_later_saved_at = new Date().toISOString();

        const stored = loadStoredOrders();
        stored.push(exported);
        saveStoredOrders(stored);

        // Reset current order to continue selling
        this.pos.add_new_order();

        this.notification.add(this.env._t("Orden guardada como 'Pagar después'"), {
            type: "success",
        });
        // Navigate back to ProductScreen
        this.showScreen("ProductScreen");
    },
});