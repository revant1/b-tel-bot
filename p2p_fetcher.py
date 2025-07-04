import aiohttp

BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
PAIRS = ["USDT", "INR"]
PAYMENT_METHODS = []

async def fetch_binance_p2p(session, rows=20):
    payload = {
        "asset": PAIRS[0],
        "fiat": PAIRS[1],
        "merchantCheck": False,
        "page": 1,
        "rows": rows,
        "tradeType": "SELL",
        "payTypes": PAYMENT_METHODS
    }
    headers = {"Content-Type": "application/json"}
    async with session.post(BINANCE_P2P_URL, json=payload, headers=headers) as resp:
        data = await resp.json()
        return data.get("data", [])

async def get_top_sellers_under_threshold(threshold, rows=20, limit=5):
    async with aiohttp.ClientSession() as session:
        ads = await fetch_binance_p2p(session, rows=rows)
        filtered_ads = []
        for ad in ads:
            adv = ad.get("adv", {})
            price_str = adv.get("price")
            if price_str:
                try:
                    price = float(price_str)
                    if price <= threshold:
                        filtered_ads.append(ad)
                except ValueError:
                    continue
            if len(filtered_ads) == limit:
                break
        return filtered_ads
