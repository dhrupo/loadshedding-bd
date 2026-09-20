import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

import utilities  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
PLACES = json.loads((ROOT / "static" / "geo" / "places.json").read_text(encoding="utf-8"))


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


class DescoScheduleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feeders = utilities.parse_desco_schedule(FIXTURES / "desco_schedule.pdf")

    def test_page_gives_the_current_pdf_and_the_day_it_was_published(self):
        url, as_of = utilities.parse_desco_page(fixture("desco_schedule.html"))
        self.assertTrue(url.endswith("95000ff7-746c-4fe7-ad25-11c773eda988.pdf"))
        self.assertEqual(as_of, "2026-09-16")

    def test_feeder_lists_its_areas_and_the_hours_it_is_cut(self):
        feeder = next(f for f in self.feeders if f["feeder"] == "Samaj Sheba")
        self.assertEqual(feeder["division"], "Agargaon")
        self.assertIn("Agargaon Govt. School", feeder["areas"])
        self.assertEqual(feeder["hours"], [10, 16, 22])

    def test_feeder_with_nothing_to_shed_has_no_hours(self):
        self.assertEqual(next(f for f in self.feeders if f["feeder"] == "ICT Tower")["hours"], [])

    def test_every_page_is_read_and_header_rows_are_dropped(self):
        self.assertGreater(len(self.feeders), 550)
        self.assertFalse([f for f in self.feeders if f["feeder"] == "Feeder Name"])
        self.assertIn("Tongi East", {f["division"] for f in self.feeders})

    def test_feeder_row_with_a_blank_time_cell_is_still_kept(self):
        badda = next(f for f in self.feeders if f["feeder"] == "Middle Badda")
        self.assertEqual((badda["division"], badda["hours"]), ("Baridhara", [12, 16, 20]))

    def test_same_pdf_with_a_newer_page_date_refreshes_the_date_without_downloading_again(self):
        import tempfile
        url, _ = utilities.parse_desco_page(fixture("desco_schedule.html"))
        original = utilities.ROOT, utilities.get, utilities.fetch
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            path = Path(d) / "data" / "desco_schedule.json"
            path.write_text(json.dumps({"as_of": "2026-09-01", "url": url, "feeders": [{"feeder": "kept"}]}), encoding="utf-8")
            utilities.ROOT, utilities.get = Path(d), lambda _: fixture("desco_schedule.html")
            utilities.fetch = lambda _: self.fail("the unchanged PDF was downloaded again")
            try:
                utilities.update_desco()
                saved = json.loads(path.read_text(encoding="utf-8"))
            finally:
                utilities.ROOT, utilities.get, utilities.fetch = original
        self.assertEqual((saved["as_of"], saved["feeders"]), ("2026-09-16", [{"feeder": "kept"}]))

    def test_page_without_a_pdf_raises(self):
        with self.assertRaises(ValueError):
            utilities.parse_desco_page("<html></html>")


class NescoNoticesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = utilities.parse_nesco(fixture("nesco_shutdown.html"), PLACES)

    def test_notice_has_day_hours_place_and_the_official_file(self):
        first = self.rows[0]
        self.assertEqual((first["published"], first["outage_date"], first["from_time"], first["to_time"]),
                         ("2026-09-17", "2026-09-19", "07:00", "13:30"))
        self.assertEqual((first["district"], first["zone"]), ("Rajshahi", "Rajshahi"))
        self.assertTrue(first["title"].startswith("বিক্রয় ও বিতরণ বিভাগ-১"))
        self.assertTrue(first["url"].endswith("2d678d9f-be6f-44ce-9388-f076d67f358e.pdf"))

    def test_afternoon_hours_are_read_as_pm(self):
        rangpur = self.rows[1]
        self.assertEqual((rangpur["district"], rangpur["from_time"], rangpur["to_time"]), ("Rangpur", "08:00", "17:00"))

    def test_two_day_notice_runs_until_its_last_day(self):
        row = next(r for r in self.rows if r["outage_date"] == "2026-07-18")
        self.assertEqual((row["outage_until"], row["from_time"], row["to_time"]), ("2026-07-19", "07:00", "13:30"))
        self.assertEqual(self.rows[0]["outage_until"], "2026-09-19")

    def test_times_written_without_the_hour_word_or_the_part_of_day(self):
        times = lambda word: next((r["from_time"], r["to_time"]) for r in self.rows if word in r["title"])
        self.assertEqual(times("পুঠিয়াবাড়ি"), ("08:00", "16:00"))
        self.assertEqual(times("নওগাঁ ২৩০/১৩২/৩৩"), ("07:00", "10:30"))

    def test_night_hours_cross_midnight(self):
        row = ('<tr class="table-tr"><td data-column="title">রাজশাহী দপ্তরের লাইনের কাজের জন্য আগামী ০১/১০/২০২৬ তারিখ '
               '{} বিদ্যুৎ সরবরাহ বন্ধ থাকবে।</td><td data-column="publish_date"> <span>৩০-০৯-২০২৬</span></td></tr>')
        times = lambda text: next((r["from_time"], r["to_time"]) for r in utilities.parse_nesco(row.format(text), PLACES))
        self.assertEqual(times("রাত ১০ ঘটিকা হইতে রাত ২ ঘটিকা পর্যন্ত"), ("22:00", "02:00"))
        self.assertEqual(times("রাত ১২ ঘটিকা হইতে ভোর ৫ ঘটিকা পর্যন্ত"), ("00:00", "05:00"))

    def test_all_rows_on_the_page_are_kept(self):
        self.assertEqual(len(self.rows), 10)

    def test_changed_layout_raises(self):
        with self.assertRaises(ValueError):
            utilities.parse_nesco("<table></table>", PLACES)


if __name__ == "__main__":
    unittest.main()
