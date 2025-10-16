import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError
import os
from dotenv import load_dotenv
from src.data_fetcher import DataFetcher
from src.report_generator import ReportGenerator
from src.visualization import StockVisualizer
from telegram_handlers import (
    start_handler, analyze_handler, signals_handler, 
    watchlist_handler, alerts_handler, help_handler,
    chart_handler, history_handler, settings_handler
)
from user_manager import UserManager
import asyncio

load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class StockAnalysisTelegramBot:
    """Main Telegram Bot for Stock Technical Analysis"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.data_fetcher = DataFetcher()
        self.report_generator = ReportGenerator()
        self.visualizer = StockVisualizer()
        self.user_manager = UserManager()
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")
    
    def setup_handlers(self, application: Application):
        """Setup all command and message handlers"""
        
        # Command handlers
        application.add_handler(CommandHandler('start', start_handler))
        application.add_handler(CommandHandler('analyze', analyze_handler))
        application.add_handler(CommandHandler('signals', signals_handler))
        application.add_handler(CommandHandler('chart', chart_handler))
        application.add_handler(CommandHandler('watchlist', watchlist_handler))
        application.add_handler(CommandHandler('alerts', alerts_handler))
        application.add_handler(CommandHandler('history', history_handler))
        application.add_handler(CommandHandler('settings', settings_handler))
        application.add_handler(CommandHandler('help', help_handler))
        
        # Message handler for general text
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Callback query handler for buttons
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        application.add_error_handler(self.error_handler)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general text messages"""
        user_id = update.effective_user.id
        message = update.message.text.strip().upper()
        
        # Check if it's a stock ticker
        if len(message) <= 5 and message.isalpha():
            await self.quick_analyze(update, context, message)
        else:
            await update.message.reply_text(
                "Please send a stock ticker (e.g., AAPL, MSFT) or use /help for available commands."
            )
    
    async def quick_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ticker: str):
        """Quick analysis for stock ticker"""
        try:
            await update.message.reply_text(f"🔍 Analyzing {ticker}... Please wait...")
            
            # Fetch data
            df = self.data_fetcher.fetch_stock_data(ticker, period='1y')
            
            if df.empty:
                await update.message.reply_text(f"�� Could not find data for {ticker}")
                return
            
            # Generate report
            report = self.report_generator.generate_report(ticker, df)
            
            # Format and send report
            message_text = self._format_report(report)
            await update.message.reply_text(message_text, parse_mode='HTML')
            
            # Log analysis
            self.user_manager.log_analysis(update.effective_user.id, ticker)
            
        except Exception as e:
            logger.error(f"Error in quick_analyze: {str(e)}")
            await update.message.reply_text(f"❌ Error analyzing {ticker}: {str(e)}")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('analyze_'):
            ticker = data.split('_')[1]
            await self.quick_analyze(update, context, ticker)
        elif data == 'watchlist_view':
            await self._show_watchlist(update, context)
    
    async def _show_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's watchlist"""
        user_id = update.effective_user.id
        watchlist = self.user_manager.get_watchlist(user_id)
        
        if not watchlist:
            await update.callback_query.edit_message_text("Your watchlist is empty. Add stocks with /watchlist add TICKER")
            return
        
        text = "📊 Your Watchlist:\n\n"
        keyboard = []
        
        for ticker in watchlist:
            text += f"• {ticker}\n"
            keyboard.append([InlineKeyboardButton(f"Analyze {ticker}", callback_data=f"analyze_{ticker}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    def _format_report(self, report: dict) -> str:
        """Format report for Telegram message"""
        text = f"""
<b>📊 Technical Analysis Report</b>
<b>Ticker:</b> {report['ticker']}
<b>Current Price:</b> ${report['current_price']:.2f}\n
<b>🎯 Recommendation: {report['recommendation']}</b>\n
<b>📈 Indicators:</b>\n• RSI: {report['indicators']['rsi']['value']:.2f} ({report['indicators']['rsi']['status']})\n• SMA 20: ${report['indicators']['sma_20']:.2f}\n• SMA 50: ${report['indicators']['sma_50']:.2f}\n
<b>🤖 AI Prediction:</b>\n• Direction: {report['ai_prediction']['direction']}\n• Confidence: {report['ai_prediction']['confidence']:.2%}\n
<b>📊 Bollinger Bands:</b>\n• Upper: ${report['indicators']['bollinger_bands']['upper']:.2f}\n• Middle: ${report['indicators']['bollinger_bands']['middle']:.2f}\n• Lower: ${report['indicators']['bollinger_bands']['lower']:.2f}\n
<b>💪 Support/Resistance:</b>\n• Support: ${report['indicators']['support_resistance']['support']:.2f}\n• Resistance: ${report['indicators']['support_resistance']['resistance']:.2f}\n
<b>🎲 Trading Signals:</b>\n• RSI Signal: {report['signals']['rsi']}\n• MACD Signal: {report['signals']['macd']}\n• SMA Signal: {report['signals']['sma']}\n"""
        return text
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Error: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later or use /help"
            )
    
    async def run(self):
        """Start the bot"""
        application = Application.builder().token(self.token).build()
        
        # Setup handlers
        self.setup_handlers(application)
        
        logger.info("🤖 Stock Analysis Telegram Bot started!")
        
        # Start polling or webhook
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("Bot is running... Press Ctrl+C to stop")

def main():
    """Main entry point"""
    try:
        bot = StockAnalysisTelegramBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")

if __name__ == '__main__':
    main()