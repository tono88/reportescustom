/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";

const MODULE = "l10n_gt_check_printing2_lx350";
let connection;
// One active send per tab: rapid double clicks must not dispatch two jobs.
let printing = false;

async function connectQZ() {
    if (!window.qz) {
        await loadJS(`/${MODULE}/static/lib/qz-tray/qz-tray.js`);
    }
    const qz = window.qz;
    if (!qz.websocket.isActive()) {
        if (!connection) {
            connection = qz.websocket.connect({ retries: 0 }).finally(() => {
                connection = undefined;
            });
        }
        await connection;
    }
    return qz;
}

function storageKey(companyId) {
    return `${MODULE}:${session.db}:${user.userId}:${companyId}:printer`;
}

function savedPrinter(companyId) {
    try {
        return browser.localStorage.getItem(storageKey(companyId));
    } catch {
        return null;
    }
}

class PrinterDialog extends Component {
    static template = "l10n_gt_check_printing2_lx350.PrinterDialog";
    static components = { Dialog };
    static props = ["close", "printers", "selected", "onSelect"];

    setup() {
        const saved = this.props.printers.includes(this.props.selected) ? this.props.selected : null;
        this.state = useState({ selected: saved || this.props.printers[0] || "" });
    }

    save() {
        if (this.state.selected) {
            this.props.onSelect(this.state.selected);
            this.props.close();
        }
    }
}

async function selectPrinter(env, companyId, printers) {
    return new Promise((resolve) => {
        env.services.dialog.add(PrinterDialog, {
            printers,
            selected: savedPrinter(companyId),
            onSelect: (name) => {
                try {
                    browser.localStorage.setItem(storageKey(companyId), name);
                } catch {
                    env.services.notification.add("El navegador no permite guardar la impresora. Se pedirá de nuevo en la próxima impresión.", { type: "warning" });
                }
                resolve(name);
            },
        }, { onClose: () => resolve(null) });
    });
}

async function availablePrinters(qz) {
    const printers = await qz.printers.find();
    if (!Array.isArray(printers) || !printers.length) {
        throw new Error("QZ Tray no encontró impresoras. Instala el controlador Epson en esta computadora.");
    }
    return [...printers].sort();
}

registry.category("actions").add(`${MODULE}.configure_printer`, async (env, action) => {
    try {
        const qz = await connectQZ();
        await selectPrinter(env, action.params.company_id, await availablePrinters(qz));
    } catch (error) {
        env.services.notification.add(`No se pudo configurar la impresora. Abre QZ Tray en esta computadora y autoriza la conexión. ${error.message || error}`, {
            type: "danger", sticky: true,
        });
    }
});

export async function printReport(action, options, env) {
    if (!action.report_name?.startsWith(`${MODULE}.`) || !action.lx350?.direct) {
        return false;
    }
    if (printing) {
        env.services.notification.add("Ya hay un envío de cheque en curso. No se envió otra copia.", { type: "warning" });
        return true;
    }
    printing = true;
    let blocked = false;
    let submitted = false;
    try {
        const qz = await connectQZ();
        const printers = await availablePrinters(qz);
        let printer = savedPrinter(action.lx350.company_id);
        if (printer && !printers.includes(printer)) {
            throw new Error(`La impresora guardada «${printer}» no está disponible. Usa Configurar Epson USB en el diario bancario.`);
        }
        if (!printer) {
            printer = await selectPrinter(env, action.lx350.company_id, printers);
        }
        if (!printer) {
            throw new Error("Selección cancelada. No se envió ningún trabajo a la impresora.");
        }
        const ids = action.context?.active_ids;
        if (!Array.isArray(ids) || !ids.length || ids.some((id) => !Number.isSafeInteger(id) || id <= 0)) {
            throw new Error("No se recibieron documentos válidos para imprimir.");
        }
        const context = { ...user.context, ...action.context };
        const url = `/report/pdf/${encodeURIComponent(action.report_name)}/${ids.join(",")}?context=${encodeURIComponent(JSON.stringify(context))}`;
        env.services.ui.block();
        blocked = true;
        // The browser fetches with the Odoo session. No public attachment URL,
        // credentials or cookies are handed to the desktop printing bridge.
        const response = await fetch(url, { credentials: "same-origin" });
        if (!response.ok || !response.headers.get("content-type")?.includes("application/pdf")) {
            throw new Error("Odoo no generó un PDF válido. Revisa el pago y la calibración con el botón PDF del cheque asignado.");
        }
        const bytes = new Uint8Array(await response.arrayBuffer());
        if (new TextDecoder().decode(bytes.slice(0, 5)) !== "%PDF-") {
            throw new Error("La respuesta no contiene un PDF. No se envió a la impresora.");
        }
        let binary = "";
        for (let offset = 0; offset < bytes.length; offset += 8192) {
            binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
        }
        const config = qz.configs.create(printer, {
            units: "mm",
            size: { width: action.lx350.width, height: action.lx350.height },
            margins: 0,
            scaleContent: false,
            copies: 1,
            duplex: false,
            colorType: "blackwhite",
            jobName: `${action.lx350.calibration ? "PRUEBA SIN VALOR" : "Cheque"} ${action.lx350.bank_label}`,
        });
        // Once dispatched, a rejection may still mean the spooler accepted it.
        // Never retry automatically or print a fallback copy after this point.
        submitted = true;
        await qz.print(config, [{ type: "pixel", format: "pdf", flavor: "base64", data: btoa(binary) }]);
        env.services.notification.add("Trabajo enviado a la cola de impresión. Verifica el resultado físico.", { type: "success" });
    } catch (error) {
        const status = submitted
            ? "El envío no pudo confirmarse; comprueba la cola y el cheque antes de reimprimir."
            : "No se envió el cheque a la impresora.";
        env.services.notification.add(`${status} ${error.message || error} El número asignado se conserva.`, {
            title: "Impresión Epson USB", type: "danger", sticky: true,
        });
    } finally {
        if (blocked) {
            env.services.ui.unblock();
        }
        printing = false;
    }
    return true;
}

registry.category("ir.actions.report handlers").add(`${MODULE}.usb`, printReport);
