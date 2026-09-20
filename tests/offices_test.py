import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_offices  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
PLACES = json.loads((ROOT / "static" / "geo" / "places.json").read_text(encoding="utf-8"))


def offices(utility):
    return build_offices.parse_offices((FIXTURES / f"offices_{utility}.html").read_text(encoding="utf-8", errors="replace"), utility, PLACES)


class OfficesTest(unittest.TestCase):
    def test_nesco_office_with_its_complaint_mobile(self):
        rows = offices("nesco")
        self.assertEqual(rows[0], {"utility": "nesco", "office": "বিক্রয় ও বিতরণ বিভাগ-১, রাজশাহী", "phone": "01321124509", "district": "Rajshahi"})
        self.assertEqual(len(rows), 59)

    def test_office_with_only_a_landline_keeps_it(self):
        pabna = next(r for r in offices("nesco") if r["office"] == "বিক্রয় ও বিতরণ বিভাগ-১, পাবনা")
        self.assertEqual(pabna["phone"], "02588845030")

    def test_desco_uses_the_round_the_clock_number(self):
        rows = offices("desco")
        self.assertEqual(rows[0], {"utility": "desco", "office": "টঙ্গী (পূর্ব) বিক্রয় ও বিতরণ বিভাগ", "phone": "01324435986", "district": ""})
        self.assertEqual(len(rows), 24)

    def test_dpdc_control_rooms_without_the_call_centre_row(self):
        rows = offices("dpdc")
        self.assertEqual(rows[0], {"utility": "dpdc", "office": "Adabor", "phone": "01766675038", "district": "Dhaka"})
        self.assertNotIn("Call Center", [r["office"] for r in rows])

    def test_wzpdcl_skips_offices_that_list_no_mobile(self):
        rows = offices("wzpdcl")
        self.assertEqual(rows[0], {"utility": "wzpdcl", "office": "বিক্রয় ও বিতরণ বিভাগ-১, খুলনা", "phone": "01711297972", "district": "Khulna"})
        self.assertEqual(rows[-1]["phone"], "01700709704")

    def test_office_naming_a_town_and_its_district_belongs_to_that_district(self):
        by_name = {r["office"]: r["district"] for r in offices("nesco")}
        self.assertEqual(by_name["বিদ্যুৎ সরবরাহ ইউনিট, শিবগঞ্জ, চাঁপাইনবাবগঞ্জ"], "Nawabganj")
        self.assertEqual(by_name["বিদ্যুৎ সরবরাহ ইউনিট, শিবগঞ্জ, বগুড়া"], "Bogra")

    def test_town_name_shared_by_two_districts_is_marked_unknown_not_guessed(self):
        self.assertEqual(build_offices.district_of("বিদ্যুৎ সরবরাহ ইউনিট, শিবগঞ্জ", "nesco", PLACES), "?")
        self.assertEqual(build_offices.district_of("বিদ্যুৎ সরবরাহ ইউনিট, ঈশ্বরদী", "nesco", PLACES), "Pabna")

    def test_page_without_a_table_raises(self):
        with self.assertRaises(ValueError):
            build_offices.parse_offices("<html></html>", "desco", PLACES)


if __name__ == "__main__":
    unittest.main()
