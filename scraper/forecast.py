#!/usr/bin/env python3
"""Forecast demand and loadshed from PGB history and Open-Meteo weather; write data/forecast.json.

next_hours: the next 24 hours, hourly (least squares on hour, weekday, weather, recent level).
next_days: a 30-day daily outlook as a range. Both are scored on past days.
Hourly loadshed = half of yesterday's loadshed at that hour + half of (demand - last 3 days' supply).
Daily peak = last 14 days' average peak, adjusted for how much warmer the day is than those 14 days.
The daily range is the 10th-90th percentile of the backtest's own errors, not the model's fit.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import json

import numpy as np

from pgb import BD_TIME, ROOT, read_csv

TRAIN_DAYS = 60
ANCHOR_HOURS = 3
ANCHOR_DECAY = 0.9
LEVEL_HOURS = range(24, 24 + 168)


def _hourly(rows):
    return [{"timestamp": r["timestamp"], **{k: float(r[k]) for k in ("demand_mw", "supply_mw")}}
            for r in rows if r["timestamp"].endswith(":00") and r.get("demand_mw") not in (None, "")]


def _weather(rows):
    return {r["timestamp"]: (float(r["temp_c"]), float(r["humidity_pct"])) for r in rows}


def _ts(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M")


def _level(demand_at: dict, t: datetime):
    values = [demand_at[k] for h in LEVEL_HOURS if (k := _ts(t - timedelta(hours=h))) in demand_at]
    return sum(values) / len(values) if len(values) >= 100 else None


def _hour_x(t: datetime, temp: float, hum: float, level: float) -> list[float]:
    return [float(t.hour == h) for h in range(24)] + [temp, temp * temp, hum, float(t.weekday() == 4), float(t.weekday() == 5), level]


def _fit(xs, ys):
    x, y = np.array(xs), np.array(ys)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    return beta, min(0.0, float(np.quantile(residuals, 0.1))), max(0.0, float(np.quantile(residuals, 0.9)))


def next_hours(history: list[dict], weather: list[dict], hours: int = 24, decay: float = ANCHOR_DECAY) -> list[dict]:
    rows, w = _hourly(history), _weather(weather)
    demand_at = {r["timestamp"]: r["demand_mw"] for r in rows}
    origin = datetime.fromisoformat(rows[-1]["timestamp"])
    xs, ys = [], []
    for r in rows:
        t = datetime.fromisoformat(r["timestamp"])
        if t <= origin - timedelta(days=TRAIN_DAYS) or r["timestamp"] not in w:
            continue
        level = _level(demand_at, t)
        if level is not None:
            xs.append(_hour_x(t, *w[r["timestamp"]], level))
            ys.append(r["demand_mw"])
    if len(xs) < 14 * 24:
        raise ValueError(f"forecast: need 14 days of history with weather, have {len(xs) // 24}")
    beta, q10, q90 = _fit(xs, ys)
    # Start from where demand actually is: the miss on the last few observed hours fades out over the day.
    recent = [(r, datetime.fromisoformat(r["timestamp"])) for r in rows[-ANCHOR_HOURS:] if r["timestamp"] in w]
    misses = [r["demand_mw"] - float(np.dot(_hour_x(t, *w[r["timestamp"]], _level(demand_at, t)), beta))
              for r, t in recent if _level(demand_at, t) is not None]
    anchor = sum(misses) / len(misses) if misses else 0.0

    by_ts = {r["timestamp"]: r for r in rows}

    def recent(t: datetime, days: range) -> list[dict]:
        return [r for d in days if (r := by_ts.get(_ts(t - timedelta(days=d))))]

    out = []
    for h in range(1, hours + 1):
        t = origin + timedelta(hours=h)
        key = _ts(t)
        if key not in w:
            raise ValueError(f"forecast: no weather for {key}")
        demand = float(np.dot(_hour_x(t, *w[key], _level(demand_at, t)), beta)) + anchor * decay ** h
        last3 = recent(t, range(1, 4))
        supply = sum(r["supply_mw"] for r in last3) / len(last3)
        yesterday = max(0.0, last3[0]["demand_mw"] - last3[0]["supply_mw"])
        out.append({
            "timestamp": key,
            "demand_mw": demand, "demand_low_mw": demand + q10, "demand_high_mw": demand + q90,
            "supply_mw": supply, "loadshed_mw": 0.5 * yesterday + 0.5 * max(0.0, demand - supply),
            "temp_c": w[key][0],
        })
    return out


def backtest_hours(history: list[dict], weather: list[dict], days: int = 30, decay: float = ANCHOR_DECAY) -> dict:
    rows = _hourly(history)
    last_midnight = next(i for i in range(len(rows) - 1, -1, -1) if rows[i]["timestamp"].endswith("T23:00")) + 1
    rows = rows[:last_midnight]
    demand_err, shed_err, eve_err, used = [], [], [], 0
    for k in range(days, 0, -1):
        cut = len(rows) - 24 * k
        actual = {r["timestamp"]: r for r in rows[cut:cut + 24]}
        try:
            predicted = next_hours(rows[:cut], weather, 24, decay)
        except ValueError:
            continue
        used += 1
        for p in predicted:
            a = actual.get(p["timestamp"])
            if not a:
                continue
            demand_err.append(abs(p["demand_mw"] - a["demand_mw"]) / a["demand_mw"] * 100)
            shed_err.append(abs(p["loadshed_mw"] - max(0.0, a["demand_mw"] - a["supply_mw"])))
            if p["timestamp"].endswith("T21:00"):
                eve_err.append(abs(p["demand_mw"] - a["demand_mw"]) / a["demand_mw"] * 100)
    return {"days": used,
            "demand_mape_pct": round(float(np.mean(demand_err)), 2) if demand_err else None,
            "loadshed_mae_mw": round(float(np.mean(shed_err))) if shed_err else None,
            "eve_peak_demand_mape_pct": round(float(np.mean(eve_err)), 2) if eve_err else None}


def _daily(history, weather):
    peak_d, peak_s = defaultdict(float), defaultdict(float)
    for r in _hourly(history):
        d = r["timestamp"][:10]
        peak_d[d] = max(peak_d[d], r["demand_mw"])
        peak_s[d] = max(peak_s[d], r["supply_mw"])
    temps = defaultdict(list)
    for r in weather:
        temps[r["timestamp"][:10]].append((float(r["temp_c"]), float(r["humidity_pct"])))
    return peak_d, peak_s, temps


def outage_hours(rows: list[dict]) -> float:
    """Average hours without power per home that day: the unserved share of energy, spread over 24 hours."""
    demand = sum(float(r["demand_mw"]) for r in rows)
    unserved = sum(max(0.0, float(r["demand_mw"]) - float(r["supply_mw"])) for r in rows)
    return 24 * unserved / demand if demand else 0.0


def _hours_by_day(history):
    days = defaultdict(list)
    for r in _hourly(history):
        days[r["timestamp"][:10]].append(r)
    return days


def _day_profile(by_day, dates):
    shape, cap = defaultdict(list), defaultdict(float)
    for d in dates:
        peak = max(r["demand_mw"] for r in by_day[d])
        for r in by_day[d]:
            shape[r["timestamp"][11:13]].append(r["demand_mw"] / peak)
            cap[r["timestamp"][11:13]] = max(cap[r["timestamp"][11:13]], r["supply_mw"])
    return {h: sum(v) / len(v) for h, v in shape.items()}, cap


def _predicted_hours(peak: float, shape: dict, cap: dict, recent: float) -> float:
    rows = [{"demand_mw": peak * shape[h], "supply_mw": cap[h]} for h in shape]
    # Half this day's model, half the last 14 days' actual average: the blend beat both in the backtest.
    return 0.5 * outage_hours(rows) + 0.5 * recent


def _recent_shed(by_day, dates) -> dict:
    shed = defaultdict(list)
    for d in dates:
        for r in by_day[d]:
            shed[r["timestamp"][11:13]].append(max(0.0, r["demand_mw"] - r["supply_mw"]))
    return {h: sum(v) / len(v) for h, v in shed.items()}


def _cut_window(peak: float, shape: dict, cap: dict, recent_shed: dict):
    """Hours around the worst expected shortfall: half this day's model, half when cuts actually fell lately."""
    hours = sorted(shape)
    weight = [0.5 * max(0.0, peak * shape[h] - cap[h]) + 0.5 * recent_shed.get(h, 0.0) for h in hours]
    top = max(weight, default=0.0)
    if top <= 0:
        return None, None
    lo = hi = weight.index(top)
    while lo > 0 and weight[lo - 1] >= 0.5 * top:
        lo -= 1
    while hi < len(hours) - 1 and weight[hi + 1] >= 0.5 * top:
        hi += 1
    return int(hours[lo]), int(hours[hi]) + 1


