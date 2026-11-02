/** @odoo-module **/
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { loadBundle } from '@web/core/assets';
import { useService } from '@web/core/utils/hooks';

class DashboardChart extends Component {
    static template = 'tecnodyne_dashboard.Chart';
    static props = ['item', 'onDrill'];
    setup() {
        this.canvas = useRef('canvas');
        onWillStart(() => loadBundle('web.chartjs_lib'));
        useEffect(() => {
            const item = this.props.item;
            this.chart = new Chart(this.canvas.el, {
                type: item.kind,
                data: { labels: item.rows.map(r => r.label), datasets: [{
                    label: item.name, data: item.rows.map(r => r.value),
                    backgroundColor: item.rows.map((r, i) => ['#167d9a', '#22ab98', '#f2b85b', '#8b78ce', '#ea7882'][i % 5]),
                    borderColor: '#167d9a',
                }] },
                options: { responsive: true, maintainAspectRatio: false,
                    onClick: (event, elements) => { if (elements.length) this.props.onDrill(item, elements[0].index); },
                    plugins: { legend: { display: item.kind === 'pie' } },
                },
            });
            return () => this.chart.destroy();
        }, () => [this.props.item]);
    }
}

class TecnodyneDashboard extends Component {
    static template = 'tecnodyne_dashboard.Dashboard';
    static components = { DashboardChart };
    static props = ['*'];
    setup() {
        this.orm = useService('orm');
        this.action = useService('action');
        this.state = useState({ data: null, error: '', busy: false, from: '', to: '', refresh: '0' });
        this.version = 0;
        onWillStart(() => this.load());
        onWillUnmount(() => { clearInterval(this.timer); this.version++; });
    }
    async load() {
        const version = ++this.version;
        this.state.busy = true;
        try {
            const data = await this.orm.call('tecnodyne.dashboard', 'get_dashboard',
                [[this.props.action.params.dashboard_id]], { date_from: this.state.from || false, date_to: this.state.to || false });
            if (version === this.version) { this.state.data = data; this.state.error = ''; }
        } catch (error) {
            if (version === this.version) { this.state.data = null; this.state.error = error.data?.message || error.message; }
        } finally { if (version === this.version) this.state.busy = false; }
    }
    setRefresh(event) {
        clearInterval(this.timer);
        const seconds = Number(event.target.value);
        if (seconds) this.timer = setInterval(() => { if (!this.state.busy) this.load(); }, seconds * 1000);
    }
    async drill(item, index = false) {
        const action = await this.orm.call('tecnodyne.dashboard.item', 'action_drill', [[item.id]],
            { row_index: index, date_from: this.state.from || false, date_to: this.state.to || false });
        await this.action.doAction(action);
    }
    format(value) { return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value); }
    download(item) {
        const quote = value => '"' + String(value).replace(/"/g, '""') + '"';
        // Prevent spreadsheet formulas when opening CSV from untrusted labels.
        const safe = value => /^[=+\-@\t\r]/.test(String(value)) ? "'" + value : value;
        const rows = item.kind === 'kpi' ? [[item.name, item.value]] : item.rows.map(r => [r.label, r.value]);
        const csv = '\ufeff' + [['Group', 'Value'], ...rows].map(row => row.map(v => quote(typeof v === 'number' ? v : safe(v))).join(',')).join('\r\n');
        const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
        const link = document.createElement('a'); link.href = url; link.download = 'tecnodyne-' + item.id + '.csv'; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
}
registry.category('actions').add('tecnodyne_dashboard', TecnodyneDashboard);
