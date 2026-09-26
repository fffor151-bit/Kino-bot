Import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Message,
    CallbackQuery
)

# ================= 1. SOZLAMALAR =================
TOKEN = "8979562987:AAEMP-FMFBmbXmSG-gyxeZe-hMwciHE5lWQ"
ADMIN_ID = 8852571142  

DB_NAME = "kino_bot.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ================= 2. BAZA BILAN ISHLASH =================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                status TEXT DEFAULT 'user',
                referrer_id INTEGER DEFAULT 0,
                referrals_count INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                last_bonus TEXT DEFAULT '',
                joined_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                file_id TEXT,
                category TEXT DEFAULT 'Umumiy',
                is_vip INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                rating_sum INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                added_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                channel_url TEXT
            )
        ''')
        conn.commit()

init_db()


# ================= 3. HOLATLAR (FSM) =================
class AdminStates(StatesGroup):
    add_movie_code = State()
    add_movie_title = State()
    add_movie_desc = State()
    add_movie_is_vip = State()
    add_movie_file = State()
    
    del_movie_code = State()
    broadcast_msg = State()
    
    add_channel_id = State()
    add_channel_url = State()

class SearchStates(StatesGroup):
    waiting_query = State()


# ================= 4. TUGMALAR (KEYBOARDS) =================
def get_main_keyboard(user_id: int):
    kb = [
        [KeyboardButton(text="🔍 Qidiruv"), KeyboardButton(text="🔥 Mashhur kinolar")],
        [KeyboardButton(text="🆕 So'nggi kinolar"), KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="🎁 Kunlik Bonus"), KeyboardButton(text="🔗 Referal tizim")],
        [KeyboardButton(text="💎 VIP/Premium")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="👑 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_keyboard():
    kb = [
        [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
        [KeyboardButton(text="📢 Kanal qo'shish"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="⬅️ Bosh menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ================= 5. OBUNA TEKSHIRISH =================
async def check_subscriptions(user_id: int) -> tuple[bool, InlineKeyboardMarkup]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, channel_url FROM channels")
        channels = cursor.fetchall()
    
    if not channels:
        return True, None
        
    unsubscribed_buttons = []
    for row in channels:
        c_id, c_url = row["channel_id"], row["channel_url"]
        try:
            member = await bot.get_chat_member(chat_id=c_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unsubscribed_buttons.append([InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=c_url)])
        except Exception:
            unsubscribed_buttons.append([InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=c_url)])
            
    if unsubscribed_buttons:
        unsubscribed_buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
        return False, InlineKeyboardMarkup(inline_keyboard=unsubscribed_buttons)
        
    return True, None


# ================= 6. ASOSIY HANDLERLAR =================
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (user_id, referrer_id, joined_at) VALUES (?, ?, ?)",
                (user_id, referrer_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            if referrer_id and referrer_id != user_id:
                cursor.execute("UPDATE users SET referrals_count = referrals_count + 1, points = points + 10 WHERE user_id = ?", (referrer_id,))
                try:
                    await bot.send_message(referrer_id, "🎉 Sizning havolangiz orqali yangi foydalanuvchi qo'shildi! +10 ball berildi.")
                except Exception:
                    pass
            conn.commit()

    is_sub, ikb = await check_subscriptions(user_id)
    if not is_sub:
        await message.answer("🔒 **Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:**", reply_markup=ikb)
        return

    await message.answer(
        f"👋 Assalomu alaykum, {message.from_user.first_name}!\n\n"
        "🎬 **KINO BOT**ga xush kelibsiz!\n"
        "Kino ko'rish uchun **kino kodini** kiriting yoki menyudan foydalaning.",
        reply_markup=get_main_keyboard(user_id)
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub_cb(callback: CallbackQuery):
    is_sub, ikb = await check_subscriptions(callback.from_user.id)
    if is_sub:
        await callback.message.delete()
        await callback.message.answer("✅ Rahmat! Barcha kanallarga obuna bo'ldingiz.", reply_markup=get_main_keyboard(callback.from_user.id))
    else:
        await callback.answer("❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)


# ================= 7. FOYDALANUVCHI MENYUSI =================
@dp.message(F.text == "⬅️ Bosh menyu")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Bosh menyu", reply_markup=get_main_keyboard(message.from_user.id))

@dp.message(F.text == "👤 Profil")
async def profile_cmd(message: Message):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, points, referrals_count FROM users WHERE user_id = ?", (message.from_user.id,))
        res = cursor.fetchone()

    status, points, refs = (res["status"], res["points"], res["referrals_count"]) if res else ("user", 0, 0)
    await message.answer(
        f"👤 **PROFILINGIZ:**\n\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"💎 Status: **{status.upper()}**\n"
        f"🌟 Ballar: **{points}**\n"
        f"👥 Taklif qilgan do'stlar: **{refs} ta**",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🎁 Kunlik Bonus")
async def daily_bonus(message: Message):
    user_id = message.from_user.id
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()

        now = datetime.now()
        if res and res["last_bonus"]:
            last_time = datetime.strptime(res["last_bonus"], "%Y-%m-%d %H:%M:%S")
            if now - last_time < timedelta(hours=24):
                await message.answer("⏳ Bugungi bonusni olgansiz! Har 24 soatda bir marta beriladi.")
                return

        cursor.execute("UPDATE users SET points = points + 5, last_bonus = ? WHERE user_id = ?", (now.strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()

    await message.answer("🎉 Tabriklaymiz! Sizga **+5 ball** kunlik bonus berildi!")

@dp.message(F.text == "🔗 Referal tizim")
async def referral_cmd(message: Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(f"🔗 Sizning referal havolangiz:\n`{ref_link}`\n\n👥 Har bir taklif uchun +10 ball!", parse_mode="Markdown")

@dp.message(F.text == "💎 VIP/Premium")
async def vip_info(message: Message):
    await message.answer("💎 **VIP / PREMIUM STATUS**\n\nVIP foydalanuvchilar barcha maxsus kinolarni tomosha qilishlari mumkin.\nMurojaat uchun: @org_R4VEN")


# ================= 8. QIDIRUV VA KINO KODI =================
@dp.message(F.text == "🔍 Qidiruv")
async def start_search(message: Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_query)
    await message.answer("🔎 Kino nomini kiriting:")

@dp.message(SearchStates.waiting_query)
async def process_search(message: Message, state: FSMContext):
    query = f"%{message.text.strip()}%"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code, title FROM movies WHERE title LIKE ? LIMIT 10", (query,))
        results = cursor.fetchall()

    await state.clear()
    if not results:
        await message.answer("❌ Hech qanday kino topilmadi.")
        return

    msg = "🔍 **Topilgan kinolar:**\n\n"
    for row in results:
        msg += f"🎬 **{row['title']}** — Kodi: `{row['code']}`\n"
    await message.answer(msg, parse_mode="Markdown")

@dp.message(F.text == "🔥 Mashhur kinolar")
async def popular_movies(message: Message):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code, title, views FROM movies ORDER BY views DESC LIMIT 5")
        movies = cursor.fetchall()

    if not movies:
        await message.answer("📂 Hozircha kinolar yo'q.")
        return

    text = "🔥 **Eng mashhur kinolar:**\n\n"
    for row in movies:
        text += f"👁 {row['views']} marta ko'rilgan: **{row['title']}** (Kodi: `{row['code']}`)\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🆕 So'nggi kinolar")
async def latest_movies(message: Message):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code, title FROM movies ORDER BY added_at DESC LIMIT 5")
        movies = cursor.fetchall()

    if not movies:
        await message.answer("📂 Hozircha kinolar yo'q.")
        return

    text = "🆕 **So'nggi kinolar:**\n\n"
    for row in movies:
        text += f"🎬 **{row['title']}** — Kodi: `{row['code']}`\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text.isdigit())
async def get_movie_by_code(message: Message):
    user_id = message.from_user.id
    is_sub, ikb = await check_subscriptions(user_id)
    if not is_sub:
        await message.answer("🔒 Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=ikb)
        return

    code = message.text.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, description, file_id, is_vip, views, rating_sum, rating_count FROM movies WHERE code = ?", (code,))
        movie = cursor.fetchone()

        if not movie:
            await message.answer("❌ Bunday kodli kino topilmadi.")
            return

        title, desc, file_id, is_vip, views, r_sum, r_count = (
            movie["title"], movie["description"], movie["file_id"], 
            movie["is_vip"], movie["views"], movie["rating_sum"], movie["rating_count"]
        )

        cursor.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
        u_res = cursor.fetchone()
        user_status = u_res["status"] if u_res else "user"

        if is_vip and user_status not in ["vip", "premium"] and user_id != ADMIN_ID:
            await message.answer("🔒 Bu kino faqat **VIP** foydalanuvchilar uchun!")
            return

        cursor.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
        conn.commit()

    avg_rating = round(r_sum / r_count, 1) if r_count > 0 else "Baho berilmagan"
    caption = (
        f"🎬 **{title}**\n\n"
        f"📝 {desc}\n\n"
        f"⭐ Reyting: {avg_rating}\n"
        f"👁 Ko'rishlar: {views + 1}\n"
        f"🔑 Kodi: `{code}`"
    )

    rate_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_{code}_1"),
        InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_{code}_2"),
        InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_{code}_3"),
        InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_{code}_4"),
        InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_{code}_5")
    ]])

    await message.answer_video(video=file_id, caption=caption, parse_mode="Markdown", reply_markup=rate_kb)

@dp.callback_query(F.data.startswith("rate_"))
async def rate_movie(callback: CallbackQuery):
    _, code, rating = callback.data.split("_")
    rating = int(rating)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE movies SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE code = ?", (rating, code))
        conn.commit()

    await callback.answer("⭐ Bahoyingiz saqlandi!", show_alert=True)


# ================= 9. ADMIN PANEL =================
@dp.message(F.text == "👑 Admin Panel")
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("👑 **Admin Panel**", reply_markup=get_admin_keyboard())

@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        u_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM movies")
        m_count = cursor.fetchone()[0]

    await message.answer(f"📊 **STATISTIKA:**\n\n👥 Foydalanuvchilar: **{u_count}**\n🎬 Kinolar: **{m_count}**")

@dp.message(F.text == "➕ Kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.add_movie_code)
    await message.answer("🔑 Kino kodini kiriting (masalan: 101):")

@dp.message(AdminStates.add_movie_code)
async def add_movie_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await state.set_state(AdminStates.add_movie_title)
    await message.answer("🎬 Kino nomini kiriting:")

@dp.message(AdminStates.add_movie_title)
async def add_movie_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminStates.add_movie_desc)
    await message.answer("📝 Kino tavsifini kiriting:")

@dp.message(AdminStates.add_movie_desc)
async def add_movie_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminStates.add_movie_is_vip)
    await message.answer("💎 Kino **VIP** bo'lsinmi? (1 - Ha, 0 - Yo'q):")

@dp.message(AdminStates.add_movie_is_vip)
async def add_movie_vip(message: Message, state: FSMContext):
    is_vip = 1 if message.text.strip() == "1" else 0
    await state.update_data(is_vip=is_vip)
    await state.set_state(AdminStates.add_movie_file)
    await message.answer("🎥 Kinoning **videosini** yuboring:")

@dp.message(AdminStates.add_movie_file, F.video)
async def add_movie_file(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO movies (code, title, description, file_id, is_vip, added_at) VALUES (?, ?, ?, ?, ?, ?)",
            (data['code'], data['title'], data['description'], file_id, data['is_vip'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

    await state.clear()
    await message.answer(f"✅ Kino saqlandi!\n🔑 Kodi: `{data['code']}`", parse_mode="Markdown")

@dp.message(F.text == "🗑 Kino o'chirish")
async def del_movie_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.del_movie_code)
    await message.answer("🗑 O'chirmoqchi bo'lgan kino kodini kiriting:")

@dp.message(AdminStates.del_movie_code)
async def del_movie_code(message: Message, state: FSMContext):
    code = message.text.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
        conn.commit()

    await state.clear()
    await message.answer(f"✅ `{code}` kodli kino o'chirildi!")

@dp.message(F.text == "📢 Kanal qo'shish")
async def add_channel_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.add_channel_id)
    await message.answer("📢 Kanal ID raqamini kiriting (masalan: `-100123456789`):")

@dp.message(AdminStates.add_channel_id)
async def add_channel_id(message: Message, state: FSMContext):
    await state.update_data(c_id=message.text.strip())
    await state.set_state(AdminStates.add_channel_url)
    await message.answer("🔗 Kanalning taklif havolasini (linkini) kiriting:")

@dp.message(AdminStates.add_channel_url)
async def add_channel_url(message: Message, state: FSMContext):
    data = await state.get_data()
    url = message.text.strip()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO channels (channel_id, channel_url) VALUES (?, ?)", (data['c_id'], url))
        conn.commit()

    await state.clear()
    await message.answer("✅ Majburiy obuna kanali qo'shildi!")

@dp.message(F.text == "📢 Broadcast")
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.broadcast_msg)
    await message.answer("📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:")

@dp.message(AdminStates.broadcast_msg)
async def broadcast_send(message: Message, state: FSMContext):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

    count = 0
    for row in users:
        try:
            await bot.copy_message(chat_id=row["user_id"], from_chat_id=message.chat.id, message_id=message.message_id)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await state.clear()
    await message.answer(f"✅ Xabar **{count} ta** foydalanuvchiga yuborildi!")


# ================= 10. BOTNI ISHGA TUSHIRISH =================
async def main():
    print("🚀 Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
