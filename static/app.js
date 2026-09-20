const $ = id => document.getElementById(id);
const S = () => I18N.s;
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const num = (n, d = 0) => I18N.num(n, d);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const zoneName = z => esc(I18N.zone(z));

const ICONS = {
  today: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
  map: '<path d="M14.1 6.3 9.9 4.2a2 2 0 0 0-1.8 0L3.6 6.5A1 1 0 0 0 3 7.4v12a1 1 0 0 0 1.4.9l3.7-1.9a2 2 0 0 1 1.8 0l4.2 2.1a2 2 0 0 0 1.8 0l4.5-2.3a1 1 0 0 0 .6-.9v-12a1 1 0 0 0-1.4-.9l-3.7 1.9a2 2 0 0 1-1.8 0z"/><path d="M15 5.8v15"/><path d="M9 3.2v15"/>',
  why: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  forecast: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  data: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
  gas: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
  oil: '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.500S12.500 5.500 12 3c-.5 2.500-2 4.900-4 6.500C6 11.100 5 13 5 15a7 7 0 0 0 7 7z"/>',
  coal: '<path d="m8 3 4 8 5-5 5 15H2L8 3z"/>',
  water: '<path d="M2 6c.6.5 1.2 1 2.500 1C7 7 7 5 9.500 5c2.600 0 2.400 2 5 2 2.500 0 2.500-2 5-2 1.300 0 1.900.5 2.500 1"/><path d="M2 12c.6.5 1.2 1 2.500 1 2.500 0 2.500-2 5-2 2.600 0 2.400 2 5 2 2.500 0 2.500-2 5-2 1.300 0 1.900.5 2.500 1"/><path d="M2 18c.6.5 1.2 1 2.500 1 2.500 0 2.500-2 5-2 2.600 0 2.400 2 5 2 2.500 0 2.500-2 5-2 1.300 0 1.900.5 2.500 1"/>',
  repair: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.900 6.900a2.100 2.100 0 0 1-3-3l6.900-6.900a6 6 0 0 1 7.900-7.900l-3.800 3.800z"/>',
  other: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  storm: '<path d="M6 16.300A7 7 0 1 1 15.700 8h1.800a4.500 4.500 0 0 1 .5 9"/><path d="m13 12-3 5h4l-3 5"/>',
  thermo: '<path d="M14 4v10.500a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0z"/>',
  phone: '<path d="M22 16.900v3a2 2 0 0 1-2.200 2 19.800 19.800 0 0 1-8.600-3.100 19.500 19.500 0 0 1-6-6A19.800 19.800 0 0 1 2.100 4.200 2 2 0 0 1 4.100 2h3a2 2 0 0 1 2 1.700c.1 1 .4 1.900.7 2.800a2 2 0 0 1-.5 2.100L8.100 9.900a16 16 0 0 0 6 6l1.300-1.300a2 2 0 0 1 2.100-.4c.9.3 1.800.6 2.800.7a2 2 0 0 1 1.700 2z"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.600 13.500 6.800 4M15.400 6.500l-6.800 4"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><path d="M12 9v4M12 17h.01"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
};
const svg = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;
const TABS = [
  { id: "today", panel: "today" }, { id: "map", panel: "map-tab" }, { id: "why", panel: "why" },
  { id: "forecast", panel: "outlook" }, { id: "data", panel: "data" },
];
const FUELS = [
  { key: "gas", cols: ["gas"] }, { key: "coal", cols: ["coal"] }, { key: "renewable", cols: ["hydro", "solar", "wind"] },
  { key: "imports", cols: ["india_bheramara_hvdc", "india_tripura", "india_adani", "nepal"] }, { key: "oil", cols: ["liquid_fuel"] },
];
const CAPACITY = { gas: ["gas"], coal: ["coal"], renewable: ["renewable"], imports: ["imported"], oil: ["hfo", "hsd"] };
const CAUSES = [["gas_limit_mw", "gasLimit", "--gas"], ["coal_limit_mw", "coalLimit", "--coal"], ["water_limit_mw", "water", "--water"], ["maintenance_mw", "maintenance", "--maintenance"]];
const STALE_HOURS = 3;
const PLANT_FUELS = ["furnace_oil", "diesel", "ldo"], HOME_FUELS = ["petrol", "octane", "diesel", "kerosene", "lpg_12_5kg"];
const DESCO_DISTRICTS = ["Dhaka", "Gazipur"], HOT_DAY_C = 36, OLD_DAYS = { plants: 7, desco: 14 };

const state = { data: null, charts: {}, tab: null, map: null, layers: {}, places: [], upazilas: null, selected: null };

/* ---------- data ---------- */

function parseCsv(text) {
  const rows = [];
  for (const line of text.trim().split("\n")) {
    const cells = [];
    let cur = "", quoted = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (quoted) {
        if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') quoted = false; else cur += ch;
      } else if (ch === '"') quoted = true;
      else if (ch === ",") { cells.push(cur); cur = ""; } else cur += ch;
    }
    cells.push(cur);
    rows.push(cells);
  }
  const [head, ...body] = rows;
  return body.map(r => Object.fromEntries(head.map((h, i) => {
    const v = r[i] ?? "";
    return [h, v === "" ? null : Number.isNaN(Number(v)) ? v : Number(v)];
  })));
}

