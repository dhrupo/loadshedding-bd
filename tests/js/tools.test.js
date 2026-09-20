const test = require("node:test");
const assert = require("node:assert/strict");
const T = require("../../static/tools.js");

test("idle plants are grouped by reason, biggest loss first", () => {
  const s = T.idleSummary([
    { plant: "A", reason: "gas", lost_mw: 100 }, { plant: "B", reason: "repair", lost_mw: 500 },
    { plant: "C", reason: "gas", lost_mw: 50 }, { plant: "D", reason: "coal", lost_mw: 20 },
  ]);
  assert.equal(s.plants, 4);
  assert.deepEqual(s.reasons.map(r => [r.reason, r.count, r.mw]), [["repair", 1, 500], ["gas", 2, 150], ["coal", 1, 20]]);
  assert.deepEqual(s.reasons[1].plants.map(p => p.plant), ["A", "C"]);
});

test("no plant rows means no summary", () => {
  assert.equal(T.idleSummary([]), null);
  assert.equal(T.idleSummary(null), null);
});

test("hotlines: the utilities that serve a place, then the national line", () => {
  const ids = place => T.hotlinesFor(place).map(h => h.id);
  assert.deepEqual(ids({ zone: "Rajshahi", district: "Bogra" }), ["nesco", "breb", "national"]);
  assert.deepEqual(ids({ zone: "Dhaka", district: "Dhaka" }), ["dpdc", "desco", "breb", "national"]);
  assert.deepEqual(ids({ zone: "Dhaka", district: "Narayanganj" }), ["dpdc", "breb", "national"]);
  assert.deepEqual(ids({ zone: "Dhaka", district: "Gazipur" }), ["desco", "breb", "national"]);
  assert.deepEqual(ids({ zone: "Dhaka", district: "Manikganj" }), ["breb", "national"]);
  assert.deepEqual(ids({ zone: "Khulna", district: "Faridpur" }), ["wzpdcl", "breb", "national"]);
  assert.deepEqual(ids({ zone: "Sylhet", district: "Sylhet" }), ["bpdb", "breb", "national"]);
  assert.equal(T.hotlinesFor({ zone: "Barisal", district: "Bhola" })[0].number, "16117");
});

test("hotlines: without a place only the national line is offered", () => {
  assert.deepEqual(T.hotlinesFor(null).map(h => h.number), ["16999"]);
});

const TARIFF = [
  { kind: "lifeline", from_units: 0, to_units: 50, rate_bdt: 4.63 }, { kind: "slab", from_units: 0, to_units: 75, rate_bdt: 5.26 },
  { kind: "slab", from_units: 76, to_units: 200, rate_bdt: 8.5 }, { kind: "slab", from_units: 201, to_units: 300, rate_bdt: 9.1 },
  { kind: "slab", from_units: 301, to_units: 400, rate_bdt: 9.62 }, { kind: "slab", from_units: 401, to_units: 600, rate_bdt: 15.01 },
  { kind: "slab", from_units: 601, to_units: null, rate_bdt: 17.35 },
];

test("bill: units are charged slab by slab", () => {
  const b = T.bill(150, TARIFF);
  assert.equal(b.total, 1032);
  assert.deepEqual(b.parts.map(p => [p.units, p.rate, p.amount]), [[75, 5.26, 394.5], [75, 8.5, 637.5]]);
  assert.equal(T.bill(700, TARIFF).total, 8066);
});

test("bill: 50 units or fewer pay the lifeline rate on everything", () => {
  assert.equal(T.bill(40, TARIFF).total, 185.2);
  assert.equal(T.bill(51, TARIFF).total, 268.26);
});

test("bill: says how many units are left before the rate goes up", () => {
  assert.deepEqual(T.bill(63, TARIFF).next, { unitsLeft: 12, rate: 5.26, nextRate: 8.5 });
  assert.deepEqual(T.bill(40, TARIFF).next, { unitsLeft: 10, rate: 4.63, nextRate: 5.26, lifeline: true });
  assert.equal(T.bill(900, TARIFF).next, null);
});

test("bill: nothing sensible to say without units or a tariff", () => {
  assert.equal(T.bill(0, TARIFF), null);
  assert.equal(T.bill(-5, TARIFF), null);
  assert.equal(T.bill(100, []), null);
});

