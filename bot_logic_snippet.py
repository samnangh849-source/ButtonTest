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

# NEW: Global variable to store the Bot's ID for the safety check
BOT_ID = None
try:
    BOT_INFO = bot.get_me()
    BOT_ID = BOT_INFO.id
    print(f"INFO: Bot ID is {BOT_ID}")
except Exception as e:
    # This warning means the safety check will be skipped, but the bot will still run.
    print(f"WARNING: Could not fetch Bot ID: {e}. Bot will not skip its own messages.")

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
    Tries to EDIT the message to attach the button. If it fails (e.g., cannot edit user message), 
    it falls back to sending a new confirmation message.
    """
    print(f"DEBUG: Message text received: {message.text}") 
    
    # We allow the bot's own message to be processed here so it can EDIT its own confirmation message.
    
    inline_keyboard, label_url = generate_label_button(message.text)

    if inline_keyboard:
        try:
            # 1. Attempt to EDIT the *original message* (User or Bot) to attach the button.
            # This fulfills the request to "edit the message it sent itself" or the user's desire 
            # to attach the button directly to the formatted message.
            bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=inline_keyboard
            )
            print(f"INFO: Successfully EDITED message ({message.message_id}) reply markup for Chat ID: {message.chat.id}")

        except Exception as edit_e:
            # 2. If editing fails (e.g., Bot cannot edit a message sent by a normal user), 
            # fall back to sending a new confirmation message.
            try:
                confirmation_text = "✅ **Bot បានទាញយកទិន្នន័យដោយជោគជ័យ។**\n\nសូមចុចប៊ូតុងខាងក្រោមដើម្បីបោះពុម្ព Label នេះ។"
                
                bot.send_message(
                    chat_id=message.chat.id,
                    text=confirmation_text, 
                    reply_markup=inline_keyboard,
                    parse_mode='Markdown' 
                )
                print(f"INFO: Edit failed, sent NEW confirmation message to Chat ID: {message.chat.id}")
                sys.stderr.write(f"WARNING: Edit failed for message {message.message_id}: {edit_e}\n")
                
            except Exception as send_e:
                # Final catch if sending the new message fails
                sys.stderr.write(f"ERROR: Failed to send or edit message for Chat ID: {message.chat.id}. Full Traceback:\n")
                sys.stderr.write(traceback.format_exc())
                sys.stderr.flush()
                
        print(f"INFO: Label URL: {label_url}") 
            
    else:
        # If no Regex match, we should still ignore the bot's message to avoid unnecessary processing.
        global BOT_ID
        if BOT_ID and message.from_user.id == BOT_ID:
             print(f"DEBUG: Ignoring bot's own message which did not match regex.")
        else:
             print(f"DEBUG: Regex failed to match for Chat ID: {message.chat.id}") 
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