def _daily_table(history, weather):
    peak_d, peak_s, temps = _daily(history, weather)
    days = sorted(d for d in peak_d if len(temps.get(d, [])) >= 20
                  and sum(1 for r in history if r["timestamp"].startswith(d)) >= 24)
    tmean = {d: sum(t for t, _ in temps[d]) / len(temps[d]) for d in temps if len(temps[d]) >= 20}
    return days, peak_d, peak_s, tmean


def _anomaly_model(days, peak_d, tmean, idx):
    xs, ys = [], []
    for j in range(max(14, idx - 59), idx + 1):
        window = days[j - 14:j]
        ys.append(peak_d[days[j]] - np.mean([peak_d[d] for d in window]))
        xs.append([1.0, tmean[days[j]] - np.mean([tmean[d] for d in window]), float(date.fromisoformat(days[j]).weekday() == 4)])
    beta, *_ = np.linalg.lstsq(np.array(xs), np.array(ys), rcond=None)
    last14 = days[idx - 13:idx + 1]
    level, temp_base = np.mean([peak_d[d] for d in last14]), np.mean([tmean[d] for d in last14])
    return lambda day, temp: float(level + beta[0] + beta[1] * (temp - temp_base) + beta[2] * (day.weekday() == 4))


def next_days(history: list[dict], weather: list[dict], normals: list[dict], band: tuple, days: int = 30) -> list[dict]:
    table, peak_d, peak_s, tmean = _daily_table(history, weather)
    if len(table) < 30:
        raise ValueError(f"outlook: need 30 days of history, have {len(table)}")
    predict = _anomaly_model(table, peak_d, tmean, len(table) - 1)
    origin = date.fromisoformat(table[-1])
    supply = max(peak_s[d] for d in table[-14:])
    by_day = _hours_by_day(history)
    shape, cap = _day_profile(by_day, table[-14:])
    recent = sum(outage_hours(by_day[d]) for d in table[-14:]) / 14
    recent_shed = _recent_shed(by_day, table[-14:])
    normal = {n["month_day"]: float(n["mean_temp_c"]) for n in normals}
    low, high = band
    out = []
    for i in range(1, days + 1):
        day = origin + timedelta(days=i)
        temp, source = ((tmean[day.isoformat()], "forecast") if day.isoformat() in tmean
                        else (normal[day.isoformat()[5:]], "normal"))
        demand = predict(day, temp)
        hours = round(_predicted_hours(demand, shape, cap, recent), 1)
        cut_from, cut_to = _cut_window(demand, shape, cap, recent_shed) if hours > 0 else (None, None)
        out.append({
            "date": day.isoformat(), "weather": source, "mean_temp_c": round(temp, 1),
            "demand_peak_mw": demand, "demand_low_mw": demand + low, "demand_high_mw": demand + high,
            "supply_peak_mw": supply,
            "loadshed_peak_mw": max(0.0, demand - supply),
            "loadshed_low_mw": max(0.0, demand + low - supply), "loadshed_high_mw": max(0.0, demand + high - supply),
            "outage_hours": hours, "cut_from": cut_from, "cut_to": cut_to,
            "outage_hours_low": round(_predicted_hours(demand + low, shape, cap, recent), 1),
            "outage_hours_high": round(_predicted_hours(demand + high, shape, cap, recent), 1),
        })
    return out


