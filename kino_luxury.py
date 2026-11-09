from datetime import datetime, timedelta
import os
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

# --- BAZANI YARATISH VA SOZLASH ---
conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

# 1. Kinolar jadvali
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    name TEXT,
    file_id TEXT,
    views INTEGER DEFAULT 0
)
"""
)

# 2. Seriallar jadvali
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    episode INTEGER,
    name TEXT,
    file_id TEXT
)
"""
)

# 3. Foydalanuvchilar jadvali
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    joined_date TEXT
)
"""
)
conn.commit()


# --- FLASK SERVER (24/7 UptimeRobot uchun) ---
app = Flask(__name__)


@app.route("/")
def home():
  return "Professional Kino Bot 24/7 rejimida ishlamoqda! 🚀"


def run_flask():
  app.run(host="0.0.0.0", port=10000)


threading.Thread(target=run_flask).start()


# --- START VA ASOSIY MENYU ---
@bot.message_handler(commands=["start"])
def start(message):
  user_id = message.from_user.id
  join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id, joined_date) VALUES (?, ?)",
      (user_id, join_date),
  )
  conn.commit()

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn_search = types.KeyboardButton("🎬 Kino qidirish")
  btn_top = types.KeyboardButton("🔥 Top Kinolar")
  btn_random = types.KeyboardButton("🎲 Tasodifiy kino")
  markup.add(btn_search, btn_top, btn_random)

  if user_id == ADMIN_ID:
    btn_admin = types.KeyboardButton("👑 Admin Panel")
    markup.add(btn_admin)

  welcome_text = (
      f"✨ Assalomu alaykum, **{message.from_user.first_name}**!\n\n"
      "💎 **VIP Kino olamimizga** xush kelibsiz! Eng sara kino va seriallarni "
      "yuqori sifatda tomosha qiling.\n\n"
      "📥 Kerakli kino yoki serial **kodini** yuboring (Masalan: `1`, `101`)"
  )
  bot.send_message(
      message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown"
  )


# --- TOP KINOLAR VA TASODIFIY KINO ---
@bot.message_handler(func=lambda message: message.text == "🔥 Top Kinolar")
def top_movies(message):
  cursor.execute(
      "SELECT code, name, views FROM movies ORDER BY views DESC LIMIT 5"
  )
  movies = cursor.fetchall()

  if not movies:
    bot.send_message(
        message.chat.id,
        "⚠️ Hozircha bazada ommabop kinolar yo'q.",
        parse_mode="Markdown",
    )
    return

  text = "🔥 **Eng ko'p ko'rilgan TOP kinolar:**\n\n"
  for idx, m in enumerate(movies, 1):
    text += f"{idx}. **{m[1]}** | 🆔 Kod: `{m[0]}` | 👀 Ko'rishlar: `{m[2]}`\n"

  bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text == "🎲 Tasodifiy kino")
def random_movie(message):
  cursor.execute("SELECT code, name, file_id FROM movies ORDER BY RANDOM() LIMIT 1")
  movie = cursor.fetchone()

  if not movie:
    bot.send_message(
        message.chat.id,
        "⚠️ Hozircha bazada kinolar mavjud emas.",
        parse_mode="Markdown",
    )
    return

  code, name, file_id = movie
  cursor.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
  conn.commit()

  bot.send_video(
      message.chat.id,
      file_id,
      caption=(
          f"🎲 **Tasodifiy tanlangan kino:**\n\n🎬 **{name}**\n🆔 Kod: `{code}`\n\n🍿"
          f" Maroqli hordiq tilaymiz! ✨\n🤖 Bot: @{bot.get_me().username}"
      ),
      parse_mode="Markdown",
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
      "👑 **Professional Admin Boshqaruv Paneliga** xush kelibsiz:",
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

  cursor.execute("SELECT SUM(views) FROM movies")
  total_views = cursor.fetchone()[0] or 0

  stats_text = (
      f"📊 **Botning To'liq Statistikasi:**\n\n"
      f"👤 Jami obunachilar: `{users_count}` ta\n"
      f"🎬 Kinolar soni: `{movies_count}` ta\n"
      f"📺 Seriallar soni: `{series_count}` ta\n"
      f"👀 Kinolar ko'rilishi: `{total_views}` marta"
  )
  bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")


# --- REKLAMA TARQATISH ---
@bot.message_handler(
    func=lambda message: message.text == "📢 Reklama"
    and message.from_user.id == ADMIN_ID
)
def broadcast_start(message):
  user_states[message.from_user.id] = {"step": "waiting_broadcast"}
  bot.send_message(
      message.chat.id,
      "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan reklama xabaringizni"
      " (matn, rasm yoki video) yuboring:",
  )


# --- O'CHIRISH BUYRUQLARI ---
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
      "🎬 Kino uchun unikal kod kiriting (masalan: `1`):",
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


# --- XABARLARNI QAYTA ISHLASH (ADMIN VA FOYDALANUVCHI) ---
@bot.message_handler(content_types=["text", "video", "photo"])
def handle_all_messages(message):
  user_id = message.from_user.id

  # 1. Reklama yuborish jarayoni
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
        f"✅ Reklama muvaffaqiyatli `{success}` ta foydalanuvchiga yetkazildi! 🚀",
        parse_mode="Markdown",
    )
    user_states[user_id] = {}
    return

  # 2. Admin boshqaruv amallari
  if user_id == ADMIN_ID and user_id in user_states:
    state = user_states[user_id]

    # Kinoni o'chirish
    if state["step"] == "delete_movie_code":
      code = message.text
      cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
      conn.commit()
      bot.send_message(
          message.chat.id,
          f"🗑 `{code}` kodli kino bazadan muvaffaqiyatli o'chirildi! ✅",
          parse_mode="Markdown",
      )
      user_states[user_id] = {}
      return

    # Serialni o'chirish
    elif state["step"] == "delete_series_code":
      code = message.text
      cursor.execute("DELETE FROM series WHERE code = ?", (code,))
      conn.commit()
      bot.send_message(
          message.chat.id,
          f"❌ `{code}` kodli serial va uning barcha qismlari o'chirildi! ✅",
          parse_mode="Markdown",
      )
      user_states[user_id] = {}
      return

    # Kino qo'shish: Kod
    elif state["step"] == "movie_code":
      state["code"] = message.text
      state["step"] = "movie_name"
      bot.send_message(message.chat.id, "📝 Kino nomini yuboring:")
      return

    # Kino qo'shish: Nomi
    elif state["step"] == "movie_name":
      state["name"] = message.text
      state["step"] = "movie_video"
      bot.send_message(
          message.chat.id,
          "🎥 Kino videosini yuboring (poster talab qilinmaydi):",
      )
      return

    # Kino qo'shish: Video
    elif state["step"] == "movie_video":
      if not message.video:
        bot.send_message(
            message.chat.id,
            "❌ Xatolik! Iltimos, video fayl yuboring. Qaytadan urinib ko'ring:",
        )
        return
      file_id = message.video.file_id
      cursor.execute(
          "INSERT OR REPLACE INTO movies (code, name, file_id, views) VALUES"
          " (?, ?, ?, 0)",
          (state["code"], state["name"], file_id),
      )
      conn.commit()
      bot.send_message(
          message.chat.id,
          f"🔥 Kino muvaffaqiyatli bazaga qo'shildi!\n🆔 Kodi: `{state['code']}`",
          parse_mode="Markdown",
      )
      user_states[user_id] = {}
      return

    # Serial qo'shish: Kod
    elif state["step"] == "series_code":
      state["code"] = message.text
      state["step"] = "series_name"
      bot.send_message(message.chat.id, "📝 Serial nomini yuboring:")
      return

    # Serial qo'shish: Nomi
    elif state["step"] == "series_name":
      state["name"] = message.text
      state["step"] = "series_episode"
      bot.send_message(
          message.chat.id, "🔢 Serial qism raqamini kiriting (masalan: 1):"
      )
      return

    # Serial qo'shish: Qism raqami
    elif state["step"] == "series_episode":
      try:
        state["episode"] = int(message.text)
      except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Faqat raqam kiriting! Qism raqamini qaytadan yuboring:",
        )
        return
      state["step"] = "series_video"
      bot.send_message(
          message.chat.id, f"🎥 Serialning {state['episode']}-qism videosini yuboring:"
      )
      return

    # Serial qo'shish: Video
    elif state["step"] == "series_video":
      if not message.video:
        bot.send_message(
            message.chat.id,
            "❌ Xatolik! Iltimos, video fayl yuboring. Qaytadan yuboring:",
        )
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
          f"🔥 Serial qismi qo'shildi!\n🆔 Kod: `{state['code']}` | 📌 Qism:"
          f" `{state['episode']}-qism`",
          parse_mode="Markdown",
      )
      user_states[user_id] = {}
      return

  # 3. Odatiy foydalanuvchi qidiruvi
  text = message.text
  if text == "🎬 Kino qidirish":
    bot.send_message(
        message.chat.id,
        "✨ Marhamat, ko'rmoqchi bo'lgan kino yoki serial kodini yuboring:",
    )
    return

  # Kinoni qidirish
  cursor.execute(
      "SELECT name, file_id, views FROM movies WHERE code = ?", (text,)
  )
  movie = cursor.fetchone()

  if movie:
    name, file_id, views = movie
    cursor.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (text,))
    conn.commit()

    bot.send_video(
        message.chat.id,
        file_id,
        caption=(
            f"🎬 **{name}**\n\n👀 Ko'rishlar soni: `{views + 1}` marta\n🍿 Maroqli"
            f" tomosha tilaymiz! ✨\n🤖 Bot manzili: @{bot.get_me().username}"
        ),
        parse_mode="Markdown",
    )
    return

  # Serialni qidirish
  cursor.execute(
      "SELECT episode FROM series WHERE code = ? ORDER BY episode ASC", (text,)
  )
  episodes = cursor.fetchall()

  if episodes:
    cursor.execute("SELECT name FROM series WHERE code = ?", (text,))
    series_name = cursor.fetchone()[0]

    markup = types.InlineKeyboardMarkup(row_width=4)
    buttons = []
    for ep in episodes:
      ep_num = ep[0]
      buttons.append(
          types.InlineKeyboardButton(
              f"✨ {ep_num}-qism", callback_data=f"ep_{text}_{ep_num}"
          )
      )
    markup.add(*buttons)

    bot.send_message(
        message.chat.id,
        f"📺 **{series_name}**\n\n💎 Kerakli qismni tanlang:",
        reply_markup=markup,
        parse_mode="Markdown",
    )
    return

  bot.send_message(
      message.chat.id,
      "❌ Kechirasiz, bunday kodli kino yoki serial topilmadi. Boshqa kod"
      " yuborib ko'ring! 🔍",
  )


# --- SERIAL QISMLARINI TANLASH (CALLBACK) ---
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
        caption=(
            f"📺 **{name}** (`{episode_num}-qism`)\n\n🍿 Maroqli tomosha! ✨\n🤖"
            f" Bot: @{bot.get_me().username}"
        ),
        parse_mode="Markdown",
    )
    bot.answer_callback_query(call.id)
  else:
    bot.answer_callback_query(call.id, "❌ Bu qism topilmadi!")


# --- BOTNI ISHGA TUSHIRISH ---
print("Professional VIP Kino Bot muvaffaqiyatli ishga tushdi...")
bot.infinity_polling()
    
