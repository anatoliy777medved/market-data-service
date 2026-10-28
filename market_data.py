
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"
SYMBOL = "BTC-USDT"

INTERVALS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

LIMIT = 350


def fetch_candles(interval, duration):
    params = urllib.parse.urlencode({
        "symbol": SYMBOL,
        "interval": interval,
        "limit": LIMIT,
    })

    request = urllib.request.Request(
        f"{BASE_URL}?{params}",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.load(response)

    if not isinstance(payload, dict) or str(payload.get("code")) != "0":
        raise ValueError(f"BingX {interval}: API error: {str(payload)[:250]}")

    rows = payload.get("data")
    if not isinstance(rows, list) or len(rows) < 300:
        raise ValueError(f"BingX {interval}: insufficient candle data")

    parsed = []

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"BingX {interval}: unexpected candle format")

        start = int(row["time"])

        if start < 1_000_000_000_000:
            raise ValueError(f"BingX {interval}: unexpected timestamp units")

        candle = {
            "open_time": start,
            "close_time": start + duration - 1,
            "open": str(row["open"]),
            "high": str(row["high"]),
            "low": str(row["low"]),
            "close": str(row["close"]),
            "volume": str(row["volume"]),
        }

        if not (
            float(candle["low"]) <= float(candle["open"]) <= float(candle["high"])
            and float(candle["low"]) <= float(candle["close"]) <= float(candle["high"])
        ):
            raise ValueError(f"BingX {interval}: invalid OHLC")

        parsed.append(candle)

    parsed.sort(key=lambda c: c["open_time"])

    now_ms = int(time.time() * 1000)
    closed = [
        c for c in parsed
        if c["close_time"] < now_ms - 1000
    ]

    if len(closed) < 300:
        raise ValueError(f"BingX {interval}: too few closed candles")

    if len({c["open_time"] for c in closed}) != len(closed):
        raise ValueError(f"BingX {interval}: duplicate candles")

    for previous, current in zip(closed, closed[1:]):
        if current["open_time"] - previous["open_time"] != duration:
            raise ValueError(f"BingX {interval}: gap in candles")

    age = now_ms - (closed[-1]["close_time"] + 1)

    if not 0 <= age <= 2 * duration + 60_000:
        raise ValueError(f"BingX {interval}: stale candles ({age} ms)")

    return closed


def main():
    result = {
        "symbol": SYMBOL,
        "market": "BingX USDT-margined perpetual",
        "source": BASE_URL,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "candles": {},
    }

    for interval, duration in INTERVALS.items():
        candles = fetch_candles(interval, duration)
        result["candles"][interval] = candles
        print(interval, "OK", len(candles), "last closed", candles[-1]["close_time"])

    Path("market_data.json").write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print("market_data.json saved")


if __name__ == "__main__":
    main()