const ALERTS = [
  { id: "a", status: "Actual", msg_type: "Alert", cancels: [], effective: "2026-09-10T04:00:00+00:00", expires: "2026-09-11T04:00:00+00:00", districts: ["Bagerhat", "Chittagong"] },
  { id: "b", status: "Actual", msg_type: "Alert", cancels: [], effective: "2026-08-06T03:00:00+00:00", expires: "2026-08-07T03:00:00+00:00", districts: ["Dhaka"] },
];

test("alerts: only warnings still in force, and only for the chosen district", () => {
  const now = Date.parse("2026-09-10T12:00:00+06:00");
  assert.deepEqual(T.activeAlerts(ALERTS, { district: "Chittagong" }, now).map(a => a.id), ["a"]);
  assert.deepEqual(T.activeAlerts(ALERTS, { district: "Dhaka" }, now), []);
  assert.deepEqual(T.activeAlerts(ALERTS, null, now).map(a => a.id), ["a"]);
  assert.deepEqual(T.activeAlerts(ALERTS, null, Date.parse("2026-09-12T00:00:00+06:00")), []);
  assert.deepEqual(T.activeAlerts(null, null, now), []);
});

test("weather: the nearest BMD station's days from today on", () => {
  const rows = [
    { date: "2026-09-19", station: "Sylhet", lat: 24.9, lon: 91.88, max_c: 30, min_c: 25 },
    { date: "2026-09-20", station: "Sylhet", lat: 24.9, lon: 91.88, max_c: 31, min_c: 25 },
    { date: "2026-09-21", station: "Sylhet", lat: 24.9, lon: 91.88, max_c: 33, min_c: 26 },
    { date: "2026-09-20", station: "Dhaka", lat: 23.77, lon: 90.38, max_c: 35, min_c: 27 },
  ];
  const near = T.nearestForecast(rows, { lat: 24.7, lon: 91.7 }, "2026-09-20");
  assert.deepEqual(near.map(r => [r.station, r.date]), [["Sylhet", "2026-09-20"], ["Sylhet", "2026-09-21"]]);
  assert.deepEqual(T.nearestForecast(rows, { lat: 24.7, lon: 91.7 }, "2026-09-25"), []);
  assert.deepEqual(T.nearestForecast(null, { lat: 1, lon: 1 }, "2026-09-20"), []);
});

test("imports: how much of the power right now comes from India and Nepal", () => {
  const row = { generation_mw: 14000, india_bheramara_hvdc: 900, india_tripura: 100, india_adani: 1000, nepal: null };
  assert.deepEqual(T.importsNow(row), { mw: 2000, oneIn: 7 });
  assert.equal(T.importsNow(undefined), null);
});

const FEEDERS = [
  { division: "Agargaon", areas: "LGED, Somaj Sheba, Agargaon Govt. School", feeder: "Samaj Sheba", hours: [10, 16, 22] },
  { division: "Pallabi", areas: "Mirpur 11, Block C, Kalshi Road", feeder: "Kalshi", hours: [9, 10, 11, 20] },
  { division: "Uttara East", areas: "Sector 4, Sector 6", feeder: "Sector-4", hours: [] },
];

test("desco: find feeders by any word in their area, feeder or office name", () => {
  assert.deepEqual(T.descoSearch(FEEDERS, "kalshi").map(f => f.feeder), ["Kalshi"]);
  assert.deepEqual(T.descoSearch(FEEDERS, "Mirpur  11").map(f => f.feeder), ["Kalshi"]);
  assert.deepEqual(T.descoSearch(FEEDERS, "agargaon school").map(f => f.feeder), ["Samaj Sheba"]);
  assert.deepEqual(T.descoSearch(FEEDERS, "gulshan"), []);
  assert.deepEqual(T.descoSearch(FEEDERS, "a"), []);
});

test("desco: back-to-back hours are read as one cut", () => {
  assert.deepEqual(T.cutWindows([9, 10, 11, 20]), [[9, 12], [20, 21]]);
  assert.deepEqual(T.cutWindows([23]), [[23, 24]]);
  assert.deepEqual(T.cutWindows([]), []);
});

const NOTICES = [
  { outage_date: "2026-09-19", district: "Rajshahi", zone: "Rajshahi", title: "r" },
  { outage_date: "2026-09-22", district: "Bogra", zone: "Rajshahi", title: "b" },
  { outage_date: "2026-09-21", district: "Rangpur", zone: "Rangpur", title: "g" },
  { outage_date: "", district: "", zone: "", title: "undated" },
];

