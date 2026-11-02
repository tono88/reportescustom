/** @odoo-module **/
import {
  Component,
  onWillStart,
  onWillUnmount,
  useEffect,
  useRef,
  useState,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { WORLD_POLYGONS } from "@tecnodyne_dashboard/world_map";

const KINDS = [
  "kpi",
  "bar",
  "horizontal",
  "line",
  "area",
  "pie",
  "doughnut",
  "polarArea",
  "radar",
  "scatter",
  "flower",
  "funnel",
  "radial",
  "bullet",
  "map",
  "table",
  "list",
  "todo",
];
const PALETTES = {
  default: ["#167d9a", "#22ab98", "#f2b85b", "#8b78ce", "#ea7882"],
  cool: ["#4477aa", "#66ccee", "#228833", "#aa3377"],
  warm: ["#c44935", "#f28e2b", "#edc948", "#b07aa1"],
  neon: ["#a855f7", "#06b6d4", "#ec4899", "#84cc16"],
};
function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob),
    link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

class DashboardChart extends Component {
  static template = "tecnodyne_dashboard.Chart";
  static props = ["item", "theme", "onDrill"];
  setup() {
    this.canvas = useRef("canvas");
    onWillStart(() => loadBundle("web.chartjs_lib"));
    useEffect(
      () => {
        const item = this.props.item,
          colors = PALETTES[this.props.theme] || PALETTES.default;
        if (
          ["flower", "funnel", "radial", "bullet", "map"].includes(item.kind)
        ) {
          const start = performance.now();
          let frame;
          const draw = (now) => {
            const progress = Math.min(1, (now - start) / 350);
            this.drawSpecial(item, colors, progress);
            if (progress < 1) frame = requestAnimationFrame(draw);
          };
          frame = requestAnimationFrame(draw);
          return () => {
            cancelAnimationFrame(frame);
            this.canvas.el.onclick = null;
          };
        }
        const labels = [...new Set(item.rows.map((r) => r.label))],
          series = [...new Set(item.rows.map((r) => r.series || ""))];
        let datasets = series.map((name, i) => ({
          label: name || item.name,
          data: labels.map((label) =>
            item.rows
              .filter((r) => r.label === label && (r.series || "") === name)
              .reduce((sum, r) => sum + r.value, 0),
          ),
          borderColor: colors[i % colors.length],
          backgroundColor: ["pie", "doughnut", "polarArea"].includes(item.kind)
            ? labels.map((v, j) => colors[j % colors.length])
            : colors[i % colors.length] + (item.kind === "area" ? "66" : ""),
          fill: item.kind === "area",
          tension: 0.2,
        }));
        if (item.has_second)
          datasets.push({
            type: item.secondary_as_line ? "line" : undefined,
            label: _t("Second measure"),
            data: labels.map((label) =>
              item.rows
                .filter((r) => r.label === label)
                .reduce((sum, r) => sum + (r.value2 || 0), 0),
            ),
            borderColor: colors[1],
            backgroundColor: colors[1],
          });
        for (const [name, label] of Object.entries(item.measure_labels || {}))
          datasets.push({
            label,
            data: labels.map((label) =>
              item.rows
                .filter((r) => r.label === label)
                .reduce((sum, r) => sum + (r.measures?.[name] || 0), 0),
            ),
            borderColor: colors[datasets.length % colors.length],
            backgroundColor: colors[datasets.length % colors.length],
          });
        if (item.cumulative_as_line)
          datasets.push({
            type: "line",
            label: _t("Cumulative"),
            data: item.rows.map((r) => r.cumulative_value || 0),
            borderColor: "#8b5cf6",
            pointRadius: 1,
          });
        if (item.kind === "scatter")
          datasets = [
            {
              label: item.name,
              data: item.rows.map((r) => ({ x: r.value, y: r.value2 || 0 })),
              backgroundColor: colors[0],
            },
          ];
        if (
          (item.target || Object.keys(item.targets || {}).length) &&
          ["bar", "line", "area", "horizontal"].includes(item.kind)
        )
          datasets.push({
            type: "line",
            label: _t("Target"),
            data: labels.map(
              (label) =>
                item.rows.find((r) => r.label === label)?.target ?? item.target,
            ),
            borderColor: "#b64040",
            borderDash: [5, 4],
            pointRadius: 0,
          });
        const plugin = {
          id: "tdValues",
          afterDatasetsDraw(chart) {
            if (!item.show_values) return;
            const ctx = chart.ctx;
            ctx.save();
            ctx.fillStyle = "#334155";
            ctx.font = "11px sans-serif";
            ctx.textAlign = "center";
            chart.data.datasets.forEach((ds, di) =>
              chart.getDatasetMeta(di).data.forEach((el, i) => {
                const position = el.tooltipPosition ? el.tooltipPosition() : el;
                if (typeof ds.data[i] === "number")
                  ctx.fillText(
                    String(Math.round(ds.data[i] * 100) / 100),
                    position.x,
                    position.y - 7,
                  );
              }),
            );
            ctx.restore();
          },
        };
        this.chart = new Chart(this.canvas.el, {
          type: { horizontal: "bar", area: "line" }[item.kind] || item.kind,
          data: { labels, datasets },
          plugins: [plugin],
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 300 },
            indexAxis: item.kind === "horizontal" ? "y" : "x",
            onClick: (event, elements) => {
              if (!elements.length) return;
              const e = elements[0],
                index =
                  item.kind === "scatter"
                    ? e.index
                    : item.rows.findIndex(
                        (r) =>
                          r.label === labels[e.index] &&
                          (r.series || "") === (series[e.datasetIndex] || ""),
                      );
              if (index >= 0) this.props.onDrill(item, index);
            },
            scales: ["bar", "horizontal", "line", "area"].includes(item.kind)
              ? {
                  x: { stacked: item.stacked },
                  y: { stacked: item.stacked, beginAtZero: true },
                }
              : {},
            plugins: { legend: { display: item.show_legend } },
          },
        });
        return () => this.chart.destroy();
      },
      () => [this.props.item, this.props.item.kind, this.props.theme],
    );
  }
  drawSpecial(item, colors, progress = 1) {
    const canvas = this.canvas.el;
    canvas.width = 800;
    canvas.height = 420;
    const ctx = canvas.getContext("2d"),
      rows = item.rows,
      zones = [],
      max = Math.max(
        1,
        ...rows.map((r) => Math.abs(r.value)),
        Math.abs(item.target),
      ),
      n = Math.max(rows.length, 1);
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, 800, 420);
    ctx.font = "13px sans-serif";
    const points = rows.filter(
      (r) =>
        Number.isFinite(r.lat) &&
        Number.isFinite(r.lon) &&
        Math.abs(r.lat) <= 90 &&
        Math.abs(r.lon) <= 180,
    );
    const lons = points.map((r) => r.lon),
      lats = points.map((r) => r.lat);
    const lonPad = Math.max(2, (Math.max(...lons) - Math.min(...lons)) * 0.25);
    const latPad = Math.max(2, (Math.max(...lats) - Math.min(...lats)) * 0.25);
    const minLon = points.length
      ? Math.max(-180, Math.min(...lons) - lonPad)
      : -180;
    const maxLon = points.length
      ? Math.min(180, Math.max(...lons) + lonPad)
      : 180;
    const minLat = points.length
      ? Math.max(-90, Math.min(...lats) - latPad)
      : -90;
    const maxLat = points.length
      ? Math.min(90, Math.max(...lats) + latPad)
      : 90;
    const project = (lon, lat) => [
      20 + ((lon - minLon) / (maxLon - minLon)) * 760,
      30 + ((maxLat - lat) / (maxLat - minLat)) * 360,
    ];
    if (item.kind === "map") {
      ctx.save();
      ctx.beginPath();
      ctx.rect(20, 30, 760, 360);
      ctx.clip();
      ctx.fillStyle = "#e7edf1";
      ctx.strokeStyle = "#a0b3bf";
      ctx.lineWidth = 0.6;
      for (const polygon of WORLD_POLYGONS) {
        ctx.beginPath();
        for (const ring of polygon) {
          ring.forEach(([lon, lat], index) => {
            const [x, y] = project(lon, lat);
            if (index) ctx.lineTo(x, y);
            else ctx.moveTo(x, y);
          });
          ctx.closePath();
        }
        ctx.fill("evenodd");
        ctx.stroke();
      }
      ctx.restore();
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 0.5;
      ctx.fillStyle = "#475569";
      for (let step = 0; step <= 4; step++) {
        const lon = minLon + ((maxLon - minLon) * step) / 4;
        const [x] = project(lon, minLat);
        ctx.beginPath();
        ctx.moveTo(x, 30);
        ctx.lineTo(x, 390);
        ctx.stroke();
        ctx.fillText(lon.toFixed(1) + "°", x, 410);
      }
      for (let step = 0; step <= 4; step++) {
        const lat = minLat + ((maxLat - minLat) * step) / 4;
        const [, y] = project(minLon, lat);
        ctx.beginPath();
        ctx.moveTo(20, y);
        ctx.lineTo(780, y);
        ctx.stroke();
        ctx.fillText(lat.toFixed(1) + "°", 2, y);
      }
    }
    rows.forEach((row, i) => {
      ctx.fillStyle = colors[i % colors.length];
      ctx.strokeStyle = colors[i % colors.length];
      let z;
      if (item.kind === "map") {
        if (
          !Number.isFinite(row.lat) ||
          !Number.isFinite(row.lon) ||
          Math.abs(row.lat) > 90 ||
          Math.abs(row.lon) > 180
        )
          return;
        const [x, y] = project(row.lon, row.lat);
        ctx.beginPath();
        ctx.arc(
          x,
          y,
          (4 + Math.sqrt(Math.abs(row.value) / max) * 10) * progress,
          0,
          Math.PI * 2,
        );
        ctx.fill();
        ctx.fillText(row.label.slice(0, 18) + ": " + row.value, x + 9, y);
        z = { x: x - 10, y: y - 10, w: 25, h: 25 };
      } else if (item.kind === "flower") {
        const a = (i / n) * Math.PI * 2 - Math.PI / 2,
          r = (40 + (Math.abs(row.value) / max) * 130) * progress,
          x = 400 + Math.cos(a) * r,
          y = 205 + Math.sin(a) * r;
        ctx.beginPath();
        ctx.moveTo(400, 205);
        ctx.quadraticCurveTo(x + 35, y - 30, x, y);
        ctx.quadraticCurveTo(x - 35, y + 30, 400, 205);
        ctx.fill();
        ctx.fillStyle = "#334155";
        ctx.fillText(row.label.slice(0, 18), x, y);
        z = { x: x - 22, y: y - 22, w: 44, h: 44 };
      } else if (item.kind === "radial") {
        const radius = (i + 1) * (175 / n),
          angle =
            Math.min(1, Math.abs(row.value) / max) * Math.PI * 2 * progress;
        ctx.lineWidth = Math.min(9, 140 / n);
        ctx.beginPath();
        ctx.arc(210, 210, radius, -Math.PI / 2, angle - Math.PI / 2);
        ctx.stroke();
        ctx.fillText(
          row.label.slice(0, 25) + ": " + row.value,
          430,
          30 + i * 18,
        );
        z = { x: 425, y: 15 + i * 18, w: 350, h: 19 };
      } else if (item.kind === "funnel") {
        const h = 350 / n,
          w = (Math.abs(row.value) / max) * 650 * progress,
          next = (Math.abs(rows[i + 1]?.value ?? 0) / max) * 650 * progress,
          y = 25 + i * h;
        ctx.beginPath();
        ctx.moveTo(400 - w / 2, y);
        ctx.lineTo(400 + w / 2, y);
        ctx.lineTo(400 + next / 2, y + h - 3);
        ctx.lineTo(400 - next / 2, y + h - 3);
        ctx.closePath();
        ctx.fill();
        ctx.fillStyle = "#172d3a";
        ctx.fillText(row.label.slice(0, 26) + ": " + row.value, 25, y + 15);
        z = { x: 0, y, w: 800, h };
      } else {
        const y = 20 + (i * 370) / n,
          h = Math.max(3, 280 / n),
          w = (Math.abs(row.value) / max) * 550 * progress;
        ctx.fillStyle = "#e2e8f0";
        ctx.fillRect(200, y, 550, h);
        ctx.fillStyle = colors[i % colors.length];
        ctx.fillRect(200, y, w, h);
        ctx.fillStyle = "#334155";
        ctx.fillText(row.label.slice(0, 22), 10, y + 12);
        ctx.fillRect(200 + ((item.target || max) / max) * 550, y - 3, 3, h + 6);
        z = { x: 0, y: y - 3, w: 800, h: Math.max(h + 6, 370 / n) };
      }
      zones.push({ ...z, index: i });
    });
    canvas.onclick = (event) => {
      const r = canvas.getBoundingClientRect(),
        x = ((event.clientX - r.left) / r.width) * 800,
        y = ((event.clientY - r.top) / r.height) * 420,
        z = zones.find(
          (z) => x >= z.x && x <= z.x + z.w && y >= z.y && y <= z.y + z.h,
        );
      if (z) this.props.onDrill(item, z.index);
    };
  }
}

