/*/ @odoo-module /*/
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";


patch(PaymentScreen.prototype, {
	setup() {
		super.setup(...arguments);
		this.orm = useService("orm");
		this.pos = usePos();
		this.report = useService("report");
	},

    /** Remove the payment lines */
	removePaymentLineByRef() {
	    const paymentLines = [...this.paymentLines];
        for (const line of paymentLines) {
            this.pos.get_order().remove_paymentline(line);
        }
    },

    /** validate the pending orders */
	async validatePendingOrder() {
        var self = this;
		var order = self.pos.get_order();
        var invoiceId = order.p_invoice_id;
		var session = order.session_id.id
		const props = {};
        props.orderUuid = order.uuid;
		var paymentLines = this.paymentLines;
		var paylines = [];
		for (const line of paymentLines) {
		    var lineChange = self.pos.get_order().get_change();
		    paylines.push({"amount":line.amount, "paymethod":line.payment_method_id.id, "name":line.payment_method_id.name});
		}
		var lineChange = self.pos.get_order().get_change();
		if (lineChange > 0) {
		    paylines.push({"amount":lineChange, "paymethod": 0})
		}
		/** Fetch Invoice Details **/
		this.orm.call('account.move', 'get_pending_invoice_details', [invoiceId, paylines, session]);
		await this.report.doAction("account.account_invoices", [
                        invoiceId,
                    ]);
        order.set_is_pending(false);
        this.removePaymentLineByRef()
        this.pos.showScreen('PayLaterScreen', props);
	},

    /** inherit the validateOrder method for validate the pending order */
    async validateOrder(isForceValidate) {
        this.numberBuffer.capture();
        if (!this.check_cash_rounding_has_been_well_applied()) {
            return;
        }
        var order = this.pos.get_order();
        const splitPayments = this.paymentLines.filter(
            (payment) => payment.payment_method_id.split_transactions
        );
        if (splitPayments.length) {
             order.set_to_invoice(true)
        }
        if (order.get_is_pending()) {
            this.validatePendingOrder();
        } else {
            const linesToRemove = this.currentOrder.lines.filter((line) => {
                const rounding = line.product_id.uom_id.rounding;
                const decimals = Math.max(0, Math.ceil(-Math.log10(rounding)));
                return floatIsZero(line.qty, decimals);
            });
            for (const line of linesToRemove) {
                this.currentOrder.removeOrderline(line);
            }
            if (await this._isOrderValid(isForceValidate)) {
                // remove pending payments before finalizing the validation
                const toRemove = [];
                for (const line of this.paymentLines) {
                    if (!line.is_done() || line.amount === 0) {
                        toRemove.push(line);
                    }
                }

                for (const line of toRemove) {
                    this.currentOrder.remove_paymentline(line);
                }
                await this._finalizeValidation();
            }
        }
    }
});