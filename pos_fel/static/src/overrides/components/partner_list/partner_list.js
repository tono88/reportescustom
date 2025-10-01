/** @odoo-module */
 
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    async getNewPartners() {
        let result = await super.getNewPartners();
        if (!result.length) {
            result = await this.pos.data.silentCall("pos.session", "crear_partner_con_datos_sat", [this.pos.company.id, this.state.query]);
            let newPartners = await this.getNewPartners();
            //if (newPartners.length) {
            //    this.clickPartner(newPartners[0]);
            //}
        }
        return result;
    }
});
