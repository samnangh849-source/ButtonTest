import re
import urllib.parse
import os
import sys # ត្រូវការសម្រាប់ Log ទៅកាន់ stderr
import traceback # ត្រូវការសម្រាប់បង្ហាញ Error ពេញលេញ
from telebot import TeleBot, types
from flask import Flask, request, abort 

# ==================== CONFIGURATION (MUST BE UPDATED) ====================
# The token is read from the TELEGRAM_BOT_TOKEN environment variable.
# !!! IMPORTANT: For security, never hardcode the real token here.
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') 
if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN environment variable is not set.")
    sys.exit(1)

# !!! 2. UPDATE THIS URL: The public HTTPS URL of your label_printer.html file
# Example: "https://your-domain.github.io/label_printer.html"
BOT_BASE_URL = "https://samnangh849-source.github.io/ButtonTest/label_printer.html"

# !!! 3. UPDATE THIS URL: The base HTTPS URL of your deployed bot server (e.g., Render)
WEBHOOK_URL_BASE = "https://buttontest-1.onrender.com" 
WEBHOOK_URL_PATH = f"/webhook" 

PORT = int(os.environ.get('PORT', 5000))

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)
# ========================================================================

# ==================== Webhook Route ====================
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        
        # Log the received payload for debugging
        print(f"DEBUG: Raw JSON Payload Received: {json_string}")
        sys.stdout.flush() 
        
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        abort(403) 

# ==================== Test Command ====================
@bot.message_handler(commands=['test'])
def test_handler(message):
    """
    Handler to test if the Bot can send a message.
    """
    try:
        bot.send_message(
            message.chat.id, 
            "Bot ដំណើរការហើយ! Chat ID របស់អ្នកគឺ: `" + str(message.chat.id) + "`",
            parse_mode='Markdown'
        )
        print("INFO: Test message sent successfully.")
        
    except Exception as e:
        sys.stderr.write(f"ERROR: Failed to send test message (Chat ID: {message.chat.id}). Full Traceback:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()

# ==================== Functionality ====================
def generate_label_button(message_text):
    """
    Checks the message for required data and constructs the print button URL.
    """
    # Regex is designed to be highly flexible to capture multi-line Khmer text
    pattern = re.compile(r"""
        [\s\S]*?អតិថិជន.*?:\s*(?P<name>.*?)                # 1. Name
        [\s\S]*?លេខទូរស័ព្ទ.*?:\s*(?P<phone>.*?)         # 2. Phone
        [\s\S]*?ទីតាំង.*?:\s*(?P<location>.*?)           # 3. Location
        [\s\S]*?សរុបចុងក្រោយ.*?:\s*\$\s*(?P<total>[\d\.]+)\s* # 4. Total (must contain digits and/or dot after $)
        [\s\S]*?$                                     # Match till the end
    """, re.VERBOSE | re.DOTALL) 

    match = pattern.search(message_text)

    if match:
        data = match.groupdict()
        customer_name = data.get('name', '').strip()
        total_amount = data.get('total', '').strip()
        phone_number = data.get('phone', '').strip()
        location = data.get('location', '').strip()

        params = {
            'name': customer_name,
            'phone': phone_number,
            'location': location,
            'total': total_amount
        }
        
        # urlencode correctly handles special characters and Khmer text
        query_string = urllib.parse.urlencode(params)
        
        # *** FIX APPLIED HERE: BOT_BASE_URL already contains the file name ***
        label_url = f"{BOT_BASE_URL}?{query_string}" 

        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("ចុចដើម្បីព្រីន Label 📦", url=label_url)
        keyboard.add(button)
        
        return keyboard, label_url
    else:
        return None, None

# ==================== Message Handler ====================
@bot.message_handler(content_types=['text'])
def handle_all_messages(message):
    """
    Handler for all text messages.
    """
    print(f"DEBUG: Message text received: {message.text}") 
    
    inline_keyboard, label_url = generate_label_button(message.text)

    if inline_keyboard:
        try:
            # FIX: Sending a generic confirmation message instead of the original message 
            # text to avoid Telegram parsing errors with complex formatting/emojis.
            confirmation_text = "✅ **Bot បានទាញយកទិន្នន័យដោយជោគជ័យ។**\n\nសូមចុចប៊ូតុងខាងក្រោមដើម្បីបោះពុម្ព Label នេះ។"
            
            bot.send_message(
                chat_id=message.chat.id,
                text=confirmation_text, 
                reply_markup=inline_keyboard,
                # Using 'Markdown' for the confirmation_text
                parse_mode='Markdown' 
            )
            print(f"INFO: Success sending button to Chat ID: {message.chat.id}")
            print(f"INFO: Label URL: {label_url}") 
            
        except Exception as e:
            # បង្ហាញ Error ក្នុង Log ពេលបរាជ័យ
            sys.stderr.write(f"ERROR: Failed to send button message: {e}\n")
            sys.stderr.flush()
            
    else:
        print(f"DEBUG: Regex failed to match for Chat ID: {message.chat.id}") 
        # Optional: You can add an error message to the user here if you want:
        # bot.send_message(message.chat.id, "❌ រកមិនឃើញទិន្នន័យអតិថិជនត្រឹមត្រូវទេ។")
        pass 

# ==================== Bot Startup (Flask) ====================
if __name__ == '__main__':
    print("INFO: Telegram Bot is starting (Webhook)...")
    
    # Set the webhook to your hosting URL
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
    
    # Flask server startup is managed by Gunicorn in production (via Procfile)
    # The code below is only needed for local testing, but we keep it commented out.
    # app.run(host="0.0.0.0", port=PORT)
