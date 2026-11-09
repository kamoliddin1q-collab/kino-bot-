from datetime import datetime
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# --- ASOSIY SOZLAMALAR ---
TOKEN = "9093234322:AAG4l6jKf52a0r-nonnskT1RDOpyDS6l5LE"
ADMIN_ID = 8823389094
DB = "kino_professional.db"

bot = telebot.TeleBot(TOKEN)
user_states = {}

# --- BAZANI YARATish ---
conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    name TEXT,
    file_id TEXT,
    views INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS vip_movies (
    code TEXT PRIMARY KEY,
    name TEXT,
    price TEXT,
    file_id TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    episode INTEGER,
    name TEXT,
    file_id TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    joined_date TEXT,
    is_vip INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cursor.execute("DELETE FROM settings WHERE key = 'required_channel'")
conn.commit()


# --- FLASK SERVER (24/7) ---
app = Flask(__name__)


@app.route("/")
def home():
  return "VIP Kino Biznes Bot 24/7 ishlamoqda! 🚀"


def run_flask():
  app.run(host="0.0.0.0", port=10000)


threading.Thread(target=run_flask).start()


# --- START ---
@bot.message_handler(commands=["start"])
def start(message):
  user_id = message.from_user.id
  user_states[user_id] = {}

  join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id, joined_date, is_vip) VALUES (?, ?,"
      " 0)",
      (user_id, join_date),
  )
  conn.commit()

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton("🎬 Kino qidirish"),
      types.KeyboardButton("🔥 Top Kinolar"),
  )
  markup.add(
      types.KeyboardButton("💎 VIP / Pullik Kinolar"),
      types.KeyboardButton("🎲 Tasodifiy kino"),
  )

  if user_id == ADMIN_ID:
    markup.add(types.KeyboardButton("👑 Admin Panel"))

  welcome_text = (
      f"✨ Assalomu alaykum, {message.from_user.first_name}!\n\n"
      "💎 VIP Kino va Premyeralar olamiga xush kelibsiz!\n"
      "📥 Kino kodini yuboring yoki VIP kinolarni xarid qiling."
  )
  bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# --- VIP KINOLAR MENYUSI ---
@bot.message_handler(func=lambda message: message.text == "💎 VIP / Pullik Kinolar")
def vip_movies_menu(message):
  cursor.execute("SELECT code, name, price FROM vip_movies")
  vips = cursor.fetchall()

  if not vips:
    bot.send_message(
        message.chat.id,
        "💎 Hozircha pullik/VIP kinolar qo'shilmagan. Tez kunda yangi"
        " premyeralar qo'shiladi!",
    )
    return

  markup = types.InlineKeyboardMarkup(row_width=1)
  for v in vips:
    markup.add(
        types.InlineKeyboardButton(
            f"🎬 {v[1]} — 💰 {v[2]}", callback_data=f"buy_vip_{v[0]}"
        )
    )

  bot.send_message(
      message.chat.id,
      "💎 Eksklyuziv VIP va Premyera kinolar ro'yxati:\nKo'rmoqchi bo'lgan"
      " kinongizni tanlang va xarid qiling:",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_vip_"))
def buy_vip_movie(call):
  code = call.data.split("_")[2]
  cursor.execute("SELECT name, price FROM vip_movies WHERE code = ?", (code,))
  res = cursor.fetchone()

  if not res:
    bot.answer_callback_query(call.id, "❌ Kino topilmadi!")
    return

  name, price = res
  cursor.execute("SELECT value FROM settings WHERE key = 'card_number'")
  card_row = cursor.fetchone()
  card_num = (
      card_row[0] if card_row and card_row[0] else "8600 *** *** *** (Admin karta)"
  )

  text = (
      f"💳 Kino xarid qilish:\n\n🎬 Kino: {name}\n💰 Narxi: {price}\n\n💳 To'lov"
      f" uchun karta:\n{card_num}\n👤 Karta egasi: Admin\n\n⚠️ Pulni"
      " o'tkazgandan so'ng, to'lov chegini (skrinshot) shu botga yuboring va"
      f" ustiga '{code} kodli kino uchun' deb yozib qo'ying!"
  )
  bot.send_message(call.message.chat.id, text)
  bot.answer_callback_query(call.id)


# --- TOP KINOLAR VA TASODIFIY ---
@bot.message_handler(func=lambda message: message.text == "🔥 Top Kinolar")
def top_movies(message):
  cursor.execute(
      "SELECT code, name, views FROM movies ORDER BY views DESC LIMIT 5"
  )
  movies = cursor.fetchall()
  if not movies:
    bot.send_message(message.chat.id, "⚠️ Hozircha bazada kinolar yo'q.")
    return
  text = "🔥 TOP Kinolar:\n\n"
  for idx, m in enumerate(movies, 1):
    text += f"{idx}. {m[1]} | 🆔 Kod: {m[0]} | 👀 {m[2]} marta\n"
  bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: message.text == "🎲 Tasodifiy kino")
