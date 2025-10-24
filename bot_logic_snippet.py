# =============================================================
# នេះគឺជាកូដឧទាហរណ៍ពេញលេញដែលប្រើបណ្ណាល័យ 'pyTelegramBotAPI' (pip install pyTelegramBotAPI)
# ដើម្បីដំណើរការ Bot នេះ អ្នកត្រូវ៖
# 1. ប្តូរ 'YOUR_BOT_TOKEN' ទៅជា API Token ពិតប្រាកដរបស់អ្នក។
# 2. ប្តូរ 'BOT_BASE_URL' ទៅជា URL របស់ Label Printer Web Service របស់អ្នក។

import re
import urllib.parse
from telebot import TeleBot, types

# ==================== កំណត់រចនាសម្ព័ន្ធ Bot ====================
BOT_TOKEN = "8076401419:AAEIBzxnT3XGRA96XIVspbxKpLHfywFqm9k" # <<<<<< ត្រូវប្តូរ Token នេះ
BOT_BASE_URL = "https://samnangh849-source.github.io/ButtonTest/" # <<<<<< ត្រូវប្តូរ URL នេះ
bot = TeleBot(BOT_TOKEN)




# នេះគឺជាកូដសម្រាប់ដំណើរការ Bot ដោយប្រើ Webhook (ល្អបំផុតសម្រាប់ Free Hosting)
# Bot នឹងត្រូវប្រើ Web Framework ដូចជា Flask ដើម្បីទទួលសារពី Telegram។

import re
import urllib.parse
import os
from telebot import TeleBot, types
from flask import Flask, request, abort # ត្រូវការ Flask សម្រាប់ Webhook

# ==================== កំណត់រចនាសម្ព័ន្ធ Bot & Server ====================
# !!! 1. ត្រូវប្តូរ Token នេះ
BOT_TOKEN = "8076401419:AAEIBzxnT3XGRA96XIVspbxKpLHfywFqm9k" 

# !!! 2. ត្រូវប្តូរ URL នេះ (ទៅជា HTTPS URL របស់ Label Printer សាធារណៈ)
BOT_BASE_URL = "https://samnangh849-source.github.io/ButtonTest/"

# !!! 3. កំណត់ URL របស់ Server របស់ Bot ដែលនឹងទទួល Webhook (ឧទាហរណ៍: https://my-telegram-bot.render.com/)
WEBHOOK_URL_BASE = "YOUR_BOT_WEBHOOK_URL" 
WEBHOOK_URL_PATH = f"/{BOT_TOKEN}"

# កំណត់ Port សម្រាប់ Flask (ប្រើ Environment Variable ឬ 5000)
# សម្រាប់ Free Hosting ដូចជា Render, Vercel ត្រូវតែប្រើ PORT ដែលគេផ្តល់ឱ្យ
PORT = int(os.environ.get('PORT', 5000))

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)
# ========================================================================

# ==================== Webhook Route ====================
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        abort(403) # បដិសេធសំណើដែលមិនមែនជា JSON (ការពារសុវត្ថិភាព)

# ==================== Functionality (ដូចដើម) ====================
def generate_label_button(message_text):
    """
    ពិនិត្យមើលសារ និងទាញយកទិន្នន័យ។
    """
    pattern = re.compile(r"""
        👤\s*អតិថិជន\s*:\s*(?P<name>.*?)\n           # Capture Name
        📞\s*លេខទូរស័ព្ទ\s*:\s*(?P<phone>.*?)\n        # Capture Phone
        📍\s*ទីតាំង\s*:\s*(?P<location>.*?)\n        # Capture Location
        .*?                                         # Skip intermediate content
        សរុបចុងក្រោយ\s*:\s*\$(?P<total>[\d\.]+)\s*\n # Capture Final Total
    """, re.VERBOSE | re.DOTALL)

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
        label_url = f"{BOT_BASE_URL}?{query_string}"

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
    
    inline_keyboard, label_url = generate_label_button(message.text)

    if inline_keyboard:
        try:
            bot.send_message(
                chat_id=message.chat.id,
                text=message.text, 
                reply_markup=inline_keyboard,
                parse_mode='HTML'
            )
            print(f"បានផ្ញើសារដែលមានប៊ូតុងជោគជ័យទៅកាន់ Chat ID: {message.chat.id}")
            print(f"URL សម្រាប់ Label: {label_url}") 
            
        except Exception as e:
            print(f"មានបញ្ហាពេលផ្ញើសារ: {e}")
            
    else:
        print(f"សារមិនត្រូវតាមទម្រង់ក្នុង Chat ID: {message.chat.id}")

# ==================== Bot Startup (Flask) ====================
if __name__ == '__main__':
    print("Telegram Bot កំពុងចាប់ផ្តើម (Webhook)...")
    
    # កំណត់ Webhook ទៅកាន់ URL របស់ Hosting របស់អ្នក
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
    
    # ចាប់ផ្តើម Flask Server
    app.run(host='0.0.0.0', port=PORT)

# ==================== Polling Startup (ជម្រើសចាស់ - សម្រាប់ Local Testing) ====================
# if __name__ == '__main__':
#     print("Telegram Bot កំពុងចាប់ផ្តើម (Polling)...")
#     try:
#         bot.polling(none_stop=True)
#     except Exception as e:
#         print(f"មានបញ្ហាក្នុងការចាប់ផ្តើម Bot: {e}")
