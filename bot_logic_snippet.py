# នេះគឺជាកូដសម្រាប់ដំណើរការ Bot ដោយប្រើ Webhook (ល្អបំផុតសម្រាប់ Free Hosting)
# Bot នឹងត្រូវប្រើ Web Framework ដូចជា Flask ដើម្បីទទួលសារពី Telegram។

import re
import urllib.parse
import os
import json # *** NEW: ត្រូវការសម្រាប់ Debugging JSON Payload ***
import sys # *** NEW: ត្រូវការសម្រាប់ Flush Log ***
from telebot import TeleBot, types
from flask import Flask, request, abort # ត្រូវការ Flask សម្រាប់ Webhook

# ==================== កំណត់រចនាសម្ព័ន្ធ Bot & Server ====================
# !!! 1. Token ត្រូវបានកំណត់តាមរយៈ Render Environment Variable (ល្អបំផុតសម្រាប់ Production)
# សូមកំណត់ TELEGRAM_BOT_TOKEN នៅក្នុង Render Dashboard របស់អ្នក
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', "8076401419:AAEIBzxnT3XGRA96XIVspbxKpLHfywFqm9k") 

# !!! 2. ត្រូវប្តូរ URL នេះ (ទៅជា HTTPS URL របស់ Label Printer HTML ដែលដាក់ Host សាធារណៈ)
BOT_BASE_URL = "https://samnangh849-source.github.io/ButtonTest/"

# !!! 3. កំណត់ URL របស់ Server របស់ Bot ដែលនឹងទទួល Webhook (ដែលបានមកពី Render)
WEBHOOK_URL_BASE = "https://buttontest-zqa5.onrender.com" 
WEBHOOK_URL_PATH = f"/{BOT_TOKEN}"

# កំណត់ Port សម្រាប់ Flask (ប្រើ Environment Variable ឬ 5000)
PORT = int(os.environ.get('PORT', 5000))

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)
# ========================================================================

# ==================== Webhook Route ====================
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        
        # នេះសម្រាប់មើលថា Telegram បានផ្ញើអ្វីមកទាំងស្រុង
        print(f"DEBUG: Raw JSON Payload Received: {json_string}")
        sys.stdout.flush() # បង្ខំឱ្យ Log ត្រូវបានបង្ហាញភ្លាមៗ
        
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        abort(403) # បដិសេធសំណើដែលមិនមែនជា JSON (ការពារសុវត្ថិភាព)

# ==================== Test Command (NEW) ====================
@bot.message_handler(commands=['test'])
def test_handler(message):
    """
    Handler សម្រាប់សាកល្បងថាតើ Bot អាចផ្ញើសារបានដែរឬទេ?
    """
    try:
        # ប្រើ parse_mode='Markdown' ធម្មតាដើម្បីជៀសវាងកំហុស formatting
        bot.send_message(
            message.chat.id, 
            "Bot ដំណើរការហើយ! Chat ID របស់អ្នកគឺ: " + str(message.chat.id),
            parse_mode='Markdown' # ប្រើ Markdown ជំនួស HTML
        )
        print("INFO: Test message sent successfully.")
        sys.stdout.flush()
    except Exception as e:
        # បង្ហាញ Error Code ក្នុង Log ពេលបរាជ័យ
        print(f"ERROR: Failed to send test message. Check Bot Permissions or Token: {e}")
        sys.stdout.flush()


# ==================== Functionality (ដូចដើម) ====================
def generate_label_button(message_text):
    """
    ពិនិត្យមើលសារ និងទាញយកទិន្នន័យ។
    """
    # Regex ត្រូវបានធ្វើឱ្យទន់ភ្លន់បំផុត (Aggressive)
    pattern = re.compile(r"""
        .*?                                             # (NEW) Skip everything before the first tag (e.g. ✅...)
        👤\s*អតិថិជន\s*:\s*(?P<name>.*?)                # Capture Name
        .*?📞\s*លេខទូរស័ព្ទ\s*:\s*(?P<phone>.*?)         # Capture Phone
        .*?📍\s*ទីតាំង\s*:\s*(?P<location>.*?)           # Capture Location
        .*?                                             # Skip all product, address, and mid-section data
        សរុបចុងក្រោយ\s*:\s*\$\s*(?P<total>[\d\.]+)\s* # Capture Final Total (Allowing space after $ sign)
        .*?                                             # Skip everything after total (like COD, Delivery methods)
    """, re.VERBOSE | re.DOTALL) # DOTALL ធ្វើឱ្យ . អាចចាប់យក Line Breaks

    match = pattern.search(message_text)

    if match:
        data = match.groupdict()

        # 1. ទាញយកទិន្នន័យ
        customer_name = data.get('name', '').strip()
        total_amount = data.get('total', '').strip()
        phone_number = data.get('phone', '').strip()
        location = data.get('location', '').strip()

        # 2. URL Encode ទិន្នន័យ
        params = {
            'name': customer_name,
            'phone': phone_number,
            'location': location,
            'total': total_amount
        }
        query_string = urllib.parse.urlencode(params)
        label_url = f"{BOT_BASE_URL}label_printer.html?{query_string}" # កែសម្រួល URL

        # 3. បង្កើត Inline Keyboard Markup
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
    Handler សម្រាប់សារអត្ថបទទាំងអស់។
    """
    # បន្ថែម Log ដើម្បីមើលសារដែល Bot ទទួលបាន
    print(f"DEBUG: Message text received: {message.text}") 
    sys.stdout.flush() # បង្ខំឱ្យ Log ត្រូវបានបង្ហាញភ្លាមៗ
    
    inline_keyboard, label_url = generate_label_button(message.text)

    if inline_keyboard:
        try:
            # ពេលផ្ញើសារ Bot ប្រើ parse_mode='HTML' ព្រោះសារដើមមាន Emoticon និង Formatting 
            bot.send_message(
                chat_id=message.chat.id,
                text=message.text, 
                reply_markup=inline_keyboard,
                parse_mode='HTML'
            )
            # សម្រាប់ Console Log នៅលើ Render
            print(f"INFO: Success sending button to Chat ID: {message.chat.id}")
            sys.stdout.flush()
            print(f"INFO: Label URL: {label_url}") 
            sys.stdout.flush()
            
        except Exception as e:
            print(f"ERROR: Failed to send message: {e}")
            sys.stdout.flush()
            
    else:
        # បន្ថែម Log ពេល Regex រកមិនឃើញទម្រង់
        print(f"DEBUG: Regex failed to match for Chat ID: {message.chat.id}") 
        sys.stdout.flush()
        # មិនធ្វើអ្វីទាំងអស់បើសារមិនត្រូវទម្រង់
        pass 

# ==================== Bot Startup (Flask) ====================
if __name__ == '__main__':
    print("INFO: Telegram Bot is starting (Webhook)...")
    
    # កំណត់ Webhook ទៅកាន់ URL របស់ Hosting របស់អ្នក
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
    
    # ចាប់ផ្តើម Flask Server
    # ប្រើ gunicorn ដើម្បីចាប់ផ្តើម Flask App ក្នុង Production Environment 
    # (ប៉ុន្តែក្នុងកូដនេះ Render ប្រើ gunicorn ដោយខ្លួនឯងតាមរយៈ Procfile)
    # app.run(host='0.0.0.0', port=PORT) 
