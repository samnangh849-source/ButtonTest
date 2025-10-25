# នេះគឺជាកូដសម្រាប់ដំណើរការ Bot ដោយប្រើ Webhook (ល្អបំផុតសម្រាប់ Free Hosting)
# Bot នឹងត្រូវប្រើ Web Framework ដូចជា Flask ដើម្បីទទួលសារពី Telegram។

import re
import urllib.parse
import os
import json 
import sys # ត្រូវការសម្រាប់ Log ទៅកាន់ stderr
from telebot import TeleBot, types
from flask import Flask, request, abort 

# ==================== កំណត់រចនាសម្ព័ន្ធ Bot & Server ====================
# !!! 1. Token ត្រូវបានកំណត់តាមរយៈ Render Environment Variable (ល្អបំផុតសម្រាប់ Production)
# !!! ខ្ញុំបានដាក់ Token របស់អ្នកជាតម្លៃលំនាំដើមវិញ ដើម្បីជៀសវាងការបរាជ័យពេលចាប់ផ្តើម
BOT_TOKEN_FALLBACK = "7976723335:AAHfuSf-umdTV3kQUd3CbM3Z7xvHGqmHMe0"
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', BOT_TOKEN_FALLBACK) 

# !!! 2. ត្រូវប្តូរ URL នេះ (ទៅជា HTTPS URL របស់ Label Printer HTML ដែលដាក់ Host សាធារណៈ)
BOT_BASE_URL = "https://samnangh849-source.github.io/ButtonTest/label_printer.html"

# !!! 3. កំណត់ URL របស់ Server របស់ Bot ដែលនឹងទទួល Webhook (ដែលបានមកពី Render)
WEBHOOK_URL_BASE = "https://buttontest-1.onrender.com" 
# ផ្លាស់ប្តូរ Webhook Path ទៅជា /webhook វិញដើម្បីជៀសវាង Token Path Error
WEBHOOK_URL_PATH = f"/webhook" 

# កំណត់ Port សម្រាប់ Flask (ប្រើ Environment Variable ឬ 5000)
PORT = int(os.environ.get('PORT', 5000))

# មិនមានការពិនិត្យ sys.exit(1) ទៀតទេ ព្រោះយើងបានដាក់ Token ជា fallback រួចហើយ

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)
# ========================================================================

# ជំនួស print() ធម្មតាដោយ Log ទៅកាន់ stderr
def log_message(level, message):
    sys.stderr.write(f"{level}: {message}\n")
    sys.stderr.flush()

# ==================== Webhook Route ====================
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        
        # នេះសម្រាប់មើលថា Telegram បានផ្ញើអ្វីមកទាំងស្រុង
        log_message("DEBUG", f"Raw JSON Payload Received: {json_string}")
        
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        abort(403) 

# ==================== Test Command ====================
@bot.message_handler(commands=['test'])
def test_handler(message):
    """
    Handler សម្រាប់សាកល្ប្បងថាតើ Bot អាចផ្ញើសារបានដែរឬទេ?
    """
    try:
        # ប្រើ parse_mode='Markdown' ធម្មតាដើម្បីជៀសវាងកំហុស formatting
        bot.send_message(
            message.chat.id, 
            "Bot ដំណើរការហើយ! Chat ID របស់អ្នកគឺ: `" + str(message.chat.id) + "`",
            parse_mode='Markdown'
        )
        log_message("INFO", "Test message sent successfully.")
    except Exception as e:
        # បង្ហាញ Error Code ក្នុង Log ពេលបរាជ័យ
        log_message("ERROR", f"Failed to send test message. Check Bot Permissions or Token: {e}")


# ==================== Functionality ====================
def generate_label_button(message_text):
    """
    ពិនិត្យមើលសារ និងទាញយកទិន្នន័យ។
    """
    # Regex ត្រូវបានធ្វើឱ្យទន់ភ្លន់បំផុត (Aggressive)
    pattern = re.compile(r"""
        .*?                                             
        👤\s*អតិថិជន\s*:\s*(?P<name>.*?)                
        .*?📞\s*លេខទូរស័ព្ទ\s*:\s*(?P<phone>.*?)         
        .*?📍\s*ទីតាំង\s*:\s*(?P<location>.*?)           
        .*?                                             
        សរុបចុងក្រោយ\s*:\s*\$\s*(?P<total>[\d\.]+)\s* .*?                                             
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
        query_string = urllib.parse.urlencode(params)
        label_url = f"{BOT_BASE_URL}label_printer.html?{query_string}"

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
    log_message("DEBUG", f"Message text received: {message.text}") 
    
    inline_keyboard, label_url = generate_label_button(message.text)

    if inline_keyboard:
        try:
            bot.send_message(
                chat_id=message.chat.id,
                text=message.text, 
                reply_markup=inline_keyboard,
                parse_mode='HTML'
            )
            log_message("INFO", f"Success sending button to Chat ID: {message.chat.id}")
            log_message("INFO", f"Label URL: {label_url}") 
            
        except Exception as e:
            log_message("ERROR", f"Failed to send button message: {e}")
            
    else:
        log_message("DEBUG", f"Regex failed to match for Chat ID: {message.chat.id}") 
        pass 

# ==================== Bot Startup (Flask) ====================
if __name__ == '__main__':
    log_message("INFO", "Telegram Bot is starting (Webhook)...")
    
    # កំណត់ Webhook ទៅកាន់ URL របស់ Hosting របស់អ្នក
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
    
    # មិនចាំបាច់ចាប់ផ្តើម Flask Server ទេ ព្រោះ Render ប្រើ gunicorn ដោយខ្លួនឯង។
