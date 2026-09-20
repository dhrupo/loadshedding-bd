import math
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

import forecast  # noqa: E402

START = datetime(2026, 5, 1)


def temp_at(t):
    return 30 + 4 * math.sin((t.hour - 9) / 24 * 2 * math.pi) + (t.timetuple().tm_yday % 7) * 0.3


def world(days=90, supply=14000):
    demand, weather = [], []
    for i in range(days * 24):
        t = START + timedelta(hours=i)
        ts = t.strftime("%Y-%m-%dT%H:%M")
        temp, hum = temp_at(t), 70.0
        d = 8000 + 250 * temp + 600 * (18 <= t.hour <= 22) - (400 if t.weekday() == 4 else 0)
        demand.append({"timestamp": ts, "demand_mw": d, "supply_mw": min(d, supply), "loadshed_mw": max(0.0, d - supply)})
        weather.append({"timestamp": ts, "temp_c": temp, "humidity_pct": hum})
    return demand, weather


class HourlyForecastTest(unittest.TestCase):
    def test_recovers_a_temperature_driven_demand_curve(self):
        demand, weather = world()
        history, future = demand[:-24], demand[-24:]
        rows = forecast.next_hours(history, weather, hours=24)
        self.assertEqual([r["timestamp"] for r in rows], [r["timestamp"] for r in future])
        for got, want in zip(rows, future):
            self.assertAlmostEqual(got["demand_mw"], want["demand_mw"], delta=60)

    def test_no_loadshed_forecast_when_supply_has_always_met_demand(self):
        demand, weather = world(supply=30000)
        self.assertTrue(all(r["loadshed_mw"] == 0 for r in forecast.next_hours(demand[:-24], weather, hours=24)))

    def test_capped_supply_gives_evening_loadshed_and_never_negative(self):
        demand, weather = world(supply=15500)
        rows = forecast.next_hours(demand[:-24], weather, hours=24)
        self.assertTrue(all(r["loadshed_mw"] >= 0 for r in rows))
        self.assertTrue(all(r["loadshed_mw"] > 0 for r in rows if r["timestamp"][11:13] in ("19", "20", "21")))

    def test_band_contains_the_point_forecast(self):
        demand, weather = world()
        for r in forecast.next_hours(demand[:-24], weather, hours=24):
            self.assertLessEqual(r["demand_low_mw"], r["demand_mw"])
            self.assertGreaterEqual(r["demand_high_mw"], r["demand_mw"])

    def test_backtest_on_a_noiseless_world_is_nearly_exact(self):
        demand, weather = world()
        score = forecast.backtest_hours(demand, weather, days=7)
        self.assertEqual(score["days"], 7)
        self.assertLess(score["demand_mape_pct"], 1.0)

    def test_forecast_starts_from_where_demand_actually_is_after_a_sudden_drop(self):
        demand, weather = world()
        for r in demand[-36:]:
            r["demand_mw"] -= 1500
            r["supply_mw"] = min(r["demand_mw"], 14000)
        history, future = demand[:-24], demand[-24:]
        first = forecast.next_hours(history, weather, hours=24)[0]
        self.assertAlmostEqual(first["demand_mw"], future[0]["demand_mw"], delta=400)

    def test_needs_enough_history(self):
        demand, weather = world(days=3)
        with self.assertRaises(ValueError):
            forecast.next_hours(demand, weather, hours=24)


