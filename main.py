import asyncio
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode
import logging

# ==================== CONFIG ====================

THRESHOLD_PRICE = 83.5  # Alert if price <= this
PAIRS = ["USDT", "INR"]
PAYMENT_METHODS = []  # Add payment methods if needed
# ================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def fetch_binance_p2p(session, rows=5):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {
        "asset": PAIRS[0],
        "fiat": PAIRS[1],
        "merchantCheck": False,
        "page": 1,
        "rows": rows,
        "tradeType": "BUY",
        "payTypes": PAYMENT_METHODS
    }
    headers = {"Content-Type": "application/json"}
    async with session.post(url, json=payload, headers=headers) as resp:
        data = await resp.json()
        return data.get("data", [])

async def send_top5_prices():
    async with aiohttp.ClientSession() as session:
        ads = await fetch_binance_p2p(session, rows=5)
        message = "<b>Top 5 USDT-INR Sellers:</b>\n\n"
        for idx, ad in enumerate(ads, 1):
            adv = ad.get("adv", {})
            price = adv.get("price", "N/A")
            available = adv.get("surplusAmount", "N/A")
            min_single_trans = adv.get("minSingleTransAmount", "N/A")
            max_single_trans = adv.get("maxSingleTransAmount", "N/A")

            advertiser = ad.get("advertiser", {})
            nickname = advertiser.get("nickName", "N/A")
            user_no = advertiser.get("userNo")
            link = f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={user_no}" if user_no else "https://p2p.binance.com/en"

            message += (
                f"{idx}. <b>{price} INR</b> | {available} USDT | {nickname}\n"
                f"Min: {min_single_trans} | Max: {max_single_trans}\n"
                f"<a href=\"{link}\">🔗 View & Buy</a>\n\n"
            )

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

async def check_threshold_and_alert():
    async with aiohttp.ClientSession() as session:
        ads = await fetch_binance_p2p(session, rows=5)
        for ad in ads:
            adv = ad.get("adv", {})
            price_str = adv.get("price")
            if price_str:
                try:
                    price = float(price_str)
                except ValueError:
                    price = 999999  # Ignore if parsing fails
            else:
                price = 999999

            if price <= THRESHOLD_PRICE:
                available = adv.get("surplusAmount", "N/A")
                min_single_trans = adv.get("minSingleTransAmount", "N/A")
                max_single_trans = adv.get("maxSingleTransAmount", "N/A")

                advertiser = ad.get("advertiser", {})
                nickname = advertiser.get("nickName", "N/A")
                user_no = advertiser.get("userNo")
                link = f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={user_no}" if user_no else "https://p2p.binance.com/en"

                message = (
                    f"🚨 <b>Alert: Price Below Threshold!</b>\n\n"
                    f"<b>Price:</b> {price} INR\n"
                    f"<b>Seller:</b> {nickname}\n"
                    f"<b>Available:</b> {available} USDT\n"
                    f"<b>Min:</b> {min_single_trans} | <b>Max:</b> {max_single_trans}\n"
                    f"<a href=\"{link}\">🔗 View & Buy</a>"
                )

                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                break

async def periodic_tasks():
    while True:
        try:
            await send_top5_prices()
        except Exception as e:
            logging.error(f"Error in top5 fetch: {e}")
        await asyncio.sleep(3600)  # 5 min

async def threshold_task():
    while True:
        try:
            await check_threshold_and_alert()
        except Exception as e:
            logging.error(f"Error in threshold check: {e}")
        await asyncio.sleep(3600)  # 1 min

async def fetch_and_print_chat_id():
    updates = await bot.get_updates()
    if updates:
        chat_id = updates[-1].message.chat.id
        print(f"✅ Detected CHAT_ID: {chat_id}")
        print("🔹 Replace TELEGRAM_CHAT_ID in your script with this ID and rerun.")
        await bot.send_message(chat_id=chat_id, text="✅ Bot test message successful.")
        return chat_id
    else:
        print("⚠️ No updates found. Send a message to your bot first in Telegram and rerun.")
        return None

async def main():
    global TELEGRAM_CHAT_ID

    if TELEGRAM_CHAT_ID == "":
        chat_id = await fetch_and_print_chat_id()
        if chat_id:
            TELEGRAM_CHAT_ID = chat_id
        else:
            return

    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Binance P2P Alert Bot Started Successfully.")

    await asyncio.gather(
        periodic_tasks(),
        threshold_task()
    )

if __name__ == "__main__":
    asyncio.run(main())
