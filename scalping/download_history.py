import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_URL = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"
SYMBOL = "BTC-USDT"
INTERVALS = ["1m", "5m", "15m", "1h", "4h"]
STEP_MS = {"1m": 60000, "5m": 300000, "15m": 900000,
           "1h": 3600000, "4h": 14400000}
OUTPUT = Path(__file__).resolve().parent / "history"
OUTPUT.mkdir(exist_ok=True)


def get_candles(interval, start_ms, end_ms):
    params = urllib.parse.urlencode({
        "symbol": SYMBOL,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": 1000,
    })
    request = urllib.request.Request(
        BASE_URL + "?" + params,
        headers={"User-Agent": "MarketHistoryResearch/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if str(payload.get("code")) != "0":
        raise RuntimeError(f"BingX error: {payload}")

    candles = payload.get("data")
    if not isinstance(candles, list):
        raise RuntimeError("Unexpected candle data")
    return candles


def normalize(candle):
    if isinstance(candle, dict):
        return [
            int(candle["time"]),
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle["volume"],
        ]
    if isinstance(candle, list) and len(candle) >= 6:
        return [int(candle[0]), *candle[1:6]]
    raise RuntimeError(f"Unexpected candle format: {candle}")


def download(interval, start_ms, end_ms):
    step = STEP_MS[interval]
    filename = OUTPUT / f"BTCUSDT_{interval}.csv"
    cursor = start_ms
    total = 0

    with filename.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "open", "high", "low", "close", "volume"])

        while cursor < end_ms:
            batch_end = min(cursor + 999 * step, end_ms)
            raw = get_candles(interval, cursor, batch_end)
            rows = sorted(
                (normalize(c) for c in raw),
                key=lambda row: row[0],
            )
            rows = [
                row for row in rows
                if cursor <= row[0] < end_ms
            ]

            if not rows:
                raise RuntimeError(
                    f"No candles for {interval} at {cursor}"
                )

            expected = cursor
            for row in rows:
                if row[0] != expected:
                    raise RuntimeError(
                        f"Missing candle in {interval}: "
                        f"expected {expected}, got {row[0]}"
                    )
                writer.writerow(row)
                expected += step
                total += 1

            cursor = expected
            if total % 10000 < len(rows):
                print(interval, "downloaded:", total, flush=True)
            time.sleep(0.25)

    print(interval, "DONE:", total, "candles", flush=True)


def main():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=183)
    for interval in INTERVALS:
        step = STEP_MS[interval]
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(now.timestamp() * 1000)
        start_ms = ((start_ms + step - 1) // step) * step
        end_ms = (end_ms // step) * step
        download(interval, start_ms, end_ms)


if __name__ == "__main__":
    main()