def random_movie(message):
  cursor.execute("SELECT code, name, file_id FROM movies ORDER BY RANDOM() LIMIT 1")
  movie = cursor.fetchone()
  if not movie:
    bot.send_message(message.chat.id, "⚠️ Kinolar mavjud emas.")
    return
  code, name, file_id = movie
  cursor.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
  conn.commit()
  bot.send_video(message.chat.id, file_id, caption=f"🎲 {name}\n🆔 Kod: {code}")


# --- ADMIN PANEL ---
@bot.message_handler(
    func=lambda message: message.text == "👑 Admin Panel"
    and message.from_user.id == ADMIN_ID
)
def admin_panel(message):
  user_states[message.from_user.id] = {}
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton("➕ Kino qo'shish"),
      types.KeyboardButton("💎 VIP Kino qo'shish"),
  )
  markup.add(
      types.KeyboardButton("➕ Serial qo'shish"),
      types.KeyboardButton("💳 Karta kiritish"),
  )
  markup.add(
      types.KeyboardButton("🗑 Kinoni o'chirish"),
      types.KeyboardButton("❌ Serialni o'chirish"),
  )
  markup.add(
      types.KeyboardButton("📊 Statistika"), types.KeyboardButton("💰 Daromad")
  )
  markup.add(types.KeyboardButton("📢 Reklama"))
  markup.add(types.KeyboardButton("🔙 Bosh menyu"))

  bot.send_message(
      message.chat.id, "👑 Biznes Admin Boshqaruv Paneli:", reply_markup=markup
  )


@bot.message_handler(
    func=lambda message: message.text == "🔙 Bosh menyu"
    and message.from_user.id == ADMIN_ID
)
def back_to_main(message):
  start(message)


# --- STATISTIKA VA DAROMAD ---
@bot.message_handler(
    func=lambda message: message.text == "📊 Statistika"
    and message.from_user.id == ADMIN_ID
)
def statistics(message):
  cursor.execute("SELECT COUNT(*) FROM users")
  users = cursor.fetchone()[0]
  cursor.execute("SELECT COUNT(*) FROM movies")
  movies = cursor.fetchone()[0]
  cursor.execute("SELECT COUNT(*) FROM vip_movies")
  vips = cursor.fetchone()[0]
  cursor.execute("SELECT SUM(views) FROM movies")
  views = cursor.fetchone()[0] or 0

  bot.send_message(
      message.chat.id,
      f"📊 Statistika:\n\n👤 Obunachilar: {users}\n🎬 Oddiy kinolar:"
      f" {movies}\n💎 VIP kinolar: {vips}\n👀 Jami ko'rishlar: {views}",
  )


@bot.message_handler(
    func=lambda message: message.text == "💰 Daromad"
    and message.from_user.id == ADMIN_ID
)
def revenue_panel(message):
  cursor.execute("SELECT COUNT(*) FROM users")
  users = cursor.fetchone()[0]
  bot.send_message(
      message.chat.id,
      f"💰 Daromad bo'limi:\n\n👥 Jami foydalanuvchilar: {users} ta\n💡 VIP"
      " kinolar savdosi va reklamalardan tushadigan mablag'ni kartangiz"
      " orqali nazorat qilasiz.",
  )


