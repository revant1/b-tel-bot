import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, ApplicationBuilder
from telegram.constants import ParseMode

# Assuming p2p_fetcher.py exists and get_top_sellers_under_threshold is defined within it
from p2p_fetcher import get_top_sellers_under_threshold

# ==================== CONFIG ====================

DEFAULT_THRESHOLD = 91
# ================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# No global 'bot' instance needed if we're always using ContextTypes.DEFAULT_TYPE.bot
# or application.bot directly after the application is built.

async def format_and_send_sellers(bot_instance: Bot, sellers, threshold, chat_id):
    """
    Formats seller data and sends it to the specified chat.
    Takes a bot_instance to allow calling it from different contexts (e.g., periodic tasks, commands).
    """
    logging.info(f"Preparing message for {len(sellers)} sellers under {threshold} for chat {chat_id}")
    if not sellers:
        message = f"⚠️ No sellers found under {threshold} INR currently."
    else:
        message = f"<b>Top {len(sellers)} Sellers under {threshold} INR:</b>\n\n"
        for idx, ad in enumerate(sellers, 1):
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

    try:
        await bot_instance.send_message( # Use the passed bot_instance
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        logging.info(f"Message sent to chat {chat_id} successfully.")
    except Exception as e:
        logging.error(f"Error sending message to chat {chat_id}: {e}")


async def format_and_send_top_prices(bot_instance: Bot, sellers, chat_id, count=10):
    """
    Formats and sends top prices from sellers data.
    """
    logging.info(f"Preparing top {count} prices message for chat {chat_id}")
    if not sellers:
        message = "⚠️ No seller data available currently."
    else:
        # Sort sellers by price (highest first)
        sorted_sellers = sorted(sellers, key=lambda x: float(x.get("adv", {}).get("price", 0)), reverse=True)
        top_sellers = sorted_sellers[:count]
        
        message = f"<b>📈 Top {len(top_sellers)} Highest Prices:</b>\n\n"
        for idx, ad in enumerate(top_sellers, 1):
            adv = ad.get("adv", {})
            price = adv.get("price", "N/A")
            available = adv.get("surplusAmount", "N/A")
            
            advertiser = ad.get("advertiser", {})
            nickname = advertiser.get("nickName", "N/A")
            user_no = advertiser.get("userNo")
            link = f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={user_no}" if user_no else "https://p2p.binance.com/en"

            message += (
                f"{idx}. <b>{price} INR</b> | {available} USDT | {nickname}\n"
                f"<a href=\"{link}\">🔗 View Profile</a>\n\n"
            )

    try:
        await bot_instance.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        logging.info(f"Top prices message sent to chat {chat_id} successfully.")
    except Exception as e:
        logging.error(f"Error sending top prices message to chat {chat_id}: {e}")


async def periodic_send_default(context: ContextTypes.DEFAULT_TYPE):
    """Periodic task to send default threshold alerts."""
    bot_instance = context.bot # Get bot instance from context
    try:
        logging.info(f"Fetching sellers under default threshold {DEFAULT_THRESHOLD} for periodic alert.")
        sellers = await get_top_sellers_under_threshold(DEFAULT_THRESHOLD)
        await format_and_send_sellers(bot_instance, sellers, DEFAULT_THRESHOLD, TELEGRAM_CHAT_ID)
    except Exception as e:
        logging.error(f"Error in periodic fetch: {e}")

async def threshold_check_task(context: ContextTypes.DEFAULT_TYPE):
    """Fast-checking task for immediate threshold alerts."""
    bot_instance = context.bot # Get bot instance from context
    try:
        logging.info(f"Checking threshold alerts under {DEFAULT_THRESHOLD}.")
        sellers = await get_top_sellers_under_threshold(DEFAULT_THRESHOLD)
        if sellers:
            logging.info("Threshold match found; sending immediate alert (first seller).")
            await format_and_send_sellers(bot_instance, sellers[:1], DEFAULT_THRESHOLD, TELEGRAM_CHAT_ID)
        else:
            logging.info("No sellers found matching the threshold for immediate alert.")
    except Exception as e:
        logging.error(f"Error in threshold check: {e}")


async def top5_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Received /top5 command handler initiated.")
    
    if not update.effective_chat:
        logging.warning("No effective chat found for /top5 command.")
        return
    
    chat_id = update.effective_chat.id
    logging.info(f"Processing /top5 command from chat_id: {chat_id}")
    
    if update.message and update.message.text:
        logging.info(f"Full command received: {update.message.text}")

    args = context.args
    threshold = DEFAULT_THRESHOLD

    if args:
        try:
            parsed_arg = float(args[0].replace(',', ''))
            threshold = parsed_arg
            logging.info(f"Parsed threshold from command arguments: {threshold}")
        except ValueError:
            logging.warning(f"Invalid threshold argument received: '{args[0]}'. Using default threshold: {DEFAULT_THRESHOLD}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Invalid threshold provided: '{args[0]}'. Using default threshold of {DEFAULT_THRESHOLD} INR.")
    else:
        logging.info(f"No threshold argument provided. Using default threshold: {DEFAULT_THRESHOLD}")

    await context.bot.send_message(chat_id=chat_id, text=f"🔄 Fetching top 5 sellers under {threshold} INR...")
    logging.info(f"Fetching top 5 sellers under threshold: {threshold} for chat {chat_id}")

    try:
        sellers = await get_top_sellers_under_threshold(threshold)
        await format_and_send_sellers(context.bot, sellers, threshold, chat_id) # Pass context.bot here
        logging.info(f"Successfully processed /top5 command for threshold {threshold}")
    except Exception as e:
        logging.error(f"Error in /top5 command for threshold {threshold}: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error fetching sellers: {e}")


async def topprices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to get top prices from all sellers."""
    logging.info("Received /topprices command handler initiated.")
    
    if not update.effective_chat:
        logging.warning("No effective chat found for /topprices command.")
        return
    
    chat_id = update.effective_chat.id
    logging.info(f"Processing /topprices command from chat_id: {chat_id}")

    args = context.args
    count = 10  # Default to top 10 prices

    if args:
        try:
            count = int(args[0])
            if count <= 0 or count > 50:  # Limit to reasonable range
                count = 10
            logging.info(f"Parsed count from command arguments: {count}")
        except ValueError:
            logging.warning(f"Invalid count argument received: '{args[0]}'. Using default count: 10")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Invalid count provided: '{args[0]}'. Using default count of 10.")

    await context.bot.send_message(chat_id=chat_id, text=f"🔄 Fetching top {count} highest prices...")
    logging.info(f"Fetching top {count} prices for chat {chat_id}")

    try:
        # Get all sellers (using a high threshold to get most sellers)
        sellers = await get_top_sellers_under_threshold(999999)  # High threshold to get all
        await format_and_send_top_prices(context.bot, sellers, chat_id, count)
        logging.info(f"Successfully processed /topprices command for count {count}")
    except Exception as e:
        logging.error(f"Error in /topprices command for count {count}: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error fetching top prices: {e}")


async def post_init(application: Application):
    """
    This function is called by python-telegram-bot *after* the application has been initialized
    and an event loop is running. This is the ideal place to schedule background tasks.
    """
    logging.info("Application post-initialization: scheduling periodic tasks.")
    # Send startup message. application.bot is now available.
    try:
        startup_message = """✅ <b>Binance P2P Alert Bot Started Successfully!</b>

🤖 <b>Available Commands:</b>

📊 <b>/top5</b> - Get top 5 sellers under threshold
   • Usage: <code>/top5</code> (uses default 90 INR)
   • Usage: <code>/top5 85</code> (custom threshold)

📈 <b>/topprices</b> - Get highest prices in market
   • Usage: <code>/topprices</code> (shows top 10)
   • Usage: <code>/topprices 15</code> (shows top 15)

🔄 <b>Automatic Alerts:</b>
   • Every 5 minutes: Sellers under 91 INR
   • Every 1 minute: Immediate alerts for good deals

💡 <b>Tip:</b> Bot will automatically notify you of good deals!"""

        await application.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, 
            text=startup_message,
            parse_mode=ParseMode.HTML
        )
        logging.info(f"Startup message with commands sent to chat {TELEGRAM_CHAT_ID}.")
    except Exception as e:
        logging.error(f"Error sending startup message to {TELEGRAM_CHAT_ID}: {e}")

    # Use application.job_queue for robust scheduling.
    # It integrates directly with the application's event loop.
    # Jobs can be configured to run periodically.
    application.job_queue.run_repeating(periodic_send_default, interval=300, first=0) # runs every 5 minutes
    application.job_queue.run_repeating(threshold_check_task, interval=60, first=0) # runs every 1 minute
    logging.info("Periodic tasks scheduled using JobQueue.")

async def post_shutdown(application: Application):
    """
    This function is called by python-telegram-bot *before* the application shuts down.
    """
    logging.info("Application post-shutdown: stopping periodic tasks.")
    # JobQueue automatically stops its jobs when the application stops.
    try:
        await application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🔴 Binance P2P Alert Bot Stopped.")
    except Exception as e:
        logging.warning(f"Could not send shutdown message: {e}")


def main():
    logging.info("🚀 Starting Binance P2P Alert Bot Setup...")

    # Use ApplicationBuilder for a cleaner setup
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    logging.info("Telegram Application built.")

    # Add handlers
    application.add_handler(CommandHandler("top5", top5_command))
    application.add_handler(CommandHandler("topprices", topprices_command))
    logging.info("Command handlers added: /top5, /topprices")

    # Set up post-initialization and post-shutdown callbacks
    # These run within the application's managed event loop.
    application.post_init = post_init  # FIXED: Assignment, not function call
    application.post_shutdown = post_shutdown  # FIXED: Assignment, not function call

    logging.info("🤖 Bot polling started.")
    # application.run_polling() is the blocking call.
    # drop_pending_updates=True will discard any updates that occurred while the bot was offline.
    # We remove stop_signals=None because the default behavior is usually sufficient (Ctrl+C).
    application.run_polling(drop_pending_updates=True)
    logging.info("Polling stopped.")

if __name__ == "__main__":
    try:
        main() # Call the synchronous main function directly
    except KeyboardInterrupt:
        logging.info("❌ Stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logging.critical(f"An unhandled critical error occurred: {e}", exc_info=True)