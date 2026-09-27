import os
import json
import telebot
from telebot import types

# Environment Variables'dan tokenni olish (Render uchun)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8979562987:AAEMP-FMFBmbXmSG-gyxeZe-hMwciHE5lWQ")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8852571142"))

bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "database.json"

# ================= BAZA BILAN ISHLASH =================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"movies": {}, "channels": [], "users": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"movies": {}, "channels": [], "users": []}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

# ================= MAJBURIY OBUNA TEKSHIRISH =================
def check_sub(user_id):
    db = load_db()
    channels = db.get("channels", [])
    if not channels:
        return True, None

    unsub_markup = types.InlineKeyboardMarkup()
    has_unsub = False

    for idx, ch in enumerate(channels, 1):
        try:
            member = bot.get_chat_member(ch["id"], user_id)
            if member.status in ["left", "kicked"]:
                has_unsub = True
                unsub_markup.add(types.InlineKeyboardButton(text=f"📢 {idx}-kanalga obuna bo'lish", url=ch["url"]))
        except Exception:
            has_unsub = True
            unsub_markup.add(types.InlineKeyboardButton(text=f"📢 {idx}-kanalga obuna bo'lish", url=ch["url"]))

    if has_unsub:
        unsub_markup.add(types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
        return False, unsub_markup

    return True, None

# ================= KEYBOARDLAR =================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔍 Qidiruv", "🔥 Mashhur kinolar")
    markup.row("👤 Profil", "🔗 Referal tizim")
    if user_id == ADMIN_ID:
        markup.row("👑 Admin Panel")
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Kino qo'shish", "🗑 Kino o'chirish")
    markup.row("📢 Kanal qo'shish", "🗑 Kanalni o'chirish")
    markup.row("📊 Statistika", "⬅️ Bosh menyu")
    return markup

# ================= COMMAND HANDLERS =================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    db = load_db()
    user_id = message.from_user.id

    if user_id not in db["users"]:
        db["users"].append(user_id)
        save_db(db)

    is_sub, ikb = check_sub(user_id)
    if not is_sub:
        bot.send_message(message.chat.id, "🔒 **Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:**", reply_markup=ikb, parse_mode="Markdown")
        return

    bot.send_message(
        message.chat.id,
        f"👋 Assalomu alaykum, {message.from_user.first_name}!\n\n"
        "🎬 **KINO BOT**ga xush kelibsiz!\n"
        "Kino ko'rish uchun **kino kodini** yuboring:",
        reply_markup=get_main_keyboard(user_id)
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_cb(call):
    is_sub, ikb = check_sub(call.from_user.id)
    if is_sub:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ Rahmat! Barcha kanallarga obuna bo'ldingiz.", reply_markup=get_main_keyboard(call.from_user.id))
    else:
        bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)

# ================= ADMIN VA FOYDALANUVCHI BO'LIMLARI =================
@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()

    is_sub, ikb = check_sub(user_id)
    if not is_sub and text != "⬅️ Bosh menyu":
        bot.send_message(message.chat.id, "🔒 Boshlashdan oldin kanallarga obuna bo'ling:", reply_markup=ikb)
        return

    db = load_db()

    if text == "⬅️ Bosh menyu":
        bot.send_message(message.chat.id, "🏠 Bosh menyu", reply_markup=get_main_keyboard(user_id))

    elif text == "👤 Profil":
        bot.send_message(message.chat.id, f"👤 **PROFILINGIZ:**\n\n🆔 ID: `{user_id}`", parse_mode="Markdown")

    elif text == "🔗 Referal tizim":
        bot_info = bot.get_me()
        bot.send_message(message.chat.id, f"🔗 Sizning referal havolangiz:\nhttps://t.me/{bot_info.username}?start={user_id}")

    elif text == "👑 Admin Panel" and user_id == ADMIN_ID:
        bot.send_message(message.chat.id, "👑 **Admin Panel**", reply_markup=get_admin_keyboard())

    elif text == "📊 Statistika" and user_id == ADMIN_ID:
        u_count = len(db.get("users", []))
        m_count = len(db.get("movies", {}))
        bot.send_message(message.chat.id, f"📊 **STATISTIKA:**\n\n👥 Foydalanuvchilar: **{u_count}** ta\n🎬 Kinolar: **{m_count}** ta", parse_mode="Markdown")

    elif text == "➕ Kino qo'shish" and user_id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "🔑 Yangi kino kodini kiriting (masalan: 101):")
        bot.register_next_step_handler(msg, process_add_movie_code)

    elif text == "🗑 Kino o'chirish" and user_id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "🗑 O'chirmoqchi bo'lgan kino kodini kiriting:")
        bot.register_next_step_handler(msg, process_del_movie)

    elif text == "📢 Kanal qo'shish" and user_id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "📢 Kanal ID sini kiriting (masalan: -100123456789):")
        bot.register_next_step_handler(msg, process_add_channel_id)

    elif text == "🗑 Kanalni o'chirish" and user_id == ADMIN_ID:
        db["channels"] = []
        save_db(db)
        bot.send_message(message.chat.id, "✅ Barcha majburiy obuna kanallari o'chirib tashlandi!")

    elif text in db["movies"]:
        movie = db["movies"][text]
        bot.send_message(
            message.chat.id,
            f"🎬 **{movie['title']}**\n\n"
            f"🍿 Tomosha qilish uchun bosing: [Kinoni ko'rish]({movie['link']})",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "❌ Bunday kodli kino topilmadi.")

# ================= ADMIN STEP PROCESSORS =================
def process_add_movie_code(message):
    code = message.text.strip()
    msg = bot.send_message(message.chat.id, f"✅ Kod: `{code}` saqlandi.\n\nEndi kino nomini va linkini quyidagi formatda yuboring:\n`Kino Nomi | https://t.me/...`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: process_add_movie_data(m, code))

def process_add_movie_data(message, code):
    try:
        title, link = message.text.split("|")
        db = load_db()
        db["movies"][code] = {"title": title.strip(), "link": link.strip()}
        save_db(db)
        bot.send_message(message.chat.id, f"🎉 Kino muvaffaqiyatli qo'shildi!\nKodi: `{code}`", parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, "❌ Xatolik! Noto'g'ri formatda yubordingiz. Qaytadan urinib ko'ring.")

def process_del_movie(message):
    code = message.text.strip()
    db = load_db()
    if code in db["movies"]:
        del db["movies"][code]
        save_db(db)
        bot.send_message(message.chat.id, f"✅ Kodi `{code}` bo'lgan kino o'chirildi!")
    else:
        bot.send_message(message.chat.id, "❌ Bunday kodli kino topilmadi.")

def process_add_channel_id(message):
    ch_id = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔗 Kanalning taklif havolasini (url) kiriting:")
    bot.register_next_step_handler(msg, lambda m: process_add_channel_url(m, ch_id))

def process_add_channel_url(message, ch_id):
    url = message.text.strip()
    db = load_db()
    db["channels"].append({"id": ch_id, "url": url})
    save_db(db)
    bot.send_message(message.chat.id, "✅ Majburiy obuna kanali muvaffaqiyatli qo'shildi!")

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
