#!/usr/bin/env python3
"""Scrape the Bangladesh Meteorological Department: station forecasts and CAP weather warnings.

Warnings name areas loosely ("Chattogram", "Payra"), so the districts they cover are worked out
from the polygons BMD publishes with each warning.
"""

from __future__ import annotations

from collections import Counter
import json
import re
import xml.etree.ElementTree as ET

from pgb import ROOT, get, write_csv, write_json

HOME_URL = "https://server6.bmd.gov.bd/home_all_json"
STATIONS_URL = "https://server6.bmd.gov.bd/assets/json/stationlist.json"
CAP_FEED = "https://cap.bmd.gov.bd/api/cap/rss.xml"
CAP = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}
FORECAST_COLUMNS = ["date", "station", "station_bn", "lat", "lon", "max_c", "min_c"]


def parse_forecast(home_json: str, stations_json: str) -> list[dict]:
    data = json.loads(home_json).get("data", {})
    points, where = data.get("MapPoints") or {}, {s["code"]: s for s in json.loads(stations_json)}
    rows = []
    for f in data.get("Forecast") or []:
        point = points.get(f["pointCode"])
        station = where.get(point["stCode"]) if point else None
        if not station or not f["maxtemp"] or not f["mintemp"]:
            continue
        rows.append({"date": f["timeUpdate"], "station": point["pointname"], "station_bn": point["pointnameBN"],
                     "lat": round(float(station["latitude"]), 4), "lon": round(float(station["longitude"]), 4),
                     "max_c": float(f["maxtemp"]), "min_c": float(f["mintemp"])})
    if not rows:
        raise ValueError("BMD forecast: no station rows found")
    return sorted(rows, key=lambda r: (r["station"], r["date"]))


def alert_links(rss: str) -> list[str]:
    return [link for item in ET.fromstring(rss.encode("utf-8")).iter("item") if (link := item.findtext("link"))]


def _inside(lat: float, lon: float, polygon: list[tuple[float, float]]) -> bool:
    hit = False
    for (y1, x1), (y2, x2) in zip(polygon, polygon[1:] + polygon[:1]):
        if (x1 > lon) != (x2 > lon) and lat < (y2 - y1) * (lon - x1) / (x2 - x1) + y1:
            hit = not hit
    return hit


def _districts(area: ET.Element, points: list[dict], per_district: Counter) -> set[str]:
    polygons = [[tuple(map(float, pair.split(","))) for pair in (p.text or "").split()] for p in area.findall("c:polygon", CAP)]
    hits = Counter(p["district"] for p in points if any(_inside(p["lat"], p["lon"], poly) for poly in polygons))
    # BMD's outlines are coarse: a district counts when most of it is inside; a port-sized area keeps whatever it touches.
    return {d for d, n in hits.items() if 2 * n >= per_district[d]} or set(hits)


def parse_alert(xml: str, places: list[dict]) -> dict:
    root = ET.fromstring(xml.encode("utf-8"))
    infos = {(i.findtext("c:language", "", CAP) or "en")[:2].lower(): i for i in root.findall("c:info", CAP)}
    en = infos.get("en")
    if en is None or not en.findtext("c:expires", "", CAP):
        raise ValueError("BMD alert: English block or expiry not found")
    points = [p for p in places if p["type"] in ("district", "upazila")]
    per_district = Counter(p["district"] for p in points)
    text = lambda info, tag: (info.findtext(f"c:{tag}", "", CAP) or "").strip() if info is not None else ""
    return {
        "id": root.findtext("c:identifier", "", CAP), "status": root.findtext("c:status", "", CAP),
        "msg_type": root.findtext("c:msgType", "", CAP),
        "cancels": [ref.split(",")[1] for ref in root.findtext("c:references", "", CAP).split() if ref.count(",") == 2],
        "event": text(en, "event"), "severity": text(en, "severity"),
        "effective": text(en, "effective"), "expires": text(en, "expires"),
        "headline": text(en, "headline"), "headline_bn": text(infos.get("bn"), "headline"), "web": text(en, "web"),
        "districts": sorted(set().union(*(_districts(a, points, per_district) for a in en.findall("c:area", CAP)))),
    }


def places() -> list[dict]:
    return json.loads((ROOT / "static" / "geo" / "places.json").read_text(encoding="utf-8"))


def update_alerts() -> list[str]:
    path, errors = ROOT / "data" / "alerts.json", []
    known = {a["id"]: a for a in (json.loads(path.read_text(encoding="utf-8")) if path.exists() else [])}
    alerts, where = [], None
    for link in alert_links(get(CAP_FEED)):
        alert = known.get(re.sub(r".*/|\.xml$", "", link))
        if alert is None:
            where = where or places()
            try:
                alert = parse_alert(get(link), where)
            except (ValueError, OSError, ET.ParseError) as e:
                errors.append(f"BMD alert {link}: {e}")
                continue
        alerts.append(alert)
    write_json(path, alerts)
    print(f"alerts: {len(alerts)} in the BMD feed")
    return errors


def update_forecast() -> None:
    rows = parse_forecast(get(HOME_URL), get(STATIONS_URL))
    write_csv(ROOT / "data" / "bmd_forecast.csv", rows, FORECAST_COLUMNS)
    print(f"bmd_forecast: {len(rows)} station-days")


def update() -> list[str]:
    errors = []
    for job in (update_forecast, update_alerts):
        try:
            errors += job() or []
        except (ValueError, KeyError, OSError, ET.ParseError) as e:
            errors.append(f"{job.__name__}: {e}")
    return errors


if __name__ == "__main__":
    import sys
    problems = update()
    for problem in problems:
        print(problem, file=sys.stderr)
    sys.exit(1 if problems else 0)