async function load(path) {
  const r = await fetch(path, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return /\.(json|geojson)$/.test(path) ? r.json() : parseCsv(await r.text());
}

const sum = (row, cols) => cols.every(c => row[c] == null) ? null : cols.reduce((a, c) => a + (row[c] ?? 0), 0);
const mean = xs => { const v = xs.filter(x => x != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
const onHour = r => r.timestamp.endsWith(":00");
const lastActual = dem => dem.findLast(r => r.demand_mw != null && r.loadshed_mw != null);
const ahead = ({ dem, forecast }) => { const t = lastActual(dem)?.timestamp ?? ""; return forecast?.next_hours?.filter(r => r.timestamp > t) ?? []; };
const bdDate = ts => new Date(ts + ":00+06:00");
const bdStamp = ms => new Date(ms + 6 * 36e5).toISOString().slice(0, 16);
const bdToday = (plusDays = 0) => bdStamp(Date.now() + plusDays * 864e5).slice(0, 10);
const daysOld = iso => (Date.parse(bdToday()) - Date.parse(iso)) / 864e5;
const digits = v => (I18N.lang === "bn" ? bnDigits(v) : String(v));

function daily(gen, dem) {
  const group = rows => rows.reduce((m, r) => m.set(r.timestamp.slice(0, 10), [...(m.get(r.timestamp.slice(0, 10)) || []), r]), new Map());
  const g = group(gen), d = group(dem);
  return [...new Set([...g.keys(), ...d.keys()])].sort().map(date => {
    const all = d.get(date) || [];
    const gr = (g.get(date) || []).filter(onHour), dr = all.filter(onHour);
    const total = gr.reduce((a, r) => a + (r.generation_mw ?? 0), 0);
    const share = cols => total ? 100 * gr.reduce((a, r) => a + (sum(r, cols) ?? 0), 0) / total : null;
    const shed = all.map(r => r.loadshed_mw).filter(x => x != null);
    return {
      date, renewable: share(FUELS[2].cols), imports: share(FUELS[3].cols),
      demand: mean(dr.map(r => r.demand_mw)), peakShed: shed.length ? Math.max(...shed) : null,
      mix: Object.fromEntries(FUELS.map(f => [f.key, mean(gr.map(r => sum(r, f.cols)))])),
    };
  });
}

function zoneStats(zones) {
  if (!zones?.length) return null;
  const dates = [...new Set(zones.map(z => z.date))].sort();
  const latestDate = dates.at(-1), window = new Set(dates.slice(-30));
  const stats = {};
  for (const z of zones) {
    const s = stats[z.zone] ??= { zone: z.zone, demand: 0, shed: 0, days: 0, latest: null };
    if (window.has(z.date)) { s.demand += z.demand_mw ?? 0; s.shed += z.loadshed_mw ?? 0; s.days += 1; }
    if (z.date === latestDate) s.latest = z;
  }
  const list = Object.values(stats).map(s => ({ ...s, share: s.demand ? 100 * s.shed / s.demand : 0, avg: s.days ? s.shed / s.days : 0 }))
    .sort((a, b) => b.share - a.share);
  list.forEach((s, i) => (s.rank = i + 1));
  return { list, byZone: Object.fromEntries(list.map(s => [s.zone, s])), latestDate, firstDate: dates.slice(-30)[0] };
}

/* ---------- i18n + chrome ---------- */

function resolve(key) { return key.split(".").reduce((o, k) => o?.[k], S()); }

function applyStatic() {
  document.documentElement.lang = I18N.lang;
  document.title = S().title;
  document.querySelectorAll("[data-t]").forEach(el => {
    const v = resolve(el.dataset.t);
    if (typeof v === "string") el.textContent = v;
  });
  $("lang-label").textContent = S().langSwitch;
  $("lang-toggle").setAttribute("aria-label", S().langSwitchLabel);
  const dark = document.documentElement.dataset.theme === "dark";
  $("theme-toggle").setAttribute("aria-pressed", String(dark));
  $("theme-label").textContent = S().themeDark;
  $("theme-toggle").innerHTML = svg(dark ? "sun" : "moon") + `<span class="visually-hidden" id="theme-label">${S().themeDark}</span>`;
  document.querySelectorAll("[data-nav]").forEach(nav => {
    nav.innerHTML = TABS.map(t => `<a href="#${t.id}" data-tab="${t.id}"${t.id === state.tab ? ' aria-current="page"' : ""}>${svg(t.id)}<span>${S().nav[t.id]}</span></a>`).join("");
  });
  document.querySelectorAll("[data-search]").forEach(buildSearch);
}

function remember(key, value) { try { localStorage.setItem(key, value); } catch { /* private mode */ } }

$("lang-toggle")?.addEventListener("click", () => {
  I18N.lang = I18N.lang === "bn" ? "en" : "bn";
  remember("lang", I18N.lang);
  renderAll();
});
$("theme-toggle")?.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  remember("theme", next);
  renderAll();
});

/* ---------- tabs ---------- */

const tabFromHash = hash => (hash === "outlook" ? "forecast" : hash);

function showTab(id, focus) {
  const tab = TABS.find(t => t.id === tabFromHash(id)) ?? TABS[0];
  state.tab = tab.id;
  for (const t of TABS) $(t.panel).hidden = t.id !== tab.id;
  document.querySelectorAll("[data-tab]").forEach(a => {
    if (a.dataset.tab === tab.id) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  if (state.data) renderTab(tab.id);
  if (focus) $(`h-${tab.id}`)?.focus();
}
addEventListener("hashchange", () => showTab(location.hash.slice(1), true));

/* ---------- charts ---------- */

function destroyCharts() { Object.values(state.charts).forEach(c => c.destroy()); state.charts = {}; }

function baseOptions({ unit = S().mw, pct = false, format, horizontal = false, months = false } = {}) {
  const muted = css("--muted");
  const value = v => pct ? `${num(v, 1)}%` : format ? format(v) : `${num(v)} ${unit}`;
  return {
    responsive: true, maintainAspectRatio: false, animation: false, locale: I18N.locale(),
    interaction: { mode: "index", intersect: false },
    plugins: { legend: { display: false }, tooltip: { filter: i => !i.dataset.hideInTooltip,
      callbacks: { label: c => `${c.dataset.label}: ${value(c.parsed[horizontal ? "x" : "y"])}` } } },
    scales: {
      x: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: muted, maxRotation: 0, autoSkipPadding: 16, maxTicksLimit: 8,
        autoSkip: !months,
        callback(v, i) {
          const labels = this.chart.data.labels, l = labels[i] ?? this.getLabelForValue(v);
          if (!months || !/^\d{4}-\d{2}/.test(l)) return l;
          if (i !== 0 && String(labels[i - 1]).slice(0, 7) === l.slice(0, 7)) return null;
          const nth = new Set(labels.slice(0, i + 1).map(x => String(x).slice(0, 7))).size - 1;
          return this.chart.width < 700 && nth % 3 ? null : I18N.date(l.slice(0, 10)).replace(/^\S+\s/, "");
        } } },
      y: { beginAtZero: true, grid: { color: css("--grid") }, border: { display: false },
        ticks: { color: muted, callback: v => pct ? `${num(v)}%` : format ? format(v) : num(v) } },
    },
  };
}
const line = (label, data, color, more = {}) => ({ label, data, borderColor: color, backgroundColor: color, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, ...more });

function chart(id, config, tweak) {
  const el = $(id);
  if (!el || !el.offsetParent) return;
  if (!el.getAttribute("aria-label") || el.dataset.autoLabel) {
    el.setAttribute("aria-label", el.closest(".card")?.querySelector("h2, h3, .big")?.textContent ?? "");
    el.dataset.autoLabel = "1";
  }
  el.setAttribute("role", "img");
  state.charts[id]?.destroy();
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  const c = new Chart(el, config);
  tweak?.(c.options);
  c.update();
  state.charts[id] = c;
}

// Re-render only when the markup changed, so a 5-minute refresh neither closes an open list nor re-announces a banner.
function setHtml(el, html) {
  if (el.lastHtml === html) return;
  el.lastHtml = el.innerHTML = html;
}

function empty(el, message = S().notYet) { el.innerHTML = `<p class="empty">${message}</p>`; }

/* ---------- Today ---------- */

function levelOf(pct) { return pct < 0.5 ? "none" : pct < 3 ? "low" : pct < 8 ? "moderate" : "severe"; }
const per100 = pct => (pct < 0.5 ? 0 : Math.max(1, Math.round(pct)));
const total24 = () => {
  const h = state.data.forecast?.next_24h_outage_hours;
  return Number.isFinite(h) ? S().next24Hours(S().duration(h)) : "";
};

function renderToday() {
  const { dem, gen, forecast, gas } = state.data;
  const last = lastActual(dem), lastGen = gen.at(-1);
  const pct = last.demand_mw ? 100 * (last.loadshed_mw ?? 0) / last.demand_mw : 0;
  const level = levelOf(pct);
  $("now-chip").className = `chip ${level}`;
  $("now-chip").innerHTML = svg(level === "none" ? "check" : "alert") + S().level[level];
  $("now-plain").textContent = per100(pct) ? S().nowPlain(num(per100(pct))) : S().nowAllOn;
  $("now-basis").textContent = S().nowBasis(I18N.dateTime(last.timestamp));
  $("now-sentence").textContent = (last.loadshed_mw ?? 0) > 0
    ? S().nowSentence(I18N.dateTime(last.timestamp), num(last.demand_mw), num(last.supply_mw), num(last.loadshed_mw), num(pct, 1))
    : S().nowNoShed(I18N.dateTime(last.timestamp), num(last.demand_mw));
  $("now-stats").innerHTML = [["demand", last.demand_mw, "--demand"], ["supply", last.supply_mw, "--supply"], ["loadshed", last.loadshed_mw, "--loadshed"]]
    .map(([k, v, c]) => `<div class="stat"><div class="label"><i style="background:var(${c})" aria-hidden="true"></i>${S().series[k]}</div><div class="value">${num(v)} <span class="unit">${S().mw}</span></div></div>`).join("");
  const ren = lastGen?.generation_mw ? 100 * (sum(lastGen, FUELS[2].cols) ?? 0) / lastGen.generation_mw : null;
  $("now-renewable").textContent = ren == null ? "" : S().renewableNow(num(ren, 1));

  const f = ahead(state.data).slice(0, 12);
  if (f?.length) {
    const cells = f.map(r => ({ r, pct: r.demand_mw ? 100 * r.loadshed_mw / r.demand_mw : 0 }));
    const worst = cells.reduce((a, c) => c.pct > a.pct ? c : a, cells[0]);
    $("hours-sentence").textContent = per100(worst.pct) ? S().hoursWorst(I18N.hour(worst.r.timestamp), num(per100(worst.pct))) : S().hoursCalm;
    $("hours-total").textContent = total24();
    $("hours-strip").innerHTML = cells.map(({ r, pct }) => {
      const n = per100(pct), label = S().hourCell(I18N.hour(r.timestamp), n ? num(n) : 0);
      return `<li aria-label="${esc(label)}"><span class="bar ${levelOf(pct)}" aria-hidden="true">${n ? num(n) : "✓"}</span><span class="when" aria-hidden="true">${I18N.hour(r.timestamp).split(" ").map(esc).join("<br>")}</span></li>`;
    }).join("");
  } else {
    $("hours-sentence").textContent = S().notYet;
    $("hours-strip").innerHTML = "";
  }

  renderArea();
  renderAlerts();
  $("share").innerHTML = svg("share") + esc(S().share);
  $("share").hidden = !(navigator.share || navigator.clipboard);
  $("share-done").textContent = "";
  const g = gas?.at(-1);
  $("today-gas").textContent = g ? S().gasSentence(I18N.date(g.date), num(g.power_demand_mmcfd), num(g.power_supply_mmcfd), num(100 * g.power_supply_mmcfd / g.power_demand_mmcfd)) : S().notYet;
}

function savedPlace() {
  try {
    const saved = JSON.parse(localStorage.getItem("place") ?? "null") ?? [];
    return state.places.find(p => JSON.stringify(placeKey(p)) === JSON.stringify(saved))
      ?? state.places.find(p => p.name === saved[0] && p.district === saved[1]) ?? null;
  } catch { return null; }
}

function renderAlerts() {
  const bn = I18N.lang === "bn", icon = { storm: "storm", heat: "thermo", other: "alert" }, advice = { storm: S().alertWhy, heat: S().weatherHot, other: "" };
  setHtml($("alerts"), activeAlerts(state.data.alerts, state.selected, Date.now()).map(a => `<div class="banner alert">${svg(icon[alertKind(a.event)])}<div>
      <strong>${esc(S().alertBy)}</strong>
      <p>${esc(bn && a.headline_bn ? a.headline_bn : a.headline)}</p>
      <p>${esc(S().alertUntil(I18N.dateTime(bdStamp(Date.parse(a.expires)))))} ${esc(advice[alertKind(a.event)])}${/^https:\/\//.test(a.web) ? ` <a href="${esc(a.web)}">${esc(S().alertLink)}</a>` : ""}</p>
    </div></div>`).join(""));
}

$("share")?.addEventListener("click", async () => {
  const text = S().shareText($("now-plain").textContent, ahead(state.data).length ? $("hours-sentence").textContent : ""), url = location.origin + location.pathname;
  try {
    if (navigator.share) await navigator.share({ title: S().title, text, url });
    else { await navigator.clipboard.writeText(`${text} ${url}`); $("share-done").textContent = S().shareDone; }
  } catch (e) {
    if (e.name !== "AbortError") $("share-done").textContent = `${text} ${url}`;
  }
});

function placeExtras(p) {
  const { bmd, notices } = state.data, today = bdToday(), bn = I18N.lang === "bn", local = officesFor(state.offices, p);
  const block = (icon, body) => `<div class="extra">${svg(icon)}<div>${body}</div></div>`;
  let html = "";
  const days = nearestForecast(bmd, p, today).slice(0, 2);
  if (days.length) {
    const label = d => d.date === today ? S().today : d.date === bdToday(1) ? S().tomorrow : I18N.date(d.date);
    html += block("thermo", days.map(d => `<p>${esc(S().weatherDay(label(d), num(d.max_c), num(d.min_c)))}</p>`).join("")
      + (days.some(d => d.max_c >= HOT_DAY_C) ? `<p>${esc(S().weatherHot)}</p>` : "")
      + `<p class="note">${esc(S().weatherSource(bn && days[0].station_bn ? days[0].station_bn : days[0].station))}</p>`);
  }
  const work = plannedWork(notices, p, today).slice(0, 3);
  if (work.length) {
    const district = n => { const d = state.places.find(x => x.type === "district" && x.name === n.district); return d ? (bn && d.name_bn ? d.name_bn : d.name) : ""; };
    html += block("repair", `<h3>${esc(S().plannedHeading)}</h3><ul class="plain">` + work.map(n => `<li>${esc(S().plannedRow(I18N.date(n.outage_date) + (n.outage_until > n.outage_date ? ` – ${I18N.date(n.outage_until)}` : ""), n.from_time && I18N.clock(n.from_time), n.to_time && I18N.clock(n.to_time), district(n)))}`
      + (/^https:\/\//.test(n.url ?? "") ? ` · <a href="${esc(n.url)}">${esc(S().plannedLink)}</a>` : "")
      + (bn ? `<p class="note">${esc(n.title)}</p>` : "") + "</li>").join("") + "</ul>");
  }
  html += block("phone", `<h3>${esc(S().callHeading)}</h3><div class="calls">` + hotlinesFor(p).map(h =>
    `<a class="btn" href="tel:${h.number}" aria-label="${esc(S().callLabel(S().hotlines[h.id], digits(h.number)))}"><span>${esc(S().hotlines[h.id])}</span><strong>${digits(h.number)}</strong></a>`).join("") + "</div>"
    + (local.length ? `<details class="more"><summary>${esc(S().officesHeading)}</summary><ul class="pairs">` + local.map(o =>
      `<li><span${/[\u0980-\u09ff]/.test(o.office) ? ' lang="bn"' : ""}>${esc(o.office)}<small>${esc(S().hotlines[o.utility])}</small></span><a class="tel" href="tel:${esc(o.phone)}">${digits(o.phone.length === 11 ? `${o.phone.slice(0, 5)}-${o.phone.slice(5)}` : o.phone)}</a></li>`).join("") + "</ul></details>" : ""));
  return html;
}

function renderArea() {
  const p = state.selected;
  const zs = zoneStats(state.data.zones);
  const s = p && zs?.byZone[p.zone];
  setHtml($("area-extras"), placeExtras(p));
  if (!s) { $("area-result").textContent = S().areaPick; return; }
  const bn = I18N.lang === "bn";
  const own = bn && p.name_bn ? p.name_bn : p.name;
  const within = p.upazila && p.upazila !== p.name ? (bn && p.upazila_bn ? p.upazila_bn : p.upazila) : null;
  const name = within ? `${own}, ${within}` : own;
  const text = s.rank <= 3 ? S().areaWorst : s.rank <= 6 ? S().areaMiddle : S().areaBest;
  $("area-result").innerHTML = esc(text(name, I18N.zone(p.zone), num(per100(s.share)))) + ` <a href="#map">${esc(S().nav.map)}</a>`;
}

/* ---------- search ---------- */

const norm = s => (s ?? "").toLowerCase().normalize("NFC").replace(/[০-৯]/g, d => "০১২৩৪৫৬৭৮৯".indexOf(d)).replace(/[^a-z0-9ঀ-৥ৰ-৿]/g, "");
const TYPE_ORDER = { district: 0, upazila: 1, area: 2, paurashava: 3, ward: 4, union: 5 };
const placeKey = p => [p.type, p.name, p.district, p.upazila];

function placeLabel(p) {
  const bn = I18N.lang === "bn";
  const name = bn && p.name_bn ? p.name_bn : p.name;
  const district = bn && p.district_bn ? p.district_bn : p.district;
  const upazila = p.upazila && p.upazila !== p.name ? (bn && p.upazila_bn ? p.upazila_bn : p.upazila) : null;
  return { name: esc(name), district: esc(district), upazila: upazila && esc(upazila) };
}

function buildSearch(host) {
  const id = `search-${host.dataset.search}`;
  host.innerHTML = `
    <label for="${id}">${S().searchLabel}</label>
    <input id="${id}" type="search" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="${id}-list" placeholder="${S().searchPlaceholder}">
    <ul role="listbox" id="${id}-list" hidden></ul>
    <p class="hint" id="${id}-hint" aria-live="polite"></p>`;
  const input = host.querySelector("input"), list = host.querySelector("ul"), hint = host.querySelector(".hint");
  let results = [], active = -1;

  const close = () => { list.hidden = true; input.setAttribute("aria-expanded", "false"); input.removeAttribute("aria-activedescendant"); active = -1; };
  const highlight = i => {
    active = i;
    [...list.children].forEach((li, j) => li.setAttribute("aria-selected", String(j === i)));
    if (i >= 0) { input.setAttribute("aria-activedescendant", `${id}-opt-${i}`); list.children[i].scrollIntoView({ block: "nearest" }); }
  };
  const choose = i => { const p = results[i]; if (!p) return; input.value = I18N.lang === "bn" && p.name_bn ? p.name_bn : p.name; close(); selectPlace(p, host.dataset.search === "today"); };

  input.addEventListener("input", () => {
    const q = norm(input.value);
    hint.textContent = "";
    if (q.length < 2) { close(); return; }
    const words = input.value.trim().split(/\s+/).map(norm).filter(Boolean);
    const scored = [];
    for (const p of state.places) {
      const own = [norm(p.name), norm(p.name_bn)];
      const around = [p.upazila, p.upazila_bn, p.district, p.district_bn].map(norm);
      let score = own.some(n => n.startsWith(q)) ? 0 : own.some(n => n.includes(q)) ? 1
        : [around[0], around[1]].some(n => n.startsWith(q)) ? 2 : 3;
      if (score === 3 && words.length > 1) {
        const first = words.slice(0, -1).join(""), last = words.at(-1);
        const nameHit = own.some(n => n.startsWith(first)) || own.some(n => n.startsWith(q.slice(0, -last.length)));
        if (nameHit && around.some(n => n.startsWith(last))) score = 0;
      }
      if (score < 3) scored.push({ p, score });
    }
    results = scored.sort((a, b) => a.score - b.score || TYPE_ORDER[a.p.type] - TYPE_ORDER[b.p.type]).slice(0, 8).map(r => r.p);
    if (!results.length) { close(); hint.textContent = S().noMatch; return; }
    list.innerHTML = results.map((p, i) => {
      const { name, district, upazila } = placeLabel(p);
      const where = [esc(S().types[p.type]), p.type === "district" ? "" : upazila ? `${upazila}, ${district}` : district, zoneName(p.zone)].filter(Boolean).join(" · ");
      return `<li role="option" id="${id}-opt-${i}" aria-selected="false">${name}<small>${where}</small></li>`;
    }).join("");
    [...list.children].forEach((li, i) => li.addEventListener("mousedown", e => { e.preventDefault(); choose(i); }));
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    highlight(-1);
  });
  input.addEventListener("keydown", e => {
    if (list.hidden) return;
    if (e.key === "ArrowDown") { e.preventDefault(); highlight(Math.min(active + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); highlight(Math.max(active - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); choose(active < 0 ? 0 : active); }
    else if (e.key === "Escape") close();
  });
  input.addEventListener("blur", () => setTimeout(close, 150));
}

function selectPlace(place, stay = false) {
  state.selected = place;
  remember("place", JSON.stringify(placeKey(place)));
  if (stay) { renderArea(); renderAlerts(); return; }
  if (location.hash !== "#map") location.hash = "#map"; else renderMapTab();
}

/* ---------- Map ---------- */

function ensureMap() {
  if (typeof L === "undefined") return Promise.resolve();
  return state.mapReady ??= setupMap().catch(e => { state.mapReady = null; throw e; });
}
async function setupMap() {
  state.districts = await load("static/geo/districts.geojson");
  const map = L.map("map", { zoomSnap: 0.25, attributionControl: false, scrollWheelZoom: false }).setView([23.7, 90.3], 6.5);
  L.control.attribution({ prefix: false }).addAttribution("geoBoundaries (CC BY 3.0 IGO) · © OpenStreetMap contributors").addTo(map);
  state.map = map;
}

function shade(share, max) {
  return `rgba(${css("--loadshed-rgb")}, ${(0.1 + 0.9 * Math.min(1, share / max)).toFixed(3)})`;
}

async function renderMapTab() {
  const zs = zoneStats(state.data.zones);
  renderZoneList(zs);
  await ensureMap();
  if (!state.map) return;
  state.map.invalidateSize();
  const max = Math.max(1, ...(zs?.list ?? []).map(s => s.share));
  $("map-max").textContent = num(per100(max));
  state.layers.districts?.remove();
  state.layers.districts = L.geoJSON(state.districts, {
    style: f => ({ color: css("--card"), weight: 1, fillOpacity: 1, fillColor: zs?.byZone[f.properties.zone] ? shade(zs.byZone[f.properties.zone].share, max) : css("--map-empty") }),
    onEachFeature: (f, layer) => {
      const name = esc(I18N.lang === "bn" && f.properties.name_bn ? f.properties.name_bn : f.properties.name);
      const s = zs?.byZone[f.properties.zone];
      layer.bindTooltip(`${name} · ${zoneName(f.properties.zone)}${s ? ` · ${esc(S().zoneRow(num(per100(s.share))))}` : ""}`, { sticky: true });
      layer.on("click", () => { const p = state.places.find(p => p.type === "district" && p.name === f.properties.name); if (p) selectPlace(p); });
    },
  }).addTo(state.map);
  if (!state.selected && !state.refreshing) state.map.fitBounds(state.layers.districts.getBounds(), { padding: [8, 8] });
  await renderPlace(zs);
}

async function renderPlace(zs) {
  const card = $("place-card"), p = state.selected;
  state.layers.selected?.remove();
  if (!p) { card.hidden = true; $("desco-card").hidden = true; return; }
  const { name, district, upazila } = placeLabel(p);
  const zone = zoneName(p.zone), s = zs?.byZone[p.zone];
  const where = p.type === "district" ? S().districtIn(district, zone) : upazila ? S().placeInUpazila(name, upazila, district, zone) : S().placeIn(name, district, zone);
  let html = `<h2>${name}</h2><p class="big">${where}</p>`;
  if (s?.latest) html += `<p>${S().zoneLatest(I18N.date(s.latest.date), num(per100(100 * s.latest.loadshed_mw / s.latest.demand_mw)))}</p>`;
  if (s) html += `<p>${S().zone30(num(per100(s.share)), S().rank(s.rank))}</p>`;
  html += `<p class="note">${S().mapZoneLevel}${p.evidence === "inferred" ? " " + S().inferred : ""}${p.type === "ward" ? " " + S().wardNote : ""}</p>`;
  setHtml(card, html + placeExtras(p));
  card.hidden = false;
  renderDesco(p);

  if (!state.map) return;
  let geometry;
  if (p.type === "district") geometry = state.districts.features.find(f => f.properties.name === p.name);
  else if (p.upazila) {
    state.upazilas ??= await load("static/geo/upazilas.geojson");
    geometry = state.upazilas.features.find(f => f.properties.name === p.upazila && f.properties.district === p.district);
  }
  const group = L.featureGroup();
  if (geometry) L.geoJSON(geometry, { style: { color: css("--fg"), weight: 3, fill: false } }).addTo(group);
  if (p.type !== "district" && p.type !== "upazila") {
    L.circleMarker([p.lat, p.lon], { radius: 9, color: css("--card"), weight: 3, fillColor: css("--accent"), fillOpacity: 1 }).addTo(group);
  }
  state.layers.selected = group.addTo(state.map);
  if (!state.refreshing && group.getLayers().length) {
    state.map.fitBounds(group.getBounds(), { maxZoom: p.type === "district" ? 9 : 12, padding: [24, 24] });
  }
}

async function renderDesco(p) {
  const card = $("desco-card");
  card.hidden = true;
  if (!DESCO_DISTRICTS.includes(p.district)) return;
  state.desco = await (state.descoLoading ??= load("data/desco_schedule.json").catch(() => null));
  if (state.selected !== p || !state.desco?.feeders?.length || daysOld(state.desco.as_of) > OLD_DAYS.desco) return;
  $("desco-note").textContent = S().descoNote(I18N.date(state.desco.as_of));
  card.hidden = false;
  descoResults();
}

function descoResults() {
  const q = $("desco-q").value, found = descoSearch(state.desco?.feeders, q);
  $("desco-results").innerHTML = found.map(f => {
    const cuts = cutWindows(f.hours).map(([a, b]) => I18N.window(a, b)).join(", ");
    return `<li><strong>${esc(f.feeder)}</strong> <span class="note">${esc(f.division)}</span><p class="note">${esc(f.areas)}</p><p>${esc(cuts ? S().descoCuts(cuts) : S().descoNoCuts)}</p></li>`;
  }).join("") || (q.trim().length >= 3 ? `<li class="note">${esc(S().descoNone)}</li>` : "");
}
$("desco-q")?.addEventListener("input", descoResults);

function renderZoneList(zs) {
  const ul = $("zone-list");
  if (!zs) { empty(ul); return; }
  const max = Math.max(1, ...zs.list.map(s => s.share));
  ul.innerHTML = zs.list.map(s => `<li><button type="button" data-zone="${esc(s.zone)}">${zoneName(s.zone)}</button><span class="row-note">${S().zoneRow(num(per100(s.share)))}</span><span class="bar" aria-hidden="true"><span style="width:${(100 * s.share / max).toFixed(1)}%"></span></span></li>`).join("");
  ul.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    const p = state.places.find(p => p.type === "district" && p.zone === b.dataset.zone && p.evidence === "verified");
    if (p) selectPlace(p);
  }));
}

/* ---------- Why ---------- */

function renderIdle() {
  const plants = state.data.plants, idle = plants?.length && daysOld(plants[0].date) <= OLD_DAYS.plants ? idleSummary(plants) : null;
  $("idle-card").hidden = !idle;
  if (!idle) return;
  const date = I18N.date(plants[0].date), lost = idle.reasons.reduce((a, r) => a + r.mw, 0), max = idle.reasons[0].mw;
  $("idle-sentence").textContent = S().idleSentence(date, num(idle.plants), num(lost));
  setHtml($("idle-reasons"), idle.reasons.map(r => `<details class="reason"><summary>
      <span class="ricon ${r.reason}">${svg(r.reason)}</span><span class="rname">${esc(S().reasons[r.reason])}</span>
      <span class="rcount">${esc(S().idleRow(num(r.count), num(r.mw)))}</span>
      ${svg("chevron")}<span class="bar" aria-hidden="true"><span class="${r.reason}" style="width:${(100 * r.mw / max).toFixed(1)}%"></span></span>
    </summary><ul class="pairs">${r.plants.sort((a, b) => b.lost_mw - a.lost_mw).map(p =>
      `<li><span>${esc(p.plant)}<small>${esc([p.remark, p.restart && S().idleRestart(p.restart)].filter(Boolean).join(" · "))}</small></span><strong>${num(p.lost_mw)} ${S().mw}</strong></li>`).join("")}</ul></details>`).join(""));
  $("idle-source").textContent = S().idleSource(date);
}

function renderImports() {
  const row = state.data.gen.findLast(r => r.generation_mw != null), now = importsNow(row);
  $("imports-card").hidden = !now;
  if (!now) return;
  $("imports-sentence").textContent = now.mw > 0 ? S().importsSentence(num(now.mw), num(now.oneIn)) : S().importsNone;
  $("imports-lines").innerHTML = FUELS[3].cols.filter(c => row[c] > 0).map(c => `<li><span>${esc(S().importLines[c])}</span><strong>${num(row[c])} ${S().mw}</strong></li>`).join("");
  $("imports-source").textContent = S().importsSource(I18N.dateTime(row.timestamp));
}

function renderWhy() {
  const { gas, bpdb, capacity, gen, prices } = state.data;
  renderIdle();
  renderImports();
  const g = gas?.at(-1);
  $("gas-sentence").textContent = g ? S().gasSentence(I18N.date(g.date), num(g.power_demand_mmcfd), num(g.power_supply_mmcfd), num(100 * g.power_supply_mmcfd / g.power_demand_mmcfd)) : S().notYet;
  const b = bpdb?.at(-1);
  const lost = b ? CAUSES.reduce((a, [k]) => a + (b[k] ?? 0), 0) : 0;
  $("causes-sentence").textContent = lost ? S().causesSentence(I18N.date(b.date), num(Math.round(10 * ((b.gas_limit_mw ?? 0) + (b.coal_limit_mw ?? 0)) / lost)), num(Math.round(10 * (b.maintenance_mw ?? 0) / lost))) : S().notYet;
  const cap = capacityRows(capacity, gen);
  $("capacity-sentence").textContent = cap ? S().capacitySentence(Math.round(2 * cap.installed / cap.output) / 2, num(100 * cap.rows[0].output / cap.rows[0].installed)) : S().notYet;
  const costRows = (bpdb ?? []).filter(r => r.energy_mkwh && r.cost_total_bdt);
  const lastCost = costRows.at(-1);
  $("cost-sentence").textContent = lastCost ? S().costSentence(num(lastCost.cost_total_bdt / (lastCost.energy_mkwh * 1e6), 2), I18N.date(lastCost.date)) : S().notYet;
  if (prices?.length) {
    const latest = Object.values(Object.fromEntries(prices.map(p => [p.product, p]))).filter(p => PLANT_FUELS.includes(p.product));
    $("fuel-prices").innerHTML = `<thead><tr><th scope="col">${S().table.fuel}</th><th scope="col">${S().table.price}</th><th scope="col">${S().table.since}</th></tr></thead><tbody>` +
      latest.map(p => `<tr><td>${esc(S().fuels[p.product] ?? p.product)}</td><td>${num(p.price_bdt, 2)}</td><td>${I18N.date(p.effective_date)}</td></tr>`).join("") + "</tbody>";
  }
  const has = { gas: gas?.length, causes: bpdb?.length, capacity: cap, cost: costRows.length };
  document.querySelectorAll("#why details[data-chart]").forEach(d => (d.hidden = !has[d.dataset.chart]));
  document.querySelectorAll("#why details[open]").forEach(d => renderDetail(d.dataset.chart));
}

function capacityRows(capacity, gen) {
  if (!capacity?.length) return null;
  const asOf = capacity.map(r => r.as_of).sort().at(-1);
  const installed = Object.fromEntries(capacity.filter(r => r.as_of === asOf).map(r => [r.fuel, r.installed_mw]));
  const lastDay = gen.filter(onHour).slice(-24);
  const rows = FUELS.map(f => ({ key: f.key, installed: CAPACITY[f.key].reduce((a, k) => a + (installed[k] ?? 0), 0), output: mean(lastDay.map(r => sum(r, f.cols))) }));
  return { rows, installed: rows.reduce((a, r) => a + r.installed, 0), output: rows.reduce((a, r) => a + (r.output ?? 0), 0) };
}

function gasChart(id) {
  const gas = state.data.gas;
  if (!gas?.length) return;
  const shortFill = `rgba(${css("--loadshed-rgb")}, 0.3)`;
  const rows = gas.slice(-365);
  chart(id, { type: "line", data: { labels: rows.map(r => r.date), datasets: [
      line(S().series.needed, rows.map(r => r.power_demand_mmcfd), css("--demand")),
      line(S().series.delivered, rows.map(r => r.power_supply_mmcfd), css("--supply"), { fill: { target: 0, above: "transparent", below: shortFill } }),
    ] }, options: baseOptions({ unit: "MMCFD", months: true }) });
}

function renderDetail(name) {
  const { gas, bpdb, capacity, gen, forecast } = state.data;
  if (name === "alldata") renderDataCharts();
  if (name === "gas" && gas?.length) gasChart("c-gas");
  if (name === "causes" && bpdb?.length) {
    const rows = bpdb.slice(-90);
    chart("c-causes", { type: "bar", data: { labels: rows.map(r => I18N.date(r.date)), datasets: CAUSES.map(([k, label, color]) => ({
      label: S().series[label], data: rows.map(r => r[k]), backgroundColor: css(color), borderColor: css("--card"), borderWidth: { top: 2 }, borderSkipped: false, stack: "c",
    })) }, options: baseOptions() }, o => { o.scales.x.stacked = o.scales.y.stacked = true; });
  }
  if (name === "capacity") {
    const cap = capacityRows(capacity, gen);
    if (cap) chart("c-capacity", { type: "bar", data: { labels: cap.rows.map(r => S().series[r.key]), datasets: [
      { label: S().series.installed, data: cap.rows.map(r => r.installed), backgroundColor: css("--installed"), borderRadius: 3 },
      { label: S().series.output, data: cap.rows.map(r => r.output), backgroundColor: css("--supply"), borderRadius: 3 },
    ] }, options: { ...baseOptions({ horizontal: true }), indexAxis: "y" } }, o => { o.scales.x.ticks.callback = v => num(v); o.scales.y.ticks.callback = (_, i) => S().series[cap.rows[i].key]; o.scales.y.grid = { display: false }; });
  }
  if (name === "cost" && bpdb?.length) {
    const rows = bpdb.filter(r => r.energy_mkwh && r.cost_total_bdt);
    chart("c-cost", { type: "line", data: { labels: rows.map(r => r.date), datasets: [line(S().series.cost, rows.map(r => r.cost_total_bdt / (r.energy_mkwh * 1e6)), css("--demand"))] },
      options: baseOptions({ months: true, format: v => `৳${num(v, 2)}` }) }, o => { o.scales.y.beginAtZero = false; });
  }
  if (name === "month" && forecast?.next_days?.length) {
    const f = forecast.next_days, band = `rgba(${css("--demand-rgb")}, 0.18)`;
    chart("c-month", { type: "line", data: { labels: f.map(r => I18N.date(r.date)), datasets: [
      line("low", f.map(r => r.demand_low_mw), "transparent", { hideInTooltip: true, pointHoverRadius: 0 }),
      line(S().series.range, f.map(r => r.demand_high_mw), "transparent", { fill: { target: 0, above: band, below: band }, hideInTooltip: true, pointHoverRadius: 0 }),
      line(S().series.demand, f.map(r => r.demand_peak_mw), css("--demand"), { borderDash: [6, 4] }),
      line(S().series.bestSupply, f.map(r => r.supply_peak_mw), css("--supply")),
    ] }, options: baseOptions() }, o => { o.scales.y.beginAtZero = false; });
  }
}

document.addEventListener("toggle", e => { if (e.target.matches?.("details[data-chart]") && e.target.open) renderDetail(e.target.dataset.chart); }, true);

/* ---------- Forecast ---------- */

function renderForecast24() {
  const { dem, forecast } = state.data;
  const f = ahead(state.data);
  if (!f?.length) { $("f24-sentence").textContent = S().notYet; $("f24-blocks").innerHTML = ""; return; }
  const worst = f.reduce((a, r) => r.loadshed_mw > a.loadshed_mw ? r : a, f[0]);
  const worstPct = 100 * worst.loadshed_mw / worst.demand_mw;
  $("f24-sentence").textContent = per100(worstPct) ? S().nextWorst(I18N.hour(worst.timestamp), num(per100(worstPct))) : S().nextCalm;
  $("f24-total").textContent = total24();

  const upTo = lastActual(dem).timestamp, past = dem.filter(r => onHour(r) && r.timestamp <= upTo).slice(-24), join = past.length - 1, last = past.at(-1);
  const labels = [...past, ...f].map(r => r.timestamp);
  const pad = n => Array(n).fill(null);
  const band = `rgba(${css("--demand-rgb")}, 0.18)`;
  $("c-f24").setAttribute("aria-label", $("f24-sentence").textContent);
  chart("c-f24", { type: "bar", data: { labels, datasets: [
    { type: "line", ...line("low", [...pad(join), last.demand_mw, ...f.map(r => r.demand_low_mw)], "transparent", { hideInTooltip: true, pointHoverRadius: 0 }) },
    { type: "line", ...line(S().series.range, [...pad(join), last.demand_mw, ...f.map(r => r.demand_high_mw)], "transparent", { fill: { target: 0, above: band, below: band }, hideInTooltip: true, pointHoverRadius: 0 }) },
    { type: "line", ...line(S().series.demand, [...past.map(r => r.demand_mw), ...pad(f.length)], css("--demand")) },
    { type: "line", ...line(`${S().series.demand} (${S().series.forecast})`, [...pad(join), last.demand_mw, ...f.map(r => r.demand_mw)], css("--demand"), { borderDash: [6, 4] }) },
    { type: "line", ...line(S().series.supply, [...past.map(r => r.supply_mw), ...pad(f.length)], css("--supply")) },
    { type: "line", ...line(`${S().series.supply} (${S().series.forecast})`, [...pad(join), last.supply_mw, ...f.map(r => r.supply_mw)], css("--supply"), { borderDash: [6, 4] }) },
    { label: S().series.loadshed, data: [...past.map(r => r.loadshed_mw), ...f.map(r => r.loadshed_mw)], backgroundColor: css("--loadshed"), borderRadius: 2, categoryPercentage: 1, barPercentage: 0.7, yAxisID: "y" },
  ] }, options: baseOptions() }, o => {
    o.scales.x.ticks.autoSkip = false;
    o.scales.x.ticks.callback = (_, i) => i % 3 === 0 ? I18N.hour(labels[i]) : null;
    o.plugins.tooltip.callbacks.title = items => I18N.dateTime(labels[items[0].dataIndex]) + (items[0].dataIndex > join ? ` · ${S().series.forecast}` : "");
  });

  const blocks = [];
  for (let i = 0; i < f.length; i += 3) {
    const part = f.slice(i, i + 3), shed = mean(part.map(r => r.loadshed_mw)), demand = mean(part.map(r => r.demand_mw));
    const end = new Date(bdDate(part.at(-1).timestamp).getTime() + 36e5);
    const endTs = new Date(end.getTime() + 6 * 36e5).toISOString().slice(0, 16);
    const pct = 100 * shed / demand, level = levelOf(pct);
    const from = I18N.hour(part[0].timestamp), to = I18N.hour(endTs);
    blocks.push(`<li><span class="chip ${level}">${S().level[level]}</span><span>${per100(pct) ? S().block(from, to, num(per100(pct))) : S().blockNone(from, to)}</span></li>`);
  }
  $("f24-blocks").innerHTML = blocks.join("");
  const sc = forecast.next_hours_score, b = forecast.bpdb_score;
  $("f24-sure").textContent = [sc?.days ? S().nextSure(num(sc.demand_mape_pct, 1), num(sc.loadshed_mae_mw)) : "",
    b?.days ? S().bpdbSure(num(b.eve_peak_demand_mape_pct, 1), num(b.days)) : ""].filter(Boolean).join(" ");
}

/* ---------- Outlook ---------- */

function renderOutlook() {
  const f = state.data.forecast?.next_days;
  if (!f?.length) { $("outlook-sentence").textContent = S().notYet; $("outlook-days").innerHTML = ""; return; }
  const risk = r => r.demand_peak_mw > r.supply_peak_mw ? "likely" : r.demand_high_mw > r.supply_peak_mw ? "possible" : "unlikely";
  const likely = f.filter(r => risk(r) === "likely").length, possible = f.filter(r => risk(r) !== "unlikely").length;
  const likelyDays = f.filter(r => risk(r) === "likely");
  const likelyHours = likelyDays.map(r => r.outage_hours).filter(Number.isFinite);
  const span = likelyHours.length ? S().durationRange(S().duration(Math.min(...likelyHours)), S().duration(Math.max(...likelyHours))) : "";
  const clock = h => I18N.hour(`2026-01-01T${String(h % 24).padStart(2, "0")}:00`);
  const windows = likelyDays.filter(r => Number.isFinite(r.cut_from) && Number.isFinite(r.cut_to)).map(r => `${r.cut_from}-${r.cut_to}`);
  const common = windows.sort((a, b) => windows.filter(w => w === b).length - windows.filter(w => w === a).length)[0];
  const [from, to] = common ? common.split("-").map(Number) : [];
  $("outlook-sentence").textContent = likely ? S().outlookLikely(num(likely), span, common ? clock(from) : "", common ? clock(to) : "") : S().outlookNone(num(possible));
  $("outlook-range").textContent = `${I18N.date(f[0].date)} – ${I18N.date(f.at(-1).date)}`;
  $("outlook-days").innerHTML = f.map(r => {
    const k = risk(r);
    const time = k !== "unlikely" && Number.isFinite(r.outage_hours) && r.outage_hours >= 0.25 ? S().dayHours(S().duration(r.outage_hours)) : "";
    const when = k !== "unlikely" && Number.isFinite(r.cut_from) && Number.isFinite(r.cut_to) ? I18N.window(r.cut_from, r.cut_to) : "";
    const full = [I18N.date(r.date), S().risk[k], time, when].filter(Boolean).join(" · ");
    return `<li class="${k}${r.weather === "normal" ? " typical" : ""}" tabindex="0" data-tip="${esc(full)}" aria-label="${esc(full)}"><div class="d">${esc(I18N.dayCard(r.date))}</div><div>${esc(S().riskShort[k])}</div><div class="h">${esc(time)}</div><div class="w">${esc(when)}</div></li>`;
  }).join("");
  const sc = state.data.forecast.next_days_score;
  $("outlook-sure").textContent = [sc?.outage_hours_mae != null ? S().hoursSure(num(sc.outage_hours_mae, 1)) : "",
    sc?.window_hit_pct != null ? S().windowSure(num(Math.round(sc.window_hit_pct / 10))) : "", S().averageNote].filter(Boolean).join(" ");
  document.querySelectorAll("#outlook details[open]").forEach(d => renderDetail(d.dataset.chart));
}

/* ---------- Data ---------- */

function renderBill() {
  const tariff = state.data?.tariff, units = Number($("bill-units").value), b = bill(units, tariff);
  $("bill-result").textContent = b ? S().billResult(num(units), num(b.total)) : S().billEmpty;
  $("bill-bar").innerHTML = (b?.parts ?? []).map((p, i) => `<span class="s${i}" style="flex:${p.amount}"></span>`).join("");
  $("bill-parts").innerHTML = (b?.parts ?? []).map((p, i) => `<li><span><i class="s${i}" aria-hidden="true"></i>${esc(S().billPart(num(p.units), num(p.rate, 2)))}</span><strong>৳${num(p.amount, p.amount % 1 ? 2 : 0)}</strong></li>`).join("");
  const n = b?.next;
  $("bill-next").textContent = !n ? "" : n.lifeline ? S().billLifeline(num(n.unitsLeft), num(units + n.unitsLeft))
    : n.unitsLeft === 0 ? S().billEdge(num(n.nextRate, 2)) : S().billNext(num(n.unitsLeft), num(n.rate, 2), num(n.nextRate, 2));
}
for (const id of ["bill-units", "bill-slider"]) {
  $(id)?.addEventListener("input", e => {
    $("bill-units").value = $("bill-slider").value = e.target.value;
    remember("units", e.target.value);
    renderBill();
  });
}

function renderCosts() {
  const { tariff, prices } = state.data;
  $("bill-card").hidden = !tariff?.length;
  if (tariff?.length) {
    if (!$("bill-units").value) {
      let saved = null;
      try { saved = localStorage.getItem("units"); } catch { /* private mode */ }
      $("bill-units").value = $("bill-slider").value = saved ?? 150;
    }
    $("bill-slider").setAttribute("aria-label", S().billLabel);
    $("bill-note").textContent = S().billNote(I18N.month(tariff[0].effective), num(tariff[0].demand_bdt_kw));
    renderBill();
  }
  const latest = Object.fromEntries((prices ?? []).map(p => [p.product, p]));
  const shown = HOME_FUELS.map(k => latest[k]).filter(Boolean);
  $("prices-card").hidden = !shown.length;
  $("prices").innerHTML = shown.map(p => `<li><span class="name">${esc(S().fuels[p.product])}</span><strong>৳${num(p.price_bdt, p.price_bdt % 1 ? 2 : 0)}</strong><span class="note">${esc(S().perUnit[p.unit] ?? p.unit)} · ${esc(S().priceSince(I18N.date(p.effective_date)))}</span></li>`).join("");
}

function renderData() {
  renderCosts();
  if ($("all-data").open) renderDataCharts();
}

function renderDataCharts() {
  const { dem, gen, forecast } = state.data;
  const days = daily(gen, dem);
  const weekFrom = bdDate(dem.at(-1).timestamp) - 7 * 864e5;
  const week = dem.filter(r => onHour(r) && bdDate(r.timestamp) > weekFrom);
  chart("c-week", { type: "line", data: { labels: week.map(r => I18N.dateTime(r.timestamp)), datasets: [
    line(S().series.demand, week.map(r => r.demand_mw), css("--demand")),
    line(S().series.supply, week.map(r => r.supply_mw), css("--supply"), { fill: { target: 0, above: "transparent", below: `rgba(${css("--loadshed-rgb")}, 0.35)` } }),
  ] }, options: baseOptions() }, o => { o.scales.y.beginAtZero = false; o.scales.x.ticks.autoSkip = false;
    o.scales.x.ticks.callback = (_, i) => week[i].timestamp.endsWith("T00:00") ? I18N.dayCard(week[i].timestamp.slice(0, 10)) : null; });

  const last30 = days.slice(-30);
  $("mix-legend").innerHTML = FUELS.map(f => `<li><i style="background:var(--${f.key})"></i>${S().series[f.key]}</li>`).join("");
  chart("c-mix", { type: "bar", data: { labels: last30.map(d => I18N.date(d.date)), datasets: FUELS.map(f => ({
    label: S().series[f.key], data: last30.map(d => d.mix[f.key]), backgroundColor: css(`--${f.key}`), borderColor: css("--card"), borderWidth: { top: 2 }, borderSkipped: false, stack: "m",
  })) }, options: baseOptions() }, o => { o.scales.x.stacked = o.scales.y.stacked = true; });

  const year = days.slice(-366);
  chart("c-share", { type: "line", data: { labels: year.map(d => d.date), datasets: [
    line(S().series.renewable, year.map(d => d.renewable), css("--renewable")), line(S().series.imports, year.map(d => d.imports), css("--imports")),
  ] }, options: baseOptions({ pct: true, months: true }) });

  const shedDays = year.filter(d => d.peakShed != null);
  chart("c-peak", { type: "bar", data: { labels: shedDays.map(d => d.date), datasets: [{ label: S().series.loadshed, data: shedDays.map(d => d.peakShed), backgroundColor: css("--loadshed"), borderRadius: 2, categoryPercentage: 1, barPercentage: 0.8 }] },
    options: baseOptions({ months: true }) });

  gasChart("c-gas-data");
  renderHeatmap(dem);
  const t = S().table;
  $("daily").innerHTML = `<thead><tr><th scope="col">${t.date}</th><th scope="col">${t.demand}</th><th scope="col">${t.peak}</th><th scope="col">${t.renewable}</th><th scope="col">${t.imports}</th></tr></thead><tbody>` +
    days.slice(-14).reverse().map(d => `<tr><td>${I18N.date(d.date)}</td><td>${num(d.demand)}</td><td>${num(d.peakShed)}</td><td>${num(d.renewable, 1)}%</td><td>${num(d.imports, 1)}%</td></tr>`).join("") + "</tbody>";

  const h = forecast?.next_hours_score, m = forecast?.next_days_score, b = forecast?.bpdb_score;
  $("accuracy").textContent = [
    h?.days ? S().nextSure(num(h.demand_mape_pct, 1), num(h.loadshed_mae_mw)) : "",
    m?.origins ? S().outlookSure(num(m.demand_mape_pct, 1), num(m.band_low_mw), num(m.band_high_mw)) : "",
    b?.days ? S().bpdbSure(num(b.eve_peak_demand_mape_pct, 1), num(b.days)) : "",
  ].filter(Boolean).join(" ");
}

function renderHeatmap(dem) {
  const cells = new Map();
  for (const r of dem) {
    if (r.loadshed_mw == null || !r.demand_mw) continue;
    const key = r.timestamp.slice(0, 13), pct = 100 * r.loadshed_mw / r.demand_mw;
    cells.set(key, Math.max(cells.get(key) ?? 0, pct));
  }
  const dates = [...new Set(dem.map(r => r.timestamp.slice(0, 10)))].sort().slice(-30).reverse();
  const max = Math.max(1, ...cells.values());
  const rgb = css("--loadshed-rgb"), hh = h => String(h).padStart(2, "0");
  let html = "<span></span>" + [...Array(24)].map((_, h) => `<span class="hour">${h % 6 === 0 ? esc(I18N.hour(`2026-01-01T${hh(h)}:00`)) : ""}</span>`).join("");
  for (const d of dates) {
    html += `<span class="day">${esc(I18N.dayCard(d))}</span>`;
    for (let h = 0; h < 24; h++) {
      const pct = cells.get(`${d}T${hh(h)}`);
      const when = `${I18N.date(d)}, ${I18N.hour(`${d}T${hh(h)}:00`)}`;
      const text = esc(pct == null ? S().heatMissing(when) : S().heatCell(when, per100(pct) ? num(per100(pct)) : 0));
      html += pct == null ? `<span class="cell none" role="img" tabindex="0" data-tip="${text}" aria-label="${text}"></span>`
        : `<span class="cell" role="img" tabindex="0" data-tip="${text}" aria-label="${text}" style="background:rgba(${rgb},${(0.08 + 0.92 * pct / max).toFixed(3)})"></span>`;
    }
  }
  $("heat").innerHTML = html;
}

const tip = $("tip");
function showTip(e) {
  const t = e.target.closest?.("[data-tip]");
  if (!t) { tip.style.display = "none"; return; }
  tip.textContent = t.dataset.tip;
  tip.style.display = "block";
  const box = t.getBoundingClientRect();
  tip.style.left = Math.min(innerWidth - tip.offsetWidth - 8, Math.max(8, box.left + box.width / 2 - tip.offsetWidth / 2)) + "px";
  tip.style.top = Math.max(8, box.top - tip.offsetHeight - 6) + "px";
}
document.addEventListener("pointerover", showTip);
document.addEventListener("focusin", showTip);

/* ---------- status ---------- */

function renderStale() {
  const { dem, gen } = state.data;
  const latest = [dem.at(-1)?.timestamp, gen.at(-1)?.timestamp].filter(Boolean).sort().at(-1);
  const age = latest ? (Date.now() - bdDate(latest)) / 36e5 : Infinity;
  $("stale").hidden = age <= STALE_HOURS;
  $("stale").textContent = S().stale(latest ? I18N.dateTime(latest) : "–");
}

async function renderStatus() {
  const updated = state.loadedAt ? " " + S().updated(I18N.dateTime(new Date(state.loadedAt + 6 * 36e5).toISOString().slice(0, 16))) : "";
  try {
    const r = await fetch("api/status", { cache: "no-store" });
    if (!r.ok) throw new Error("no status endpoint");
    const s = await r.json();
    const ago = s.live_checked_at ? Math.max(0, Math.round(s.server_time - s.live_checked_at)) : null;
    $("status").textContent = (s.live_error ? S().unreachable(s.live_error)
      : ago == null ? "" : S().checked(ago < 60 ? S().seconds(num(ago)) : S().minutes(num(Math.round(ago / 60))))) + updated;
  } catch { $("status").textContent = updated.trim(); }
}

/* ---------- boot ---------- */

const REFRESH_MS = 5 * 60 * 1000;

async function refreshData() {
  const [gen, dem] = await Promise.all([load("data/generation.csv"), load("data/demand.csv")]);
  const names = ["zones.csv", "bpdb_daily.csv", "gas.csv", "capacity.csv", "fuel_prices.csv", "forecast.json",
    "plants.csv", "tariff.csv", "alerts.json", "bmd_forecast.csv", "nesco_notices.csv"];
  const [zones, bpdb, gas, capacity, prices, forecast, plants, tariff, alerts, bmd, notices] = (await Promise.allSettled(names.map(n => load(`data/${n}`)))).map(r => r.status === "fulfilled" ? r.value : null);
  if (!state.places.length) {
    [state.places, state.offices] = await Promise.all(["places", "offices"].map(n => load(`static/geo/${n}.json`).catch(() => [])));
    state.selected ??= savedPlace();
  }
  const first = !state.data;
  state.data = { gen, dem, zones, bpdb, gas, capacity, prices, forecast, plants, tariff, alerts, bmd, notices };
  state.loadedAt = Date.now();
  if (first) renderAll(); else redraw();
}

async function renderTab(id) {
  if (id === "today") renderToday();
  if (id === "map") await renderMapTab();
  if (id === "why") renderWhy();
  if (id === "forecast") { renderForecast24(); renderOutlook(); }
  if (id === "data") renderData();
}

async function redraw() {
  destroyCharts();
  renderStale();
  renderStatus();
  state.refreshing = true;
  try { await renderTab(state.tab); } finally { state.refreshing = false; }
}

function renderAll() {
  destroyCharts();
  applyStatic();
  if (!state.data) return;
  renderStale();
  renderStatus();
  renderTab(state.tab);
}

(async () => {
  let lang = null;
  try { lang = localStorage.getItem("lang"); } catch { /* private mode */ }
  I18N.lang = lang === "bn" ? "bn" : "en";
  state.tab = TABS.some(t => t.id === tabFromHash(location.hash.slice(1))) ? tabFromHash(location.hash.slice(1)) : "today";
  applyStatic();
  showTab(state.tab, false);
  try {
    await refreshData();
  } catch (err) {
    $("stale").hidden = false;
    $("stale").textContent = S().loadError(err.message);
  }
  setInterval(() => { if (!document.hidden) refreshData().catch(() => {}); }, REFRESH_MS);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && Date.now() - (state.loadedAt ?? 0) > REFRESH_MS) refreshData().catch(() => {});
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", e => {
    let saved = null;
    try { saved = localStorage.getItem("theme"); } catch { /* private mode */ }
    if (!saved) { document.documentElement.dataset.theme = e.matches ? "dark" : "light"; renderAll(); }
  });
})();
