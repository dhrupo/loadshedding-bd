#!/usr/bin/env python3
"""Scrape Power Grid Bangladesh PLC's public hourly generation and demand tables into CSV.

Values are copied as published. A blank cell stays blank; it is never turned into 0.
Timestamps are Bangladesh local time (UTC+6), exactly as PGB prints them.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import ssl
import time
import unicodedata
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://erp.powergrid.gov.bd"
BD_TIME = timezone(timedelta(hours=6))
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
BLANK = {"", "—", "-"}

GENERATION = {
    "name": "generation",
    "url": BASE + "/w/generations/view_generations_bn",
    "headers": ["তারিখ", "সময়", "উৎপাদন", "গ্যাস", "তরল জ্বালানী", "কয়লা", "হাইড্রো", "সৌর", "বায়ু",
                "ভারত", "নেপাল", "মন্তব্য", "ভেড়ামারা", "ত্রিপুরা", "আদানি"],
    "fields": ["generation_mw", "gas", "liquid_fuel", "coal", "hydro", "solar", "wind",
               "india_bheramara_hvdc", "india_tripura", "india_adani", "nepal"],
}

DEMAND = {
    "name": "demand",
    "url": BASE + "/web/generations/view_demand_supply_loadshed_bn",
    "headers": ["তারিখ", "সময়", "চাহিদা", "সরবরাহ", "লোডশেড", "মন্তব্য"],
    "fields": ["demand_mw", "supply_mw", "loadshed_mw"],
}


class _FirstTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.depth, self.done, self.cell = [], 0, False, None

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if tag == "table":
            self.depth += 1
        elif self.depth and tag == "tr":
            self.rows.append([])
        elif self.depth and tag in ("td", "th"):
            self.cell = []

    def handle_endtag(self, tag):
        if self.done:
            return
        if tag == "table" and self.depth:
            self.depth -= 1
            self.done = not self.depth
        elif self.cell is not None and tag in ("td", "th"):
            self.rows[-1].append((tag, " ".join("".join(self.cell).split())))
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def number(text: str):
    text = text.translate(BN_DIGITS).replace(",", "").strip()
    if text in BLANK:
        return None
    value = float(text)
    return int(value) if "." not in text else value


def timestamp(date: str, clock: str) -> str:
    day, month, year = date.translate(BN_DIGITS).split("-")
    return f"{year}-{month}-{day}T{clock.split()[0].translate(BN_DIGITS)[:5]}"


def parse(html: str, schema: dict) -> list[dict]:
    table = _FirstTable()
    table.feed(html)
    nfc = lambda s: unicodedata.normalize("NFC", s)
    headers = [nfc(text) for row in table.rows for tag, text in row if tag == "th"]
    expected = [nfc(label) for label in schema["headers"]]
    if len(headers) != len(expected) or not all(h.startswith(e) for h, e in zip(headers, expected)):
        raise ValueError(f"{schema['name']}: PGB table layout changed: {headers}")

    width = 2 + len(schema["fields"]) + 1
    rows = []
    for row in table.rows:
        cells = [text for tag, text in row if tag == "td"]
        if len(cells) <= 1:
            continue
        if len(cells) != width:
            raise ValueError(f"{schema['name']}: expected {width} cells, got {len(cells)}: {cells}")
        record = {"timestamp": timestamp(cells[0], cells[1])}
        record.update(zip(schema["fields"], map(number, cells[2:-1])))
        record["remarks"] = "" if cells[-1] in BLANK else cells[-1]
        rows.append(record)
    return rows


def crawl(fetch, cutoff: str, max_pages: int, delay: float) -> list[dict]:
    collected = []
    for page in range(1, max_pages + 1):
        rows = fetch(page)
        if not rows:
            break
        collected += [r for r in rows if r["timestamp"] >= cutoff]
        if min(r["timestamp"] for r in rows) <= cutoff:
            break
        time.sleep(delay)
    return collected


def cutoff(existing: list[dict], now: datetime, days: int) -> str:
    if existing:
        return max(r["timestamp"] for r in existing)
    return (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M")


def merge(existing: list[dict], new: list[dict]) -> list[dict]:
    by_time = {r["timestamp"]: r for r in existing}
    by_time.update((r["timestamp"], r) for r in new)
    return [by_time[t] for t in sorted(by_time)]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: "" if r.get(k) is None else r[k] for k in columns} for r in rows)
    os.replace(tmp, path)


def write_json(path: Path, value) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def tls_context() -> ssl.SSLContext:
    # Several gov.bd servers omit their intermediate CA; add them so verification can still reach a trusted root.
    context = ssl.create_default_context()
    context.load_verify_locations(Path(__file__).with_name("missing-intermediates.pem"))
    return context


def fetch(url: str, attempts: int = 3, timeout: float = 60) -> bytes:
    context = tls_context()
    request = urllib.request.Request(url, headers={"User-Agent": "loadshedding-bd (+github)"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == attempts - 1:
                raise
        except OSError:
            if attempt == attempts - 1:
                raise
        time.sleep(5 * (attempt + 1))


def get(url: str, attempts: int = 3, timeout: float = 60) -> str:
    return fetch(url, attempts, timeout).decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365, help="history to backfill when a CSV is empty")
    parser.add_argument("--max-pages", type=int, default=400)
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between page requests")
    args = parser.parse_args()
    update(args.days, args.max_pages, args.delay)


def update(days: int = 365, max_pages: int = 400, delay: float = 1.0, timeout: float = 60, attempts: int = 3) -> int:
    now = datetime.now(BD_TIME).replace(tzinfo=None)
    fetched = 0
    for schema in (GENERATION, DEMAND):
        path = ROOT / "data" / f"{schema['name']}.csv"
        existing = read_csv(path)
        since = cutoff(existing, now, days)
        new = crawl(lambda page: parse(get(f"{schema['url']}?page={page}", timeout=timeout, attempts=attempts), schema),
                    since, max_pages, delay)
        write_csv(path, merge(existing, new), ["timestamp", *schema["fields"], "remarks"])
        print(f"{schema['name']}: {len(new)} rows fetched since {since}, {path.name} updated")
        fetched += sum(1 for r in new if r["timestamp"] > since)
    return fetched


if __name__ == "__main__":
    main()
