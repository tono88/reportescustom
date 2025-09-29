/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosStockWarehouse } from "@bi_pos_multi_warehouse/app/popup/pos_stock_warehouse_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";


patch(PosStore.prototype, {
    async processServerData() {
        super.processServerData();
        this.locations = this.data.models["stock.location"].getAll(); 
        this.pos_custom_location = this.data.models["stock.warehouse"].getAll();
        this.prod_with_quant = this.load_prod_with_quant();
        this.loc_by_id = this.load_loc_by_id();
    },

    load_loc_by_id(){
        let loc_by_id = {}
        let locations = this.models['stock.warehouse'].getAll();
        for (var loc of locations){
            loc_by_id[loc.id]  = loc
        }
        return loc_by_id;
    },

    load_prod_with_quant(){
        let prods = {}
        let products = this.models['product.product'].getAll();
        for (var prd of products){
            prods[prd.id]  = prd.quant_text
        }
        return prods;
    },

    async addLineToCurrentOrder(vals, opt = {}, configure = true) {
        let product = vals.product_id
        product['bi_on_hand'] = 0;
        let warehouse_id = []
        let order = this.get_order();
        let location = this.config.warehouse_ids;
        let partner_id = order.get_partner();
        let lines = order.get_orderlines();
        let warehouse = this.pos_custom_location;
        let session = this.config.current_session_id.id; 
        let product_qty = this.config.stock_qty
        warehouse.forEach(function (data) { 
                warehouse_id.push(data.id) 
            
        })

        if (this.config.default_location_src_id){
            let config_loc = this.config.default_location_src_id[0];
            let loc_qty = this.prod_with_quant[product.id];
            let config_loc_qty = loc_qty[config_loc] || 0;
            let rec = 0;
            console.log("llll",product)
            if (product.type == 'consu'  && this.config.display_stock && product.product_variant_count == 1){
                let products = this.calculate_prod_qty();
                if(config_loc_qty > 0 || this.config.Negative_selling ||  this.config.stock_qty){
                    await this.data.orm.call(
                        'stock.quant',
                        'warehouse_qty',
                        [, warehouse_id, product.id, session, product_qty],
                    ).then(function(output){
                        if (lines.length > 0){
                            for (let i in output){
                                for (let k in output[i]) {
                                    if (output[i].hasOwnProperty(k)) {
                                        let v = output[i][k];
                                        if (k == 'location') {
                                            if (products[v]) {
                                                products[v].forEach(function(q) {
                                                    if (q['name'] == product.display_name) {
                                                        output[i]['quantity'] = output[i]['quantity'] - q['qty'];
                                                    }
                                                });
                                            }
                                        }
                                    }
                                }
                            }
                            rec = output;
                        }
                        else{
                            rec = output;
                        }
                    });
                    order.set_loaded_qty(rec)
                    await this.dialog.add(PosStockWarehouse, {
                        product: product,
                        rec: rec,
                    });
                }else{
                    this.dialog.add(AlertDialog, {
                        title: _t('Out of Stock'),
                        body:  _t('Quantity is not available')
                    });
                }
            }else{
                let res = await super.addLineToCurrentOrder(vals, opt, configure);
                if (res){
                    
                    let prod = res.product_id.id
                    res.order_id.removeOrderline(res)
                    let products = this.calculate_prod_qty();
                    if(config_loc_qty > 0 || this.config.Negative_selling ||  this.config.stock_qty){
                        await this.data.orm.call(
                            'stock.quant',
                            'warehouse_qty',
                            [, warehouse_id, prod, session, product_qty],
                        ).then(function(output){
                            if (lines.length > 0){
                                for (let i in output){
                                    for (let k in output[i]) {
                                        if (output[i].hasOwnProperty(k)) {
                                            let v = output[i][k];
                                            if (k == 'location') {
                                                if (products[v]) {
                                                    products[v].forEach(function(q) {
                                                        if (q['name'] == product.display_name) {
                                                            output[i]['quantity'] = output[i]['quantity'] - q['qty'];
                                                        }
                                                    });
                                                }
                                            }
                                        }
                                    }
                                }
                                rec = output;
                            }
                            else{
                                rec = output;
                            }
                        });
                        order.set_loaded_qty(rec)
                        await this.dialog.add(PosStockWarehouse, {
                            product: product,
                            rec: rec,
                        });
                    }else{
                        this.dialog.add(AlertDialog, {
                            title: _t('Out of Stock'),
                            body:  _t('Quantity is not available')
                        });
                    }
                }


            }
        }else{
            await super.addLineToCurrentOrder(vals, opt, configure);
        }
    },

    calculate_prod_qty() {
        var self = this;
        var products = {};
        var order = this.get_order();
        if(order){
            var orderlines = order.get_orderlines();
            if(order.prd_qty  == undefined){
                order.prd_qty = {};
            }
            if(order.order_products  == undefined){
                order.order_products = {};
            }

            if(orderlines.length > 0 && self.config.default_location_src_id){
                orderlines.forEach(function (line) {
                    var prod = line.product_id;

                    order.order_products[prod.id] = self.prod_with_quant[prod.id];
                    var loc = line.stock_location_name;
                    if(prod.type == 'consu'){
                        if(products[loc] == undefined){
                            products[loc] =  [{
                                'loc' :loc,
                                'line' : line.id,
                                'name': prod.display_name,
                                'id':prod.id,
                                'prod_qty' : self.get_display_product_qty(line.product_id),
                                'qty' :parseFloat(line.qty)
                            }];
                        }
                        else{
                            let found = null;
                            for (let i = 0; i < products[loc].length; i++) {
                                let v = products[loc][i];
                                if (v.id === prod.id) {
                                    found = v;
                                }
                            }
                            if(found){
                                products[loc].forEach(function (val) {
                                    if(val['id'] == prod.id){
                                        if(val['line'] == line.id){
                                            val['qty'] = parseFloat(line.qty);
                                        }else{
                                            val['qty'] += parseFloat(line.qty);
                                        }
                                    }
                                });
                            }
                            if(found && found.length == 0){
                                products[loc].push({
                                    'loc' :loc,
                                    'line' : line.id,
                                    'name': prod.display_name,
                                    'id':prod.id,
                                    'prod_qty' : self.get_display_product_qty(line.product_id),
                                    'qty' :parseFloat(line.qty)
                                })
                            }
                        }
                    }
                });
            }
            order.prd_qty = products;
        }
        return products;
    },

    get_display_product_qty(prd){
        var self = this;
        var products = {};
        var order = this.get_order();
        var display_qty = 0;
        if(order){
            var orderlines = order.get_orderlines();
            if(orderlines.length > 0 && self.config.default_location_src_id){
                orderlines.forEach(function (line) {
                    if(line.product_id.id == prd.id){
                        display_qty += line.get_quantity()
                    }
                });
            }
        }
        return display_qty
    },
});

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        this.order_products = this.order_products || {};
        this.prd_qty = this.prd_qty || {};  
        this.loaded_qty = this.loaded_qty || {};
    },

    set_loaded_qty(loaded_qty){
        this.loaded_qty = loaded_qty;
    },
});


patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.stock_location_name = this.stock_location_name || '';
    },

    set_stock_location_name (stock_location_name){
        this.stock_location_name = stock_location_name
    },

    get_stock_location_name(){
        return this.stock_location_name
    },

    export_for_printing(baseUrl, headerData) {
        const json = super.export_for_printing(...arguments);
        json.stock_location_name = this.stock_location_name || "";
        return json;
    },

    getDisplayData() {
        return {
        	...super.getDisplayData(),
            stock_location_name: this.get_stock_location_name(),
        };
    }
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                stock_location_name: { type: String, optional: true },
            },
        },
    },
});
