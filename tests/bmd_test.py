import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

import bmd  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
PLACES = json.loads((ROOT / "static" / "geo" / "places.json").read_text(encoding="utf-8"))


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


class ForecastTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = bmd.parse_forecast(fixture("bmd_home.json"), fixture("bmd_stations.json"))

    def test_each_station_has_a_row_per_forecast_day(self):
        dhaka = [r for r in self.rows if r["station"] == "Dhaka"]
        self.assertEqual([r["date"] for r in dhaka], ["2026-09-20", "2026-09-21"])
        self.assertEqual(len(self.rows), 92)

    def test_row_carries_names_position_and_temperatures(self):
        ctg = next(r for r in self.rows if r["station"] == "Chattogram" and r["date"] == "2026-09-20")
        self.assertEqual((ctg["station_bn"], ctg["max_c"], ctg["min_c"]), ("চট্টগ্রাম", 32.3, 26.1))
        self.assertAlmostEqual(ctg["lat"], 22.27, places=1)
        self.assertAlmostEqual(ctg["lon"], 91.82, places=1)

    def test_changed_layout_raises(self):
        with self.assertRaises(ValueError):
            bmd.parse_forecast('{"data": {"Forecast": []}}', fixture("bmd_stations.json"))


class AlertTest(unittest.TestCase):
    def test_feed_lists_alert_links_newest_first(self):
        links = bmd.alert_links(fixture("bmd_cap_rss.xml"))
        self.assertEqual(len(links), 5)
        self.assertTrue(links[0].endswith("39b75b96-d793-43c7-9119-59fdfba2c5dd.xml"))

    def test_port_warning_in_both_languages_with_the_districts_it_covers(self):
        alert = bmd.parse_alert(fixture("bmd_cap_ports.xml"), PLACES)
        self.assertEqual(alert["id"], "39b75b96-d793-43c7-9119-59fdfba2c5dd")
        self.assertEqual((alert["event"], alert["severity"]), ("Wind", "Moderate"))
        self.assertEqual((alert["effective"], alert["expires"]), ("2026-09-10T04:00:00+00:00", "2026-09-11T04:00:00+00:00"))
        self.assertTrue(alert["headline"].startswith("Maritime Signal 3 Warning"))
        self.assertTrue(alert["headline_bn"].startswith("চট্টগ্রাম, কক্সবাজার"))
        self.assertTrue(alert["web"].startswith("https://cap.bmd.gov.bd/"))
        self.assertEqual(alert["districts"], ["Bagerhat", "Chittagong", "Cox's Bazar", "Patuakhali"])

    def test_division_warning_covers_whole_districts_but_not_neighbours_clipped_by_the_outline(self):
        alert = bmd.parse_alert(fixture("bmd_cap_divisions.xml"), PLACES)
        self.assertEqual(alert["headline_bn"], "")
        for district in ("Dhaka", "Noakhali", "Khulna", "Bhola", "Tangail"):
            self.assertIn(district, alert["districts"])
        for district in ("Sirajganj", "Habiganj", "Sylhet", "Rangpur"):
            self.assertNotIn(district, alert["districts"])


class AlertKindTest(unittest.TestCase):
    def test_real_alert_is_marked_actual(self):
        alert = bmd.parse_alert(fixture("bmd_cap_ports.xml"), PLACES)
        self.assertEqual((alert["status"], alert["msg_type"], alert["cancels"]), ("Actual", "Alert", []))

    def test_cancel_message_names_the_alert_it_withdraws(self):
        xml = fixture("bmd_cap_ports.xml").replace("<cap:msgType>Alert</cap:msgType>",
            "<cap:msgType>Cancel</cap:msgType><cap:references>swc@bmd.gov.bd,abc-123,2026-09-09T06:00:00+00:00</cap:references>")
        alert = bmd.parse_alert(xml, PLACES)
        self.assertEqual((alert["msg_type"], alert["cancels"]), ("Cancel", ["abc-123"]))

    def test_empty_outline_does_not_break_the_alert(self):
        xml = fixture("bmd_cap_ports.xml").replace("<cap:area><cap:areaDesc>Chattogram</cap:areaDesc>",
            "<cap:area><cap:areaDesc>Chattogram</cap:areaDesc><cap:polygon></cap:polygon>", 1)
        self.assertIn("Chittagong", bmd.parse_alert(xml, PLACES)["districts"])

    def test_feed_item_without_a_link_is_skipped(self):
        rss = fixture("bmd_cap_rss.xml").replace("<item>", "<item><title>no link</title></item><item>", 1)
        self.assertEqual(len(bmd.alert_links(rss)), 5)


class UpdateTest(unittest.TestCase):
    def test_a_broken_forecast_does_not_stop_the_warnings(self):
        calls = []
        original = bmd.update_forecast, bmd.update_alerts

        def broken():
            raise ValueError("BMD forecast: no station rows found")

        bmd.update_forecast, bmd.update_alerts = broken, lambda: calls.append("alerts") or []
        try:
            errors = bmd.update()
        finally:
            bmd.update_forecast, bmd.update_alerts = original
        self.assertEqual(calls, ["alerts"])
        self.assertEqual(len(errors), 1)
        self.assertIn("no station rows", errors[0])


class UpdateAlertsTest(unittest.TestCase):
    def test_known_alerts_are_not_downloaded_again(self):
        import tempfile
        fetched = []

        def get(url):
            fetched.append(url)
            if url == bmd.CAP_FEED:
                return fixture("bmd_cap_rss.xml")
            return fixture("bmd_cap_ports.xml").replace("39b75b96-d793-43c7-9119-59fdfba2c5dd", url.rsplit("/", 1)[-1][:-4])

        original = bmd.ROOT, bmd.get, bmd.places
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            bmd.ROOT, bmd.get, bmd.places = Path(d), get, lambda: PLACES
            try:
                bmd.update_alerts()
                first = len(fetched)
                bmd.update_alerts()
                saved = json.loads((Path(d) / "data" / "alerts.json").read_text(encoding="utf-8"))
            finally:
                bmd.ROOT, bmd.get, bmd.places = original
        self.assertEqual(first, 6)
        self.assertEqual(len(fetched), 7)
        self.assertEqual(saved[0]["districts"], ["Bagerhat", "Chittagong", "Cox's Bazar", "Patuakhali"])


if __name__ == "__main__":
    unittest.main()