def backtest_days(history: list[dict], weather: list[dict], horizon: int = 30, step: int = 7) -> dict:
    table, peak_d, peak_s, tmean = _daily_table(history, weather)
    by_day = _hours_by_day(history)
    pct_err, shed_err, hour_err, window_hits, residuals, origins = [], [], [], [], [], 0
    for idx in range(45, len(table) - horizon, step):
        origins += 1
        predict = _anomaly_model(table, peak_d, tmean, idx)
        supply = max(peak_s[d] for d in table[idx - 13:idx + 1])
        shape, cap = _day_profile(by_day, table[idx - 13:idx + 1])
        recent = sum(outage_hours(by_day[d]) for d in table[idx - 13:idx + 1]) / 14
        recent_shed = _recent_shed(by_day, table[idx - 13:idx + 1])
        for d in table[idx + 1:idx + 1 + horizon]:
            pred, actual = predict(date.fromisoformat(d), tmean[d]), peak_d[d]
            hour_err.append(abs(_predicted_hours(pred, shape, cap, recent) - outage_hours(by_day[d])))
            gaps = [(r["demand_mw"] - r["supply_mw"], int(r["timestamp"][11:13])) for r in by_day[d]]
            worst_gap, worst_hour = max(gaps)
            start, end = _cut_window(pred, shape, cap, recent_shed)
            if worst_gap > 0 and start is not None:
                window_hits.append(start <= worst_hour < end)
            pct_err.append(abs(pred - actual) / actual * 100)
            residuals.append(actual - pred)
            shed_err.append(abs(max(0.0, pred - supply) - max(0.0, actual - peak_s[d])))
    if not residuals:
        return {"origins": 0, "demand_mape_pct": None, "loadshed_mae_mw": None, "outage_hours_mae": None, "window_hit_pct": None, "band_low_mw": 0.0, "band_high_mw": 0.0}
    return {"origins": origins,
            "demand_mape_pct": round(float(np.mean(pct_err)), 2),
            "loadshed_mae_mw": round(float(np.mean(shed_err))),
            "outage_hours_mae": round(float(np.mean(hour_err)), 2),
            "window_hit_pct": round(100 * float(np.mean(window_hits))) if window_hits else None,
            "band_low_mw": min(0.0, round(float(np.quantile(residuals, 0.1)))),
            "band_high_mw": max(0.0, round(float(np.quantile(residuals, 0.9))))}


