
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://fapi.binance.com/fapi/v1/klines"
SYMBOL = "BTCUSDT"

INTERVALS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def fetch_candles(interval, duration):
    params = urllib.parse.urlencode({
        "symbol": SYMBOL,
        "interval": interval,
        "limit": 350,
    })

    request = urllib.request.Request(
        f"{BASE_URL}?{params}",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        rows = json.load(response)

    if not isinstance(rows, list):
        raise ValueError(f"{interval}: unexpected API response")

    now_ms = int(time.time() * 1000)

    closed = [
        row for row in rows
        if int(row[6]) < now_ms
    ][-300:]

    if len(closed) != 300:
        raise ValueError(
            f"{interval}: only {len(closed)} closed candles"
        )

    for previous, current in zip(closed, closed[1:]):
        if int(current[0]) - int(previous[0]) != duration:
            raise ValueError(f"{interval}: missing candles")

    if now_ms - int(closed[-1][6]) > duration * 2:
        raise ValueError(f"{interval}: stale data")

    return [
        {
            "open_time": int(row[0]),
            "close_time": int(row[6]),
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5],
            "quote_volume": row[7],
            "trades": int(row[8]),
        }
        for row in closed
    ]


def main():
    result = {
        "symbol": SYMBOL,
        "market": "Binance USD-M Futures",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "candles": {},
    }

    for interval, duration in INTERVALS.items():
        result["candles"][interval] = fetch_candles(
            interval, duration
        )
        print(
            interval,
            "OK",
            len(result["candles"][interval]),
        )

    Path("market_data.json").write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    print("market_data.json saved")


if __name__ == "__main__":
    main()