# --- ADMIN BUYRUQLARI ---
@bot.message_handler(
    func=lambda message: message.text == "💳 Karta kiritish"
    and message.from_user.id == ADMIN_ID
)
def set_card_start(message):
  user_states[message.from_user.id] = {"step": "waiting_card"}
  bot.send_message(message.chat.id, "💳 To'lov uchun karta raqamini yuboring:")


@bot.message_handler(
    func=lambda message: message.text == "📢 Reklama"
    and message.from_user.id == ADMIN_ID
)
def broadcast_start(message):
  user_states[message.from_user.id] = {"step": "waiting_broadcast"}
  bot.send_message(message.chat.id, "📢 Reklama xabarini yuboring:")


@bot.message_handler(
    func=lambda message: message.text == "➕ Kino qo'shish"
    and message.from_user.id == ADMIN_ID
)
def add_movie_start(message):
  user_states[message.from_user.id] = {"step": "movie_code"}
  bot.send_message(message.chat.id, "🎬 Kino uchun unikal kod kiriting:")


@bot.message_handler(
    func=lambda message: message.text == "💎 VIP Kino qo'shish"
    and message.from_user.id == ADMIN_ID
)
def add_vip_start(message):
  user_states[message.from_user.id] = {"step": "vip_code"}
  bot.send_message(message.chat.id, "💎 VIP kino uchun kod kiriting:")


@bot.message_handler(
    func=lambda message: message.text == "➕ Serial qo'shish"
    and message.from_user.id == ADMIN_ID
)
def add_series_start(message):
  user_states[message.from_user.id] = {"step": "series_code"}
  bot.send_message(message.chat.id, "📺 Serial uchun kod kiriting:")


@bot.message_handler(
    func=lambda message: message.text == "🗑 Kinoni o'chirish"
    and message.from_user.id == ADMIN_ID
)
def del_movie(message):
  user_states[message.from_user.id] = {"step": "delete_movie"}
  bot.send_message(message.chat.id, "🗑 O'chiriladigan kino kodini kiriting:")


