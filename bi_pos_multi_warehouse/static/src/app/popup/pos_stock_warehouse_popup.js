/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class PosStockWarehouse extends Component {
    static template = "bi_pos_multi_warehouse.PosStockWarehouse";
    static props = {
        close: Function,
        product: Object,
        rec: Object,
    };
    static components = { Dialog };

    setup() {
        super.setup();  
        this.pos = usePos();
    }

    async apply(){
        var self = this;

        var product = this.pos.models["product.product"].getBy("id", this.props.product.id);
        let rec = this.props.rec;
        let entered_code = document.querySelector("#entered_item_qty").value;
        let list_of_qty = document.querySelectorAll('.entered_item_qty');
        let order = this.pos.get_order();
        let warehouse = this.pos.pos_custom_location;

        list_of_qty.forEach((value) => {
            let entered_item_qty = value.querySelector('input');
            let qty_id = parseFloat(entered_item_qty.getAttribute('qty-id')) || 0;
            let loc_id = entered_item_qty.getAttribute('locdbid');
            let loc_name = entered_item_qty.getAttribute('loc-id');
            let entered_qty = parseFloat(entered_item_qty.value || 0);
            let selectedOrder = self.pos.get_order();

            if (entered_qty > 0) {
                if (qty_id >= entered_qty) {
                    if (entered_qty !== 0) {
                        if (self.pos.config.stock_qty === 'qty_available') {
                            product['bi_on_hand'] += entered_qty;
                        } else {
                            product.virtual_available -= entered_qty;
                        }

                        const taxes = product.taxes_id
                            .map((taxId) => self.pos.models["account.tax"].get(taxId.id))
                            .filter(Boolean);

                        const line = this.pos.models["pos.order.line"].create({
                            product_id: product,
                            order_id: order,
                            qty: entered_qty,
                            tax_ids: [["link", ...taxes]],
                            price_unit: product.lst_price,
                        });
                        line.set_stock_location_name(loc_name)
                        this.pos.selectOrderLine(order, line);
                        self.props.close()
                    }
                } else {
                    if (self.pos.config.Negative_selling) {
                        if (entered_qty !== 0) {

                            const taxes = product.taxes_id
                                .map((taxId) => self.pos.models["account.tax"].get(taxId.id))
                                .filter(Boolean);

                            const line = this.pos.models["pos.order.line"].create({
                                product_id: product,
                                order_id: order,
                                qty: entered_qty,
                                tax_ids: [["link", ...taxes]],
                                price_unit: product.lst_price,
                            });
                            line.set_stock_location_name(loc_name)
                            this.pos.selectOrderLine(order, line);
                            self.props.close()
                        }
                    } else {
                        let result = `This Location has: ${qty_id} QTY. You have entered: ${entered_qty}`;
                        this.pos.dialog.add(AlertDialog, {
                            title: _t('Please enter a valid amount of quantity.'),
                            body:  _t(result)
                        });
                    }
                }
            }
        });
        self.props.close()
    }
}