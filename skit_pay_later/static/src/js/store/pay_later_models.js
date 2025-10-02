/*/ @odoo-module /*/
import { floatIsZero } from "@web/core/utils/numbers";
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { lt } from "@point_of_sale/utils";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(PosOrder.prototype, {
	setup() {
		super.setup(...arguments);
	},

    /** inherit this method for add pay later options */
	init_from_JSON(json) {
		super.init_from_JSON(...arguments);
		this.is_pending = json.is_pending || false;
		this.is_pay_later = json.is_pay_later || false;
		this.p_invoice_id = json.p_invoice_id || 0;
		this.p_invoice_amt = json.p_invoice_amt || 0;
		this.p_porder_id = json.p_porder_id || 0;
		this.p_order_type = json.p_order_type || 'POS';
		this.pendingTaxTotals = json.pendingTaxTotals;
	},

    /** inherit this method for add pay later options */
	export_as_JSON() {
		const json = super.export_as_JSON(...arguments);
		json.is_pending = this.get_is_pending();
		json.is_pay_later = this.get_is_pay_later();
		json.p_invoice_id = this.get_p_invoice_id();
		json.p_invoice_amt = this.get_p_invoice_amt();
		json.p_porder_id = this.get_p_porder_id();
		json.p_order_type = this.get_p_order_type();
		return json;
	},

    /** START GET and SET method for pay later action */
	set_is_pending(is_pending) {
		this.is_pending = is_pending;
	},

	get_is_pending() {
	    return this.is_pending
	},

	set_is_pay_later(is_pay_later) {
	    this.is_pay_later = is_pay_later
	},

	get_is_pay_later() {
	    return this.is_pay_later
	},

	set_p_invoice_id(p_invoice_id) {
	    this.p_invoice_id = p_invoice_id
	},

	get_p_invoice_id() {
	    return this.p_invoice_id
	},

	set_p_invoice_amt(p_invoice_amt) {
	    this.p_invoice_amt = p_invoice_amt
	},

	get_p_invoice_amt() {
	    return this.p_invoice_amt
	},

	set_p_porder_id(p_porder_id) {
	    this.p_porder_id = p_porder_id
	},

	get_p_porder_id() {
	    return this.p_porder_id
	},

	set_p_order_type(p_order_type) {
	    this.p_order_type = p_order_type
	},

	get_p_order_type() {
	    return this.p_order_type
	},
	/** END GET and SET method for pay later action */

	/**

     * Get the details total amounts with and without taxes, the details of taxes per subtotal and per tax group.
     * @returns See '_get_tax_totals_summary' in account_tax.py for the full details.
     */
    get taxTotals() {
        const currency = this.config.currency_id;
        const company = this.company;
        const orderLines = this.lines;
        // If each line is negative, we assume it's a refund order.
        // It's a normal order if it doesn't contain a line (useful for pos_settle_due).
        // TODO: Properly differentiate refund orders from normal ones.
        const documentSign =
            this.lines.length === 0 ||
            !this.lines.every((l) => lt(l.qty, 0, { decimals: currency.decimal_places }))
                ? 1
                : -1;

        const baseLines = orderLines.map((line) => {
            return accountTaxHelpers.prepare_base_line_for_taxes_computation(
                line,
                line.prepareBaseLineForTaxesComputationExtraValues({
                    quantity: documentSign * line.qty,
                })
            );
        });
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, company);
        // For the generic 'get_tax_totals_summary', we only support the cash rounding that round the whole document.
        const cashRounding =
            !this.config.only_round_cash_method && this.config.cash_rounding
                ? this.config.rounding_method
                : null;

        const taxTotals = accountTaxHelpers.get_tax_totals_summary(baseLines, currency, company, {
            cash_rounding: cashRounding,
        });

        taxTotals.order_sign = documentSign;
        taxTotals.order_total =
            taxTotals.total_amount_currency - (taxTotals.cash_rounding_base_amount_currency || 0.0);
        if(this.get_is_pending()) {
            taxTotals.order_total = this.get_p_invoice_amt()
        }


        let order_rounding = 0;
        let remaining = taxTotals.order_total;
        const validPayments = this.payment_ids.filter((p) => p.is_done() && !p.is_change);
        for (const [payment, isLast] of validPayments.map((p, i) => [
            p,
            i === validPayments.length - 1,
        ])) {
            const paymentAmount = documentSign * payment.get_amount();
            if (isLast) {
                if (this.config.cash_rounding) {
                    const roundedRemaining = this.getRoundedRemaining(
                        this.config.rounding_method,
                        remaining
                    );
                    if (!floatIsZero(paymentAmount - remaining, this.currency.decimal_places)) {
                        order_rounding = roundedRemaining - remaining;
                    }
                }
            }
            remaining -= paymentAmount;
        }

        taxTotals.order_rounding = order_rounding;
        taxTotals.order_remaining = remaining;

        const remaining_with_rounding = remaining + order_rounding;
        if (floatIsZero(remaining_with_rounding, currency.decimal_places)) {
            taxTotals.order_has_zero_remaining = true;
        } else {
            taxTotals.order_has_zero_remaining = false;
        }

        return taxTotals;
    },

    /** inherit this method for add pay later options */
	export_for_printing() {
		const result = super.export_for_printing(...arguments);
		result.is_pending = this.get_is_pending();
		result.is_pay_later = this.get_is_pay_later();
		result.p_invoice_id = this.get_p_invoice_id();
		result.p_invoice_amt = this.get_p_invoice_amt();
		result.p_porder_id = this.get_p_porder_id();
		result.p_order_type = this.get_p_order_type();
		return result;
	},

});