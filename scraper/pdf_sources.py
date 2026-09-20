#!/usr/bin/env python3
"""Scrape the daily PDF sources: BPDB daily generation report and Petrobangla gas report.

Each value is read by its printed label. A missing label is an error, never a guess.
A day that fails to parse is reported and skipped; the run then exits non-zero so it is noticed.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import io
from pathlib import Path
import re
import sys
import time
import urllib.error

import pdfplumber

from pgb import BD_TIME, ROOT, fetch, get, read_csv, write_csv
from sources import days_to_fetch, merge_by

BPDB_URL = "https://misc.bpdb.gov.bd/storage/daily_entry/{:%Y-%m-%d}.pdf"
PETROBANGLA_LIST = ('https://petrobangla.org.bd/pages/reports?filters='
                    '%7B%22reports_type%22:%226922d2b181fc96cef9e99f16%22%7D&page={}')
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

NUM = r"(-?[\d.]+)"
BPDB_ACTUAL = {
    "eve_peak_demand_mw": r"Max\. Demand at eve\. peak \(Generation end\)\s*:\s*" + NUM,
    "eve_peak_generation_mw": r"Evening-peak Generation \(Generation end\)\s*:\s*" + NUM,
    "eve_peak_loadshed_mw": r"Evening Peak Load-shed \(Sub-station end\)\s*:\s*" + NUM,
    "gas_limit_mw": r"Gas/LF limitation\s*:\s*" + NUM,
    "coal_limit_mw": r"Coal supply Limitation\s*:\s*" + NUM,
    "water_limit_mw": r"Low water level in Kaptai lake\s*:\s*" + NUM,
    "maintenance_mw": r"Plants under shut down/ maintenance\s*:\s*" + NUM,
    "energy_mkwh": r"Total Energy \(Generation \+ Import\)\s*:\s*" + NUM,
    "gas_supplied_mmcfd": r"Total Gas Supplied\s*:\s*" + NUM,
    "max_temp_c": r"(?<!Probable )Maximum Temperature:\s*" + NUM,
    "cost_gas_bdt": r"\(a\) Gas = " + NUM,
    "cost_oil_bdt": r"\(b\) Oil = " + NUM,
    "cost_coal_bdt": r"\(c\) Coal = " + NUM,
    "cost_renewable_bdt": r"\(d\) Renewable " + NUM,
    "cost_import_bdt": r"\(e\)\s*Import= " + NUM,
    "cost_total_bdt": r"Import= [\d.]+\s*Taka Total = " + NUM,
}
BPDB_FORECAST = {
    "eve_peak_demand_mw": r"Probable Maximum Demand at Evening Peak:\s*" + NUM,
    "eve_peak_generation_mw": r"Probable Maximum Generation at Evening Peak:\s*" + NUM,
    "max_temp_c": r"Probable Maximum Temperature:\s*" + NUM,
}
BPDB_ACTUAL_COLUMNS = ["date", *BPDB_ACTUAL]
BPDB_FORECAST_COLUMNS = ["date", *BPDB_FORECAST]
GAS_COLUMNS = ["date", "production_capacity_mmcfd", "production_mmcfd", "rlng_mmcfd",
               "power_demand_mmcfd", "power_supply_mmcfd", "fertilizer_demand_mmcfd",
               "fertilizer_supply_mmcfd", "others_supply_mmcfd", "total_supply_mmcfd"]


def pdf_text(source) -> str:
    try:
        with pdfplumber.open(io.BytesIO(source) if isinstance(source, bytes) else source) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        raise ValueError(f"unreadable PDF: {type(e).__name__}: {e}") from e


def pdf_tables(source) -> list[list[str]]:
    try:
        with pdfplumber.open(io.BytesIO(source) if isinstance(source, bytes) else source) as pdf:
            return [[" ".join((cell or "").split()) for cell in row]
                    for page in pdf.pages for table in page.extract_tables() for row in table]
    except Exception as e:
        raise ValueError(f"unreadable PDF: {type(e).__name__}: {e}") from e


def as_number(text: str):
    value = float(text)
    return int(value) if value.is_integer() and "." not in text else value


def extract(text: str, patterns: dict, name: str) -> dict:
    values = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"{name}: label for {key} not found")
        values[key] = as_number(match.group(1))
    return values


def parse_bpdb_daily(text: str) -> tuple[dict, dict]:
    actual_day = re.search(r"\(C\) Actual data of (\d{2})\.(\d{2})\.(\d{2})", text)
    forecast_day = re.search(r"\(D\) Forecast of (\d{2})-(\d{2})-(\d{4})", text)
    if not actual_day or not forecast_day:
        raise ValueError("BPDB daily: report dates not found")
    d, m, y = forecast_day.groups()
    report_day = date(int(y), int(m), int(d))
    day_before = report_day - timedelta(days=1)
    # BPDB often prints the wrong year here (e.g. 31.12.24 on the 01-01-2026 report); trust the report date.
    if actual_day.group(1, 2) != (f"{day_before.day:02d}", f"{day_before.month:02d}"):
        raise ValueError(f"BPDB daily: actual data {'.'.join(actual_day.groups())} is not the day before {report_day}")
    actual = {"date": day_before.isoformat(), **extract(text, BPDB_ACTUAL, "BPDB daily")}
    forecast = {"date": report_day.isoformat(),
                **{k: float(v) for k, v in extract(text, BPDB_FORECAST, "BPDB forecast").items()}}
    return actual, forecast


def _reason(remark: str, shut_down: bool) -> str:
    text = remark.lower()
    if shut_down:
        return "repair"
    return next((key for key, words in (("gas", ("gas",)), ("coal", ("coal",)), ("water", ("water",)),
                                        ("oil", ("fuel", "oil", "hfo", "hsd"))) if any(w in text for w in words)), "other")


def parse_bpdb_plants(source, day: str) -> list[dict]:
    """Plants that lost output on `day`: the last four columns are fuel-limited MW, shut-down MW, remark, restart date."""
    rows = []
    for row in pdf_tables(source):
        if "Gross Total" in row[0]:
            break
        if len(row) < 13 or "Total" in row[0] or not row[1]:
            continue
        *mw, remark, restart = row[-4:]
        try:
            limited, shut = (as_number(cell.replace(",", "")) if cell else 0 for cell in mw)
        except ValueError:
            continue
        if limited + shut > 0:
            rows.append({"date": day, "plant": re.sub(r"^[a-z]\) ", "", row[1]), "reason": _reason(remark, shut > limited),
                         "lost_mw": limited + shut, "remark": remark, "restart": restart})
    if not rows:
        raise ValueError("BPDB daily: no plant rows found")
    return rows


def period_start(text: str) -> str:
    match = re.search(r"Date\s*:\s*(\d{1,2})\s*([A-Za-z]+)?\s*-\s*\d{1,2}\s*([A-Za-z]+)\s*,\s*(\d{4})", text)
    if not match or match.group(3)[:3].title() not in MONTHS or (match.group(2) and match.group(2)[:3].title() not in MONTHS):
        raise ValueError("Petrobangla: report date not found")
    day, start_month, end_month, year = match.groups()
    month = MONTHS[(start_month or end_month)[:3].title()]
    year = int(year) - (1 if month == 12 and MONTHS[end_month[:3].title()] == 1 else 0)
    return f"{year}-{month:02d}-{int(day):02d}"


def parse_petrobangla(text: str) -> dict:
    production = re.search(r"Grand Total \(1\+2\+3\+4\+5\):\s*\d+\s+" + NUM + r"\s+" + NUM, text)
    lng = re.search(r"RPGCL \(R-LNG\)\s+" + NUM + r"\s+" + NUM, text)
    total = re.search(r"Total :" + r"\s+([\d.]+)" * 6, text)
    if not (production and lng and total):
        raise ValueError("Petrobangla: production, R-LNG or distribution total not found")
    power_d, power_s, fert_d, fert_s, others, supply = map(float, total.groups())
    return {
        "date": period_start(text),
        "production_capacity_mmcfd": as_number(production.group(1)),
        "production_mmcfd": as_number(production.group(2)),
        "rlng_mmcfd": as_number(lng.group(2)),
        "power_demand_mmcfd": power_d, "power_supply_mmcfd": power_s,
        "fertilizer_demand_mmcfd": fert_d, "fertilizer_supply_mmcfd": fert_s,
        "others_supply_mmcfd": others, "total_supply_mmcfd": supply,
    }


def petrobangla_links(html: str) -> list[str]:
    return re.findall(r'href="(https://[^"]+/office-petrobangla/[^"]+\.pdf)"', html)


def update_bpdb(days: int, delay: float, errors: list) -> None:
    actual_path, forecast_path = ROOT / "data" / "bpdb_daily.csv", ROOT / "data" / "bpdb_forecast.csv"
    actuals, forecasts = read_csv(actual_path), read_csv(forecast_path)
    today = datetime.now(BD_TIME).date()
    wanted = [d + timedelta(days=1) for d in days_to_fetch({r["date"] for r in actuals}, today - timedelta(days=1), days)]
    new_a, new_f = [], []
    for report_day in wanted:
        try:
            actual, forecast = parse_bpdb_daily(pdf_text(fetch(BPDB_URL.format(report_day))))
            new_a.append(actual)
            new_f.append(forecast)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                errors.append(f"BPDB {report_day}: HTTP {e.code}")
        except (ValueError, OSError) as e:
            errors.append(f"BPDB {report_day}: {e}")
        time.sleep(delay)
    write_csv(actual_path, merge_by(actuals, new_a, ("date",)), BPDB_ACTUAL_COLUMNS)
    write_csv(forecast_path, merge_by(forecasts, new_f, ("date",)), BPDB_FORECAST_COLUMNS)
    print(f"bpdb: {len(new_a)} daily reports from {len(wanted)} days checked")


def update_plants(errors: list) -> None:
    path = ROOT / "data" / "plants.csv"
    latest = max((r["date"] for r in read_csv(ROOT / "data" / "bpdb_daily.csv")), default=None)
    if not latest or latest == max((r["date"] for r in read_csv(path)), default=None):
        return
    try:
        rows = parse_bpdb_plants(fetch(BPDB_URL.format(date.fromisoformat(latest) + timedelta(days=1))), latest)
    except (ValueError, OSError) as e:
        errors.append(f"BPDB plants {latest}: {e}")
        return
    write_csv(path, rows, ["date", "plant", "reason", "lost_mw", "remark", "restart"])
    print(f"plants: {len(rows)} idle plants on {latest}")


def update_gas(days: int, delay: float, errors: list, max_pages: int = 60) -> None:
    path = ROOT / "data" / "gas.csv"
    existing = read_csv(path)
    cutoff = (max(r["date"] for r in existing) if existing
              else (datetime.now(BD_TIME).date() - timedelta(days=days)).isoformat())
    new = []
    for page in range(1, max_pages + 1):
        links = petrobangla_links(get(PETROBANGLA_LIST.format(page)))
        if not links:
            break
        reached = False
        for link in links:
            try:
                row = parse_petrobangla(pdf_text(fetch(link)))
            except (ValueError, OSError) as e:
                errors.append(f"Petrobangla {link.rsplit('/', 1)[-1]}: {e}")
                continue
            finally:
                time.sleep(delay)
            if row["date"] <= cutoff:
                reached = True
                break
            new.append(row)
        if reached:
            break
    write_csv(path, merge_by(existing, new, ("date",)), GAS_COLUMNS)
    print(f"gas: {len(new)} daily reports after {cutoff}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365, help="history to backfill when a CSV is empty")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    errors = update(args.days, args.delay)
    for error in errors:
        print(error, file=sys.stderr)
    sys.exit(1 if errors else 0)


def update(days: int = 365, delay: float = 1.0) -> list[str]:
    errors: list[str] = []
    update_bpdb(days, delay, errors)
    update_plants(errors)
    update_gas(days, delay, errors)
    return errors


if __name__ == "__main__":
    main()
