import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

import weather  # noqa: E402

PAYLOAD = json.loads((ROOT / "tests" / "fixtures" / "openmeteo_forecast.json").read_text())


class HourlyTest(unittest.TestCase):
    def test_rows_keep_timestamp_temperature_humidity(self):
        rows = weather.hourly(PAYLOAD)
        self.assertEqual(len(rows), 72)
        self.assertEqual(rows[0]["timestamp"], "2026-09-18T00:00")
        self.assertEqual(set(rows[0]), {"timestamp", "temp_c", "humidity_pct"})
        self.assertEqual(rows[0]["temp_c"], PAYLOAD["hourly"]["temperature_2m"][0])

    def test_wrong_timezone_is_rejected(self):
        with self.assertRaises(ValueError):
            weather.hourly({**PAYLOAD, "utc_offset_seconds": 0})


class SplitTest(unittest.TestCase):
    def test_past_hours_are_history_future_hours_are_forecast(self):
        rows = weather.hourly(PAYLOAD)
        past, future = weather.split(rows, "2026-09-19T11:00")
        self.assertEqual(past[-1]["timestamp"], "2026-09-19T11:00")
        self.assertEqual(future[0]["timestamp"], "2026-09-19T12:00")
        self.assertEqual(len(past) + len(future), 72)


class NormalsTest(unittest.TestCase):
    def test_daily_normals_average_each_calendar_day_across_years(self):
        rows = [
            {"timestamp": "2024-09-20T13:00", "temp_c": 32.0, "humidity_pct": 70},
            {"timestamp": "2024-09-20T02:00", "temp_c": 26.0, "humidity_pct": 90},
            {"timestamp": "2025-09-20T14:00", "temp_c": 34.0, "humidity_pct": 60},
            {"timestamp": "2025-09-20T03:00", "temp_c": 27.0, "humidity_pct": 80},
        ]
        self.assertEqual(weather.daily_normals(rows), [
            {"month_day": "09-20", "mean_temp_c": 29.75, "max_temp_c": 33.0, "mean_humidity_pct": 75.0},
        ])


if __name__ == "__main__":
    unittest.main()
