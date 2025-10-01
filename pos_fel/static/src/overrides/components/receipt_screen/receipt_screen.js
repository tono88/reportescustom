/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        if (!this.currentOrder.firma_fel) {
            this.currentOrder.contingencia_fel = true;
        }
    }
});