/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

function firstDefined(arr) {
  for (let i = 0; i < arr.length; i++) if (arr[i]) return arr[i];
  return null;
}

// Mantiene compatibilidad: no rompe si otro módulo también parchea export_for_printing
patch(PosOrder.prototype, {
  async after_server_push() {
    const res = await super.after_server_push(...arguments);
    const v = firstDefined([
      this?.backendOrder?.internal_correlative,
      this?.backendOrder?.pos_internal_seq,
      this?.internal_correlative,
      this?.pos_internal_seq,
      this?.internal_pos_sequence,
    ]);
    if (v) this.internal_correlative = String(v);
    return res;
  },

  export_for_printing() {
    const res = super.export_for_printing(...arguments);
    const v = firstDefined([
      this?.backendOrder?.internal_correlative,
      this?.backendOrder?.pos_internal_seq,
      this?.internal_correlative,
      this?.pos_internal_seq,
      this?.internal_pos_sequence,
      res?.internal_correlative,
    ]);
    if (v) {
      const s = String(v);
      res.internal_correlative = s;
      // no tocamos tracking_number aquí para evitar colisiones con otros módulos
    }
    return res;
  },
});
