import json
import urllib.request
import urllib.error

URLS = {
    "IP": "https://api.ipify.org?format=json",
    "Binance Futures": "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=2",
    "Bybit": "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=2",
    "OKX": "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT-SWAP&bar=1m&limit=2",
    "Bitget": "https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=1m&limit=2",
    "BingX": "https://open-api.bingx.com/openApi/swap/v3/quote/klines?symbol=BTC-USDT&interval=1m&limit=2",
}

for name, url in URLS.items():
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.load(response)
            print(name, "HTTP", response.status)
            if name == "IP":
                print("Server IP:", data)
            elif isinstance(data, dict):
                print("API code:", data.get("code", data.get("retCode")))
            else:
                print("Rows:", len(data))
    except urllib.error.HTTPError as e:
        print(name, "HTTP ERROR", e.code)
    except Exception as e:
        print(name, "ERROR", str(e)[:150])
