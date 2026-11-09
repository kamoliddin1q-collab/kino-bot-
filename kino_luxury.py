from datetime import datetime, timedelta
import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# --- ASOSIY SOZLAMALAR ---
TOKEN = "9093234322:AAG416jKf52a0r-nonns..."  # O'z tokeningni yozasan
ADMIN_ID = 8823389094  # Sening Telegram ID raqaming
DB = "kino_luxury.db"

bot = telebot.TeleBot(TOKEN)
user_states = {}

# --- BAZANI YARATISH ---
conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    name TEXT,
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
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# --- FLASK SERVER (24/7 UptimeRobot uchun) ---
app = Flask(__name__)


@app.route("/")
def home():
  return "Bot 24/7 rejimida VIP formatda ishlayapti! 🚀"


def run_flask():
  app.run(host="0.0.0.0", port=10000)


threading.Thread(target=run_flask).start()


# --- START VA ASOSIY VIP MENYU ---
@bot.message_handler(commands=["start"])
def start(message):
  user_id = message.from_user.id
  cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
  conn.commit()

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add(types.KeyboardButton("🎬 Kino qidirish"))
  if user_id == ADMIN_ID:
    markup.add(types.KeyboardButton("👑 Admin Panel"))

  welcome_text = (
      f"✨ Salom, **{message.from_user.first_name}**! VIP Kino olamimizga xush"
      " kelibsiz! 💎\n\n🍿 Maroqli hordiq chiqarish uchun istalgan kino yoki"
      " serial **kodini** yuboring (Masalan: `1`, `101`)"
  )
  bot.send_message(
      message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown"
  )


# --- ADMIN PANEL ---
@bot.message_handler(
    func=lambda message: message.text == "👑 Admin Panel"
    and message.from_user.id == ADMIN_ID
)
def admin_panel(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton("➕ Kino qo'shish"),
      types.KeyboardButton("➕ Serial qo'shish"),
  )
  markup.add(
      types.KeyboardButton("🗑 Kinoni o'chirish"),
      types.KeyboardButton("❌ Serialni o'chirish"),
  )
  markup.add(
      types.KeyboardButton("📊 Statistika"), types.KeyboardButton("📢 Reklama")
  )
  markup.add(types.KeyboardButton("🔙 Bosh menyu"))
  bot.send_message(
      message.chat.id,
      "👑 **VIP Boshqaruv Paneliga** xush kelibsiz:",
      reply_markup=markup,
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: message.text == "🔙 Bosh menyu"
    and message.from_user.id == ADMIN_ID
)
def back_to_main(message):
  start(message)


# --- STATISTIKA ---
@bot.message_handler(
    func=lambda message: message.text == "📊 Statistika"
    and message.from_user.id == ADMIN_ID
)
def statistics(message):
  cursor.execute("SELECT COUNT(*) FROM users")
  users_count = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(*) FROM movies")
  movies_count = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(DISTINCT code) FROM series")
  series_count = cursor.fetchone()[0]

  stats_text = (
      f"📊 **VIP Bot Statistikasi:**\n\n👤 Obunachilar: `{users_count}` ta\n🎬"
      f" Kinolar: `{movies_count}` ta\n📺 Seriallar: `{series_count}` ta"
  )
  bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")


# --- REKLAMA ---
@bot.message_handler(
    func=lambda message: message.text == "📢 Reklama"
    and message.from_user.id == ADMIN_ID
)
def broadcast_start(message):
  user_states[message.from_user.id] = {"step": "waiting_broadcast"}
  bot.send_message(
      message.chat.id,
      "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan VIP xabaringizni"
      " (matn, rasm yoki video) yuboring:",
  )


# --- O'CHIRISH BUYRUQLARI (ADMIN) ---
@bot.message_handler(
    func=lambda message: message.text == "🗑 Kinoni o'chirish"
    and message.from_user.id == ADMIN_ID
)
def delete_movie_start(message):
  user_states[message.from_user.id] = {"step": "delete_movie_code"}
  bot.send_message(
      message.chat.id,
      "🗑 O'chirmoqchi bo'lgan kino kodini kiriting (masalan: `1`):",
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: message.text == "❌ Serialni o'chirish"
    and message.from_user.id == ADMIN_ID
)
def delete_series_start(message):
  user_states[message.from_user.id] = {"step": "delete_series_code"}
  bot.send_message(
      message.chat.id,
      "❌ Barcha qismlari bilan o'chirmoqchi bo'lgan serial kodini kiriting"
      " (masalan: `10`):",
      parse_mode="Markdown",
  )


# --- KINO VA SERIAL QO'SHISH BOSQICHLARI ---
@bot.message_handler(
    func=lambda message: message.text == "➕ Kino qo'shish"
    and message.from_user.id == ADMIN_ID
)
def add_movie_start(message):
  user_states[message.from_user.id] = {"step": "movie_code"}
  bot.send_message(
      message.chat.id,
      "🎬 Kino uchun VIP kod kiriting (masalan: `1`):",
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: message.text == "➕ Serial qo'shish"
    and message.from_user.id == ADMIN_ID
)
def add_series_start(message):
  user_states[message.from_user.id] = {"step": "series_code"}
  bot.send_message(
      message.chat.id,
      "📺 Serial uchun kod kiriting (masalan: `10`):",
      parse_mode="Markdown",
  )


# --- XABARLARNI QAYTA ISHLASH ---
@bot.message_handler(content_types=["text", "video", "photo"])
def handle_all_messages(message):
  user_id = message.from_user.id

  # 1. Reklama tarqatish
  if user_id == ADMIN_ID and user_states.get(user_id, {}).get(
      "step"
  ) == "waiting_broadcast":
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    success = 0
    for u in users:
      try:
        bot.copy_message(u[0], message.chat.id, message.message_id)
        success += 1
      except:
        pass
    bot.send_message(
        message.chat.id,
        f"✨ Reklama muvaffaqiyatli `{success}` ta foydalanuvchiga yuborildi! 🚀",
        parse_mode="Markdown",
)
