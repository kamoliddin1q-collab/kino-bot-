import telebot
from flask import Flask
import threading
import os
import sqlite3
from datetime import datetime, timedelta
TOKEN = "9093234322:AAG4l6jKf52a0r-nonnskT1RDOpyDS6l5LE"
ADMIN_ID = 8823389094

DB = "kino_luxury.db"
PAYMENT_INFO = "💳 **Karta raqami:** `9860 1606 3597 0363`\n👤 **Karta egasi:** G'aybulla Shahzoda\n\n📌 Pulni ushbu kartaga o'tkazib, chek rasmini shu yerga yuboring!"

bot = telebot.TeleBot(TOKEN)
states = {}

PLANS = {
    "premium": ("💎 PREMIUM", 5000, 15),
    "vip": ("👑 VIP", 10000, 15)
}

def connect():
    return sqlite3.connect(DB)

def setup():
    c = connect()
    q = c.cursor()

    q.execute("""CREATE TABLE IF NOT EXISTS users(
        uid INTEGER PRIMARY KEY,
        name TEXT,
        expiry TEXT DEFAULT ''
    )""")

    q.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid INTEGER,
        plan TEXT,
        amount INTEGER,
        status TEXT DEFAULT 'pending',
        created TEXT
    )""")

    q.execute("""CREATE TABLE IF NOT EXISTS movies(
        code TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        poster TEXT,
        video_id TEXT,
        views INTEGER DEFAULT 0
    )""")

    q.execute("""CREATE TABLE IF NOT EXISTS prices(
        plan TEXT PRIMARY KEY,
        amount INTEGER
    )""")

    q.execute("""CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )""")

    for name, (_, price_val, _) in PLANS.items():
        q.execute("INSERT OR IGNORE INTO prices VALUES(?,?)", (name, price_val))

    q.execute("INSERT OR IGNORE INTO settings VALUES('channel', ?)", ("@Kamol_kino_pro_bot",))

    c.commit()
    c.close()

def get_channel():
    c = connect()
    row = c.execute("SELECT value FROM settings WHERE key='channel'").fetchone()
    c.close()
    return row[0] if row else ""

def price(plan):
    c = connect()
    row = c.execute("SELECT amount FROM prices WHERE plan=?", (plan,)).fetchone()
    c.close()
    return row[0] if row else PLANS[plan][1]

def is_admin(uid):
    return uid == ADMIN_ID

def check_subscription(uid):
    channel = get_channel()
    if not channel:
        return True
    try:
        member = bot.get_chat_member(channel, uid)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return True

def sub_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    channel = get_channel()
    if channel:
        channel_link = f"https://t.me/{channel.replace('@', '')}"
        kb.add(types.InlineKeyboardButton("📢 Kanalga a'zo bo'lish 🚀", url=channel_link))
    kb.add(types.InlineKeyboardButton("✅ Obunani tekshirish 🔄", callback_data="check_sub"))
    return kb

def register_user(m):
    c = connect()
    c.execute("INSERT OR IGNORE INTO users(uid,name) VALUES(?,?)", (m.from_user.id, m.from_user.first_name))
    c.commit()
    c.close()

def home(chat_id):
    k = types.InlineKeyboardMarkup(row_width=2)
    k.add(
        types.InlineKeyboardButton("🎬 KINOLAR 🎞", callback_data="movies"),
        types.InlineKeyboardButton("🔥 TOP KINOLAR 🚀", callback_data="top")
    )
    k.add(
        types.InlineKeyboardButton("💎 PREMIUM ⚡️", callback_data="tariffs"),
        types.InlineKeyboardButton("👑 VIP 🌟", callback_data="tariffs")
    )
    k.add(
        types.InlineKeyboardButton("👤 OBUNAM 📊", callback_data="sub"),
        types.InlineKeyboardButton("📞 YORDAM 🆘", callback_data="help")
    )
    if is_admin(chat_id):
        k.add(types.InlineKeyboardButton("⚙️ ADMIN PANEL 🛠", callback_data="admin"))

    bot.send_message(
        chat_id,
        "👑 **KINO OLAMI PRO** 🎬\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💜 **LUXURY MOVIE EXPERIENCE** ✨\n\n"
        "🎞 Eng sara va eksklyuziv kinolar olamiga xush kelibsiz!\n\n"
        "👇 Botdan foydalanish uchun kino **kodini** yuboring (masalan: `11`) yoki pastdagi menyudan foydalaning:",
        parse_mode="Markdown",
        reply_markup=k
    )

def admin_panel(chat_id):
    k = types.ReplyKeyboardMarkup(resize_keyboard=True)
    k.row("💰 DAROMAD 📈", "📢 XABAR YUBORISH 📨")
    k.row("➕ KINO QO'SHISH 🎬", "🔥 TOP KINOLAR 🏆")
    k.row("💎 PREMIUM NARXI 💵", "👑 VIP NARXI 💶")
    k.row("📢 KANALNI O'ZGARTIRISH 🔗", "🏠 BOSH MENYU 🔙")
    bot.send_message(chat_id, "👑 **LUXURY ADMIN PANEL** 🛠\nKerakli bo'limni tanlang:", parse_mode="Markdown", reply_markup=k)

@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    if not check_subscription(uid) and not is_admin(uid):
        bot.send_message(
            m.chat.id,
            "⚠️ **Diqqat! Botimizdan foydalanish uchun avval rasmiy kanalimizga a'zo bo'lishingiz kerak!** 👇\n\n"
            "Kanalga qo'shilgach, <b>✅ Obunani tekshirish</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=sub_keyboard()
        )
        return
    register_user(m)
    home(m.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_sub_callback(c):
    uid = c.from_user.id
    if check_subscription(uid):
        bot.answer_callback_query(c.id, "✅ Obunangiz tasdiqlandi! Hush kelibsiz! 🎉")
        try:
            bot.delete_message(c.message.chat.id, c.message.message_id)
        except Exception:
            pass
        register_user(c.message)
        home(c.message.chat.id)
    else:
        bot.answer_callback_query(c.id, "❌ Siz hali kanalga a'zo bo'lmadingiz! Obuna bo'ling 🔔", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data in ["movies", "top", "tariffs", "sub", "help", "admin"])
def menu_callback(c):
    uid = c.from_user.id
    chat = c.message.chat.id
    action = c.data

    if not check_subscription(uid) and not is_admin(uid):
        bot.answer_callback_query(c.id, "📢 Avval kanalga obuna bo'ling!", show_alert=True)
        return

    bot.answer_callback_query(c.id)

    if action == "tariffs":
        k = types.InlineKeyboardMarkup()
        for plan, (label, _, days) in PLANS.items():
            k.add(types.InlineKeyboardButton(f"{label} — {price(plan):,} so'm / {days} kun ⚡️", callback_data="buy_" + plan))
        bot.send_message(chat, "👑 **KINO OLAMI PRO TARIFLARI** 🌟\n\n💜 O'zingizga mos keladigan VIP yoki PREMIUM tarifni tanlang:", parse_mode="Markdown", reply_markup=k)

    elif action == "movies":
        c = connect()
        rows = c.execute("SELECT code, title FROM movies ORDER BY title").fetchall()
        c.close()
        if not rows:
            bot.send_message(chat, "🎬 Hozircha bazaga kinolar qo'shilmagan ❌")
            return
        msg = "🎞 **MAVJUD KINOLAR RO'YXATI** 📋\n\n"
        for code, title in rows:
            msg += f"🎬 <b>{title}</b> ➔ Kod: <code>{code}</code>\n"
        msg += "\n👇 Kino ko'rish uchun istalgan <b>kodni</b> yuboring (masalan: <b>11</b>)"
        bot.send_message(chat, msg, parse_mode="HTML")

    elif action == "top":
        c = connect()
        rows = c.execute("SELECT code, title, views FROM movies ORDER BY views DESC LIMIT 10").fetchall()
        c.close()
        msg = "🔥 **ENG KO'P KO'RILGAN TOP KINOLAR** 🏆\n\n"
        for code, title, views in rows:
            msg += f"🌟 {title} (Kod: <code>{code}</code>) — 👁 {views} marta ko'rilgan\n"
        bot.send_message(chat, msg if rows else "Kinolar topilmadi ❌", parse_mode="HTML")

    elif action == "sub":
        c = connect()
        row = c.execute("SELECT expiry FROM users WHERE uid=?", (uid,)).fetchone()
        c.close()
        if row and row[0]:
            bot.send_message(chat, f"👑 **OBUNANGIZ HOLATI** ✅\n\n⏳ Tugash vaqti:\n<code>{row[0]}</code>", parse_mode="HTML")
        else:
            bot.send_message(chat, "👤 Obunangiz faol emas ❌\nTariflar bo'limidan VIP yoki PREMIUM sotib olishingiz mumkin 💎")

    elif action == "help":
        bot.send_message(chat, "📞 **Yordam va qo'llab-quvvatlash** 🤖\n\nSavollar bo'yicha adminga murojaat qiling 👨‍💻")

    elif action == "admin":
        if is_admin(uid):
            admin_panel(chat)
        else:
            bot.send_message(chat, "❌ Sizda bu bo'limga kirishga ruxsat yo'q!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    uid = c.from_user.id
    plan = c.data[4:]
    if plan not in PLANS:
        return
    label, _, days = PLANS[plan]
    amount = price(plan)

    c_db = connect()
    cur = c_db.cursor()
    cur.execute("INSERT INTO orders(uid,plan,amount,created) VALUES(?,?,?,?)", (uid, plan, amount, datetime.now().isoformat()))
    order_id = cur.lastrowid
    c_db.commit()
    c_db.close()

    states[uid] = ("receipt", order_id)
    bot.send_message(
        c.message.chat.id,
        f"👑 **KINO OLAMI PRO — TO'LOV** 💳\n\n"
        f"📦 Tarif: {label}\n"
        f"💰 Narxi: {amount:,} so'm\n"
        f"⏳ Muddati: {days} kun\n\n"
        f"{PAYMENT_INFO}",
        parse_mode="Markdown"
    )
    bot.answer_callback_query(c.id)

@bot.message_handler(content_types=["photo"])
def photo_handler(m):
    uid = m.from_user.id
    if not check_subscription(uid) and not is_admin(uid):
        return

    state = states.get(uid)
    if not state:
        return

    if state[0] == "receipt":
        order_id = state[1]
        c = connect()
        order = c.execute("SELECT plan,amount,status FROM orders WHERE id=? AND uid=?", (order_id, uid)).fetchone()
        c.close()
        if not order or order[2] != "pending":
            return
        plan, amount, _ = order
        k = types.InlineKeyboardMarkup()
        k.row(
            types.InlineKeyboardButton("✅ TASDIQLASH 🟢", callback_data=f"ok_{order_id}"),
            types.InlineKeyboardButton("❌ RAD ETISH 🔴", callback_data=f"no_{order_id}")
        )
        bot.send_photo(
            ADMIN_ID,
            m.photo[-1].file_id,
            caption=f"🆕 **YANGI TO'LOV CHEKI!** 💳\n\n"
                    f"🔢 Buyurtma: #{order_id}\n"
                    f"👤 Foydalanuvchi: {m.from_user.first_name}\n"
                    f"🆔 ID: <code>{uid}</code>\n"
                    f"📦 Tarif: {plan.upper()}\n"
                    f"💰 Summa: {amount:,} so'm",
            parse_mode="HTML",
            reply_markup=k
        )
        states.pop(uid, None)
        bot.send_message(uid, "✅ Chekingiz adminga yuborildi! Tez orada tekshirib tasdiqlashadi ⏳")

    elif state[0] == "movie_poster" and is_admin(uid):
        code, title, desc = state[1], state[2], state[3]
        poster_id = m.photo[-1].file_id
        states[uid] = ("movie_video", code, title, desc, poster_id)
        bot.send_message(uid, "📤 Ajoyib! Endi kino **videosini** yuboring 🎥:")

@bot.message_handler(content_types=["video"])
def video_handler(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    state = states.get(uid)
    if not state or state[0] != "movie_video":
        return

    code, title, desc, poster = state[1], state[2], state[3], state[4]
    video_id = m.video.file_id

    c = connect()
    c.execute(
        "INSERT OR REPLACE INTO movies(code,title,description,poster,video_id) VALUES(?,?,?,?,?)",
        (code, title, desc, poster, video_id)
    )
    c.commit()
    c.close()

    states.pop(uid, None)
    
    bot.send_message(
        m.chat.id, 
        f"🎉 **TABRIKLAYMAN! KINO MUVAFFAQIYATLI YUKLANDI!** 🚀\n\n"
        f"🎬 Nomi: <b>{title}</b>\n"
        f"🔑 Kodi: <code>{code}</code>\n"
        f"💾 Bazaga to'liq saqlandi ✅", 
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith(("ok_", "no_")))
def order_action(c):
    if not is_admin(c.from_user.id):
        bot.answer_callback_query(c.id, "❌ Ruxsat yo'q!")
        return

    action, oid = c.data.split("_")
    oid = int(oid)
    c = connect()
    p = c.cursor()
    order = p.execute("SELECT uid,plan,amount,status FROM orders WHERE id=?", (oid,)).fetchone()
    if not order or order[3] != "pending":
        c.close()
        bot.answer_callback_query(c.id, "⚠️ Buyurtma allaqachon ko'rib chiqilgan!")
        return

    uid, plan, amount, _ = order
    if action == "ok":
        days = PLANS[plan][2]
        row = p.execute("SELECT expiry FROM users WHERE uid=?", (uid,)).fetchone()
        now = datetime.now()
        if row and row[0]:
            try:
                old = datetime.fromisoformat(row[0])
                if old > now:
                    now = old
            except ValueError:
                pass
        expiry = now + timedelta(days=days)
        p.execute("UPDATE users SET expiry=? WHERE uid=?", (expiry.isoformat(), uid))
        p.execute("UPDATE orders SET status='approved' WHERE id=?", (oid,))
        c.commit()
        c.close()
        bot.send_message(uid, f"🎉 **TO'LOVINGIZ TASDIQLANDI!** ✅\n\n👑 {plan.upper()} tarifi\n⏳ {days} kun davomida faollashdi! Maroqli tomosha 🍿")
        bot.answer_callback_query(c.id, "Muvaffaqiyatli tasdiqlandi! 👍")
        bot.send_message(ADMIN_ID, "✅ Buyurtma muvaffaqiyatli tasdiqlandi!")
    else:
        p.execute("UPDATE orders SET status='rejected' WHERE id=?", (oid,))
        c.commit()
        c.close()
        bot.send_message(uid, "❌ Afsuski, to'lovingiz tasdiqlanmadi. Admin bilan bog'laning ⚠️")
        bot.answer_callback_query(c.id, "Buyurtma rad etildi ❌")

@bot.message_handler(func=lambda m: m.text == "💰 DAROMAD 📈")
def income(m):
    if not is_admin(m.from_user.id):
        return
    c = connect()
    total = c.execute("SELECT COUNT(*),COALESCE(SUM(amount),0) FROM orders WHERE status='approved'").fetchone()
    today = datetime.now().date().isoformat()
    daily = c.execute("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='approved' AND substr(created,1,10)=?", (today,)).fetchone()[0]
    c.close()
    bot.send_message(m.chat.id, f"📊 **KASSALAR VA DAROMAD** 💰\n\n📅 Bugungi tushum: <b>{daily:,} so'm</b>\n💎 Umumiy tushum: <b>{total[1]:,} so'm</b>\n🧾 Tasdiqlangan to'lovlar: <b>{total[0]} ta</b>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in ["💎 PREMIUM NARXI 💵", "👑 VIP NARXI 💶"])
def price_start(m):
    if not is_admin(m.from_user.id):
        return
    plan = "premium" if "PREMIUM" in m.text else "vip"
    states[m.from_user.id] = ("price", plan)
    bot.send_message(m.chat.id, "💵 Yangi narxni faqat raqamlarda yuboring (masalan: <code>7000</code>):", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📢 XABAR YUBORISH 📨")
def broadcast_start(m):
    if not is_admin(m.from_user.id):
        return
    states[m.from_user.id] = ("broadcast",)
    bot.send_message(m.chat.id, "📨 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:")

@bot.message_handler(func=lambda m: m.text == "📢 KANALNI O'ZGARTIRISH 🔗")
def change_channel_start(m):
    if not is_admin(m.from_user.id):
        return
    current = get_channel()
    states[m.from_user.id] = ("set_channel",)
    bot.send_message(m.chat.id, f"📢 Hozirgi kanal: <b>{current}</b>\n\nYangi kanal userini yuboring (masalan: <code>@yangi_kanal</code>):", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🔥 TOP KINOLAR 🏆")
def admin_top(m):
    if not is_admin(m.from_user.id):
        return
    c = connect()
    rows = c.execute("SELECT code, title, views FROM movies ORDER BY views DESC LIMIT 10").fetchall()
    c.close()
    msg = "🔥 **TOP KINOLAR STATISTIKASI** 📊\n\n"
    for code, title, views in rows:
        msg += f"🎬 {title} (Kod: <code>{code}</code>) — 👁 {views} marta\n"
    bot.send_message(m.chat.id, msg if rows else "Hozircha kinolar yo'q ❌", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "➕ KINO QO'SHISH 🎬")
def add_movie_start(m):
    if not is_admin(m.from_user.id):
        return
    states[m.from_user.id] = ("movie_code",)
    bot.send_message(m.chat.id, "🎬 Kino uchun unikallik kodini yuboring (masalan: <b>11</b>):", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🏠 BOSH MENYU 🔙")
def back_home(m):
    if is_admin(m.from_user.id):
        home(m.chat.id)

@bot.message_handler(func=lambda m: True)
def text_handler(m):
    uid = m.from_user.id
    if not check_subscription(uid) and not is_admin(uid):
        return

    text = m.text.strip()
    state = states.get(uid)

    if state and is_admin(uid):
        st_type = state[0]
        if st_type == "movie_code":
            states[uid] = ("movie_title", text)
            bot.send_message(m.chat.id, f"📝 Kino <b>nomini</b> yuboring (Kiritilgan kod: <code>{text}</code>):", parse_mode="HTML")
            return
        elif st_type == "movie_title":
            code = state[1]
            states[uid] = ("movie_desc", code, text)
            bot.send_message(m.chat.id, "📄 Kino uchun qisqacha <b>tavsif</b> (opisaniya) yuboring:", parse_mode="HTML")
            return
        elif st_type == "movie_desc":
            code, title = state[1], state[2]
            states[uid] = ("movie_poster", code, title, text)
            bot.send_message(m.chat.id, "🖼 Kino uchun <b>poster (rasm)</b> yuboring:", parse_mode="HTML")
            return
        elif st_type == "price":
            try:
                amount = int(text)
                c = connect()
                c.execute("UPDATE prices SET amount=? WHERE plan=?", (amount, state[1]))
                c.commit()
                c.close()
                states.pop(uid, None)
                bot.send_message(m.chat.id, "✅ Tarif narxi muvaffaqiyatli yangilandi! 💵")
            except ValueError:
                bot.send_message(m.chat.id, "❌ Xato! Faqat musbat raqam kiriting.")
            return
        elif st_type == "set_channel":
            states.pop(uid, None)
            new_ch = text if text.startswith("@") else "@" + text
            c = connect()
            c.execute("INSERT OR REPLACE INTO settings VALUES('channel', ?)", (new_ch,))
            c.commit()
            c.close()
            bot.send_message(m.chat.id, f"✅ Majburiy obuna kanali muvaffaqiyatli o'zgartirildi: <b>{new_ch}</b> 📢", parse_mode="HTML")
            return
        elif st_type == "broadcast":
            states.pop(uid, None)
            c = connect()
            users = c.execute("SELECT uid FROM users").fetchall()
            c.close()
            sent = 0
            for (u_id,) in users:
                try:
                    bot.send_message(u_id, text)
                    sent += 1
                except Exception:
                    pass
            bot.send_message(m.chat.id, f"✅ Xabar muvaffaqiyatli {sent} ta foydalanuvchiga yetkazildi! 📨")
            return

    c = connect()
    row = c.execute("SELECT code,title,description,poster,video_id FROM movies WHERE code=?", (text,)).fetchone()
    if row:
        code, title, desc, poster, video_id = row
        c.execute("UPDATE movies SET views=views+1 WHERE code=?", (code,))
        c.commit()
    c.close()

    if row:
        _, title, desc, poster, video_id = row
        bot.send_photo(m.chat.id, poster, caption=f"🎬 <b>{title}</b>\n\n🔑 Kodi: <code>{code}</code>\n\n📄 {desc}", parse_mode="HTML")
        bot.send_video(m.chat.id, video_id, caption=f"🍿 Maroqli tomosha: {title} ✨")
    else:
        bot.send_message(m.chat.id, "❌ Kechirasiz, bunday kino kodi topilmadi! To'g'ri kodni kiriting (masalan: 11) 🔍")

setup()
app = Flask(__name__)

@app.route('/')
def home_web():
    return "Bot online 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    setup()
    t = threading.Thread(target=run_web)
    t.start()
    print("👑 KINO OLAMI PRO LUXURY ISHGA TUSHDI! 🚀")
    bot.infinity_polling(skip_pending=True)
    
