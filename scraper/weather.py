#!/usr/bin/env python3
"""Fetch hourly Dhaka temperature and humidity from Open-Meteo (not a government source).

weather.csv          observed history (reanalysis archive, recent days from the forecast model's past hours)
weather_forecast.csv next 16 days, overwritten every run
weather_normals.csv  average daily mean/max temperature and humidity per calendar day, 2021-2025
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import json

from pgb import BD_TIME, ROOT, get, read_csv, write_csv
from sources import merge_by

PLACE = "latitude=23.81&longitude=90.41&timezone=Asia%2FDhaka&hourly=temperature_2m,relative_humidity_2m"
FORECAST_URL = f"https://api.open-meteo.com/v1/forecast?{PLACE}&forecast_days=16&past_days=7"
ARCHIVE_URL = f"https://archive-api.open-meteo.com/v1/archive?{PLACE}" + "&start_date={}&end_date={}"
COLUMNS = ["timestamp", "temp_c", "humidity_pct"]


def hourly(payload: dict) -> list[dict]:
    if payload.get("utc_offset_seconds") != 6 * 3600:
        raise ValueError("Open-Meteo: expected Bangladesh time (UTC+6)")
    h = payload["hourly"]
    return [{"timestamp": t, "temp_c": temp, "humidity_pct": hum}
            for t, temp, hum in zip(h["time"], h["temperature_2m"], h["relative_humidity_2m"])
            if temp is not None]


def split(rows: list[dict], now: str) -> tuple[list[dict], list[dict]]:
    return [r for r in rows if r["timestamp"] <= now], [r for r in rows if r["timestamp"] > now]


def daily_normals(rows: list[dict]) -> list[dict]:
    days = defaultdict(list)
    for r in rows:
        days[r["timestamp"][:10]].append(r)
    by_month_day = defaultdict(list)
    for day, hours in days.items():
        temps = [float(h["temp_c"]) for h in hours]
        by_month_day[day[5:]].append((sum(temps) / len(temps), max(temps),
                                      sum(float(h["humidity_pct"]) for h in hours) / len(hours)))
    mean = lambda v, i: round(sum(x[i] for x in v) / len(v), 2)
    return [{"month_day": md, "mean_temp_c": mean(v, 0), "max_temp_c": mean(v, 1), "mean_humidity_pct": mean(v, 2)}
            for md, v in sorted(by_month_day.items())]


def main() -> None:
    update()


def update() -> None:
    now = datetime.now(BD_TIME)
    history_path = ROOT / "data" / "weather.csv"
    history = read_csv(history_path)
    past, future = split(hourly(json.loads(get(FORECAST_URL))), now.strftime("%Y-%m-%dT%H:%M"))

    archive_end = now.date() - timedelta(days=6)
    archive_start = (date.fromisoformat(max(r["timestamp"] for r in history)[:10])
                     if history else now.date() - timedelta(days=400))
    archived = []
    if archive_start <= archive_end:
        archived = hourly(json.loads(get(ARCHIVE_URL.format(archive_start, archive_end))))

    write_csv(history_path, merge_by(history, past + archived, ("timestamp",)), COLUMNS)
    write_csv(ROOT / "data" / "weather_forecast.csv", future, COLUMNS)

    normals_path = ROOT / "data" / "weather_normals.csv"
    if not normals_path.exists():
        rows = hourly(json.loads(get(ARCHIVE_URL.format("2021-01-01", "2025-12-31"))))
        write_csv(normals_path, daily_normals(rows), ["month_day", "mean_temp_c", "max_temp_c", "mean_humidity_pct"])
    print(f"weather: {len(past) + len(archived)} history rows, {len(future)} forecast hours")


if __name__ == "__main__":
    main()
