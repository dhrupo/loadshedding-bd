function idleSummary(plants) {
  if (!plants?.length) return null;
  const groups = {};
  for (const p of plants) {
    const g = groups[p.reason] ??= { reason: p.reason, count: 0, mw: 0, plants: [] };
    g.count += 1; g.mw += p.lost_mw ?? 0; g.plants.push(p);
  }
  return { plants: plants.length, reasons: Object.values(groups).sort((a, b) => b.mw - a.mw) };
}

// Short codes from the Power Division circular of 18 Sep 2026.
const HOTLINES = { national: "16999", dpdc: "16116", desco: "16120", breb: "16899", nesco: "16603", wzpdcl: "16117", bpdb: "16200" };
const ZONE_UTILITY = { Rajshahi: "nesco", Rangpur: "nesco", Khulna: "wzpdcl", Barisal: "wzpdcl", Chittagong: "bpdb", Comilla: "bpdb", Mymensingh: "bpdb", Sylhet: "bpdb" };
const DHAKA_CITY = { Dhaka: ["dpdc", "desco"], Narayanganj: ["dpdc"], Gazipur: ["desco"] };

function hotlinesFor(place) {
  const town = !place ? [] : place.zone === "Dhaka" ? DHAKA_CITY[place.district] ?? [] : [ZONE_UTILITY[place.zone]].filter(Boolean);
  return [...town, ...(place ? ["breb"] : []), "national"].map(id => ({ id, number: HOTLINES[id] }));
}

function bill(units, tariff) {
  const lifeline = tariff?.find(t => t.kind === "lifeline"), slabs = tariff?.filter(t => t.kind === "slab") ?? [];
  if (!(units > 0) || !slabs.length) return null;
  const money = x => Math.round(x * 100) / 100;
  if (lifeline && units <= lifeline.to_units) {
    return { total: money(units * lifeline.rate_bdt), parts: [{ units, rate: lifeline.rate_bdt, amount: money(units * lifeline.rate_bdt) }],
      next: { unitsLeft: lifeline.to_units - units, rate: lifeline.rate_bdt, nextRate: slabs[0].rate_bdt, lifeline: true } };
  }
  const parts = [];
  let next = null;
  slabs.forEach((s, i) => {
    const start = Math.max(1, s.from_units), used = Math.min(units, s.to_units ?? Infinity) - start + 1;
    if (used <= 0) return;
    parts.push({ units: used, rate: s.rate_bdt, amount: money(used * s.rate_bdt) });
    next = s.to_units != null && units <= s.to_units && slabs[i + 1] ? { unitsLeft: s.to_units - units, rate: s.rate_bdt, nextRate: slabs[i + 1].rate_bdt } : null;
  });
  return { total: money(parts.reduce((a, p) => a + p.amount, 0)), parts, next };
}

function activeAlerts(alerts, place, now) {
  const withdrawn = new Set((alerts ?? []).flatMap(a => a.cancels ?? []));
  return (alerts ?? []).filter(a => a.status === "Actual" && a.msg_type !== "Cancel" && !withdrawn.has(a.id) && Date.parse(a.expires) > now
    && (!place || !a.districts.length || a.districts.includes(place.district)));
}

function alertKind(event) {
  return /wind|rain|storm|cyclone|thunder|squall|lightning|tornado/i.test(event ?? "") ? "storm" : /heat|temperature/i.test(event ?? "") ? "heat" : "other";
}

function nearestForecast(rows, place, today) {
  const ahead = (rows ?? []).filter(r => r.date >= today);
  if (!ahead.length || place?.lat == null) return [];
  const far = r => (r.lat - place.lat) ** 2 + (r.lon - place.lon) ** 2;
  const station = ahead.reduce((a, r) => (far(r) < far(a) ? r : a)).station;
  return ahead.filter(r => r.station === station).sort((a, b) => a.date.localeCompare(b.date));
}

const IMPORT_COLS = ["india_bheramara_hvdc", "india_tripura", "india_adani", "nepal"];

function importsNow(row) {
  const known = IMPORT_COLS.map(c => row?.[c]).filter(v => v != null);
  if (!known.length || !row.generation_mw) return null;
  const mw = known.reduce((a, v) => a + v, 0);
  return { mw, oneIn: mw > 0 ? Math.round(row.generation_mw / mw) : null };
}

const plain = s => (s ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\b0+(?=\d)/g, "").trim();

function descoSearch(feeders, query) {
  const asked = plain(query), words = asked.split(" ").filter(Boolean);
  if (asked.length < 3) return [];
  const text = f => ` ${plain(`${f.areas} ${f.feeder} ${f.division}`)}`;
  return (feeders ?? []).filter(f => words.every(w => text(f).includes(` ${w}`)))
    .sort((a, b) => text(b).includes(` ${asked}`) - text(a).includes(` ${asked}`)).slice(0, 8);
}

function cutWindows(hours) {
  const windows = [];
  for (const h of hours ?? []) {
    if (windows.length && windows.at(-1)[1] === h) windows.at(-1)[1] = h + 1; else windows.push([h, h + 1]);
  }
  return windows;
}

function plannedWork(notices, place, today) {
  return (notices ?? []).filter(n => place && n.zone === place.zone && (n.outage_until || n.outage_date) >= today)
    .sort((a, b) => (b.district === place.district) - (a.district === place.district) || a.outage_date.localeCompare(b.outage_date));
}

const phrase = s => ` ${(s ?? "").toLowerCase().normalize("NFC").replace(/[^a-z\u0980-\u09ff]+/g, " ").trim()} `;

function officesFor(offices, place) {
  if (!place) return [];
  const utilities = hotlinesFor(place).map(h => h.id);
  const mine = (offices ?? []).filter(o => utilities.includes(o.utility) && (o.district === place.district || o.district === ""));
  for (const names of [[place.name, place.name_bn], [place.upazila, place.upazila_bn], [place.district, place.district_bn]]) {
    const keys = names.map(phrase).filter(k => k.length >= 6);
    const found = mine.filter(o => keys.some(k => phrase(o.office).includes(k)));
    if (found.length) return found.slice(0, 6);
  }
  return [];
}

if (typeof module !== "undefined") module.exports = { idleSummary, hotlinesFor, bill, activeAlerts, alertKind, nearestForecast, importsNow, descoSearch, cutWindows, plannedWork, officesFor };
