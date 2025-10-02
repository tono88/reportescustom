/*/ @odoo-module /*/
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { onWillStart, useState, } from "@odoo/owl";


export class PayLaterScreen extends Component {
	static template = "PayLaterScreen";
	static defaultProps = {
		order: [],
	};
	static props = {
        orderUuid: String,
    };
	setup() {
		super.setup(...arguments);
		this.orm = useService("orm");
		this.pos = usePos();
		this.report = useService("report");
		this.state = useState({
            order: [],
		});

		/*Get orders details*/
		onWillStart(async () => {
			var self = this;
			const orders = this.pos.get_order();
			const partner = orders.get_partner();
			if (partner) {
				const result = await this.orm.call('pos.order', 'fetch_partner_order', [partner.id, self.pos.pos_session]);
				let lines = result;
				this.state.order = lines;
			}

		})
	}

    /** action for pay now button */
	async payNow(pending_invoice_id,unpaid_amount,pending_porder_id,pending_order_type) {
        var order = this.pos.get_order();
        const props = {};
        order.set_is_pending(true);
	    var invoiceId = pending_invoice_id;
	    var amount = unpaid_amount;
		var pOrderId = pending_porder_id;
	    var pOrderType = pending_order_type;
	    order.set_p_invoice_id(invoiceId);
	    order.set_p_invoice_amt(amount);
	    order.set_p_porder_id(pOrderId);
	    order.set_p_order_type(pOrderType);
	    props.orderUuid = order.uuid;
        this.pos.showScreen('PaymentScreen', props);
	}

	/** Expand action for invoice line */
	async toggleExpand(line) {
		line.expanded = !line.expanded;
		const productRow = document.querySelector(`.invoicescreen[id="${line.id}"]`);
		if (productRow) {
			productRow.style.display = line.expanded ? 'table-row' : 'none';
		}
	}
};
registry.category("pos_screens").add("PayLaterScreen", PayLaterScreen);