# --- XABARLARNI QAYTA ISHLASH ---
@bot.message_handler(content_types=["text", "video", "photo"])
def handle_all_messages(message):
  user_id = message.from_user.id
  text = message.text if message.text else ""

  if user_id == ADMIN_ID and user_id in user_states and user_states[user_id]:
    state = user_states[user_id]
    step = state.get("step")

    if step == "waiting_card":
      cursor.execute(
          "INSERT OR REPLACE INTO settings (key, value) VALUES ('card_number',"
          " ?)",
          (text,),
      )
      conn.commit()
      bot.send_message(message.chat.id, f"✅ Karta raqami saqlandi: {text} ✅")
      user_states[user_id] = {}
      return

    elif step == "waiting_broadcast":
      cursor.execute("SELECT user_id FROM users")
      users = cursor.fetchall()
      success = 0
      for u in users:
        try:
          bot.copy_message(u[0], message.chat.id, message.message_id)
          success += 1
        except:
          pass
      bot.send_message(message.chat.id, f"✅ Reklama {success} kishiga yuborildi!")
      user_states[user_id] = {}
      return

    elif step == "delete_movie":
      cursor.execute("DELETE FROM movies WHERE code = ?", (text,))
      cursor.execute("DELETE FROM vip_movies WHERE code = ?", (text,))
      conn.commit()
      bot.send_message(message.chat.id, f"🗑 {text} kodli kino o'chirildi! ✅")
      user_states[user_id] = {}
      return

    elif step == "vip_code":
      state["code"] = text
      state["step"] = "vip_name"
      bot.send_message(message.chat.id, "📝 VIP kino nomini yuboring:")
      return
    elif step == "vip_name":
      state["name"] = text
      state["step"] = "vip_price"
      bot.send_message(
          message.chat.id, "💰 Kino narxini yuboring (masalan: 10000 so'm):"
      )
      return
    elif step == "vip_price":
      state["price"] = text
      state["step"] = "vip_video"
      bot.send_message(message.chat.id, "🎥 VIP kino videosini yuboring:")
      return
    elif step == "vip_video":
      if not message.video:
        bot.send_message(message.chat.id, "❌ Iltimos, video yuboring:")
        return
      file_id = message.video.file_id
      cursor.execute(
          "INSERT OR REPLACE INTO vip_movies (code, name, price, file_id)"
          " VALUES (?, ?, ?, ?)",
          (state["code"], state["name"], state["price"], file_id),
      )
      conn.commit()
      bot.send_message(
          message.chat.id, f"💎 VIP kino bazaga qo'shildi! Kod: {state['code']}"
      )
      user_states[user_id] = {}
      return

    elif step == "movie_code":
      state["code"] = text
      state["step"] = "movie_name"
      bot.send_message(message.chat.id, "📝 Kino nomini yuboring:")
      return
    elif step == "movie_name":
      state["name"] = text
      state["step"] = "movie_video"
      bot.send_message(message.chat.id, "🎥 Kino videosini yuboring:")
      return
    elif step == "movie_video":
      if not message.video:
        bot.send_message(message.chat.id, "❌ Video fayl yuboring:")
        return
      file_id = message.video.file_id
      cursor.execute(
          "INSERT OR REPLACE INTO movies (code, name, file_id, views) VALUES"
          " (?, ?, ?, 0)",
          (state["code"], state["name"], file_id),
      )
      conn.commit()
      bot.send_message(message.chat.id, f"🔥 Kino qo'shildi! Kod: {state['code']}")
      user_states[user_id] = {}
      return

    elif step == "series_code":
      state["code"] = text
      state["step"] = "series_name"
      bot.send_message(message.chat.id, "📝 Serial nomini yuboring:")
      return
    elif step == "series_name":
      state["name"] = text
      state["step"] = "series_episode"
      bot.send_message(message.chat.id, "🔢 Qism raqamini yuboring:")
      return
    elif step == "series_episode":
      try:
        state["episode"] = int(text)
      except:
        bot.send_message(message.chat.id, "❌ Faqat raqam yuboring:")
        return
      state["step"] = "series_video"
      bot.send_message(message.chat.id, f"🎥 {state['episode']}-qism videosini yuboring:")
      return
    elif step == "series_video":
      if not message.video:
        bot.send_message(message.chat.id, "❌ Video fayl yuboring:")
        return
      file_id = message.video.file_id
      cursor.execute(
          "INSERT INTO series (code, episode, name, file_id) VALUES (?, ?, ?,"
          " ?)",
          (state["code"], state["episode"], state["name"], file_id),
      )
      conn.commit()
      bot.send_message(
          message.chat.id,
          f"🔥 Serial qismi qo'shildi! Kod: {state['code']}",
      )
      user_states[user_id] = {}
      return

  # Qidirish
  cursor.execute(
      "SELECT name, file_id, views FROM movies WHERE code = ?", (text,)
  )
  movie = cursor.fetchone()
  if movie:
    name, file_id, views = movie
    cursor.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (text,))
    conn.commit()
    bot.send_video(
        message.chat.id, file_id, caption=f"🎬 {name}\n👀 Ko'rishlar: {views + 1}"
    )
    return

  cursor.execute(
      "SELECT name, file_id, price FROM vip_movies WHERE code = ?", (text,)
  )
  vip = cursor.fetchone()
  if vip:
    name, file_id, price = vip
    bot.send_video(
        message.chat.id,
        file_id,
        caption=f"💎 Eksklyuziv VIP Kino: {name}\n✨ Maroqli tomosha qiling!",
    )
    return

  bot.send_message(message.chat.id, "❌ Bunday kodli kino topilmadi. Qaytadan urinib ko'ring! 🔍")


# --- CALLBACK ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("ep_"))
def callback_episode(call):
  data_parts = call.data.split("_")
  code = data_parts[1]
  episode_num = data_parts[2]

  cursor.execute(
      "SELECT name, file_id FROM series WHERE code = ? AND episode = ?",
      (code, episode_num),
  )
  res = cursor.fetchone()

  if res:
    name, file_id = res
    bot.send_video(
        call.message.chat.id,
        file_id,
        caption=f"📺 {name} ({episode_num}-qism)\n🍿 Maroqli tomosha!",
    )
    bot.answer_callback_query(call.id)
  else:
    bot.answer_callback_query(call.id, "❌ Bu qism topilmadi!")


# --- ISHGA TUSHIRISH ---
print("VIP Biznes Kino Bot muvaffaqiyatli ishga tushdi...")
bot.infinity_polling()