test("planned work: coming shutdowns in the place's region, its own district first", () => {
  const place = { zone: "Rajshahi", district: "Bogra" };
  assert.deepEqual(T.plannedWork(NOTICES, place, "2026-09-19").map(n => n.title), ["b", "r"]);
  assert.deepEqual(T.plannedWork(NOTICES, place, "2026-09-20").map(n => n.title), ["b"]);
  assert.deepEqual(T.plannedWork(NOTICES, { zone: "Dhaka", district: "Dhaka" }, "2026-09-19"), []);
  assert.deepEqual(T.plannedWork(null, place, "2026-09-19"), []);
});

const OFFICES = [
  { utility: "nesco", office: "বিক্রয় ও বিতরণ বিভাগ-১, রাজশাহী", phone: "01321124509", district: "Rajshahi" },
  { utility: "nesco", office: "বিক্রয় ও বিতরণ বিভাগ, পাবনা", phone: "02588845030", district: "Pabna" },
  { utility: "nesco", office: "বিক্রয় ও বিতরণ বিভাগ-১, চাঁপাইনবাবগঞ্জ", phone: "01700000001", district: "Nawabganj" },
  { utility: "nesco", office: "বিদ্যুৎ সরবরাহ ইউনিট, শিবগঞ্জ, চাঁপাইনবাবগঞ্জ", phone: "01700000002", district: "Nawabganj" },
  { utility: "nesco", office: "বিদ্যুৎ সরবরাহ ইউনিট, ফুলবাড়ী", phone: "01700000003", district: "?" },
  { utility: "desco", office: "পল্লবী বিক্রয় ও বিতরণ বিভাগ", phone: "01324435990", district: "Dhaka" },
  { utility: "dpdc", office: "Adabor", phone: "01766675038", district: "Dhaka" },
  { utility: "dpdc", office: "Banglabazar", phone: "01700000004", district: "" },
  { utility: "wzpdcl", office: "বিক্রয় ও বিতরণ বিভাগ-১, খুলনা", phone: "01711297972", district: "Khulna" },
];

test("offices: the local office named after the place, else its upazila, else its district", () => {
  const phones = place => T.officesFor(OFFICES, place).map(o => o.phone);
  assert.deepEqual(phones({ zone: "Rajshahi", district: "Rajshahi", district_bn: "রাজশাহী", name: "Rajshahi", name_bn: "রাজশাহী" }), ["01321124509"]);
  assert.deepEqual(phones({ zone: "Dhaka", district: "Dhaka", district_bn: "ঢাকা", upazila: "Pallabi", upazila_bn: "পল্লবী", name: "Mirpur 11", name_bn: "মিরপুর ১১" }), ["01324435990"]);
  assert.deepEqual(phones({ zone: "Dhaka", district: "Dhaka", district_bn: "ঢাকা", upazila: "Adabor", upazila_bn: "আদাবর", name: "Adabor", name_bn: "আদাবর" }), ["01766675038"]);
});

test("offices: another utility's office is never offered, and no match means none", () => {
  assert.deepEqual(T.officesFor(OFFICES, { zone: "Sylhet", district: "Khulna", district_bn: "খুলনা", name: "Khulna", name_bn: "খুলনা" }), []);
  assert.deepEqual(T.officesFor(OFFICES, { zone: "Rajshahi", district: "Natore", district_bn: "নাটোর", name: "Natore", name_bn: "নাটোর" }), []);
  assert.deepEqual(T.officesFor(null, { zone: "Rajshahi", district: "Rajshahi" }), []);
  assert.deepEqual(T.officesFor(OFFICES, null), []);
});

test("offices: a town that shares its name with one in another district never gets that district's office", () => {
  const phones = place => T.officesFor(OFFICES, place).map(o => o.phone);
  assert.deepEqual(phones({ zone: "Rangpur", district: "Dinajpur", district_bn: "দিনাজপুর", upazila: "Nawabganj", upazila_bn: "নবাবগঞ্জ", name: "Nawabganj", name_bn: "নবাবগঞ্জ" }), []);
  assert.deepEqual(phones({ zone: "Rajshahi", district: "Bogra", district_bn: "বগুড়া", upazila: "Shibganj", upazila_bn: "শিবগঞ্জ", name: "Shibganj", name_bn: "শিবগঞ্জ" }), []);
  assert.deepEqual(phones({ zone: "Rajshahi", district: "Nawabganj", district_bn: "চাঁপাইনবাবগঞ্জ", upazila: "Shibganj", upazila_bn: "শিবগঞ্জ", name: "Shibganj", name_bn: "শিবগঞ্জ" }), ["01700000002"]);
});

