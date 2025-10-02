/** @odoo-module */
//Imports
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


//SyncNotification Extended
patch(Navbar.prototype, {
	setup() {
        super.setup();
        this.orm = useService("orm");
        this.pos = usePos();
        this.state = useState({
			order: [],
		});
    },

    /*Get customer details*/
	async selectPartner() {
		const order = this.pos.get_order();
		const { confirmed, payload: newPartner } = await this.pos.showTempScreen(
			'PartnerListScreen',
			{ partner: order.get_partner() }
		);
		if (confirmed) {
			await order.set_partner(newPartner);
		}
	},

    /*Fetch the details for customer orders*/
	async onClickPayLaterOrder(event) {
		const order = this.pos.get_order();
		const partner = order.get_partner();
		if (partner) {
            const props = {};
            props.orderUuid = order.uuid;
			this.pos.showScreen('PayLaterScreen', props);
		} else {
			await this.showSelectCustomerAlert();
		}
	},

   /*Action for customer select popup */
	async showSelectCustomerAlert() {
	    await this.dialog.add(ConfirmationDialog, {
			title: _t('Please select the Customer'),
			body: _t('You need to select the customer before you proceed.'),
			cancel: () => { },
			cancelLabel: _t("Discard"),
			confirm: () => {
				this.pos.selectPartner();
			}
		});
	}
});