def score_bpdb(forecasts: list[dict], actuals: list[dict]) -> dict:
    actual = {r["date"]: float(r["eve_peak_demand_mw"]) for r in actuals}
    errors = [abs(float(f["eve_peak_demand_mw"]) - actual[f["date"]]) / actual[f["date"]] * 100
              for f in forecasts if f["date"] in actual]
    return {"days": len(errors), "eve_peak_demand_mape_pct": round(float(np.mean(errors)), 2) if errors else None}


def main() -> None:
    update()


def update() -> None:
    data = ROOT / "data"
    demand = read_csv(data / "demand.csv")
    weather = read_csv(data / "weather.csv") + read_csv(data / "weather_forecast.csv")
    history_weather = read_csv(data / "weather.csv")
    result = {
        "generated_at": datetime.now(BD_TIME).strftime("%Y-%m-%dT%H:%M"),
        "next_hours": next_hours(demand, weather, 24),
        "next_hours_score": backtest_hours(demand, history_weather, 30),
        "next_days_score": backtest_days(demand, history_weather),
        "bpdb_score": score_bpdb(read_csv(data / "bpdb_forecast.csv"), read_csv(data / "bpdb_daily.csv")),
    }
    score = result["next_days_score"]
    result["next_days"] = next_days(demand, weather, read_csv(data / "weather_normals.csv"),
                                    (score["band_low_mw"], score["band_high_mw"]), 30)
    ahead = result["next_hours"]
    result["next_24h_outage_hours"] = round(outage_hours([{"demand_mw": r["demand_mw"], "supply_mw": r["demand_mw"] - r["loadshed_mw"]} for r in ahead]), 1)
    for section in ("next_hours", "next_days"):
        result[section] = [{k: round(v) if isinstance(v, float) and k.endswith("_mw") else v for k, v in r.items()}
                           for r in result[section]]
    tmp = data / "forecast.json.tmp"
    tmp.write_text(json.dumps(result, indent=1))
    tmp.replace(data / "forecast.json")
    print(f"forecast: {result['next_hours_score']} {result['next_days_score']} bpdb {result['bpdb_score']}")


if __name__ == "__main__":
    main()