test("offices: an office whose district is unclear is never offered, one with no district only by its own name", () => {
  const phones = place => T.officesFor(OFFICES, place).map(o => o.phone);
  assert.deepEqual(phones({ zone: "Rangpur", district: "Dinajpur", district_bn: "দিনাজপুর", upazila: "Fulbari", upazila_bn: "ফুলবাড়ী", name: "Fulbari", name_bn: "ফুলবাড়ী" }), []);
  assert.deepEqual(phones({ zone: "Dhaka", district: "Dhaka", district_bn: "ঢাকা", upazila: "Kotwali", upazila_bn: "কোতোয়ালী", name: "Banglabazar", name_bn: "বাংলাবাজার" }), ["01700000004"]);
  assert.deepEqual(phones({ zone: "Dhaka", district: "Dhaka", district_bn: "ঢাকা", upazila: "Kotwali", upazila_bn: "কোতোয়ালী", name: "Kotwali", name_bn: "কোতোয়ালী" }), []);
});

test("alerts: tests, drafts, cancellations and the warnings they withdraw are never shown", () => {
  const now = Date.parse("2026-09-10T12:00:00+06:00"), live = { ...ALERTS[0] };
  const ids = list => T.activeAlerts(list, null, now).map(a => a.id);
  assert.deepEqual(ids([{ ...live, status: "Test" }]), []);
  assert.deepEqual(ids([{ ...live, status: "Exercise" }]), []);
  assert.deepEqual(ids([live, { ...live, id: "c", msg_type: "Cancel", cancels: ["a"] }]), []);
  assert.deepEqual(ids([live, { ...live, id: "u", msg_type: "Update", cancels: ["a"] }]), ["u"]);
});

test("alerts: a warning that names no district is shown to everyone", () => {
  const now = Date.parse("2026-09-10T12:00:00+06:00");
  assert.deepEqual(T.activeAlerts([{ ...ALERTS[0], districts: [] }], { district: "Rangpur" }, now).map(a => a.id), ["a"]);
});

test("alerts: the advice matches the kind of weather", () => {
  assert.deepEqual(["Wind", "Rain", "Thunderstorm", "Tropical Cyclone"].map(T.alertKind), ["storm", "storm", "storm", "storm"]);
  assert.deepEqual(["Heat Wave", "High Temperature"].map(T.alertKind), ["heat", "heat"]);
  assert.deepEqual(["Landslide", "Fog", "Cold Wave", "", undefined].map(T.alertKind), ["other", "other", "other", "other", "other"]);
});

test("imports: missing figures are not reported as zero imports", () => {
  assert.equal(T.importsNow({ generation_mw: 14000, india_adani: null, nepal: null }), null);
  assert.deepEqual(T.importsNow({ generation_mw: 14000, india_adani: 0, india_tripura: 0 }), { mw: 0, oneIn: null });
});

test("desco: a feeder that has the words side by side comes before one that merely contains them", () => {
  const feeders = [
    { division: "Uttara East", areas: "Sec-03, Road-2,4,7", feeder: "Sector-3 East", hours: [] },
    { division: "Uttara East", areas: "Sector-04, Road-1 to 9", feeder: "Lake", hours: [] },
  ];
  assert.deepEqual(T.descoSearch(feeders, "sector 4").map(f => f.feeder), ["Lake", "Sector-3 East"]);
});

test("planned work: a two-day shutdown stays listed on its second day", () => {
  const notices = [{ outage_date: "2026-07-18", outage_until: "2026-07-19", district: "Rajshahi", zone: "Rajshahi", title: "two days" }];
  const place = { zone: "Rajshahi", district: "Rajshahi" };
  assert.equal(T.plannedWork(notices, place, "2026-07-19").length, 1);
  assert.equal(T.plannedWork(notices, place, "2026-07-20").length, 0);
});
