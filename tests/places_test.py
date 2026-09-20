import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_places  # noqa: E402

SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}
HOLE = {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]]}
MULTI = {"type": "MultiPolygon", "coordinates": [[[[20, 20], [22, 20], [22, 22], [20, 22], [20, 20]]], SQUARE["coordinates"]]}


class GeometryTest(unittest.TestCase):
    def test_point_in_polygon_respects_holes_and_multipolygons(self):
        self.assertTrue(build_places.contains(SQUARE, (5, 5)))
        self.assertFalse(build_places.contains(HOLE, (5, 5)))
        self.assertTrue(build_places.contains(HOLE, (2, 2)))
        self.assertTrue(build_places.contains(MULTI, (21, 21)))
        self.assertFalse(build_places.contains(MULTI, (15, 15)))

    def test_parent_is_the_district_holding_most_of_the_upazila(self):
        districts = [{"name": "A", "geometry": SQUARE},
                     {"name": "B", "geometry": {"type": "Polygon", "coordinates": [[[10, 0], [20, 0], [20, 10], [10, 10], [10, 0]]]}}]
        upazila = {"type": "Polygon", "coordinates": [[[1, 1], [9, 1], [9, 9], [1, 9], [1, 1]]]}
        self.assertEqual(build_places.parent(upazila, districts), "A")

    def test_rounding_keeps_shape_and_shrinks_numbers(self):
        g = {"type": "Polygon", "coordinates": [[[90.123456, 23.987654], [90.2, 23.9], [90.123456, 23.987654]]]}
        self.assertEqual(build_places.rounded(g, 3)["coordinates"][0][0], [90.123, 23.988])


class NamesTest(unittest.TestCase):
    def test_spelling_variants_match(self):
        self.assertEqual(build_places.key("Brahamanbaria"), build_places.key("Brahmanbaria"))
        self.assertEqual(build_places.key("Maulvibazar"), build_places.key("Moulvibazar"))
        self.assertEqual(build_places.key("Cox's Bazar"), build_places.key("Coxsbazar"))

    def test_best_match_within_a_district(self):
        candidates = {"Debidwar": "দেবিদ্বার", "Barura": "বরুড়া"}
        self.assertEqual(build_places.best_match("Debidar", candidates), "দেবিদ্বার")
        self.assertIsNone(build_places.best_match("Adabor", candidates))


class BuiltPlacesTest(unittest.TestCase):
    """Checks on the committed output of tools/build_places.py."""

    @classmethod
    def setUpClass(cls):
        cls.places = json.loads((ROOT / "static" / "geo" / "places.json").read_text(encoding="utf-8"))

    def test_every_upazila_and_district_is_searchable(self):
        kinds = [p["type"] for p in self.places]
        self.assertEqual(kinds.count("upazila"), 544)
        self.assertEqual(kinds.count("district"), 64)

    def test_every_place_has_one_of_the_nine_bpdb_zones(self):
        zones = {"Dhaka", "Chittagong", "Khulna", "Rajshahi", "Comilla", "Mymensingh", "Sylhet", "Barisal", "Rangpur"}
        self.assertEqual({p["zone"] for p in self.places}, zones)

    def test_known_upazilas_land_in_the_right_district(self):
        where = {(p["name"], p["district"]) for p in self.places if p["type"] == "upazila"}
        for pair in [("Savar", "Dhaka"), ("Teknaf", "Cox's Bazar"), ("Debidwar", "Comilla"), ("Companiganj", "Sylhet")]:
            self.assertIn(pair, where)

    def test_greater_faridpur_is_in_khulna_zone_with_evidence_level(self):
        by_name = {p["name"]: p for p in self.places if p["type"] == "district"}
        self.assertEqual(by_name["Faridpur"]["zone"], "Khulna")
        self.assertEqual(by_name["Faridpur"]["evidence"], "verified")
        self.assertEqual(by_name["Madaripur"]["evidence"], "inferred")

    def test_unions_are_searchable_with_bangla_names(self):
        unions = [p for p in self.places if p["type"] == "union"]
        self.assertGreater(len(unions), 4000)
        self.assertGreater(sum(1 for p in unions if p["name_bn"]) / len(unions), 0.9)

    def test_city_neighbourhoods_and_towns_land_in_the_right_zone(self):
        areas = {(p["name"], p["district"]): p for p in self.places if p["type"] == "area"}
        self.assertEqual(areas[("Mirpur 2", "Dhaka")]["zone"], "Dhaka")
        self.assertEqual(areas[("Mirpur 2", "Dhaka")]["name_bn"], "মিরপুর ২")
        self.assertEqual(areas[("Sreemangal", "Maulvibazar")]["zone"], "Sylhet")
        agrabad = [p for (name, _), p in areas.items() if "Agrabad" in name]
        self.assertTrue(agrabad and all(p["zone"] == "Chittagong" for p in agrabad))

    def test_city_wards_are_searchable_by_number_with_their_thana(self):
        wards = [p for p in self.places if p["type"] == "ward"]
        self.assertGreater(len(wards), 250)
        self.assertTrue(all(p["upazila"] and p["name"].startswith("Ward ") and p["name_bn"].startswith("ওয়ার্ড ") for p in wards))
        self.assertTrue(any(p["district"] == "Dhaka" and p["name"] == "Ward 12" for p in wards))

    def test_pourashavas_are_searchable(self):
        pour = {p["name"]: p for p in self.places if p["type"] == "paurashava"}
        self.assertGreater(len(pour), 200)
        self.assertEqual(pour["Ishwardi Paurashava"]["zone"], "Rajshahi")

    def test_every_place_has_a_point_for_the_map(self):
        for p in self.places:
            self.assertTrue(20 < p["lat"] < 27 and 88 < p["lon"] < 93, p["name"])

    def test_all_upazilas_and_thanas_have_bangla_names(self):
        missing = [p["name"] for p in self.places if p["type"] == "upazila" and not p["name_bn"]]
        self.assertEqual(missing, [])

    def test_all_districts_have_bangla_names(self):
        self.assertTrue(all(p["name_bn"] for p in self.places if p["type"] == "district"))


if __name__ == "__main__":
    unittest.main()
