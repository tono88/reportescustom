/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
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

// Odoo 18: patch(target, props)
patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    async onClickRecallPayLater() {
        const stored = loadStoredOrders();
        if (!stored.length) {
            this.notification.add(this.env._t("No hay órdenes 'Pagar después'."), { type: "info" });
            return;
        }

        const choices = stored.map((o, idx) => ({
            id: idx,
            label: `${o.name || "Orden"} | ${o.partner_id?.[1] || "Sin cliente"} | ${new Date(o.skit_pay_later_saved_at).toLocaleString()}`,
        }));

        const { confirmed, payload } = await this.showPopup("SelectionPopup", {
            title: this.env._t("Órdenes 'Pagar después'"),
            list: choices,
        });

        if (confirmed && payload != null) {
            const toLoad = stored[payload.id];
            if (!toLoad) return;

            const newOrder = this.pos.add_new_order();
            newOrder.init_from_JSON(toLoad);

            const remaining = stored.filter((_, i) => i !== payload.id);
            saveStoredOrders(remaining);

            this.notification.add(this.env._t("Orden cargada. Proceda al cobro."), { type: "success" });
            this.showScreen("PaymentScreen");
        }
    },
});
