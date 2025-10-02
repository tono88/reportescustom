/* @odoo-module */
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ActionScreen } from "@point_of_sale/app/screens/action_screen";


patch(PosStore.prototype, {

	async setup() {
        await super.setup(...arguments);
        if (this.config.module_pos_hr) {
            this.showTempScreen("LoginScreen");
        }
    },

    /** Override thr back action for pay later */
    async onClickBackButton() {
        var order = this.get_order();
        if (order.get_is_pending()) {
            order.set_is_pending(false);
            const props = {};
            props.orderUuid = order.uuid;
            this.showScreen('PayLaterScreen', props);
		} else {
            if (this.mainScreen.component === TicketScreen) {
                if (this.ticket_screen_mobile_pane == "left") {
                    this.closeScreen();
                } else {
                    this.ticket_screen_mobile_pane = "left";
                }
            } else if (
                this.mobile_pane == "left" ||
                [PaymentScreen, ActionScreen].includes(this.mainScreen.component)
            ) {
                this.mobile_pane = this.mainScreen.component === PaymentScreen ? "left" : "right";
                this.showScreen("ProductScreen");
            }
        }
    }
});