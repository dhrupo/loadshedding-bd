#!/usr/bin/env python3
"""Build static/geo/offices.json: the local complaint offices the four town utilities publish, with a mobile number each.

Run once in a while; these lists change rarely. Every page is a table whose second column is the office name.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

from pgb import BN_DIGITS, get  # noqa: E402
from sources import tables  # noqa: E402

PAGES = {
    "desco": "https://desco.gov.bd/pages/static-pages/6922dcbc933eb65569e11ba3",
    "dpdc": "https://dpdc.org.bd/site/home_gov/control_room",
    "nesco": "https://customer.nesco.gov.bd/office-wise-complain",
    "wzpdcl": "https://wzpdcl.gov.bd/pages/static-pages/6922dc49933eb65569e0f7f0",
}
ZONES = {"desco": ("Dhaka",), "dpdc": ("Dhaka",), "nesco": ("Rajshahi", "Rangpur"), "wzpdcl": ("Khulna", "Barisal")}
PHONE = re.compile(r"(?<![\d-])0\d[\d-]{6,11}(?!\d)")


def phones(cell: str) -> list[str]:
    numbers = [found.replace("-", "") for found in PHONE.findall(cell.translate(BN_DIGITS))]
    return [n for n in numbers if 9 <= len(n) <= 11]


def words(text: str | None) -> str:
    return " " + " ".join(re.findall(r"[a-z\u0980-\u09ff]+", unicodedata.normalize("NFC", text or "").lower())) + " "


def district_of(office: str, utility: str, places: list[dict]) -> str:
    """The one district an office name points to; "" when it names none, "?" when the name fits more than one."""
    name = words(office)
    for kind in ("district", "upazila"):
        found = {p["district"] for p in places if p["type"] == kind and p["zone"] in ZONES[utility]
                 and any(len(w) > 2 and w in name for w in (words(p["name"]), words(p["name_bn"])))}
        if found:
            return found.pop() if len(found) == 1 else "?"
    return ""


def parse_offices(html: str, utility: str, places: list[dict]) -> list[dict]:
    table = max(tables(html), key=len, default=[])
    rows = []
    for row in table[1:]:
        # DESCO lists its round-the-clock number last, so read the cells from the right. Mobiles first: they get answered.
        found = [n for cell in reversed(row[2:]) for n in phones(cell)]
        if found:
            rows.append({"utility": utility, "office": row[1], "phone": next((n for n in found if n.startswith("01")), found[0]),
                         "district": district_of(row[1], utility, places)})
    if not rows:
        raise ValueError(f"{utility}: no offices found")
    return rows


def main() -> None:
    places = json.loads((ROOT / "static" / "geo" / "places.json").read_text(encoding="utf-8"))
    offices = [office for utility, url in PAGES.items() for office in parse_offices(get(url), utility, places)]
    (ROOT / "static" / "geo" / "offices.json").write_text(json.dumps(offices, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"offices: {len(offices)}")


if __name__ == "__main__":
    main()
