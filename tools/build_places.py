#!/usr/bin/env python3
"""Build the place search index and map layers from open boundary data.

Inputs:  geoBoundaries BGD ADM2/ADM3/ADM4 (CC BY 3.0 IGO; ADM4 = unions, pourashavas, city wards, BBS 2020),
         bangladesh-geocode Bangla names (MIT), OpenStreetMap towns and neighbourhoods (ODbL),
         geo/zone_districts.csv (district -> BPDB/NLDC zone, with evidence level).
Outputs: static/geo/places.json, static/geo/districts.geojson, static/geo/upazilas.geojson

geoBoundaries does not say which district an upazila is in, so it is worked out from the shapes:
a grid of points inside the upazila votes for the district that contains them.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
import difflib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "geo" / "raw"
OUT = ROOT / "static" / "geo"
GEOBOUNDARIES = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/BGD/{0}/geoBoundaries-BGD-{0}_simplified.geojson"
GEOCODE = "https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/{0}/{0}.json"
OSM_PLACES = ('https://overpass-api.de/api/interpreter?data=[out:json][timeout:170];area["ISO3166-1"="BD"][admin_level=2]->.bd;'
              'node(area.bd)["place"~"^(city|town|suburb|neighbourhood|quarter)$"]["name"];out;')
BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
ALIASES = {"chattogram": "chittagong", "chapainawabganj": "nawabganj", "chapai nawabganj": "nawabganj"}


def _rings(geom):
    return [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]


def _in_ring(ring, x, y):
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def contains(geom, point) -> bool:
    x, y = point
    return any(_in_ring(poly[0], x, y) and not any(_in_ring(h, x, y) for h in poly[1:]) for poly in _rings(geom))


def _bbox(geom):
    xs = [p[0] for poly in _rings(geom) for p in poly[0]]
    ys = [p[1] for poly in _rings(geom) for p in poly[0]]
    return min(xs), min(ys), max(xs), max(ys)


def _inside_points(geom):
    x0, y0, x1, y1 = _bbox(geom)
    for n in (7, 15, 31):
        pts = [(x0 + (x1 - x0) * (i + 0.5) / n, y0 + (y1 - y0) * (j + 0.5) / n) for i in range(n) for j in range(n)]
        inside = [p for p in pts if contains(geom, p)]
        if inside:
            return inside
    return [((x0 + x1) / 2, (y0 + y1) / 2)]


def parent(geom, districts: list[dict]) -> str | None:
    votes = Counter()
    for p in _inside_points(geom):
        for d in districts:
            if contains(d["geometry"], p):
                votes[d["name"]] += 1
                break
    return votes.most_common(1)[0][0] if votes else None


def inside_point(geom):
    points = _inside_points(geom)
    return points[len(points) // 2]


def locator(entries):
    """entries: (value, geometry). Returns a function point -> value of the first shape containing it."""
    indexed = [(value, geom, _bbox(geom)) for value, geom in entries]

    def locate(point):
        x, y = point
        for value, geom, (x0, y0, x1, y1) in indexed:
            if x0 <= x <= x1 and y0 <= y <= y1 and contains(geom, point):
                return value
        return None
    return locate


def rounded(geom, digits: int) -> dict:
    def walk(c):
        return [round(c[0], digits), round(c[1], digits)] if isinstance(c[0], (int, float)) else [walk(x) for x in c]
    return {"type": geom["type"], "coordinates": walk(geom["coordinates"])}


def key(name: str) -> str:
    letters = re.sub(r"[^a-z]", "", name.lower())
    letters = ALIASES.get(letters, letters)
    consonants = re.sub(r"[aeiouh]", "", letters)
    return re.sub(r"(.)\1+", r"\1", consonants)


def best_match(name: str, candidates: dict, cutoff: float = 0.85) -> str | None:
    by_key = {key(k): v for k, v in candidates.items()}
    if key(name) in by_key:
        return by_key[key(name)]
    plain = {re.sub(r"[^a-z]", "", k.lower()): v for k, v in candidates.items()}
    close = difflib.get_close_matches(re.sub(r"[^a-z]", "", name.lower()), list(plain), n=1, cutoff=cutoff)
    return plain[close[0]] if close else None


def _load(path: Path, url: str):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = next(block["data"] for block in data if isinstance(block, dict) and "data" in block)
    return data


def main() -> None:
    adm2 = _load(RAW / "ADM2.geojson", GEOBOUNDARIES.format("ADM2"))["features"]
    adm3 = _load(RAW / "ADM3.geojson", GEOBOUNDARIES.format("ADM3"))["features"]
    adm4 = _load(RAW / "ADM4.geojson", GEOBOUNDARIES.format("ADM4"))["features"]
    osm = _load(RAW / "osm_places.json", OSM_PLACES)["elements"]
    bn_districts = _load(RAW / "bn_districts.json", GEOCODE.format("districts"))
    bn_upazilas = _load(RAW / "bn_upazilas.json", GEOCODE.format("upazilas"))
    bn_unions = _load(RAW / "bn_unions.json", GEOCODE.format("unions"))
    with (ROOT / "geo" / "zone_districts.csv").open(encoding="utf-8") as f:
        zones = {r["district"]: r for r in csv.DictReader(f)}

    districts = [{"name": f["properties"]["shapeName"], "geometry": f["geometry"]} for f in adm2]
    missing = {d["name"] for d in districts} ^ set(zones)
    if missing:
        raise SystemExit(f"zone_districts.csv does not match the district list: {sorted(missing)}")

    district_bn = {d["name"]: best_match(d["name"], {b["name"]: b["bn_name"] for b in bn_districts}) for d in districts}
    geocode_district = {b["id"]: best_match(b["name"], {d["name"]: d["name"] for d in districts}) for b in bn_districts}

    upazilas = []
    for f in adm3:
        home = parent(f["geometry"], districts)
        if home is None:
            raise SystemExit(f"no district found for upazila {f['properties']['shapeName']}")
        upazilas.append({"name": f["properties"]["shapeName"], "district": home, "geometry": f["geometry"]})
    names_in = defaultdict(dict)
    for u in upazilas:
        names_in[u["district"]][u["name"]] = u["name"]

    upazila_bn, geocode_upazila = defaultdict(dict), {}
    for u in bn_upazilas:
        district = geocode_district.get(u["district_id"])
        upazila_bn[district][u["name"]] = u["bn_name"]
        geocode_upazila[u["id"]] = (district, best_match(u["name"], names_in.get(district, {})))
    union_bn, union_bn_district = defaultdict(dict), defaultdict(dict)
    for u in bn_unions:
        where = geocode_upazila.get(u["upazilla_id"])
        if where and where[1]:
            union_bn[where][u["name"]] = u["bn_name"]
        if where:
            union_bn_district[where[0]][u["name"]] = u["bn_name"]

    in_upazila = locator([((u["district"], u["name"]), u["geometry"]) for u in upazilas])
    in_district = locator([(d["name"], d["geometry"]) for d in districts])
    osm_bn = defaultdict(dict)
    for e in osm:
        tags = e["tags"]
        if tags.get("name:bn") and tags.get("name:en"):
            district = in_district((e["lon"], e["lat"]))
            if district:
                osm_bn[district][tags["name:en"]] = tags["name:bn"]

    with (ROOT / "geo" / "upazila_bn_extra.csv").open(encoding="utf-8") as f:
        extra_bn = {r["name"]: r["name_bn"] for r in csv.DictReader(f)}

    def upazila_name_bn(name, district):
        exact = {k.lower(): v for k, v in osm_bn.get(district, {}).items()}
        return best_match(name, upazila_bn.get(district, {})) or exact.get(name.lower()) or extra_bn.get(name)

    def place(kind, name, name_bn, district, upazila, point):
        z = zones[district]
        up_bn = upazila_name_bn(upazila, district) if upazila else None
        return {"type": kind, "name": name, "name_bn": name_bn, "upazila": upazila, "upazila_bn": up_bn,
                "district": district, "district_bn": district_bn[district], "zone": z["zone"], "evidence": z["evidence"],
                "lon": round(point[0], 4), "lat": round(point[1], 4)}

    places, unmatched = [], []
    for d in districts:
        places.append(place("district", d["name"], district_bn[d["name"]], d["name"], None, inside_point(d["geometry"])))
    for u in upazilas:
        bn = upazila_name_bn(u["name"], u["district"])
        if bn is None:
            unmatched.append(f"{u['name']} ({u['district']})")
        places.append(place("upazila", u["name"], bn, u["district"], u["name"], inside_point(u["geometry"])))

    skipped = 0
    for f in adm4:
        name, point = f["properties"]["shapeName"], inside_point(f["geometry"])
        where = in_upazila(point)
        if where is None:
            skipped += 1
            continue
        district, upazila = where
        ward = re.match(r"Ward No-?\s*(\d+)", name, re.I)
        if ward:
            number = int(ward.group(1))
            places.append(place("ward", f"Ward {number}", f"ওয়ার্ড {str(number).translate(BN_DIGITS)}", district, upazila, point))
        elif re.search(r"paurashava", name, re.I):
            base = re.sub(r"\s*paurashava.*", "", name, flags=re.I)
            base_bn = (best_match(base, upazila_bn.get(district, {})) or best_match(base, osm_bn.get(district, {}))
                       or best_match(base, union_bn.get((district, upazila), {})) or best_match(base, upazila_bn.get(district, {}), 0.7))
            places.append(place("paurashava", name, f"{base_bn} পৌরসভা" if base_bn else None, district, upazila, point))
        else:
            bn = (best_match(name, union_bn.get((district, upazila), {})) or best_match(name, union_bn_district.get(district, {}))
                  or best_match(name, upazila_bn.get(district, {})) or best_match(name, union_bn.get((district, upazila), {}), 0.7))
            places.append(place("union", name, bn, district, upazila, point))

    for e in osm:
        tags, point = e["tags"], (e["lon"], e["lat"])
        district = in_district(point)
        if district is None:
            continue
        where = in_upazila(point)
        en = tags.get("name:en") or tags["name"]
        bn = tags.get("name:bn") or (tags["name"] if re.search(r"[\u0980-\u09ff]", tags["name"]) else None)
        places.append(place("area", en, bn, district, where[1] if where else None, point))

    seen, unique = set(), []
    for p in places:
        k = (p["type"], p["name"], p["district"], p["upazila"])
        if k not in seen:
            seen.add(k)
            unique.append(p)
    order = {"district": 0, "upazila": 1, "area": 2, "paurashava": 3, "ward": 4, "union": 5}
    unique.sort(key=lambda p: (order[p["type"]], p["name"], p["district"]))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "places.json").write_text(json.dumps(unique, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "districts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": d["name"], "name_bn": district_bn[d["name"]], "zone": zones[d["name"]]["zone"]},
         "geometry": rounded(d["geometry"], 3)} for d in districts]}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "upazilas.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": u["name"], "district": u["district"]}, "geometry": rounded(u["geometry"], 3)}
        for u in upazilas]}, separators=(",", ":")), encoding="utf-8")
    counts = defaultdict(int)
    for p in unique:
        counts[p["type"]] += 1
    no_bn = sum(1 for p in unique if not p["name_bn"])
    print(f"{len(unique)} places {dict(counts)}; {no_bn} without a Bangla name; {skipped} unions/wards outside every upazila")


if __name__ == "__main__":
    main()
