const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../static/src/printing.js"), "utf8")
    .replace(/^import .*;\r?$/gm, "")
    .replace("export async function printReport", "async function printReport");

function fixture({ printers = ["EPSON LX-350"], saved = "EPSON LX-350", pdf = true, reject = false, cancel = false, hold = false } = {}) {
    const calls = { print: [], fetch: [], messages: [], storage: [], blocks: 0 };
    let finish;
    const qz = {
        websocket: { isActive: () => true },
        printers: { find: async () => printers },
        configs: { create: (printer, options) => ({ printer, options }) },
        print: async (...args) => {
            calls.print.push(args);
            if (reject) throw Error("spooler error");
            if (hold) await new Promise((resolve) => { finish = resolve; });
        },
    };
    const env = { services: {
        notification: { add: (...args) => calls.messages.push(args) },
        ui: { block: () => calls.blocks++, unblock: () => calls.blocks-- },
        dialog: { add: (cls, props, options) => { if (!cancel) props.onSelect(printers[0]); options.onClose(); } },
    } };
    const context = {
        Component: class {}, useState: (value) => value, Dialog: class {},
        loadJS: async () => {}, window: { qz },
        browser: { localStorage: {
            getItem: (key) => { calls.storage.push(key); return saved; },
            setItem: () => {},
        } },
        registry: { category: () => ({ add: () => {} }) },
        user: { userId: 7, context: { lang: "es_GT" } }, session: { db: "testdb" },
        TextDecoder, Uint8Array, btoa: (s) => Buffer.from(s, "binary").toString("base64"),
        fetch: async (...args) => {
            calls.fetch.push(args);
            return { ok: true, headers: { get: () => pdf ? "application/pdf" : "text/html" },
                arrayBuffer: async () => new TextEncoder().encode("%PDF-1.4 test").buffer };
        },
    };
    vm.createContext(context);
    vm.runInContext(source + "\nglobalThis.run = printReport;", context);
    const action = {
        report_name: "l10n_gt_check_printing2_lx350.check_personal",
        context: { active_ids: [42] },
        lx350: { direct: true, company_id: 1, width: 165, height: 70, bank_label: "Banrural" },
    };
    return { calls, env, action, run: context.run, finish: () => finish() };
}

test("USB sends one PDF at actual size to exact saved printer", async () => {
    const f = fixture();
    assert.equal(await f.run(f.action, {}, f.env), true);
    assert.equal(f.calls.print.length, 1);
    const [config, data] = f.calls.print[0];
    assert.equal(config.printer, "EPSON LX-350");
    assert.equal(config.options.scaleContent, false);
    assert.equal(config.options.copies, 1);
    assert.equal(config.options.size.width, 165);
    assert.equal(data[0].flavor, "base64");
    assert.equal(Buffer.from(data[0].data, "base64").toString(), "%PDF-1.4 test");
    assert.equal(f.calls.fetch[0][1].credentials, "same-origin");
    assert.equal(f.calls.blocks, 0);
});

test("unavailable saved printer never chooses another printer", async () => {
    const f = fixture({ printers: ["Office Laser"] });
    await f.run(f.action, {}, f.env);
    assert.equal(f.calls.print.length, 0);
    assert.equal(f.calls.fetch.length, 0);
});

test("bridge rejection never retries or downloads fallback", async () => {
    const f = fixture({ reject: true });
    await f.run(f.action, {}, f.env);
    assert.equal(f.calls.print.length, 1);
    assert.equal(f.calls.fetch.length, 1);
    assert.match(f.calls.messages.at(-1)[0], /comprueba la cola/);
    assert.equal(f.calls.blocks, 0);
});

test("HTML error response is not dispatched", async () => {
    const f = fixture({ pdf: false });
    await f.run(f.action, {}, f.env);
    assert.equal(f.calls.print.length, 0);
    assert.equal(f.calls.blocks, 0);
});

test("ordinary PDF and other reports keep standard Odoo behavior", async () => {
    const f = fixture();
    f.action.lx350.direct = false;
    assert.equal(await f.run(f.action, {}, f.env), false);
    f.action.lx350.direct = true;
    f.action.report_name = "account.report_invoice";
    assert.equal(await f.run(f.action, {}, f.env), false);
    assert.equal(f.calls.print.length, 0);
});

test("cancelling initial printer selection sends nothing", async () => {
    const f = fixture({ saved: null, cancel: true });
    await f.run(f.action, {}, f.env);
    assert.equal(f.calls.print.length, 0);
    assert.equal(f.calls.fetch.length, 0);
});

test("printer preference is scoped to user database and company", async () => {
    const f = fixture();
    await f.run(f.action, {}, f.env);
    f.action.lx350.company_id = 2;
    await f.run(f.action, {}, f.env);
    assert.notEqual(f.calls.storage[0], f.calls.storage[1]);
    assert.match(f.calls.storage[0], /testdb:7:1:printer$/);
    assert.match(f.calls.storage[1], /testdb:7:2:printer$/);
});

test("rapid duplicate click dispatches one job", async () => {
    const f = fixture({ hold: true });
    const first = f.run(f.action, {}, f.env);
    await new Promise((resolve) => setImmediate(resolve));
    await f.run(f.action, {}, f.env);
    assert.equal(f.calls.print.length, 1);
    f.finish();
    await first;
    assert.equal(f.calls.print.length, 1);
});

test("G&T personal report uses its own report and job name at personal size", async () => {
    const f = fixture();
    f.action.report_name = "l10n_gt_check_printing2_lx350.check_gyt";
    f.action.lx350.bank_label = "G&T Continental";
    await f.run(f.action, {}, f.env);
    assert.match(f.calls.fetch[0][0], /check_gyt\/42/);
    const [config] = f.calls.print[0];
    assert.equal(config.options.jobName, "Cheque G&T Continental");
    assert.equal(config.options.size.width, 165);
    assert.equal(config.options.size.height, 70);
});
