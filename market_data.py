import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://api.bybit.com/v5/market/kline"
SYMBOL = "BTCUSDT"
INTERVALS = {
    "1m": ("1", 60_000),
    "5m": ("5", 300_000),
    "15m": ("15", 900_000),
    "1h": ("60", 3_600_000),
    "4h": ("240", 14_400_000),
    "1d": ("D", 86_400_000),
}

def fetch_candles(interval, api_interval, duration):
    params = urllib.parse.urlencode({
        "category": "linear",
        "symbol": SYMBOL,
        "interval": api_interval,
        "limit": 350,
    })
    request = urllib.request.Request(
        f"{BASE_URL}?{params}",
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.load(response)

    if data.get("retCode") != 0:
        raise RuntimeError(str(data.get("retMsg")))

    rows = data["result"]["list"]
    now_ms = int(time.time() * 1000)

    closed = [
        row for row in rows
        if int(row[0]) + duration <= now_ms
    ]
    closed.sort(key=lambda row: int(row[0]))
    closed = closed[-300:]

    if len(closed) != 300:
        raise ValueError(f"{interval}: insufficient closed candles")

    for previous, current in zip(closed, closed[1:]):
        if int(current[0]) - int(previous[0]) != duration:
            raise ValueError(f"{interval}: candle gap detected")

    return [
        {
            "open_time": int(row[0]),
            "close_time": int(row[0]) + duration - 1,
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5],
            "turnover": row[6],
        }
        for row in closed
    ]

def main():
    result = {
        "symbol": SYMBOL,
        "market": "Bybit USDT Perpetual",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "candles": {},
    }

    for interval, (api_interval, duration) in INTERVALS.items():
        result["candles"][interval] = fetch_candles(
            interval, api_interval, duration
        )
        print(interval, "OK", len(result["candles"][interval]))

    Path("market_data.json").write_text(
        json.dumps(result, ensure_ascii=False),
        encoding="utf-8",
    )
    print("market_data.json saved")

if __name__ == "__main__":
    main()