class OutlookTest(unittest.TestCase):
    def setUp(self):
        self.demand, weather = world(days=90)
        last = datetime.fromisoformat(self.demand[-1]["timestamp"])
        ahead = [{"timestamp": (last + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M"), "temp_c": 31.0, "humidity_pct": 70.0}
                 for h in range(1, 16 * 24 + 1)]
        self.weather = weather + ahead
        self.normals = [{"month_day": f"{m:02d}-{d:02d}", "mean_temp_c": 29.0, "max_temp_c": 33.0, "mean_humidity_pct": 70.0}
                        for m in range(1, 13) for d in range(1, 32)]

    def test_thirty_days_from_forecast_weather_then_normals(self):
        rows = forecast.next_days(self.demand, self.weather, self.normals, band=(-300, 1500), days=30)
        self.assertEqual(len(rows), 30)
        self.assertEqual(rows[0]["weather"], "forecast")
        self.assertEqual(rows[-1]["weather"], "normal")

    def test_range_is_the_backtest_band_around_the_point(self):
        for r in forecast.next_days(self.demand, self.weather, self.normals, band=(-300, 1500), days=30):
            self.assertAlmostEqual(r["demand_low_mw"], r["demand_peak_mw"] - 300)
            self.assertAlmostEqual(r["demand_high_mw"], r["demand_peak_mw"] + 1500)
            self.assertGreaterEqual(r["loadshed_low_mw"], 0)
            self.assertLessEqual(r["loadshed_low_mw"], r["loadshed_peak_mw"])
            self.assertLessEqual(r["loadshed_peak_mw"], r["loadshed_high_mw"])

    def test_warmer_days_mean_higher_demand(self):
        hot = [{**w, "temp_c": 36.0} if w["timestamp"] > self.demand[-1]["timestamp"] else w for w in self.weather]
        cool = [{**w, "temp_c": 26.0} if w["timestamp"] > self.demand[-1]["timestamp"] else w for w in self.weather]
        h = forecast.next_days(self.demand, hot, self.normals, band=(0, 0), days=5)
        c = forecast.next_days(self.demand, cool, self.normals, band=(0, 0), days=5)
        self.assertTrue(all(a["demand_peak_mw"] > b["demand_peak_mw"] for a, b in zip(h, c)))

    def test_backtest_reports_error_and_calibrated_band(self):
        score = forecast.backtest_days(self.demand, self.weather)
        self.assertGreater(score["origins"], 0)
        self.assertLessEqual(score["band_low_mw"], 0)
        self.assertGreaterEqual(score["band_high_mw"], 0)


class OutageHoursTest(unittest.TestCase):
    def test_share_of_energy_not_supplied_becomes_hours_per_home(self):
        rows = [{"timestamp": f"2026-09-01T{h:02d}:00", "demand_mw": 100.0, "supply_mw": 90.0} for h in range(24)]
        self.assertAlmostEqual(forecast.outage_hours(rows), 2.4)

    def test_no_cuts_means_zero_hours(self):
        rows = [{"timestamp": f"2026-09-01T{h:02d}:00", "demand_mw": 100.0, "supply_mw": 100.0} for h in range(24)]
        self.assertEqual(forecast.outage_hours(rows), 0.0)

    def test_outlook_days_carry_hours_range(self):
        demand, weather = world(days=90, supply=15500)
        last = datetime.fromisoformat(demand[-1]["timestamp"])
        ahead = [{"timestamp": (last + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M"), "temp_c": 31.0, "humidity_pct": 70.0}
                 for h in range(1, 16 * 24 + 1)]
        normals = [{"month_day": f"{m:02d}-{d:02d}", "mean_temp_c": 29.0, "max_temp_c": 33.0, "mean_humidity_pct": 70.0}
                   for m in range(1, 13) for d in range(1, 32)]
        rows = forecast.next_days(demand, weather + ahead, normals, band=(-300, 1500), days=30)
        for r in rows:
            self.assertGreaterEqual(r["outage_hours_low"], 0)
            self.assertLessEqual(r["outage_hours_low"], r["outage_hours"])
            self.assertLessEqual(r["outage_hours"], r["outage_hours_high"])
            self.assertLessEqual(r["outage_hours_high"], 24)
        self.assertTrue(any(r["outage_hours_high"] > 0 for r in rows))

    def test_ample_supply_means_no_outage_hours_ahead(self):
        demand, weather = world(days=90, supply=30000)
        last = datetime.fromisoformat(demand[-1]["timestamp"])
        ahead = [{"timestamp": (last + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M"), "temp_c": 31.0, "humidity_pct": 70.0}
                 for h in range(1, 16 * 24 + 1)]
        normals = [{"month_day": f"{m:02d}-{d:02d}", "mean_temp_c": 29.0, "max_temp_c": 33.0, "mean_humidity_pct": 70.0}
                   for m in range(1, 13) for d in range(1, 32)]
        rows = forecast.next_days(demand, weather + ahead, normals, band=(0, 0), days=10)
        self.assertTrue(all(r["outage_hours"] == 0 for r in rows))

    def test_each_likely_day_has_a_cut_window_around_the_worst_hour(self):
        demand, weather = world(days=90, supply=15500)
        last = datetime.fromisoformat(demand[-1]["timestamp"])
        ahead = [{"timestamp": (last + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M"), "temp_c": 31.0, "humidity_pct": 70.0}
                 for h in range(1, 16 * 24 + 1)]
        normals = [{"month_day": f"{m:02d}-{d:02d}", "mean_temp_c": 29.0, "max_temp_c": 33.0, "mean_humidity_pct": 70.0}
                   for m in range(1, 13) for d in range(1, 32)]
        rows = forecast.next_days(demand, weather + ahead, normals, band=(-300, 1500), days=10)
        shortfall = {}
        for r in demand[-14 * 24:]:
            h = int(r["timestamp"][11:13])
            shortfall[h] = shortfall.get(h, 0) + max(0.0, r["demand_mw"] - 15500)
        worst = max(shortfall, key=shortfall.get)
        windows = [(r["cut_from"], r["cut_to"]) for r in rows if r["outage_hours"] > 0]
        self.assertTrue(windows)
        for start, end in windows:
            self.assertLessEqual(start, worst)
            self.assertLess(worst, end)
            self.assertLessEqual(end, 24)

    def test_no_window_when_no_cuts_expected(self):
        demand, weather = world(days=90, supply=30000)
        last = datetime.fromisoformat(demand[-1]["timestamp"])
        ahead = [{"timestamp": (last + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M"), "temp_c": 31.0, "humidity_pct": 70.0}
                 for h in range(1, 16 * 24 + 1)]
        normals = [{"month_day": f"{m:02d}-{d:02d}", "mean_temp_c": 29.0, "max_temp_c": 33.0, "mean_humidity_pct": 70.0}
                   for m in range(1, 13) for d in range(1, 32)]
        rows = forecast.next_days(demand, weather + ahead, normals, band=(0, 0), days=5)
        self.assertTrue(all(r["cut_from"] is None and r["cut_to"] is None for r in rows))

    def test_backtest_scores_the_window(self):
        demand, weather = world(days=90, supply=15500)
        self.assertIsNotNone(forecast.backtest_days(demand, weather)["window_hit_pct"])

    def test_backtest_scores_hours(self):
        demand, weather = world(days=90, supply=15500)
        self.assertIsNotNone(forecast.backtest_days(demand, weather)["outage_hours_mae"])


class BpdbScoreTest(unittest.TestCase):
    def test_official_forecast_scored_against_next_days_actual(self):
        forecasts = [{"date": "2026-09-16", "eve_peak_demand_mw": "18000"}, {"date": "2026-09-17", "eve_peak_demand_mw": "18020"}]
        actuals = [{"date": "2026-09-16", "eve_peak_demand_mw": "17857"}]
        score = forecast.score_bpdb(forecasts, actuals)
        self.assertEqual(score["days"], 1)
        self.assertAlmostEqual(score["eve_peak_demand_mape_pct"], abs(18000 - 17857) / 17857 * 100, places=2)


if __name__ == "__main__":
    unittest.main()
