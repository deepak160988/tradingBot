# app.py

from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This is crucial for securely managing your API keys and chat IDs
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
# It is highly recommended to store sensitive information like API tokens
# in environment variables and load them using python-dotenv.
# Create a file named .env in the same directory as app.py with these lines:
# TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
# TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID_HERE"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in environment variables or .env file.")
    print("Please create a .env file and add them, or set them directly in your environment.")
    # Exit or handle this error appropriately in a production environment
    # For local testing, you might choose to hardcode for a moment,
    # but NEVER do this for deployed applications.

# --- Helper Function to Send Telegram Messages ---
def send_telegram_message(message: str) -> bool:
    """ 
    Sends a message to the configured Telegram chat.
    Returns True on success, False on failure.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Cannot send Telegram message: Bot token or chat ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML" # Use HTML parse mode for richer formatting (e.g., <b>, <i>)
    }
    try:
        response = requests.post(url, json=payload, timeout=10) # Add a timeout for robustness
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print(f"Successfully sent message to Telegram. Response: {response.json()}")
        return True
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while sending Telegram message: {http_err} - {response.text}")
        return False
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred while sending Telegram message: {conn_err}")
        return False
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred while sending Telegram message: {timeout_err}")
        return False
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred while sending Telegram message: {req_err}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

# --- Flask Route for TradingView Webhook ---
@app.route('/tradingview-alert', methods=['POST'])
def tradingview_alert():
    """
    Receives webhook POST requests from TradingView.
    Parses the JSON payload and sends a formatted message to Telegram.
    """
    if request.method == 'POST':
        try:
            # TradingView typically sends alerts as JSON.
            # Ensure your TradingView alert message is formatted as JSON.
            alert_data = request.json
            if not alert_data:
                raise ValueError("No JSON payload received.")

            print(f"Received alert data: {alert_data}")

            # Extract data from the alert_data. Adjust these keys based on
            # how you configure your TradingView alert message.
            # Example TradingView alert message JSON:
            # {
            #   "strategy_name": "{{strategy.name}}",
            #   "ticker": "{{ticker}}",
            #   "interval": "{{interval}}",
            #   "action": "{{strategy.order.action}}",
            #   "price": "{{close}}",
            #   "volume": "{{volume}}",
            #   "time": "{{time}}"
            # }

            strategy = alert_data.get('strategy_name', 'N/A')
            ticker = alert_data.get('ticker', 'N/A')
            interval = alert_data.get('interval', 'N/A')
            action = alert_data.get('action', 'N/A')
            price = alert_data.get('price', 'N/A')
            volume = alert_data.get('volume', 'N/A')
            alert_time = alert_data.get('time', 'N/A')

            # Construct the message for Telegram using HTML formatting
            telegram_message = f"🚨 <b>TradingView Alert!</b> 🚨\n" \
                               f"<b>Strategy:</b> <i>{strategy}</i>\n" \
                               f"<b>Instrument:</b> <code>{ticker}</code>\n" \
                               f"<b>Timeframe:</b> {interval}\n" \
                               f"<b>Action:</b> <b style='color:#{'green' if 'buy' in action.lower() else ('red' if 'sell' in action.lower() else 'orange')}'>{action}</b>\n" \
                               f"<b>Price:</b> <code>${price}</code>\n" \
                               f"<b>Volume:</b> {volume}\n" \
                               f"<b>Alert Time:</b> {alert_time}"

            # Send the message to Telegram
            if send_telegram_message(telegram_message):
                return jsonify({"status": "success", "message": "Alert received and sent to Telegram"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to send message to Telegram"}), 500

        except Exception as e:
            print(f"Error processing alert: {e}")
            return jsonify({"status": "error", "message": f"Internal server error: {e}"}), 500
    else:
        return jsonify({"status": "error", "message": "Method Not Allowed"}), 405

# --- Health Check Route (Optional but Recommended) ---
@app.route('/')
def health_check():
    """
    Simple health check endpoint to confirm the server is running.
    """
    return jsonify({"status": "ok", "message": "TradingView Telegram Bot backend is running!"}), 200

# --- Run the Flask Application ---
if __name__ == '__main__':
    # When running locally, Flask development server starts on http://127.0.0.1:5000/
    # For production, use a more robust WSGI server like Gunicorn or Waitress.
    # debug=True allows for automatic reloading on code changes and provides
    # more detailed error messages, but should be False in production.
    app.run(debug=True, host='0.0.0.0', port=5000)
