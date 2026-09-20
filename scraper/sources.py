#!/usr/bin/env python3
"""Scrape the linked sources: BPDB zone demand/loadshed, BPC fuel prices, SREDA installed capacity.

Same rules as pgb.py: values as published, blanks stay blank, a changed layout is an error.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
import re
import sys
import time
import unicodedata

from pgb import BD_TIME, BN_DIGITS, ROOT, get, number, read_csv, write_csv

ZONES_URL = "https://misc.bpdb.gov.bd/area-wise-demand?date={:%d-%m-%Y}"
FUEL_URL = "https://bpc.gov.bd/pages/static-pages/6922ddb6933eb65569e15fbc"
CAPACITY_URL = "https://www.renewableenergy.gov.bd/index.php?id=7"
TARIFF_URL = "https://dpdc.gov.bd/pages/static-pages/6922de6f933eb65569e1a9c4"

FUEL_PRODUCTS = {"ডিজেল": "diesel", "ফার্নেস অয়েল": "furnace_oil", "এলডিও": "ldo", "কেরোসিন": "kerosene",
                 "অকটেন": "octane", "পেট্রোল": "petrol", "এলপি গ্যাস (১২.৫০ কেজি প্রতি সিলিন্ডার)": "lpg_12_5kg"}
CAPACITY_FUELS = ["Coal", "Gas", "HFO", "HSD", "Imported", "Renewable", "Captive"]
BN_MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self.row = []
            self.tables[-1].append(self.row)
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(unicodedata.normalize("NFC", " ".join("".join(self.cell).split())))
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def tables(html: str) -> list[list[list[str]]]:
    parser = _Tables()
    parser.feed(html)
    return parser.tables


def find_table(html: str, header: list[str], name: str) -> list[list[str]] | None:
    for table in tables(html):
        if table and table[0] == header:
            return table[1:]
    return None


def parse_zones(html: str, day: str) -> list[dict]:
    if "Data not found" in html:
        return []
    body = find_table(html, ["Sl", "Zone Name", "Demand (MW)", "Load shed (MW)"], "zones")
    if body is None:
        raise ValueError("BPDB zones: table layout changed")
    return [{"date": day, "zone": zone, "demand_mw": number(demand), "loadshed_mw": number(shed)}
            for sl, zone, demand, shed in (r for r in body if len(r) == 4 and r[0].isdigit())]


def bn_date(text: str) -> str:
    d, m, y = text.translate(BN_DIGITS).strip().split("/")
    return f"{y}-{int(m):02d}-{int(d):02d}"


def parse_fuel_prices(html: str) -> list[dict]:
    names = {unicodedata.normalize("NFC", k): v for k, v in FUEL_PRODUCTS.items()}
    body = find_table(html, [unicodedata.normalize("NFC", h) for h in ("নং", "পণ্যের নাম", "স্থানীয় বিক্রয় মূল্য", "কার্যকরের তারিখ")], "fuel")
    if body is None:
        raise ValueError("BPC fuel prices: table layout changed")
    rows = [{"effective_date": bn_date(r[3]), "product": names[r[1]], "price_bdt": float(number(re.split(r"[ /]", r[2])[0])),
             "unit": "cylinder" if "সিলিন্ডার" in r[2] else "litre"}
            for r in body if len(r) == 4 and r[1] in names]
    if len(rows) != len(names):
        raise ValueError(f"BPC fuel prices: expected {len(names)} products, got {len(rows)}")
    return rows


def parse_tariff(html: str) -> list[dict]:
    """Home (LT-A) slabs from the retail tariff table; the same BERC order applies to every utility."""
    nfc = lambda t: unicodedata.normalize("NFC", t)
    table = next((t for t in tables(html) if len(t) > 1 and len(t[1]) == 2 and nfc("এলটি") in t[1][1] and nfc("আবাসিক") in t[1][1]), None)
    month = re.search(nfc(r"বিল মাস (\S+?), ([০-৯]{4})"), nfc(html))
    if table is None or not month or month.group(1) not in [nfc(m) for m in BN_MONTHS]:
        raise ValueError("DPDC tariff: home slabs or effective month not found")
    effective = f"{month.group(2).translate(BN_DIGITS)}-{[nfc(m) for m in BN_MONTHS].index(month.group(1)) + 1:02d}"
    rows, demand = [], None
    for row in table[2:]:
        if row[0].translate(BN_DIGITS).isdigit():
            break
        units = [int(n) for n in re.findall(r"\d+", row[0].translate(BN_DIGITS))]
        if not units or len(row) < 2 or number(row[1]) is None:
            raise ValueError(f"DPDC tariff: unreadable slab row {row}")
        demand = float(number(row[2])) if len(row) > 2 else demand
        rows.append({"effective": effective, "kind": "lifeline" if nfc("লাইফ") in row[0] else "slab", "from_units": units[0],
                     "to_units": units[1] if len(units) > 1 else "", "rate_bdt": float(number(row[1])), "demand_bdt_kw": demand})
    if len(rows) < 2 or demand is None:
        raise ValueError("DPDC tariff: slab rows not found")
    return rows


def parse_capacity(html: str, as_of: str) -> list[dict]:
    body = find_table(html, ["Fuel/Resource", "Installed Capacity", "Share"], "capacity")
    if body is None:
        raise ValueError("SREDA capacity: table layout changed")
    found = {r[0]: float(number(r[1].split()[0])) for r in body if r and r[0] in CAPACITY_FUELS}
    if list(found) != CAPACITY_FUELS:
        raise ValueError(f"SREDA capacity: fuels changed: {list(found)}")
    return [{"as_of": as_of, "fuel": fuel.lower(), "installed_mw": mw} for fuel, mw in found.items()]


def append_if_changed(existing: list[dict], snapshot: list[dict], key: str) -> list[dict]:
    strip = lambda rows: [{k: str(v) for k, v in r.items() if k != key} for r in rows]
    latest = max((r[key] for r in existing), default=None)
    if latest and strip([r for r in existing if r[key] == latest]) == strip(snapshot):
        return existing
    return existing + snapshot


def merge_by(existing: list[dict], new: list[dict], keys: tuple[str, ...]) -> list[dict]:
    rows = {tuple(r[k] for k in keys): r for r in existing}
    rows.update((tuple(r[k] for k in keys), r) for r in new)
    return [rows[k] for k in sorted(rows)]


def days_to_fetch(have: set[str], today: date, days: int, recheck: int = 7) -> list[date]:
    """New days after the latest saved one, plus any day still missing from the last `recheck` days."""
    if not have:
        start = today - timedelta(days=days)
    else:
        start = min(date.fromisoformat(max(have)) + timedelta(days=1), today - timedelta(days=recheck))
    return [d for d in (start + timedelta(days=i) for i in range((today - start).days + 1)) if d.isoformat() not in have]


def update_zones(days: int, delay: float) -> None:
    path = ROOT / "data" / "zones.csv"
    existing = read_csv(path)
    wanted = days_to_fetch({r["date"] for r in existing}, datetime.now(BD_TIME).date(), days)
    new = []
    for day in wanted:
        try:
            new += parse_zones(get(ZONES_URL.format(day)), day.isoformat())
        except OSError as e:
            print(f"zones {day}: {e}")
        time.sleep(delay)
    write_csv(path, merge_by(existing, new, ("date", "zone")), ["date", "zone", "demand_mw", "loadshed_mw"])
    print(f"zones: {len(new)} rows from {len(wanted)} days checked")


def update_fuel_prices() -> None:
    path = ROOT / "data" / "fuel_prices.csv"
    new = parse_fuel_prices(get(FUEL_URL))
    write_csv(path, merge_by(read_csv(path), new, ("effective_date", "product")),
              ["effective_date", "product", "price_bdt", "unit"])
    print(f"fuel_prices: {len(new)} current prices")


def update_tariff() -> None:
    write_csv(ROOT / "data" / "tariff.csv", parse_tariff(get(TARIFF_URL)),
              ["effective", "kind", "from_units", "to_units", "rate_bdt", "demand_bdt_kw"])
    print("tariff: checked")


def update_capacity() -> None:
    path = ROOT / "data" / "capacity.csv"
    snapshot = parse_capacity(get(CAPACITY_URL), datetime.now(BD_TIME).date().isoformat())
    write_csv(path, append_if_changed(read_csv(path), snapshot, "as_of"), ["as_of", "fuel", "installed_mw"])
    print("capacity: checked")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365, help="zone history to backfill when zones.csv is empty")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    errors = update(args.days, args.delay)
    for error in errors:
        print(error, file=sys.stderr)
    sys.exit(1 if errors else 0)


def update(days: int = 365, delay: float = 1.0) -> list[str]:
    errors = []
    for job in (lambda: update_zones(days, delay), update_fuel_prices, update_capacity, update_tariff):
        try:
            job()
        except (ValueError, OSError) as e:
            errors.append(str(e))
    return errors


if __name__ == "__main__":
    main()