class TecnodyneDashboard extends Component {
  static template = "tecnodyne_dashboard.Dashboard";
  static components = { DashboardChart };
  static props = ["*"];
  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.notification = useService("notification");
    this.bus = useService("bus_service");
    this.state = useState({
      data: null,
      error: "",
      busy: false,
      from: "",
      to: "",
      preset: "custom",
      filters: [],
      layout: {},
      paths: {},
      edit: false,
      insight: "",
      insightBusy: false,
      layoutName: "",
    });
    this.kinds = KINDS;
    this.version = 0;
    this.changed = () => {
      clearTimeout(this.debounce);
      this.debounce = setTimeout(() => {
        if (!this.state.busy) this.load();
      }, 800);
    };
    onWillStart(async () => {
      await this.load();
      this.bus.addChannel("tecnodyne_dashboard_updates");
      this.bus.subscribe("tecnodyne_dashboard_changed", this.changed);
    });
    onWillUnmount(() => {
      clearInterval(this.timer);
      clearTimeout(this.debounce);
      this.bus.unsubscribe("tecnodyne_dashboard_changed", this.changed);
      this.bus.deleteChannel("tecnodyne_dashboard_updates");
      this.version++;
    });
  }
  get id() {
    return this.props.action.params.dashboard_id;
  }
  kindsFor(item) {
    if (["kpi", "todo", "list", "map"].includes(item.source_kind || item.kind))
      return [item.source_kind || item.kind];
    return this.kinds.filter(
      (k) => !["kpi", "todo", "list", "map"].includes(k),
    );
  }
  get options() {
    return {
      date_from: this.state.from || false,
      date_to: this.state.to || false,
      preset: this.state.preset,
      filter_ids: [...this.state.filters],
    };
  }
  async safe(work) {
    try {
      return await work();
    } catch (e) {
      this.notification.add(e.data?.message || e.message, { type: "danger" });
    }
  }
  async load() {
    const version = ++this.version;
    this.state.busy = true;
    try {
      const data = await this.orm.call(
        "tecnodyne.dashboard",
        "get_dashboard",
        [[this.id]],
        this.options,
      );
      if (version === this.version) {
        this.state.data = data;
        this.state.layout = data.layout || {};
        this.state.paths = {};
        this.state.error = "";
      }
    } catch (e) {
      if (version === this.version) {
        this.state.data = null;
        this.state.error = e.data?.message || e.message;
      }
    } finally {
      if (version === this.version) this.state.busy = false;
    }
  }
  setRefresh(event) {
    clearInterval(this.timer);
    const seconds = Number(event.target.value);
    if (seconds)
      this.timer = setInterval(() => {
        if (!this.state.busy) this.load();
      }, seconds * 1000);
  }
  async toggleFilter(id) {
    this.state.filters = this.state.filters.includes(id)
      ? this.state.filters.filter((x) => x !== id)
      : [...this.state.filters, id];
    await this.load();
  }
  async favorite() {
    await this.orm.call(
      "tecnodyne.dashboard",
      "save_preferences",
      [[this.id]],
      { favorite: !this.state.data.favorite },
    );
    this.state.data.favorite = !this.state.data.favorite;
  }
  async drill(item, index = false) {
    if (
      index !== false &&
      item.level < item.depth &&
      !["list", "map"].includes(item.kind)
    ) {
      await this.drillPath(item, [
        ...(this.state.paths[item.id] || []),
        index + item.page * item.limit,
      ]);
      return;
    }
    await this.safe(async () =>
      this.action.doAction(
        await this.orm.call(
          "tecnodyne.dashboard.item",
          "action_drill",
          [[item.id]],
          {
            row_index: index,
            ...this.options,
            path: this.state.paths[item.id] || [],
            page: item.page,
          },
        ),
      ),
    );
  }
  async page(item, page) {
    await this.safe(async () => {
      const data = await this.orm.call(
        "tecnodyne.dashboard.item",
        "get_page",
        [[item.id]],
        { page, path: this.state.paths[item.id] || [], ...this.options },
      );
      this.state.data.items[
        this.state.data.items.findIndex((x) => x.id === item.id)
      ] = data;
    });
  }
  async drillPath(item, path) {
    await this.safe(async () => {
      const data = await this.orm.call(
        "tecnodyne.dashboard.item",
        "get_item",
        [[item.id]],
        { path, ...this.options },
      );
      this.state.data.items[
        this.state.data.items.findIndex((x) => x.id === item.id)
      ] = data;
      this.state.paths[item.id] = path;
    });
  }
  up(item) {
    return this.drillPath(item, (this.state.paths[item.id] || []).slice(0, -1));
  }
  async openItem(item, method = "action_edit") {
    await this.safe(async () =>
      this.action.doAction(
        await this.orm.call("tecnodyne.dashboard.item", method, [[item.id]]),
      ),
    );
  }
  async quickSave(item) {
    await this.safe(async () => {
      await this.orm.write("tecnodyne.dashboard.item", [item.id], {
        name: item.name,
        kind: item.kind,
        color: item.color,
      });
      await this.load();
    });
  }
  duplicate(item) {
    return this.openItem(item, "action_duplicate");
  }
  async task(row) {
    await this.safe(async () => {
      await this.orm.write("tecnodyne.dashboard.task", [row.id], {
        done: !row.done,
      });
      row.done = !row.done;
    });
  }
  format(value, item = {}) {
    return new Intl.NumberFormat(
      item.number_format === "indian" ? "en-IN" : undefined,
      {
        maximumFractionDigits: 2,
        notation:
          item.number_format === "compact"
            ? "compact"
            : item.number_format === "scientific"
              ? "scientific"
              : "standard",
      },
    ).format(value);
  }
  cardStyle(item) {
    const l = this.state.layout[String(item.id)] || {};
    return `order:${l.order ?? item.sequence ?? item.id};grid-column:span ${l.width || 1};min-height:${item.tile_style === "compact" && item.kind === "kpi" ? 230 : l.height || 420}px;--td-height:${l.height || 420}px;border-top:4px solid ${item.color || "#167d9a"};${item.kind === "kpi" && item.tile_style === "solid" ? "background:" + item.color + ";color:white;" : ""}`;
  }
  resize(item, key, event) {
    this.state.layout[String(item.id)] = {
      ...(this.state.layout[String(item.id)] || {}),
      [key]: Number(event.target.value),
    };
  }
  drag(event, item) {
    event.dataTransfer.setData("text/plain", String(item.id));
  }
  drop(event, item) {
    event.preventDefault();
    const source = Number(event.dataTransfer.getData("text/plain")),
      ordered = [...this.state.data.items]
        .sort(
          (a, b) =>
            (this.state.layout[String(a.id)]?.order ?? a.id) -
            (this.state.layout[String(b.id)]?.order ?? b.id),
        )
        .map((x) => x.id);
    if (!ordered.includes(source)) return;
    ordered.splice(ordered.indexOf(source), 1);
    ordered.splice(ordered.indexOf(item.id), 0, source);
    ordered.forEach((id, i) => {
      this.state.layout[String(id)] = {
        ...(this.state.layout[String(id)] || {}),
        order: i,
      };
    });
  }
  async saveLayout() {
    await this.safe(() =>
      this.orm.call("tecnodyne.dashboard", "save_preferences", [[this.id]], {
        layout: JSON.parse(JSON.stringify(this.state.layout)),
      }),
    );
  }
  async saveNamed() {
    await this.safe(async () => {
      this.state.data.layouts = await this.orm.call(
        "tecnodyne.dashboard",
        "save_named_layout",
        [[this.id]],
        {
          name: this.state.layoutName,
          layout: JSON.parse(JSON.stringify(this.state.layout)),
        },
      );
    });
  }
  async selectNamed(event) {
    if (!event.target.value) return;
    await this.safe(async () => {
      this.state.layout = await this.orm.call(
        "tecnodyne.dashboard",
        "select_named_layout",
        [[this.id]],
        { name: event.target.value },
      );
    });
  }
  async exportData(item, format) {
    await this.safe(async () => {
      const r = await this.orm.call(
          "tecnodyne.dashboard.item",
          "export_file",
          [[item.id]],
          { format, ...this.options, path: this.state.paths[item.id] || [] },
        ),
        bytes = Uint8Array.from(atob(r.content), (c) => c.charCodeAt(0));
      saveBlob(new Blob([bytes], { type: r.mime }), r.name);
    });
  }
  snapshot(item) {
    const chart = document.querySelector(`[data-item-id="${item.id}"] canvas`),
      canvas = document.createElement("canvas");
    canvas.width = 1200;
    canvas.height = chart ? 700 : Math.max(180, 90 + item.rows.length * 30);
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#167d9a";
    ctx.font = "bold 25px sans-serif";
    ctx.fillText("TECNODYNE · " + item.name, 30, 45);
    if (chart) ctx.drawImage(chart, 25, 80, 1150, 580);
    else {
      ctx.fillStyle = "#1e293b";
      ctx.font = "20px sans-serif";
      if (item.kind === "kpi")
        ctx.fillText(this.format(item.value, item) + " " + item.unit, 30, 110);
      else
        item.rows.forEach((row, i) =>
          ctx.fillText(
            (row.cells
              ? row.cells.join("  |  ")
              : row.label +
                "  |  " +
                (item.kind === "todo"
                  ? row.done
                    ? "✓"
                    : "□"
                  : this.format(row.value, item))
            ).slice(0, 115),
            30,
            90 + i * 30,
          ),
        );
    }
    return canvas;
  }
  png(item) {
    this.snapshot(item).toBlob((blob) =>
      saveBlob(blob, `tecnodyne-${item.id}.png`),
    );
  }
  async pdf(item) {
    await this.safe(async () =>
      this.action.doAction(
        await this.orm.call(
          "tecnodyne.dashboard.item",
          "action_pdf",
          [[item.id]],
          {
            ...this.options,
            path: this.state.paths[item.id] || [],
            chart_image: this.snapshot(item)
              .toDataURL("image/png")
              .split(",")[1],
          },
        ),
      ),
    );
  }
  async insights(item) {
    this.state.insightBusy = true;
    this.state.insight = "";
    await this.safe(async () => {
      this.state.insight = await this.orm.call(
        "tecnodyne.dashboard.item",
        "ai_insight",
        [[item.id]],
        { ...this.options, path: this.state.paths[item.id] || [] },
      );
    });
    this.state.insightBusy = false;
  }
}
registry.category("actions").add("tecnodyne_dashboard", TecnodyneDashboard);
