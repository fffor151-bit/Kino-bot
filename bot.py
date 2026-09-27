import json
import os
import logging
import telebot

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Telegram Bot Tokeni
TOKEN = "8979562987:AAE90B2YYzhMu_k7qFeDhJAAKoOehsM6Iqc"
bot = telebot.TeleBot(TOKEN)

# Admin ID raqami kiritildi
ADMIN_IDS = [8852571142]

DB_FILE = "database.json"

# ================= BAZA BILAN ISHLASH =================
def load_movies():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_movies(movies):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=4)

# ================= ASOSIY BUYRUQLAR =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    msg = (
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        f"🎬 Kino ko'rish uchun kino kodini yuboring (Masalan: 101):"
    )
    if user_id in ADMIN_IDS:
        msg += (
            "\n\n👨‍💻 **Admin buyruqlari:**\n"
            "/add - Yangi kino qo'shish\n"
            "/del - Kinoni o'chirish\n"
            "/list - Barcha kinolar ro'yxati"
        )
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# ================= KINO QO'SHISH (ADMIN) =================
@bot.message_handler(commands=['add'])
def add_movie_start(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Siz admin emassiz!")
        return

    msg = bot.send_message(message.chat.id, "➕ Yangi kino **kodini** kiriting (Masalan: 101):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_code_step)

def process_code_step(message):
    code = message.text.strip()
    movies = load_movies()

    if code in movies:
        bot.send_message(message.chat.id, "⚠️ Bu kod bilan kino allaqachon mavjud! Amal bekor qilindi.")
        return

    msg = bot.send_message(
        message.chat.id, 
        f"✅ Kod `{code}` saqlandi.\nEndi kino **linkini** (veb havola yoki kanal post ssilkasini) yuboring:", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_link_step, code)

def process_link_step(message, code):
    link = message.text.strip()
    movies = load_movies()
    movies[code] = link
    save_movies(movies)

    bot.send_message(
        message.chat.id, 
        f"🎉 **Kino muvaffaqiyatli qo'shildi!**\n\nKodi: `{code}`\nLink: {link}", 
        parse_mode="Markdown"
    )

# ================= KINO O'CHIRISH (ADMIN) =================
@bot.message_handler(commands=['del'])
def del_movie_start(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Siz admin emassiz!")
        return

    msg = bot.send_message(message.chat.id, "🗑 O'chirmoqchi bo'lgan kinoning **kodini** kiriting:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_del_step)

def process_del_step(message):
    code = message.text.strip()
    movies = load_movies()

    if code in movies:
        del movies[code]
        save_movies(movies)
        bot.send_message(message.chat.id, f"✅ Kodi `{code}` bo'lgan kino o'chirib tashlandi!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Bunday kodli kino bazada topilmadi.")

# ================= KINOLAR RO'YXATI (ADMIN) =================
@bot.message_handler(commands=['list'])
def list_movies(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Siz admin emassiz!")
        return

    movies = load_movies()
    if not movies:
        bot.send_message(message.chat.id, "📂 Bazada hech qanday kino yo'q.")
        return

    text = "📋 **Mavjud kinolar ro'yxati:**\n\n"
    for code, link in movies.items():
        text += f"🔹 **Kod:** `{code}` | [Ko'rish]({link})\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

# ================= FOYDALANUVCHILAR UCHUN KINO IZLASH =================
@bot.message_handler(func=lambda message: True)
def handle_user_code(message):
    code = message.text.strip()
    movies = load_movies()

    if code in movies:
        movie_link = movies[code]
        bot.send_message(
            message.chat.id,
            f"🎬 **Kino topildi!**\n\n"
            f"Kino kodi: `{code}`\n"
            f"🍿 Tomosha qilish uchun bosing: [Kinoni ko'rish]({movie_link})",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "❌ Bunday kodli kino topilmadi. Kodi to'g'riligini tekshiring!")

# ================= BOTNI ISHGA TUSHIRISH =================
if __name__ == "__main__":
    print("Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
