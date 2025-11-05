#!/usr/bin/env python3
"""Simple echo bot for testing - mirrors all incoming messages."""

import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

def main():
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add echo handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Run bot
    print("Bot started - send any message to test")
    application.run_polling()

if __name__ == '__main__':
    main()
