/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    get productsToDisplay() {
        let self = this;
        let prods = super.productsToDisplay;
        let order = self.pos.get_order();
        let location_list = [];
        let virtual_location_list = [];
        if (self.pos.config.display_stock){
            let prod_ids = [];
            prods.forEach(function(prd) {
                prod_ids.push(prd.id)               
            })
            let locations = self.pos.locations; 
            if(self.pos.config.stock_qty == 'qty_available'){
                for (const prd of prods) {
                    prd['qty_available'] = 0; 
                    const loc_onhand = JSON.parse(prd.quant_text);
                    let config_locations = self.pos.config.warehouse_ids; 
                    let quantity_available = 0;  
                    config_locations.forEach((warehouse) =>{
                        locations.forEach((location) => {  
                            if(warehouse && location.warehouse_id){
                                if(warehouse.id == location.warehouse_id.id){
                                    if (!location_list.includes(location)){
                                        location_list.push(location)

                                    }
                                }
                            }
                            
                        });
                    }); 
                    location_list.forEach((location) => {  
                        for (const [k, v] of Object.entries(loc_onhand)) {   
                            if (location.id == k) { 
                                quantity_available=quantity_available+v[0]; 
                            } 
                        }
                        
                    });  
                    let remain_on_hand_qty = 0;
                    if (prd['bi_on_hand'] > 0) {
                        const bi_on_hand = self.pos.get_display_product_qty(prd);
                        quantity_available -= bi_on_hand;
                    } else {
                        remain_on_hand_qty = quantity_available;
                        const reserved_qty = self.pos.get_display_product_qty(prd);
                        remain_on_hand_qty -= reserved_qty;
                    }

                    prd['qty_available'] = quantity_available; 
                    prd['remain_on_hand_qty'] = remain_on_hand_qty;
                }
            }
            else{ 
                prods.forEach((prd) => {
                    const loc_available = JSON.parse(prd.quant_text);
                    prd['virtual_available'] = 0;
                    let virtual_available = 0;
                    let total = 0;
                    let out = 0;
                    let inc = 0;
                    let config_locations = self.pos.config.warehouse_ids; 
                    config_locations.forEach((warehouse) =>{
                        locations.forEach((location) => {  
                            if(warehouse && location.warehouse_id){
                                if(warehouse.id == location.warehouse_id.id){
                                    if (!virtual_location_list.includes(location)){
                                        virtual_location_list.push(location)

                                    }
                                }
                            }
                            
                        });
                    });
                    virtual_location_list.forEach((location) => {
                        Object.entries(loc_available).forEach(([k, v]) => {
                            if (location.id == k) {
                                total += v[0];
                                if (v[1]) {
                                    out += v[1];
                                }
                                if (v[2]) {
                                    inc += v[2];
                                }
                                const final_data = total + inc - out;
                                virtual_available = final_data;
                            }
                        });
                    });

                    let remain_virtual_qty = 0;
                    if (prd['bi_on_virtual'] > 0) {
                        const bi_on_virtual = self.pos.get_display_product_qty(prd);
                        virtual_available -= bi_on_virtual;
                    } else {
                        remain_virtual_qty = virtual_available;
                        const reserved_qty = self.pos.get_display_product_qty(prd);
                        remain_virtual_qty -= reserved_qty;
                    }

                    prd['virtual_available'] = virtual_available;
                    prd['remain_virtual_qty'] = remain_virtual_qty;
                });
            }
        } 
        if (this.searchWord !== '') {
            return prods;
        } else {
            return prods;
        }
        
    }
});

