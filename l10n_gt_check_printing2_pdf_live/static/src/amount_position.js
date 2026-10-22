/* Classic module also works when static assets are imported as attachments. */
odoo.define("l10n_gt_check_printing2_pdf_live.amount_position", [
    "@odoo/owl", "@web/core/browser/browser", "@web/core/dialog/dialog",
    "@web/core/registry", "@web/core/user", "@web/session",
    "@web/core/network/rpc", "@web/webclient/actions/reports/utils",
], function (require) {
    "use strict";

    const { Component, useState, xml } = require("@odoo/owl");
    const { browser } = require("@web/core/browser/browser");
    const { Dialog } = require("@web/core/dialog/dialog");
    const { registry } = require("@web/core/registry");
    const { user } = require("@web/core/user");
    const { session } = require("@web/session");
    const { rpc } = require("@web/core/network/rpc");
    const { downloadReport } = require("@web/webclient/actions/reports/utils");
    const MODULE = "l10n_gt_check_printing2_pdf_live";
    const BANKS = { banrural: "Banrural", gyt: "G&T Continental" };

    function normalizeShift(value) {
        if (value === null || value === "" || typeof value === "boolean") return 0;
        const number = Number(value);
        return Number.isFinite(number) ? Math.round(Math.max(-20, Math.min(20, number)) * 2) / 2 : 0;
    }

    function storageKey(companyId, journalId, bank) {
        return `${MODULE}:amount-x:${session.db}:${user.userId}:${companyId}:${journalId}:${bank}`;
    }

    function loadShift(key) {
        try { return normalizeShift(browser.localStorage.getItem(key)); }
        catch { return 0; }
    }

    class AmountPositionDialog extends Component {
        static components = { Dialog };
        static props = ["close", "bank", "paymentId", "journalName", "storageKey", "context"];
        static template = xml`
            <Dialog title="title" size="'md'">
                <p class="mb-1">Diario: <strong t-esc="props.journalName"/></p>
                <p>Mueve solo el monto en números. La altura y los demás campos se conservan.</p>
                <label class="form-label fw-bold" for="check-amount-shift">Movimiento horizontal (mm)</label>
                <input id="check-amount-shift" type="range" class="form-range"
                    min="-20" max="20" step="0.5" t-att-value="state.shift"
                    t-att-disabled="state.busy" t-on-input="onInput"
                    aria-label="Mover el monto en milímetros"/>
                <div class="d-flex justify-content-between text-muted mb-3">
                    <span>← Izquierda: −20 mm</span><span>Derecha: +20 mm →</span>
                </div>
                <div class="d-flex align-items-center justify-content-center gap-2 mb-2">
                    <button class="btn btn-outline-secondary" t-on-click="moveLeft" t-att-disabled="state.busy" aria-label="Medio milímetro a la izquierda">−0.5 mm</button>
                    <input type="number" class="form-control text-center" style="width:110px"
                        min="-20" max="20" step="0.5" t-att-value="state.shift"
                        t-att-disabled="state.busy" t-on-input="onInput" aria-label="Ajuste horizontal en milímetros"/>
                    <button class="btn btn-outline-secondary" t-on-click="moveRight" t-att-disabled="state.busy" aria-label="Medio milímetro a la derecha">+0.5 mm</button>
                </div>
                <p class="text-center fw-bold" role="status" aria-live="polite" t-esc="movement"/>
                <div class="text-center mb-3">
                    <button class="btn btn-link" t-on-click="reset" t-att-disabled="state.busy">Volver a 0 mm (posición de v1.0.11)</button>
                </div>
                <p class="text-muted small">Al generar el PDF, el ajuste se guarda en este navegador para este banco y diario.</p>
                <div class="alert alert-info mb-0">Genera un PDF nuevo con cada ajuste. Prueba primero en papel común, Carta y 100 %. Si faltan cifras al moverlo a la derecha, retrocede la barra.</div>
                <t t-set-slot="footer">
                    <button class="btn btn-primary" t-on-click="generate" t-att-disabled="state.busy">
                        <t t-if="state.busy">Generando…</t><t t-else="">Generar PDF con este ajuste</t>
                    </button>
                    <button class="btn btn-secondary" t-on-click="props.close" t-att-disabled="state.busy">Cerrar</button>
                </t>
            </Dialog>`;

        setup() {
            this.state = useState({ shift: loadShift(this.props.storageKey), busy: false });
        }
        get title() { return `Ajustar monto · ${BANKS[this.props.bank]}`; }
        get movement() {
            const shift = this.state.shift;
            return shift === 0 ? "Sin movimiento adicional" : `${Math.abs(shift)} mm hacia la ${shift < 0 ? "izquierda" : "derecha"}`;
        }
        onInput(event) { if (!this.state.busy) this.state.shift = normalizeShift(event.target.value); }
        moveLeft() { if (!this.state.busy) this.state.shift = normalizeShift(this.state.shift - 0.5); }
        moveRight() { if (!this.state.busy) this.state.shift = normalizeShift(this.state.shift + 0.5); }
        reset() { if (!this.state.busy) this.state.shift = 0; }

        async generate() {
            if (this.state.busy) return;
            this.state.busy = true;
            const shift = normalizeShift(this.state.shift);
            try {
                const context = {
                    ...user.context, ...this.props.context,
                    active_model: "account.payment", active_id: this.props.paymentId,
                    active_ids: [this.props.paymentId], check_amount_shift_x: shift,
                };
                const result = await downloadReport(rpc, {
                    report_type: "qweb-pdf", report_name: `${MODULE}.check_${this.props.bank}`,
                    context,
                }, "pdf", context);
                if (!result.success) throw new Error("No se pudo generar el PDF. Revisa el generador de reportes del servidor.");
                try { browser.localStorage.setItem(this.props.storageKey, String(shift)); }
                catch {
                    this.env.services.notification.add("PDF generado. El navegador no permite recordar el ajuste; deberás elegirlo de nuevo.", { type: "warning" });
                    return;
                }
                this.env.services.notification.add(`PDF descargado. Ajuste del monto: ${shift > 0 ? "+" : ""}${shift} mm.`, { type: "success" });
                // Keep the dialog open so the operator can adjust and repeat.
            } catch (error) {
                this.env.services.notification.add(`No se descargó el PDF. ${error.message || error}`, { type: "danger", sticky: true });
            } finally {
                this.state.busy = false;
            }
        }
    }

    async function openAmountPosition(env, action) {
        const bank = action.params && action.params.bank;
        const context = action.context || {};
        const ids = context.active_ids || (context.active_id ? [context.active_id] : []);
        if (!Object.hasOwn(BANKS, bank) || context.active_model !== "account.payment" ||
                ids.length !== 1 || !Number.isInteger(ids[0]) || ids[0] <= 0) {
            env.services.notification.add("Abre un único pago por cheque ya numerado y usa el botón de su banco.", { type: "warning" });
            return;
        }
        try {
            const [payment] = await env.services.orm.read("account.payment", ids, [
                "company_id", "journal_id", "state", "payment_type", "payment_method_code", "check_number",
            ]);
            if (!payment || !payment.check_number || !["in_process", "paid"].includes(payment.state) ||
                    payment.payment_type !== "outbound" || payment.payment_method_code !== "check_printing") {
                env.services.notification.add("Primero asigna el número con el flujo habitual de Imprimir cheque.", { type: "warning" });
                return;
            }
            env.services.dialog.add(AmountPositionDialog, {
                bank, paymentId: ids[0], context: { ...context },
                journalName: payment.journal_id[1],
                storageKey: storageKey(payment.company_id[0], payment.journal_id[0], bank),
            });
        } catch (error) {
            env.services.notification.add(`No se pudo abrir el ajuste. ${error.message || error}`, { type: "danger", sticky: true });
        }
    }

    registry.category("actions").add(`${MODULE}.amount_position`, openAmountPosition);
    return { AmountPositionDialog, normalizeShift, storageKey, openAmountPosition };
});
