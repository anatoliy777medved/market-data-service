import csv
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_URL = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"
SYMBOL = "BTC-USDT"
INTERVALS = ["1m", "5m", "15m", "1h", "4h"]
STEP_MS = {
    "1m": 60000,
    "5m": 300000,
    "15m": 900000,
    "1h": 3600000,
    "4h": 14400000,
}
OUTPUT = Path(__file__).resolve().parent / "data"
OUTPUT.mkdir(parents=True, exist_ok=True)

def get_candles(interval, start_ms, end_ms):
    params = urllib.parse.urlencode({
        "symbol": SYMBOL,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": 1000,
    })
    url = BASE_URL + "?" + params

    for attempt in range(8):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=35) as response:
                payload = json.load(response)

            if str(payload.get("code", 0)) == "0":
                candles = payload.get("data")
                if isinstance(candles, list):
                    return candles
                raise RuntimeError("Invalid candle data")

            error = str(payload.get("code"))
            if error not in ("100410", "100429", "429"):
                raise RuntimeError(f"BingX error: {payload}")

        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"Network error: {exc}", flush=True)

        delay = min(15 * (2 ** attempt), 180)
        print(f"Retry {attempt + 1}/8 in {delay}s", flush=True)
        time.sleep(delay)

    raise RuntimeError("BingX unavailable after 8 retries")

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
    raise RuntimeError("Unexpected candle format")

def read_last_timestamp(filename):
    if not filename.exists():
        return None
    last = None
    with filename.open(newline="") as f:
        for row in csv.reader(f):
            if row and row[0].isdigit():
                last = int(row[0])
    return last

def download(interval, start_ms, end_ms):
    step = STEP_MS[interval]
    filename = OUTPUT / f"BTCUSDT_{interval}.csv"
    last = read_last_timestamp(filename)
    cursor = max(start_ms, last + step) if last is not None else start_ms
    total = 0

    if cursor >= end_ms:
        print(interval, "already up to date", flush=True)
        return

    new_file = not filename.exists() or filename.stat().st_size == 0

    with filename.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["time", "open", "high", "low", "close", "volume"])

        while cursor < end_ms:
            batch_end = min(cursor + step * 999, end_ms)
            raw = get_candles(interval, cursor, batch_end)
            rows = sorted((normalize(c) for c in raw), key=lambda r: r[0])
            rows = [r for r in rows if cursor <= r[0] < end_ms]

            if not rows:
                raise RuntimeError(f"No candles at {interval}: {cursor}")

            expected = cursor
            for row in rows:
                if row[0] != expected:
                    raise RuntimeError(
                        f"Missing candle {interval}: expected {expected}, "
                        f"got {row[0]}"
                    )
                writer.writerow(row)
                expected += step
                total += 1

            f.flush()
            cursor = expected

            if total % 10000 < 1000:
                print(interval, "downloaded:", total, flush=True)

            time.sleep(1.5)

    print(interval, "DONE:", total, flush=True)

def main():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=183)

    for interval in INTERVALS:
        step = STEP_MS[interval]
        start_ms = (int(start.timestamp() * 1000) // step) * step
        end_ms = (int(now.timestamp() * 1000) // step) * step
        download(interval, start_ms, end_ms)

if __name__ == "__main__":
    main()
