from datetime import datetime
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# --- ASOSIY SOZLAMALAR (Yangi Token bilan) ---
TOKEN = "9093234322:AAFMmvGVEl-1LvAQrl4qZTaUdr-iWGOdOMY"
ADMIN_ID = 8823389094
DB = "kino_professional.db"

bot = telebot.TeleBot(TOKEN)
user_states = {}

# --- BAZANI YARATISH ---
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
conn.commit()


# --- KANALNI TEKSHIRISH FUNKSIYASI ---
def check_channel_sub(user_id):
  cursor.execute("SELECT value FROM settings WHERE key = 'required_channel'")
  row = cursor.fetchone()
  if not row or not row[0]:
    return True

  channel = row[0]
  try:
    member = bot.get_chat_member(channel, user_id)
    if member.status in ["member", "administrator", "creator"]:
      return True
  except:
    pass
  return False


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

  if not check_channel_sub(user_id) and user_id != ADMIN_ID:
    cursor.execute("SELECT value FROM settings WHERE key = 'required_channel'")
    channel = cursor.fetchone()[0]
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "📢 Kanalga a'zo bo'lish",
            url=f"https://t.me/{channel.replace('@', '')}",
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "✅ Obunani tekshirish", callback_data="check_sub"
        )
    )
    bot.send_message(
        message.chat.id,
        "⚠️ Botdan foydalanish uchun quyidagi kanalimizga a'zo bo'lishingiz"
        " kerak:",
        reply_markup=markup,
    )
    return

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton("🎬 Kino qidirish"),
      types.KeyboardButton("📺 Seriallar"),
  )
  markup.add(
      types.KeyboardButton("🔥 Top Kinolar"),
      types.KeyboardButton("💎 VIP / Pullik Kinolar"),
  )
  markup.add(types.KeyboardButton("🎲 Tasodifiy kino"))

  if user_id == ADMIN_ID:
    markup.add(types.KeyboardButton("👑 Admin Panel"))

  welcome_text = (
      f"✨ Assalomu alaykum, {message.from_user.first_name}!\n\n"
      "💎 VIP Kino va Seriallar olamiga xush kelibsiz!\n"
      "📥 Kino yoki serial kodini yuboring."
  )
  bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
  if check_channel_sub(call.from_user.id):
    bot.answer_callback_query(call.id, "Rahmat! Obuna tasdiqlandi ✅")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start(call.message)
  else:
    bot.answer_callback_query(
        call.id, "❌ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True
    )


# --- SERIALLAR MENYUSI ---
@bot.message_handler(func=lambda message: message.text == "📺 Seriallar")
def series_menu(message):
  cursor.execute("SELECT DISTINCT code, name FROM series")
  all_series = cursor.fetchall()

  if not all_series:
    bot.send_message(
        message.chat.id,
        "📺 Hozircha bazada seriallar yo'q. Tez kunda yangi seriallar"
        " qo'shiladi!",
    )
    return

  text = "📺 Bazadagi mavjud seriallar ro'yxati:\n\n"
  for s in all_series:
    text += f"🎬 {s[1]} | 🆔 Kod: {s[0]}\n"
  text

