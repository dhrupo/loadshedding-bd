#!/usr/bin/env python3
"""Scrape what the distribution utilities publish for their own customers.

DESCO: the feeder-by-feeder loadshedding schedule (north Dhaka and Tongi).
NESCO: planned shutdown notices (Rajshahi and Rangpur divisions).
"""

from __future__ import annotations

import html as html_lib
import json
import re
import unicodedata

from bmd import places
from pdf_sources import pdf_tables
from pgb import BN_DIGITS, ROOT, fetch, get, write_csv, write_json
from sources import BN_MONTHS

DESCO_PAGE = "https://desco.gov.bd/pages/static-pages/69db2a3c6a42b12e9344d1f1"
NESCO_NOTICES = ("https://nesco.gov.bd/pages/miscellaneous-infos?filters="
                 "%7B%22miscellaneous_info_type%22%3A%20%226922d90281fc96cef9eb0748%22%7D")
NESCO_COLUMNS = ["published", "outage_date", "outage_until", "from_time", "to_time", "district", "zone", "title", "url"]
PM_WORDS = ("দুপুর", "বিকাল", "বিকেল", "সন্ধ্যা")
CLOCK = r"(?:(ভোর|সকাল|দুপুর|বিকাল|বিকেল|সন্ধ্যা|রাত)\s*)?([০-৯]{1,2}:[০-৯]{2}|[০-৯]{1,2}(?=\s*(?:ঘটিকা|টা)))"


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def parse_desco_page(page: str) -> tuple[str, str]:
    link = re.search(r'href="(https://[^"]+/office-desco/[^"]+\.pdf)"', page)
    updated = re.search(nfc(r"হাল-নাগাদ করা হয়েছে:\s*\S+,\s*([০-৯]+) (\S+), ([০-৯]{4})"), nfc(page))
    months = [nfc(m) for m in BN_MONTHS]
    if not link or not updated or updated.group(2) not in months:
        raise ValueError("DESCO schedule: PDF link or update date not found")
    day, month, year = updated.groups()
    return link.group(1), f"{year.translate(BN_DIGITS)}-{months.index(month) + 1:02d}-{int(day.translate(BN_DIGITS)):02d}"


def parse_desco_schedule(source) -> list[dict]:
    """One row per 11 kV feeder; columns 5-28 are the 24 hours, filled with the load to shed in that hour."""
    feeders = [{"division": row[0], "areas": row[1], "feeder": row[2],
                "hours": [hour for hour, cell in enumerate(row[4:28]) if cell.replace(".", "").isdigit() and float(cell) > 0]}
               for row in pdf_tables(source) if len(row) == 28 and row[2] and row[3] != "Time"]
    if not feeders:
        raise ValueError("DESCO schedule: no feeder rows found")
    return feeders


def _clock(word: str, text: str, after: str = "") -> str:
    hour, _, minute = text.translate(BN_DIGITS).partition(":")
    hour = int(hour) % 12
    # "রাত" covers both sides of midnight: রাত ১০টা is 22:00, রাত ২টা is 02:00.
    if word in PM_WORDS or (word == nfc("রাত") and hour >= 6):
        hour += 12
    clock = f"{hour:02d}:{int(minute or 0):02d}"
    return f"{hour + 12:02d}:{int(minute or 0):02d}" if not word and clock < after else clock


def parse_nesco(page: str, where: list[dict]) -> list[dict]:
    districts = {nfc(p["name_bn"]): p for p in where if p["type"] == "district" and p["zone"] in ("Rajshahi", "Rangpur")}
    rows = []
    for block in re.findall(r'<tr class="table-tr">([\s\S]*?)</tr>', re.sub(r"<!--[\s\S]*?-->", "", page)):
        title = re.search(r'data-column="title">([\s\S]*?)</td>', block)
        published = re.search(r'data-column="publish_date">\s*<span>([০-৯]{2})-([০-৯]{2})-([০-৯]{4})</span>', block)
        if not title or not published:
            continue
        text = nfc(" ".join(html_lib.unescape(title.group(1)).split()))
        days = list(re.finditer(r"([০-৯]{1,2})/([০-৯]{1,2})/([০-৯]{4})", text))
        times = re.findall(nfc(CLOCK), text)
        place = next((p for name, p in districts.items() if name in text), None)
        file = re.search(r'href="(https://[^"]+\.pdf)"', block)
        iso = lambda m: "-".join(part.translate(BN_DIGITS).zfill(2) for part in reversed(m.groups()))
        start = _clock(*times[0]) if len(times) == 2 else ""
        rows.append({"published": iso(published), "outage_date": iso(days[0]) if days else "", "outage_until": iso(days[-1]) if days else "",
                     "from_time": start, "to_time": _clock(*times[1], after=start) if start else "",
                     "district": place["name"] if place else "", "zone": place["zone"] if place else "",
                     "title": text, "url": file.group(1) if file else ""})
    if not rows:
        raise ValueError("NESCO notices: no rows found")
    return rows


def update_desco() -> None:
    path = ROOT / "data" / "desco_schedule.json"
    url, as_of = parse_desco_page(get(DESCO_PAGE))
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if saved.get("url") == url and saved.get("as_of") == as_of:
        return
    feeders = saved["feeders"] if saved.get("url") == url else parse_desco_schedule(fetch(url))
    write_json(path, {"as_of": as_of, "url": url, "feeders": feeders})
    print(f"desco_schedule: published {as_of}")


def update_nesco() -> None:
    rows = parse_nesco(get(NESCO_NOTICES), places())
    write_csv(ROOT / "data" / "nesco_notices.csv", rows, NESCO_COLUMNS)
    print(f"nesco_notices: {len(rows)} notices")


def update() -> list[str]:
    errors = []
    for job in (update_desco, update_nesco):
        try:
            job()
        except (ValueError, OSError) as e:
            errors.append(f"{job.__name__}: {e}")
    return errors


if __name__ == "__main__":
    import sys
    problems = update()
    for problem in problems:
        print(problem, file=sys.stderr)
    sys.exit(1 if problems else 0)
