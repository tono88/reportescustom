const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname,
    "../../l10n_gt_check_printing2_pdf_live/static/src/amount_position.js"), "utf8");

function fixture({ saved = null, blocked = false, failed = false, success = true, hold = false, payment = {} } = {}) {
    const calls = { reads: [], reports: [], dialogs: [], messages: [], saved: [], closed: 0 };
    let exported, finish;
    const record = { company_id: [1, "Empresa"], journal_id: [8, "Banco G&T"],
        state: "in_process", payment_type: "outbound", payment_method_code: "check_printing",
        check_number: "123", ...payment };
    const env = { services: {
        orm: { read: async (...args) => { calls.reads.push(args); return [record]; } },
        dialog: { add: (cls, props) => calls.dialogs.push({ cls, props }) },
        notification: { add: (...args) => calls.messages.push(args) },
    } };
    const modules = {
        "@odoo/owl": { Component: class {}, useState: v => v, xml: strings => strings[0] },
        "@web/core/browser/browser": { browser: { localStorage: {
            getItem: () => { if (blocked) throw Error("denied"); return saved; },
            setItem: (...args) => { if (blocked) throw Error("denied"); calls.saved.push(args); },
        } } },
        "@web/core/dialog/dialog": { Dialog: class {} },
        "@web/core/registry": { registry: { category: () => ({ add: () => {} }) } },
        "@web/core/user": { user: { userId: 7, context: { lang: "es_GT", allowed_company_ids: [1, 2] } } },
        "@web/session": { session: { db: "db" } },
        "@web/core/network/rpc": { rpc: () => {} },
        "@web/webclient/actions/reports/utils": { downloadReport: async (...args) => {
            calls.reports.push(args);
            if (hold) await new Promise(resolve => { finish = resolve; });
            if (failed) throw Error("download failed");
            return { success };
        } },
    };
    vm.runInNewContext(source, { odoo: { define: (name, deps, factory) => {
        for (const dep of deps) assert.ok(modules[dep], dep);
        exported = factory(name => modules[name]);
    } } });
    function dialog(bank = "gyt") {
        const instance = new exported.AmountPositionDialog();
        instance.env = env;
        instance.props = { close: () => calls.closed++, bank, paymentId: 42, journalName: "Banco G&T",
            storageKey: exported.storageKey(1, 8, bank),
            context: { active_model: "account.payment", active_ids: [42], allowed_company_ids: [1, 2] } };
        instance.setup();
        return instance;
    }
    return { ...exported, calls, env, dialog, finish: () => finish() };
}

test("restores calibration and rounds/clamps inputs in half millimetres", () => {
    const f = fixture({ saved: "-87.5" });
    const d = f.dialog();
    assert.equal(d.state.shift, -87.5);
    d.onInput({ target: { value: "2.7" } });
    assert.equal(d.state.shift, 2.5);
    d.moveRight(); assert.equal(d.state.shift, 3);
    d.moveLeft(); assert.equal(d.state.shift, 2.5);
    d.reset(); assert.equal(d.state.shift, 0);
    assert.equal(f.normalizeShift(999), 100);
    assert.equal(f.normalizeShift(87.5), 87.5);
    assert.equal(f.normalizeShift(-999), -100);
    for (const value of [NaN, Infinity, "bad", null, "", true]) assert.equal(f.normalizeShift(value), 0);
    assert.equal(f.calls.reports.length, 0);
    assert.equal(f.calls.saved.length, 0);
});

test("storage separates database/user/company/journal/bank", () => {
    const f = fixture();
    const keys = [f.storageKey(1, 8, "gyt"), f.storageKey(2, 8, "gyt"),
        f.storageKey(1, 9, "gyt"), f.storageKey(1, 8, "banrural")];
    assert.equal(new Set(keys).size, 4);
    assert.ok(keys[0].includes(":db:7:1:8:gyt"));
});

test("downloads existing bank report with the selected shift and record context, then remembers it", async () => {
    for (const bank of ["gyt", "banrural"]) {
        const f = fixture();
        const d = f.dialog(bank);
        d.state.shift = -100;
        await d.generate();
        const [, action, type, context] = f.calls.reports[0];
        assert.equal(action.report_name, `l10n_gt_check_printing2_pdf_live.check_${bank}`);
        assert.equal(type, "pdf");
        assert.equal(action.context, context);
        assert.equal(context.check_amount_shift_x, -100);
        assert.equal(context.active_model, "account.payment");
        assert.deepEqual(Array.from(context.active_ids), [42]);
        assert.deepEqual(Array.from(context.allowed_company_ids), [1, 2]);
        assert.equal(f.calls.saved[0][1], "-100");
        assert.equal(f.calls.closed, 0); // stay open for another test
        assert.equal(d.state.busy, false);
    }
});

test("does not save a new setting when download fails or wkhtmltopdf is unavailable", async () => {
    for (const options of [{ failed: true }, { success: false }]) {
        const f = fixture(options); const d = f.dialog();
        d.state.shift = 3; await d.generate();
        assert.equal(f.calls.saved.length, 0);
        assert.equal(f.calls.messages[0][1].type, "danger");
        assert.equal(d.state.busy, false);
    }
});

test("blocked local storage still allows download with selected adjustment", async () => {
    const f = fixture({ blocked: true }); const d = f.dialog();
    assert.equal(d.state.shift, 0);
    d.state.shift = 1.5; await d.generate();
    assert.equal(f.calls.reports[0][3].check_amount_shift_x, 1.5);
    assert.equal(f.calls.messages[0][1].type, "warning");
});

test("prevents double downloads and changes while a report is being generated", async () => {
    const f = fixture({ hold: true }); const d = f.dialog();
    d.state.shift = 2;
    const first = d.generate();
    await d.generate(); d.moveLeft(); d.reset(); d.onInput({ target: { value: "10" } });
    assert.equal(d.state.shift, 2);
    assert.equal(f.calls.reports.length, 1);
    f.finish(); await first;
    assert.equal(d.state.busy, false);
});

test("opens the bank dialog only for one numbered outbound cheque", async () => {
    const f = fixture();
    await f.openAmountPosition(f.env, { params: { bank: "gyt" },
        context: { active_model: "account.payment", active_ids: [42] } });
    assert.equal(f.calls.dialogs.length, 1);
    assert.equal(f.calls.dialogs[0].props.paymentId, 42);
    assert.equal(f.calls.dialogs[0].props.bank, "gyt");
    assert.equal(f.calls.reads.length, 1);
    for (const payment of [{ state: "draft" }, { check_number: false },
        { payment_type: "inbound" }, { payment_method_code: "manual" }]) {
        const bad = fixture({ payment });
        await bad.openAmountPosition(bad.env, { params: { bank: "gyt" },
            context: { active_model: "account.payment", active_id: 42 } });
        assert.equal(bad.calls.dialogs.length, 0);
        assert.equal(bad.calls.reports.length, 0);
    }
});

test("rejects wrong bank, model, multiple or missing payment without any RPC", async () => {
    for (const action of [{ params: { bank: "other" } },
        { params: { bank: "gyt" }, context: { active_model: "account.move", active_ids: [42] } },
        { params: { bank: "gyt" }, context: { active_model: "account.payment", active_ids: [42, 43] } },
        { params: { bank: "gyt" }, context: { active_model: "account.payment", active_ids: [] } }]) {
        const f = fixture(); await f.openAmountPosition(f.env, action);
        assert.equal(f.calls.reads.length, 0);
        assert.equal(f.calls.dialogs.length, 0);
    }
});
