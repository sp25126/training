"""
Run the Telegram bot with proper error handling
"""

import os
import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from integrations.telegram_bot import TelegramFileBot
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()
    
    # Get bot token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token or bot_token == "your_telegram_bot_token_here":
        print("❌ TELEGRAM_BOT_TOKEN not configured!")
        print("📋 Steps to fix:")
        print("1. Open Telegram and message @BotFather")
        print("2. Send /newbot and follow instructions")
        print("3. Copy your bot token")
        print("4. Add to .env file: TELEGRAM_BOT_TOKEN=your_token_here")
        print("5. Restart this script")
        return
    
    # Validate token format
    if not (bot_token.count(":") == 1 and len(bot_token.split(":")[0]) >= 8):
        print("❌ Invalid token format!")
        print("Token should look like: 123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg_hijklmnop")
        return
    
    # Start bot
    try:
        print("🚀 Starting Telegram QA Generator Bot...")
        print("📱 Find your bot on Telegram and send /start")
        print("📤 Upload files, send text, or paste URLs")
        print("⏹️  Press Ctrl+C to stop")
        print("-" * 50)
        
        bot = TelegramFileBot(bot_token)
        bot.run()
        
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"\n❌ Bot error: {e}")
        print("💡 Check your internet connection and bot token")

if __name__ == "__main__":
    main()
