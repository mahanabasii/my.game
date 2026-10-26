import asyncio
import datetime
import os
import random
import time

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

# ==========================================
# تنظیمات اولیه
# ==========================================
# توکن رو توی متغیر محیطی BOT_TOKEN بذار (نه داخل کد)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7663602336"))
DB_NAME = "ocean_game.db"

if not BOT_TOKEN:
    raise SystemExit("❌ متغیر محیطی BOT_TOKEN تنظیم نشده.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# بازی‌های در حال اجرا (در حافظه)
active_games = {}
rps_games = {}
tictactoe_games = {}

# ==========================================
# ثابت‌ها و داده‌های بازی
# ==========================================
BABY_NAMES = ["آراد", "آوا", "ماهان", "رها", "پارسا", "نیلا", "امیر", "سارا", "علی", "مریم"]

MISSION_POOL = [
    {"code": "wheel", "title": "گردونه امروز رو بچرخون", "target": 1, "reward_money": 500, "reward_xp": 15},
    {"code": "slots", "title": "۲۰ بار اسلات بزن", "target": 20, "reward_money": 800, "reward_xp": 37},
    {"code": "duel", "title": "۵ بار دعوا کن", "target": 5, "reward_money": 500, "reward_xp": 25},
    {"code": "rps", "title": "۱۰ بار سنگ کاغذ قیچی", "target": 10, "reward_money": 500, "reward_xp": 25},
    {"code": "dice", "title": "۱۰ بار تاس بازی کن", "target": 10, "reward_money": 300, "reward_xp": 15},
    {"code": "roulette", "title": "۵ بار رولت روسی", "target": 5, "reward_money": 400, "reward_xp": 20},
    {"code": "bomb", "title": "۵ بار انفجار", "target": 5, "reward_money": 600, "reward_xp": 30},
    {"code": "collect", "title": "۳ بار برداشت درآمد", "target": 3, "reward_money": 300, "reward_xp": 15},
]

# (نام، قیمت، نوع، قدرت)
BLACK_MARKET_ITEMS = [
    ("🎭 نقاب", 2000, "steal_gear", 5), ("🧤 دستکش", 2000, "steal_gear", 5),
    ("🪢 طناب", 3200, "steal_gear", 8), ("💎 الماس", 60000, "steal_gear", 10),
    ("🏍️ موتور", 10000, "steal_gear", 15), ("🧪 اسپری", 12000, "steal_gear", 20),
    ("🚗 ماشین فرار", 50000, "steal_gear", 25), ("💻 ابزار هک", 100000, "steal_gear", 30),
    ("🗡️ شمشیر چوبی", 2000, "duel_item", 5), ("🔪 چاقو", 2000, "duel_item", 10),
    ("🛡️ زره چرمی", 3200, "duel_item", 15), ("⚔️ شمشیر آهنی", 12000, "duel_item", 25),
    ("🛡️ زره آهنی", 24000, "duel_item", 30), ("🔫 کلت", 10000, "duel_item", 40),
    ("🛡️ جلیقه", 16000, "duel_item", 45), ("🔫 مسلسل", 32000, "duel_item", 60),
    ("🔫 تفنگ", 48000, "duel_item", 75), ("🗡️ شمشیر الماسی", 100000, "duel_item", 85),
    ("🛡️ سپر روئین", 120000, "duel_item", 90), ("🛡️ زره تیتانیوم", 200000, "duel_item", 100),
    ("🔫 اسنایپر", 600000, "duel_item", 120), ("🛡️ زره طلایی", 320000, "duel_item", 130),
    ("🗡️ شمشیر افسانه‌ای", 800000, "duel_item", 150), ("💥 RPG", 1000000, "duel_item", 180),
    ("🛡️ زره اژدها", 1200000, "duel_item", 200),
    ("🛡️ هکر اخلاقی", 3200000, "protection_ethical", 0), ("🛡️ بادیگارد", 2000000, "protection_bodyguard", 0),
    ("🚀 موشک F14", 9000000, "missile_f14", 0), ("🚀 موشک F35", 25000000, "missile_f35", 0),
    ("🛡️ پدافند", 15000000, "defense", 0),
    ("🐇 خرگوش", 3000, "pet_rabbit", 6), ("🐈 گربه", 5000, "pet_cat", 10), ("🐕 سگ", 8000, "pet_dog", 15),
    ("🐺 گرگ", 50000, "pet_wolf", 50), ("🦅 عقاب", 800000, "pet_eagle", 250), ("🐉 اژدها", 2000000, "pet_dragon", 1000),
]

# قدرت آیتم‌های دعوا (از لیست بازار سیاه ساخته می‌شه)
DUEL_POWER = {name: power for name, _, itype, power in BLACK_MARKET_ITEMS if itype == "duel_item"}

CARS_LIST = [
    ("🚙 پریاید", 80000, 20), ("🚗 پژو ۲۰۶", 250000, 50), ("🚗 سمند", 400000, 80), ("🚕 شاهین", 800000, 150),
    ("🏍️ BMW", 2500000, 350), ("🚘 مرسدس", 4000000, 600), ("🏎️ فراری", 10000000, 1000), ("🏆 بوگاتی", 30000000, 2500),
]

SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "⭐", "7️⃣", "💎"]
WEEK_SECONDS = 604800


class AdminStates(StatesGroup):
    waiting_code = State()
    waiting_transfer = State()
    waiting_xp = State()


# ==========================================
# کیبوردها
# ==========================================
def back_kb(target: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data=target)]])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 پروفایل / موجودی", callback_data="profile"), InlineKeyboardButton(text="🏡 کسب درآمد", callback_data="earn")],
        [InlineKeyboardButton(text="🏦 بانک و ترید", callback_data="bank"), InlineKeyboardButton(text="💸 صرافی رمزارز", callback_data="crypto")],
        [InlineKeyboardButton(text="🏁 مسابقه ماشین", callback_data="car_menu"), InlineKeyboardButton(text="🕶️ بازار سیاه", callback_data="blackmarket")],
        [InlineKeyboardButton(text="🕸️ دارک وب", callback_data="darkweb"), InlineKeyboardButton(text="📦 انبار", callback_data="inventory")],
        [InlineKeyboardButton(text="🐾 پت‌ها", callback_data="my_pets"), InlineKeyboardButton(text="🎯 ماموریت‌ها", callback_data="missions")],
        [InlineKeyboardButton(text="🎁 کد هدیه", callback_data="gift_code"), InlineKeyboardButton(text="🛒 فروشگاه", callback_data="shop")],
        [InlineKeyboardButton(text="⚔️ دعوا", callback_data="duel_menu"), InlineKeyboardButton(text="❓ راهنما", callback_data="help")],
    ])


# ==========================================
# دیتابیس
# ==========================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        tables = [
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, balance INTEGER DEFAULT 500, bank_balance INTEGER DEFAULT 0, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0, created_at INTEGER DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS properties (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, income_5h INTEGER)",
            "CREATE TABLE IF NOT EXISTS user_properties (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, property_id INTEGER, last_collected_time INTEGER, workers_count INTEGER DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS workers (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, income_bonus INTEGER)",
            "CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT, item_type TEXT, price INTEGER, quantity INTEGER DEFAULT 1)",
            "CREATE TABLE IF NOT EXISTS gift_codes (code TEXT PRIMARY KEY, amount INTEGER, max_uses INTEGER, current_uses INTEGER DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS code_history (user_id INTEGER, code TEXT, PRIMARY KEY(user_id, code))",
            "CREATE TABLE IF NOT EXISTS protections (user_id INTEGER PRIMARY KEY, ethical_hacker_expiry INTEGER DEFAULT 0, ethical_hacker_uses INTEGER DEFAULT 0, bodyguard_expiry INTEGER DEFAULT 0, bodyguard_uses INTEGER DEFAULT 0, insurance_expiry INTEGER DEFAULT 0, defense_expiry INTEGER DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS hack_history (user_id INTEGER PRIMARY KEY, last_hack_time INTEGER)",
            "CREATE TABLE IF NOT EXISTS user_pets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, pet_name TEXT, level INTEGER DEFAULT 1, power INTEGER, hunger INTEGER DEFAULT 100)",
            "CREATE TABLE IF NOT EXISTS marriages (user_id INTEGER PRIMARY KEY, spouse_id INTEGER, last_sex_time INTEGER DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS children (id INTEGER PRIMARY KEY AUTOINCREMENT, parent1_id INTEGER, parent2_id INTEGER, name TEXT, stage INTEGER DEFAULT 0, birth_time INTEGER)",
            "CREATE TABLE IF NOT EXISTS crypto_prices (coin TEXT PRIMARY KEY, price REAL NOT NULL)",
            "CREATE TABLE IF NOT EXISTS user_crypto (user_id INTEGER, coin TEXT, amount REAL DEFAULT 0, PRIMARY KEY(user_id, coin))",
            "CREATE TABLE IF NOT EXISTS daily_cooldowns (user_id INTEGER PRIMARY KEY, last_wheel_spin INTEGER DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS user_missions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, mission_code TEXT, title TEXT, target INTEGER, progress INTEGER DEFAULT 0, reward_money INTEGER, reward_xp INTEGER, reset_date TEXT)",
            "CREATE TABLE IF NOT EXISTS user_cars (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, car_name TEXT, level INTEGER DEFAULT 1, power INTEGER)",
            "CREATE TABLE IF NOT EXISTS attack_cooldown (user_id INTEGER PRIMARY KEY, last_hacker_time INTEGER DEFAULT 0, last_assassin_time INTEGER DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, amount INTEGER, trans_type TEXT, trans_time INTEGER)",
            "CREATE TABLE IF NOT EXISTS lottery (user_id INTEGER PRIMARY KEY, tickets INTEGER DEFAULT 0)",
        ]
        for sql in tables:
            await db.execute(sql)

        if (await (await db.execute("SELECT COUNT(*) FROM properties")).fetchone())[0] == 0:
            await db.executemany("INSERT INTO properties VALUES (?, ?, ?, ?)", [
                (1, "🏪 سوپرمارکت", 200000, 8000), (2, "🍞 نانوایی", 700000, 28000),
                (3, "🌿 مزرعه گل", 1500000, 60000), (4, "🏭 کارگاه", 3500000, 150000),
                (5, "🥀 مزرعه تریاک", 7000000, 300000), (6, "💊 آزمایشگاه", 13000000, 420000),
                (7, "🏦 بانک", 25000000, 800000), (8, "🏝️ جزیره", 50000000, 1500000),
            ])
        if (await (await db.execute("SELECT COUNT(*) FROM workers")).fetchone())[0] == 0:
            await db.executemany("INSERT INTO workers VALUES (?, ?, ?, ?)", [
                (1, "👨‍🍳 آشپز", 250000, 9500), (2, "🚚 راننده", 400000, 16000),
                (3, "⛏️ معدن‌چی", 1000000, 40000), (4, "🧕 جندس", 1400000, 58000),
                (5, "👸 فمبوی", 1800000, 76000), (6, "🤖 ربات", 3500000, 155000),
                (7, "🚀 ایلان ماسک", 4500000, 200000),
            ])
        for coin, price in [("BTC", 60000.0), ("ETH", 3000.0), ("DOGE", 0.15)]:
            await db.execute("INSERT OR IGNORE INTO crypto_prices (coin, price) VALUES (?, ?)", (coin, price))
        await db.commit()


# ==========================================
# توابع کمکی
# ==========================================
async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT user_id, first_name, balance, bank_balance, level, xp FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def ensure_user(user_id: int, first_name=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, first_name, created_at) VALUES (?, ?, ?)", (user_id, first_name, int(time.time())))
        await db.commit()


async def add_xp(user_id, amount, db):
    user = await (await db.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))).fetchone()
    if not user:
        return
    current_xp, current_level = user[0] + amount, user[1]
    xp_needed = 100 + (current_level - 1) * 75
    new_level = current_level
    while current_xp >= xp_needed and new_level < 30:
        current_xp -= xp_needed
        new_level += 1
        xp_needed = 100 + (new_level - 1) * 75
    await db.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (current_xp, new_level, user_id))
    if new_level > current_level:
        try:
            await bot.send_message(user_id, f"🎉 **تبریک!** تو به لول **{new_level}** رسیدی!\n(پاداش: ۱۰,۰۰۰ دلار)")
            await db.execute("UPDATE users SET balance = balance + 10000 WHERE user_id = ?", (user_id,))
        except Exception:
            pass


async def track_mission(user_id, code, amount, db):
    today = datetime.date.today().isoformat()
    await db.execute("UPDATE user_missions SET progress = MIN(target, progress + ?) WHERE user_id = ? AND mission_code = ? AND reset_date = ?", (amount, user_id, code, today))
    comp = await (await db.execute("SELECT id, reward_money, reward_xp FROM user_missions WHERE user_id = ? AND mission_code = ? AND progress >= target AND reset_date = ?", (user_id, code, today))).fetchone()
    if comp:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (comp[1], user_id))
        await db.execute("DELETE FROM user_missions WHERE id = ?", (comp[0],))
        await add_xp(user_id, comp[2], db)


def calc_income(base_income: int, workers: int, last_collected: int) -> int:
    """درآمد ملک: پایه + ۴۰,۰۰۰ به ازای هر کارگر، حداکثر برای ۵ ساعت (۱۸۰۰۰ ثانیه)."""
    elapsed = min(int(time.time()) - last_collected, 18000)
    return int(((base_income + workers * 40000) / 18000) * elapsed)


def parse_amount(text: str, index: int):
    """عدد مثبت از یک بخش پیام می‌گیره؛ اگه نامعتبر بود None برمی‌گردونه."""
    try:
        value = int(text.split()[index])
    except (ValueError, IndexError):
        return None
    return value if value > 0 else None


# ==========================================
# 1. منوی اصلی، پروفایل، راهنما، فروشگاه
# ==========================================
def main_menu_text(first_name: str, user) -> str:
    return f"👋 سلام {first_name}\n\n💰 موجودی: ${user[2]:,}\n🏦 بانک: ${user[3]:,}\n🏷️ سطح: {user[4]}\n\nاز منوی زیر استفاده کن:"


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await ensure_user(message.from_user.id, message.from_user.first_name)
    user = await get_user(message.from_user.id)
    await message.answer(main_menu_text(message.from_user.first_name, user), reply_markup=main_menu_keyboard())


@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    await callback.message.edit_text(main_menu_text(callback.from_user.first_name, user), reply_markup=main_menu_keyboard())


@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if user[4] >= 30:
        xp_txt = "حداکثر لول (۳۰) 👑"
    else:
        xp_txt = f"تا لول بعدی: {(100 + (user[4] - 1) * 75) - user[5]:,} XP"
    await callback.message.edit_text(
        f"👤 **پروفایل شما**\n\n🆔 آیدی: `{user[0]}`\n💰 موجودی: ${user[2]:,}\n🏦 بانک: ${user[3]:,}\n🏷️ سطح: **{user[4]}** (XP: {user[5]:,})\n📈 {xp_txt}\n",
        reply_markup=back_kb(), parse_mode="Markdown")


@dp.callback_query(F.data == "help")
async def help_cmd(callback: CallbackQuery):
    text = (
        "❓ **راهنمای بازی**\n\n"
        "🏡 **کسب درآمد:** ملک بخر و کارگر استخدام کن تا درآمد بگیری.\n"
        "🏦 **بانک:** پولت رو سپرده کن تا سود بگیری.\n"
        "🕶️ **بازار سیاه:** آیتم بخر تا قوی‌تر شی.\n"
        "🕸️ **دارک وب:** هک و اجیر کردن با ریسک.\n"
        "🎁 **کد هدیه:** توی گروه بنویس `کد هدیه mk4`\n"
        "🎯 **ماموریت‌ها:** هر روز انجام بده و XP بگیر.\n\n"
        "🎮 **بازی‌های گروهی (توی گروه بنویس):**\n"
        "`فایت 5000` ← فایت پت\n"
        "`مسابقه 5000` ← مسابقه ماشین\n"
        "`دعوا آیدی مبلغ` ← دعوا\n"
        "`اسلات 1000` / `گردونه` / `تاس` / `رولت`"
    )
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")


@dp.callback_query(F.data == "shop")
async def shop_cmd(callback: CallbackQuery):
    await callback.answer("🚧 فروشگاه به زودی...", show_alert=True)


@dp.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


# ==========================================
# 2. کسب درآمد (ملک و کارگر)
# ==========================================
@dp.callback_query(F.data == "earn")
async def earn_menu(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    async with aiosqlite.connect(DB_NAME) as db:
        props = await (await db.execute(
            "SELECT up.id, p.name, p.income_5h, up.last_collected_time, up.workers_count FROM user_properties up JOIN properties p ON up.property_id = p.id WHERE up.user_id = ?",
            (callback.from_user.id,))).fetchall()
    for up in props:
        money = calc_income(up[2], up[4], up[3])
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"🏠 {up[1]} | برداشت: ${money:,}", callback_data=f"collect_{up[0]}")])
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"👷‍♂️ کارگرهای {up[1]} ({up[4]})", callback_data=f"workers_{up[0]}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="خرید ملک جدید 🛒", callback_data="buy_prop_menu")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")])
    await callback.message.edit_text("🏡 **مدیریت کسب و کارها:**", reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data == "buy_prop_menu")
async def buy_prop_menu(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    async with aiosqlite.connect(DB_NAME) as db:
        for p in await (await db.execute("SELECT * FROM properties")).fetchall():
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"{p[1]} | ${p[2]:,}", callback_data=f"buy_prop_{p[0]}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="earn")])
    await callback.message.edit_text("🛒 **خرید ملک:**", reply_markup=kb)


@dp.callback_query(F.data.startswith("buy_prop_"))
async def buy_prop(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        p = await (await db.execute("SELECT * FROM properties WHERE id = ?", (int(callback.data.split("_")[2]),))).fetchone()
        if (await get_user(callback.from_user.id))[2] >= p[2]:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (p[2], callback.from_user.id))
            await db.execute("INSERT INTO user_properties (user_id, property_id, last_collected_time) VALUES (?, ?, ?)", (callback.from_user.id, p[0], int(time.time())))
            await add_xp(callback.from_user.id, 50, db)
            await db.commit()
            await callback.answer(f"✅ {p[1]} خریداری شد!", show_alert=True)
            await earn_menu(callback)
        else:
            await callback.answer("❌ پول نداری!", show_alert=True)


@dp.callback_query(F.data.startswith("collect_"))
async def collect_income(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        up = await (await db.execute(
            "SELECT up.*, p.income_5h FROM user_properties up JOIN properties p ON up.property_id = p.id WHERE up.id = ?",
            (int(callback.data.split("_")[1]),))).fetchone()
        money = calc_income(up[5], up[4], up[3])
        if money > 0:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (money, callback.from_user.id))
            await db.execute("UPDATE user_properties SET last_collected_time = ? WHERE id = ?", (int(time.time()), up[0]))
            await track_mission(callback.from_user.id, "collect", 1, db)
            await add_xp(callback.from_user.id, 10, db)
            await db.commit()
            await callback.answer(f"💰 ${money:,} برداشت شد!", show_alert=True)
        else:
            await callback.answer("⏳ زمان نگذشته!", show_alert=True)
    await earn_menu(callback)


@dp.callback_query(F.data.startswith("workers_"))
async def workers_menu(callback: CallbackQuery):
    up_id = int(callback.data.split("_")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    async with aiosqlite.connect(DB_NAME) as db:
        for w in await (await db.execute("SELECT * FROM workers")).fetchall():
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"{w[1]} | ${w[2]:,} (+${w[3]:,})", callback_data=f"hire_{up_id}_{w[0]}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="earn")])
    await callback.message.edit_text("👷‍♂️ **استخدام کارگر:**", reply_markup=kb)


@dp.callback_query(F.data.startswith("hire_"))
async def hire_worker(callback: CallbackQuery):
    _, up_id, worker_id = callback.data.split("_")
    async with aiosqlite.connect(DB_NAME) as db:
        w = await (await db.execute("SELECT * FROM workers WHERE id = ?", (int(worker_id),))).fetchone()
        if (await get_user(callback.from_user.id))[2] >= w[2]:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (w[2], callback.from_user.id))
            await db.execute("UPDATE user_properties SET workers_count = workers_count + 1 WHERE id = ?", (int(up_id),))
            await db.commit()
            await callback.answer(f"✅ {w[1]} استخدام شد!", show_alert=True)
        else:
            await callback.answer("❌ پول نداری!", show_alert=True)
    await workers_menu(callback)


# ==========================================
# 3. بانک و ترید
# ==========================================
@dp.callback_query(F.data == "bank")
async def bank_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ واریز ۱۰,۰۰۰", callback_data="bank_dep_10000")],
        [InlineKeyboardButton(text="➖ برداشت ۱۰,۰۰۰", callback_data="bank_with_10000")],
        [InlineKeyboardButton(text="📈 ترید (شرط ۵۰-۵۰)", callback_data="trade")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")],
    ])
    await callback.message.edit_text(f"🏦 **بانک**\n\n💰 موجودی شما: ${user[2]:,}\n🏦 سپرده شما: ${user[3]:,}\n\nسود روزانه ۱٪", reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("bank_dep_"))
async def bank_deposit(callback: CallbackQuery):
    amount = int(callback.data.split("_")[2])
    if (await get_user(callback.from_user.id))[2] >= amount:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET balance = balance - ?, bank_balance = bank_balance + ? WHERE user_id = ?", (amount, amount, callback.from_user.id))
            await db.execute("INSERT INTO transactions (sender_id, receiver_id, amount, trans_type, trans_time) VALUES (?, 0, ?, 'واریز', ?)", (callback.from_user.id, amount, int(time.time())))
            await db.commit()
        await callback.answer(f"✅ ${amount:,} واریز شد!", show_alert=True)
        await bank_menu(callback)
    else:
        await callback.answer("❌ موجودی کافی نیست!", show_alert=True)


@dp.callback_query(F.data.startswith("bank_with_"))
async def bank_withdraw(callback: CallbackQuery):
    amount = int(callback.data.split("_")[2])
    user = await get_user(callback.from_user.id)
    if user[3] >= amount:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET balance = balance + ?, bank_balance = bank_balance - ? WHERE user_id = ?", (amount, amount, callback.from_user.id))
            await db.execute("INSERT INTO transactions (sender_id, receiver_id, amount, trans_type, trans_time) VALUES (0, ?, ?, 'برداشت', ?)", (callback.from_user.id, amount, int(time.time())))
            await db.commit()
        await callback.answer(f"✅ ${amount:,} برداشت شد!", show_alert=True)
        await bank_menu(callback)
    else:
        await callback.answer("❌ موجودی بانکی کافی نیست!", show_alert=True)


@dp.callback_query(F.data == "trade")
async def trade(callback: CallbackQuery):
    if (await get_user(callback.from_user.id))[2] < 1000:
        return await callback.answer("❌ پول کافی نداری!", show_alert=True)
    won = random.choice([True, False])
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (1000 if won else -1000, callback.from_user.id))
        await db.commit()
    await callback.answer("🎉 بردی! ۱۰۰۰ دلار گرفتی." if won else "😢 باختی! ۱۰۰۰ دلار دادی.", show_alert=True)


# ==========================================
# 4. صرافی رمزارز
# ==========================================
@dp.callback_query(F.data == "crypto")
async def crypto_menu(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        prices = {r[0]: r[1] for r in await (await db.execute("SELECT coin, price FROM crypto_prices")).fetchall()}
        user_coins = {r[0]: r[1] for r in await (await db.execute("SELECT coin, amount FROM user_crypto WHERE user_id = ?", (callback.from_user.id,))).fetchall()}
    user = await get_user(callback.from_user.id)
    text = f"💸 **صرافی**\n\n💰 موجودی: ${user[2]:,.2f}\n\n📊 **قیمت‌ها:**\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for coin, price in prices.items():
        text += f"• {coin}: ${price:,.2f} | دارایی: {user_coins.get(coin, 0):.4f}\n"
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"🛒 خرید {coin}", callback_data=f"buy_crypto_{coin}"),
            InlineKeyboardButton(text=f"💵 فروش {coin}", callback_data=f"sell_crypto_{coin}"),
        ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 آپدیت", callback_data="crypto"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("buy_crypto_"))
async def buy_crypto(callback: CallbackQuery):
    coin = callback.data.split("_")[2]
    async with aiosqlite.connect(DB_NAME) as db:
        price = (await (await db.execute("SELECT price FROM crypto_prices WHERE coin = ?", (coin,))).fetchone())[0]
        if (await get_user(callback.from_user.id))[2] < 10:
            return await callback.answer("❌ نیاز به ۱۰ دلار!", show_alert=True)
        await db.execute("UPDATE users SET balance = balance - 10 WHERE user_id = ?", (callback.from_user.id,))
        await db.execute("INSERT INTO user_crypto (user_id, coin, amount) VALUES (?, ?, ?) ON CONFLICT(user_id, coin) DO UPDATE SET amount = amount + excluded.amount", (callback.from_user.id, coin, 10 / price))
        await db.commit()
    await callback.answer(f"✅ {10 / price:.4f} {coin} خریدی!", show_alert=True)
    await crypto_menu(callback)


@dp.callback_query(F.data.startswith("sell_crypto_"))
async def sell_crypto(callback: CallbackQuery):
    coin = callback.data.split("_")[2]
    async with aiosqlite.connect(DB_NAME) as db:
        price = (await (await db.execute("SELECT price FROM crypto_prices WHERE coin = ?", (coin,))).fetchone())[0]
        row = await (await db.execute("SELECT amount FROM user_crypto WHERE user_id = ? AND coin = ?", (callback.from_user.id, coin))).fetchone()
        amount = row[0] if row else 0
        if amount <= 0:
            return await callback.answer("❌ نداری!", show_alert=True)
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount * price, callback.from_user.id))
        await db.execute("UPDATE user_crypto SET amount = 0 WHERE user_id = ? AND coin = ?", (callback.from_user.id, coin))
        await db.commit()
    await callback.answer(f"✅ ${amount * price:,.2f} گرفتی!", show_alert=True)
    await crypto_menu(callback)


# ==========================================
# 5. بازار سیاه (با صفحه‌بندی)
# ==========================================
BM_PAGE_SIZE = 8


async def blackmarket_render(callback: CallbackQuery, page: int):
    total = len(BLACK_MARKET_ITEMS)
    total_pages = (total + BM_PAGE_SIZE - 1) // BM_PAGE_SIZE
    start = (page - 1) * BM_PAGE_SIZE
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    # در callback_data فقط ایندکس آیتم می‌ره (محدودیت ۶۴ بایت تلگرام + جلوگیری از خراب شدن split با _)
    for i in range(start, min(start + BM_PAGE_SIZE, total)):
        name, price, _, _ = BLACK_MARKET_ITEMS[i]
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{name} | ${price:,}", callback_data=f"buy_bm_{i}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"bm_page_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"bm_page_{page + 1}"))
    kb.inline_keyboard.append(nav)
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")])
    await callback.message.edit_text("🕶️ **بازار سیاه**", reply_markup=kb)


@dp.callback_query(F.data.startswith("bm_page_"))
async def bm_page_cb(callback: CallbackQuery):
    await blackmarket_render(callback, int(callback.data.split("_")[2]))


@dp.callback_query(F.data == "blackmarket")
async def bm_main_cb(callback: CallbackQuery):
    await blackmarket_render(callback, 1)


@dp.callback_query(F.data.startswith("buy_bm_"))
async def buy_bm(callback: CallbackQuery):
    name, price, itype, power = BLACK_MARKET_ITEMS[int(callback.data.split("_")[2])]
    user_id = callback.from_user.id
    if (await get_user(user_id))[2] < price:
        return await callback.answer("❌ پول کافی نیست!", show_alert=True)
    expiry = int(time.time()) + WEEK_SECONDS
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        if itype == "protection_ethical":
            await db.execute("INSERT INTO protections (user_id, ethical_hacker_expiry, ethical_hacker_uses) VALUES (?, ?, 5) ON CONFLICT(user_id) DO UPDATE SET ethical_hacker_expiry = excluded.ethical_hacker_expiry, ethical_hacker_uses = 5", (user_id, expiry))
        elif itype == "protection_bodyguard":
            await db.execute("INSERT INTO protections (user_id, bodyguard_expiry, bodyguard_uses) VALUES (?, ?, 2) ON CONFLICT(user_id) DO UPDATE SET bodyguard_expiry = excluded.bodyguard_expiry, bodyguard_uses = 2", (user_id, expiry))
        elif itype == "defense":
            await db.execute("INSERT INTO protections (user_id, defense_expiry) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET defense_expiry = excluded.defense_expiry", (user_id, expiry))
        elif itype.startswith("pet_"):
            await db.execute("INSERT INTO user_pets (user_id, pet_name, power) VALUES (?, ?, ?)", (user_id, name, power))
        else:
            await db.execute("INSERT INTO inventory (user_id, item_name, item_type, price) VALUES (?, ?, ?, ?)", (user_id, name, itype, price))
        await db.commit()
    await callback.answer(f"✅ {name} خریداری شد!", show_alert=True)


# ==========================================
# 6. دارک وب و هک
# ==========================================
@dp.callback_query(F.data == "darkweb")
async def darkweb(callback: CallbackQuery):
    text = "🕸️ **دارک وب**\n\n⚔️ **خدمات جنایی (با ریپلای):**\n• `اجیر هکر` (دزدی ۳۰٪)\n• `اجیر قاتل` (دزدی ۱۵٪)\n\n💻 **ابزار هک:**\n`هک [آیدی عددی]`"
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")


@dp.message(F.text.lower().startswith("هک "))
async def process_hack(message: Message):
    user_id = message.from_user.id
    try:
        target_id = int(message.text.split()[1])
    except (ValueError, IndexError):
        return await message.reply("❌ فرمت: `هک 123456789`")
    if user_id == target_id:
        return await message.reply("❌ خودت رو نه!")
    async with aiosqlite.connect(DB_NAME) as db:
        hack_item = await (await db.execute("SELECT id FROM inventory WHERE user_id = ? AND item_name = '💻 ابزار هک' LIMIT 1", (user_id,))).fetchone()
        if not hack_item:
            return await message.reply("❌ ابزار هک نداری!")
        hack_data = await (await db.execute("SELECT last_hack_time FROM hack_history WHERE user_id = ?", (user_id,))).fetchone()
        now = int(time.time())
        if hack_data and now - hack_data[0] < 86400:
            return await message.reply("⏳ روزی یک بار!")

        prot = await (await db.execute("SELECT ethical_hacker_expiry, ethical_hacker_uses FROM protections WHERE user_id = ?", (target_id,))).fetchone()
        if prot and prot[0] > now and prot[1] > 0 and random.randint(1, 100) > 10:
            new_uses = prot[1] - 1
            await db.execute("UPDATE protections SET ethical_hacker_uses = ? WHERE user_id = ?", (new_uses, target_id))
            if new_uses <= 0:
                await db.execute("UPDATE protections SET ethical_hacker_expiry = 0 WHERE user_id = ?", (target_id,))
            await db.execute("DELETE FROM inventory WHERE id = ?", (hack_item[0],))
            await db.execute("INSERT OR REPLACE INTO hack_history (user_id, last_hack_time) VALUES (?, ?)", (user_id, now))
            await db.commit()
            left = "(سوخت)" if new_uses <= 0 else f"({new_uses} بار مونده)"
            return await message.reply(f"🛡️ هکر اخلاقی جلوش رو گرفت! {left} ❌")

        victim = await get_user(target_id)
        if not victim:
            return await message.reply("❌ عضو نیست!")
        transactions = await (await db.execute(
            "SELECT sender_id, receiver_id, amount, trans_type, trans_time FROM transactions WHERE sender_id = ? OR receiver_id = ? ORDER BY trans_time DESC LIMIT 5",
            (target_id, target_id))).fetchall()
        report = f"💻 **گزارش هک `{target_id}`**\n\n💰 موجودی: ${victim[2]:,}\n\n📜 ۵ تراکنش آخر:\n"
        if not transactions:
            report += "• خالی.\n"
        else:
            for t in transactions:
                report += f"{'📤' if t[0] == target_id else '📥'} {time.strftime('%m-%d %H:%M', time.localtime(t[4]))} | ${t[2]:,} ({t[3]})\n"
        await db.execute("DELETE FROM inventory WHERE id = ?", (hack_item[0],))
        await db.execute("INSERT OR REPLACE INTO hack_history (user_id, last_hack_time) VALUES (?, ?)", (user_id, now))
        await db.commit()
    await message.reply(report, parse_mode="Markdown")


# ==========================================
# 7. انبار و پت‌ها
# ==========================================
@dp.callback_query(F.data == "inventory")
async def inventory_menu(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        items = await (await db.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (callback.from_user.id,))).fetchall()
    text = "📦 **انبار شما خالیه!**" if not items else "📦 **آیتم‌های انبار:**\n\n" + "\n".join(f"• {i[0]} (تعداد: {i[1]})" for i in items)
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")


@dp.callback_query(F.data == "my_pets")
async def my_pets(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        pets = await (await db.execute("SELECT id, pet_name, level, power FROM user_pets WHERE user_id = ?", (callback.from_user.id,))).fetchall()
    if not pets:
        return await callback.message.edit_text("🐾 پت نداری!", reply_markup=back_kb())
    text = "🐾 **پت‌های شما:**\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in pets:
        text += f"• {p[1]} — لول {p[2]} | قدرت {p[3]:,}\n"
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"🥩 غذا {p[1]}", callback_data=f"feed_pet_{p[0]}"),
            InlineKeyboardButton(text=f"⬆️ ارتقا {p[1]}", callback_data=f"upgrade_pet_{p[0]}"),
        ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("feed_pet_"))
async def feed_pet(callback: CallbackQuery):
    pet_id = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(callback.from_user.id))[2] < 500:
            return await callback.answer("❌ نیاز به ۵۰۰ دلار!", show_alert=True)
        await db.execute("UPDATE users SET balance = balance - 500 WHERE user_id = ?", (callback.from_user.id,))
        await db.execute("UPDATE user_pets SET hunger = 100 WHERE id = ? AND user_id = ?", (pet_id, callback.from_user.id))
        await db.commit()
    await callback.answer("✅ غذا خورد!", show_alert=True)
    await my_pets(callback)


@dp.callback_query(F.data.startswith("upgrade_pet_"))
async def upgrade_pet(callback: CallbackQuery):
    pet_id = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_NAME) as db:
        pet = await (await db.execute("SELECT level, power FROM user_pets WHERE id = ? AND user_id = ?", (pet_id, callback.from_user.id))).fetchone()
        if not pet:
            return await callback.answer("❌ پیدا نشد!", show_alert=True)
        cost = pet[0] * 5000
        if (await get_user(callback.from_user.id))[2] < cost:
            return await callback.answer(f"❌ نیاز به ${cost:,}!", show_alert=True)
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, callback.from_user.id))
        await db.execute("UPDATE user_pets SET level = level + 1, power = ? WHERE id = ?", (int(pet[1] * 2.5), pet_id))
        await db.commit()
    await callback.answer(f"✅ به لول {pet[0] + 1} رفت!", show_alert=True)
    await my_pets(callback)


# ==========================================
# 8. ماشین‌ها
# ==========================================
@dp.callback_query(F.data == "car_menu")
async def car_menu(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        my_cars = await (await db.execute("SELECT id, car_name, level, power FROM user_cars WHERE user_id = ?", (callback.from_user.id,))).fetchall()
    text = "🏁 **ماشین‌ها**\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if my_cars:
        for c in my_cars:
            text += f"• `#{c[0]}` {c[1]} — لول {c[2]} | قدرت {c[3]:,}\n"
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"⬆️ ارتقا #{c[0]}", callback_data=f"upgrade_car_{c[0]}_{c[2] * 100000}")])
        text += "\n"
    text += "برای مسابقه بنویس: `مسابقه 5000`\n\n**خرید ماشین:**"
    for name, price, power in CARS_LIST:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"خرید {name} — {price:,}", callback_data=f"buy_car_{name}_{price}_{power}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("buy_car_"))
async def buy_car(callback: CallbackQuery):
    parts = callback.data.split("_")
    name, price, power = parts[2], int(parts[3]), int(parts[4])
    if (await get_user(callback.from_user.id))[2] < price:
        return await callback.answer("❌ پول نداری!", show_alert=True)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, callback.from_user.id))
        await db.execute("INSERT INTO user_cars (user_id, car_name, power) VALUES (?, ?, ?)", (callback.from_user.id, name, power))
        await db.commit()
    await callback.answer(f"✅ {name} خریداری شد!", show_alert=True)
    await car_menu(callback)


@dp.callback_query(F.data.startswith("upgrade_car_"))
async def upgrade_car(callback: CallbackQuery):
    parts = callback.data.split("_")
    car_id, cost = int(parts[2]), int(parts[3])
    if (await get_user(callback.from_user.id))[2] < cost:
        return await callback.answer("❌ پول نداری!", show_alert=True)
    async with aiosqlite.connect(DB_NAME) as db:
        car = await (await db.execute("SELECT level, power FROM user_cars WHERE id = ? AND user_id = ?", (car_id, callback.from_user.id))).fetchone()
        if not car:
            return await callback.answer("❌ پیدا نشد!", show_alert=True)
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, callback.from_user.id))
        await db.execute("UPDATE user_cars SET level = level + 1, power = ? WHERE id = ?", (int(car[1] * 2.5), car_id))
        await db.commit()
    await callback.answer("✅ ارتقا یافت!", show_alert=True)
    await car_menu(callback)




# ==========================================
# 9. ماموریت‌ها
# ==========================================
@dp.callback_query(F.data == "missions")
async def show_missions(callback: CallbackQuery):
    user_id, today = callback.from_user.id, datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        if not await (await db.execute("SELECT id FROM user_missions WHERE user_id = ? AND reset_date = ?", (user_id, today))).fetchone():
            await db.execute("DELETE FROM user_missions WHERE user_id = ?", (user_id,))
            for m in random.sample(MISSION_POOL, 5):
                await db.execute(
                    "INSERT INTO user_missions (user_id, mission_code, title, target, reward_money, reward_xp, reset_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, m["code"], m["title"], m["target"], m["reward_money"], m["reward_xp"], today))
            await db.commit()
        missions = await (await db.execute("SELECT title, target, progress, reward_money, reward_xp FROM user_missions WHERE user_id = ?", (user_id,))).fetchall()
    text = f"🎯 **ماموریت‌های امروز ({sum(1 for m in missions if m[2] >= m[1])}/5)**\n\n"
    for m in missions:
        text += f"{'✅' if m[2] >= m[1] else '⬜️'} {m[0]}\n🎁 ${m[3]:,} + {m[4]} XP • {min(m[2], m[1])}/{m[1]}\n\n"
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")


# ==========================================
# 10. خانواده (ازدواج، بچه، شهریه، خیانت)
# ==========================================
@dp.message(F.text.lower() == "ازدواج")
async def marry(message: Message):
    if message.chat.type == "private" or not message.reply_to_message:
        return await message.reply("❌ باید توی گروه روی پیام طرف ریپلای کنی و بنویسی `ازدواج`!")
    target_id, user_id = message.reply_to_message.from_user.id, message.from_user.id
    if user_id == target_id:
        return await message.reply("❌ با خودت نمیتونی ازدواج کنی!")
    await ensure_user(user_id, message.from_user.first_name)
    await ensure_user(target_id, message.reply_to_message.from_user.first_name)
    async with aiosqlite.connect(DB_NAME) as db:
        if await (await db.execute("SELECT spouse_id FROM marriages WHERE user_id = ?", (user_id,))).fetchone():
            return await message.reply("❌ تو از قبل متاهلی!")
        if await (await db.execute("SELECT spouse_id FROM marriages WHERE user_id = ?", (target_id,))).fetchone():
            return await message.reply("❌ این شخص از قبل متاهله!")
        await db.execute("INSERT INTO marriages (user_id, spouse_id) VALUES (?, ?)", (user_id, target_id))
        await db.execute("INSERT INTO marriages (user_id, spouse_id) VALUES (?, ?)", (target_id, user_id))
        await db.commit()
    await message.reply(f"💍 **تبریک!** <a href='tg://user?id={user_id}'>این کاربر</a> و <a href='tg://user?id={target_id}'>این کاربر</a> با هم ازدواج کردن! 🎉", parse_mode="HTML")


@dp.message(F.text.lower() == "سکس")
async def have_sex(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    user_id, now = message.from_user.id, int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        marriage = await (await db.execute("SELECT spouse_id, last_sex_time FROM marriages WHERE user_id = ?", (user_id,))).fetchone()
        if not marriage:
            return await message.reply("❌ تو هنوز ازدواج نکردی!")
        spouse_id, last_time = marriage
        if now - last_time < 3600:
            return await message.reply(f"⏳ باید {(3600 - (now - last_time)) // 60} دقیقه دیگه صبر کنی!")
        if (await get_user(user_id))[2] < 250 or (await get_user(spouse_id))[2] < 250:
            return await message.reply("❌ هر نفر به ۲۵۰ دلار نیاز داره!")
        count = (await (await db.execute("SELECT COUNT(*) FROM children WHERE parent1_id = ? OR parent2_id = ?", (user_id, user_id))).fetchone())[0]
        if count >= 5:
            return await message.reply("👨‍👩‍👧‍👦 **خانه‌تون پر از بچه‌ست!** (پولتون کم نشد)")
        await db.execute("UPDATE users SET balance = balance - 250 WHERE user_id IN (?, ?)", (user_id, spouse_id))
        await db.execute("UPDATE marriages SET last_sex_time = ? WHERE user_id IN (?, ?)", (now, user_id, spouse_id))
        if random.random() <= 0.3:
            baby_name = random.choice(BABY_NAMES)
            await db.execute("INSERT INTO children (parent1_id, parent2_id, name, birth_time) VALUES (?, ?, ?, ?)", (user_id, spouse_id, baby_name, now))
            await db.commit()
            await message.reply(f"🤰 **تبریک!** یه نوزاد به اسم **{baby_name}** به دنیا اومد! 🍼")
        else:
            await db.commit()
            await message.reply("😐 **این دفعه بچه‌دار نشدید!**")


@dp.message(F.text.lower() == "بچه ها")
async def my_children(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        children = await (await db.execute("SELECT id, name, stage FROM children WHERE parent1_id = ? OR parent2_id = ?", (user_id, user_id))).fetchall()
    if not children:
        return await message.reply("👶 تو هنوز هیچ بچه‌ای نداری!")
    stages = {0: "نوزاد 👶", 1: "مدرسه‌ای 🎒", 2: "دانشجو 🎓", 3: "بزرگسال 👱 (درآمد: ۲۰۰$/روز)"}
    text = "👨‍👩‍👧‍👦 **فرزندان تو:**\n\n"
    for c in children:
        text += f"• `#{c[0]}` {c[1]} — {stages.get(c[2], 'نامشخص')}\n"
    text += "\n📝 **دستورات:**\n• `شهریه <آیدی>`\n• `فروش فرزند <آیدی>`\n• `خیانت`"
    await message.reply(text, parse_mode="Markdown")


@dp.message(F.text.lower().startswith("شهریه "))
async def pay_tuition(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    user_id = message.from_user.id
    try:
        child_id = int(message.text.split()[1])
    except (ValueError, IndexError):
        return await message.reply("❌ فرمت: `شهریه 123`")
    async with aiosqlite.connect(DB_NAME) as db:
        child = await (await db.execute("SELECT name, stage FROM children WHERE id = ? AND (parent1_id = ? OR parent2_id = ?)", (child_id, user_id, user_id))).fetchone()
        if not child:
            return await message.reply("❌ بچه پیدا نشد!")
        if child[1] >= 3:
            return await message.reply("🎓 این بچه بزرگسال شده و درآمد داره!")
        cost = {0: 300, 1: 600, 2: 1000}[child[1]]
        if (await get_user(user_id))[2] < cost:
            return await message.reply(f"❌ برای این مرحله به ${cost:,} نیاز داری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, user_id))
        await db.execute("UPDATE children SET stage = stage + 1 WHERE id = ?", (child_id,))
        await db.commit()
    await message.reply(f"🏫 **شهریه پرداخت شد!** {child[0]} به مرحله بعد رفت. (هزینه: ${cost:,})")


@dp.message(F.text.lower().startswith("فروش فرزند "))
async def sell_child(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    user_id = message.from_user.id
    try:
        child_id = int(message.text.split()[2])
    except (ValueError, IndexError):
        return await message.reply("❌ فرمت: `فروش فرزند 123`")
    async with aiosqlite.connect(DB_NAME) as db:
        child = await (await db.execute("SELECT name, stage FROM children WHERE id = ? AND (parent1_id = ? OR parent2_id = ?)", (child_id, user_id, user_id))).fetchone()
        if not child:
            return await message.reply("❌ بچه پیدا نشد!")
        price = 900 if child[1] >= 2 else 500
        await db.execute("DELETE FROM children WHERE id = ?", (child_id,))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, user_id))
        await db.commit()
    await message.reply(f"💼 **معامله با کارتل انجام شد!**\n**{child[0]}** رو به قیمت **${price:,}** فروختی.")


@dp.message(F.text.lower() == "خیانت")
async def cheat(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        marriage = await (await db.execute("SELECT spouse_id FROM marriages WHERE user_id = ?", (user_id,))).fetchone()
        if not marriage:
            return await message.reply("❌ تو ازدواج نکردی!")
        if random.random() <= 0.5:
            fine = max(int((await get_user(user_id))[2] * 0.10), 100)
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (fine, user_id))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (fine, marriage[0]))
            await db.commit()
            await message.reply(f"🚨 **گیر افتادی!** جریمه **${fine:,}** به همسرت پرداخت شد.")
        else:
            await message.reply("🤫 **موفق شدی!** همسرت نفهمید.")


# ==========================================
# 11. لاتاری
# ==========================================
@dp.message(F.text.lower() == "لاتاری")
async def lottery_menu(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    async with aiosqlite.connect(DB_NAME) as db:
        total = (await (await db.execute("SELECT SUM(tickets) FROM lottery")).fetchone())[0] or 0
        row = await (await db.execute("SELECT tickets FROM lottery WHERE user_id = ?", (message.from_user.id,))).fetchone()
    my_tickets = row[0] if row else 0
    await message.reply(
        f"🎟️ **لاتاری بزرگ**\n\n💰 جایزه: **$10,000,000**\n📅 هر ۳ روز!\n\n🎫 کل بلیت‌ها: {total}\n🎫 بلیت‌های تو: {my_tickets}\n\nقیمت: **$1,000**\nبرای خرید بنویس: `خرید بلیت`",
        parse_mode="Markdown")


@dp.message(F.text.lower() == "خرید بلیت")
async def buy_lottery(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    await ensure_user(message.from_user.id, message.from_user.first_name)
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(message.from_user.id))[2] < 1000:
            return await message.reply("❌ پول کافی نداری!")
        await db.execute("UPDATE users SET balance = balance - 1000 WHERE user_id = ?", (message.from_user.id,))
        await db.execute("INSERT INTO lottery (user_id, tickets) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET tickets = tickets + 1", (message.from_user.id,))
        await db.commit()
    await message.reply("✅ یک بلیت خریداری شد! شانس با تو! 🍀")


# ==========================================
# 12. کد هدیه
# ==========================================
@dp.callback_query(F.data == "gift_code")
async def gift_code_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎁 **کد هدیه**\n\nبرای دریافت جایزه، کافیه توی چت یا گروه تایپ کنی:\n👉 `کد هدیه mk4`",
        reply_markup=back_kb(), parse_mode="Markdown")


@dp.message(F.text.lower().startswith("کد هدیه "))
async def process_code(message: Message):
    code = message.text.strip().lower().replace("کد هدیه ", "")
    await ensure_user(message.from_user.id, message.from_user.first_name)
    async with aiosqlite.connect(DB_NAME) as db:
        gift = await (await db.execute("SELECT * FROM gift_codes WHERE code = ?", (code,))).fetchone()
        if not gift:
            return await message.reply("❌ کد نامعتبر است!")
        if gift[3] >= gift[2]:
            return await message.reply("⛔️ ظرفیت پر شده!")
        if await (await db.execute("SELECT * FROM code_history WHERE user_id = ? AND code = ?", (message.from_user.id, code))).fetchone():
            return await message.reply("⚠️ قبلاً استفاده کردی!")
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (gift[1], message.from_user.id))
        await db.execute("UPDATE gift_codes SET current_uses = current_uses + 1 WHERE code = ?", (code,))
        await db.execute("INSERT INTO code_history (user_id, code) VALUES (?, ?)", (message.from_user.id, code))
        await db.commit()
    await message.reply(f"🎉 تبریک! ${gift[1]:,} گرفتی. ✅")


# ==========================================
# 13. پنل ادمین
# ==========================================
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔️ شما ادمین نیستید!")
    await message.answer("👑 **پنل مدیریت**", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 ساخت کد هدیه", callback_data="admin_make_code")],
        [InlineKeyboardButton(text="💰 انتقال سکه", callback_data="admin_transfer")],
        [InlineKeyboardButton(text="⬆️ افزودن XP", callback_data="admin_add_xp")],
        [InlineKeyboardButton(text="🔙 بستن", callback_data="main_menu")],
    ]))


@dp.callback_query(F.data == "admin_make_code")
async def admin_make_code(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔️ ادمین نیستید!", show_alert=True)
    await callback.message.edit_text("🎁 فرمت: `اسم_کد مبلغ ظرفیت` (مثلاً `mk4 20000 1000`)")
    await state.set_state(AdminStates.waiting_code)


@dp.message(AdminStates.waiting_code)
async def process_admin_code(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("لغو شد.", reply_markup=main_menu_keyboard())
    try:
        parts = message.text.split()
        code, amount, max_uses = parts[0].lower(), int(parts[1]), int(parts[2])
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT INTO gift_codes (code, amount, max_uses) VALUES (?, ?, ?)", (code, amount, max_uses))
            await db.commit()
        await state.clear()
        await message.answer(f"✅ کد `{code}` ساخته شد!", reply_markup=main_menu_keyboard())
    except Exception:
        await message.answer("❌ فرمت اشتباهه!")


@dp.callback_query(F.data == "admin_transfer")
async def admin_transfer(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔️ ادمین نیستید!", show_alert=True)
    await callback.message.edit_text("💰 فرمت: `آیدی مبلغ` (مثلاً `123456789 50000`)")
    await state.set_state(AdminStates.waiting_transfer)


@dp.message(AdminStates.waiting_transfer)
async def process_admin_transfer(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("لغو شد.", reply_markup=main_menu_keyboard())
    try:
        target, amount = int(message.text.split()[0]), int(message.text.split()[1])
        async with aiosqlite.connect(DB_NAME) as db:
            if not await get_user(target):
                return await message.answer("❌ کاربر پیدا نشد!")
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target))
            await db.commit()
        await state.clear()
        await message.answer(f"✅ ${amount:,} به کاربر {target} داده شد.", reply_markup=main_menu_keyboard())
        try:
            await bot.send_message(target, f"🎁 ادمین به شما ${amount:,} هدیه داد!")
        except Exception:
            pass
    except Exception:
        await message.answer("❌ فرمت اشتباهه!")


@dp.callback_query(F.data == "admin_add_xp")
async def admin_add_xp(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔️ ادمین نیستید!", show_alert=True)
    await callback.message.edit_text("⬆️ فرمت: `آیدی مقدار_XP` (مثلاً `123456789 5000`)")
    await state.set_state(AdminStates.waiting_xp)


@dp.message(AdminStates.waiting_xp)
async def process_admin_xp(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("لغو شد.", reply_markup=main_menu_keyboard())
    try:
        target, amount = int(message.text.split()[0]), int(message.text.split()[1])
        async with aiosqlite.connect(DB_NAME) as db:
            await add_xp(target, amount, db)
            await db.commit()
        await state.clear()
        await message.answer(f"✅ {amount:,} XP به کاربر {target} داده شد.", reply_markup=main_menu_keyboard())
    except Exception:
        await message.answer("❌ فرمت اشتباهه!")


# ==========================================
# 14. بازی‌های تکی (گردونه، اسلات، تاس، رولت)
# ==========================================
@dp.message(F.text.lower() == "گردونه")
async def spin_wheel_group(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    async with aiosqlite.connect(DB_NAME) as db:
        data = await (await db.execute("SELECT last_wheel_spin FROM daily_cooldowns WHERE user_id = ?", (message.from_user.id,))).fetchone()
        if data and time.time() - data[0] < 86400:
            return await message.reply("⏳ امروز چرخوندی! فردا بیا.")
        won = random.choices([1000000, 2000, 500, 100, 0], weights=[10, 20, 30, 20, 20], k=1)[0]
        await db.execute("INSERT INTO daily_cooldowns (user_id, last_wheel_spin) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET last_wheel_spin = excluded.last_wheel_spin", (message.from_user.id, int(time.time())))
        if won > 0:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (won, message.from_user.id))
        await track_mission(message.from_user.id, "wheel", 1, db)
        await db.commit()
    result = f"🎉 تبریک! ${won:,} برنده شدی!" if won > 0 else "😂 پوچ"
    await message.reply(f"🎡 **گردونه چرخید...**\n\nنتیجه: {result}")


@dp.message(F.text.lower().startswith("اسلات "))
async def play_slots(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    bet = parse_amount(message.text, 1)
    if bet is None:
        return await message.reply("❌ فرمت: `اسلات 5000`")
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(message.from_user.id))[2] < bet:
            return await message.reply("❌ پول نداری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, message.from_user.id))
        s = random.choices(SLOT_SYMBOLS, k=3)
        if s[0] == s[1] == s[2]:
            win, label = bet * 5, "🎰 جکپات!"
        elif len(set(s)) == 2:
            win, label = bet * 2, "✅ دوتایی!"
        else:
            win, label = 0, "😢 باختی!"
        if win > 0:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, message.from_user.id))
        await track_mission(message.from_user.id, "slots", 1, db)
        await db.commit()
        new_bal = (await get_user(message.from_user.id))[2]
    sign = "+" if win > 0 else ""
    await message.reply(f"🎰 **اسلات {bet:,}**\n\n[ {s[0]} | {s[1]} | {s[2]} ]\n\n{label}\n{sign}{win - bet:,} $\n💵 موجودی: ${new_bal:,}")


@dp.message(F.text.lower().startswith("تاس "))
async def play_dice(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    bet = parse_amount(message.text, 2)
    if bet is None:
        return await message.reply("❌ فرمت: `تاس زوج 500`")
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(message.from_user.id))[2] < bet:
            return await message.reply("❌ پول نداری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, message.from_user.id))
        roll = random.randint(1, 6)
        win = roll % 2 == 0
        if win:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bet * 2, message.from_user.id))
        await track_mission(message.from_user.id, "dice", 1, db)
        await db.commit()
        new_bal = (await get_user(message.from_user.id))[2]
    await message.reply(
        f"🎲 **تاس: {roll} ({'زوج' if win else 'فرد'}) — {'بردی!' if win else 'باختی.'}**\n"
        f"{'💰 +' if win else '📉 -'}${bet:,} $\n💵 موجودی: ${new_bal:,}")


@dp.message(F.text.lower().startswith("رولت "))
async def play_roulette(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    bet = parse_amount(message.text, 1)
    if bet is None:
        return await message.reply("❌ فرمت: `رولت 500`")
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(message.from_user.id))[2] < bet:
            return await message.reply("❌ پول نداری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, message.from_user.id))
        if random.randint(1, 4) == 1:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bet * 4, message.from_user.id))
            msg = f"🔫 **رولت روسی {bet:,}**\n\n⚪ ⚪ ⚪ O\n😮‍💨 کلیک... زنده موندی! +${bet * 3:,} سود."
        else:
            msg = f"🔫 **رولت روسی {bet:,}**\n\n⚪ ⚪ ⚪ 💥\n💀 بنگ! گلوله شلیک شد و ${bet:,} رو باختی."
        await track_mission(message.from_user.id, "roulette", 1, db)
        await db.commit()
        new_bal = (await get_user(message.from_user.id))[2]
    await message.reply(f"{msg}\n💵 موجودی: ${new_bal:,}")


# ==========================================
# 15. دزدی، انتقال، بیمه، اجیر، موشک
# ==========================================
@dp.message(F.text.lower().startswith("دزدی "))
async def process_steal(message: Message):
    try:
        target_id = int(message.text.split()[1])
    except (ValueError, IndexError):
        return await message.reply("❌ فرمت: `دزدی 123456789`")
    if target_id == message.from_user.id:
        return await message.reply("❌ از خودت نه!")
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(message.from_user.id))[2] < 100:
            return await message.reply("❌ حداقل ۱۰۰ دلار نیاز داری!")
        victim = await get_user(target_id)
        if not victim:
            return await message.reply("❌ عضو نیست!")
        if random.randint(1, 100) <= 50:
            steal = int(victim[2] * 0.10)
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (steal, target_id))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (steal, message.from_user.id))
            await track_mission(message.from_user.id, "steal", 1, db)
            await db.commit()
            await message.reply(f"🥷 **دزدی موفق!** ${steal:,} دزدیدی. ✅")
        else:
            await db.execute("UPDATE users SET balance = balance - 100 WHERE user_id = ?", (message.from_user.id,))
            await db.commit()
            await message.reply("🚔 **پلیس دستگیرت کرد!** ۱۰۰ دلار جریمه شدی. ❌")


@dp.message(F.text.lower().startswith("انتقال "))
async def transfer_money(message: Message):
    if message.chat.type == "private" or not message.reply_to_message:
        return await message.reply("❌ ریپلای کن!")
    target_id, user_id = message.reply_to_message.from_user.id, message.from_user.id
    if user_id == target_id:
        return await message.reply("❌ به خودت نده!")
    amount = parse_amount(message.text, 1)
    if amount is None:
        return await message.reply("❌ فرمت: `انتقال 1000`")
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[2] < amount:
            return await message.reply("❌ پول نداری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        await db.execute("INSERT INTO transactions (sender_id, receiver_id, amount, trans_type, trans_time) VALUES (?, ?, ?, 'انتقال', ?)", (user_id, target_id, amount, int(time.time())))
        await track_mission(user_id, "transfer", amount, db)
        await db.commit()
    await message.reply(f"💸 **انتقال انجام شد!**\n<a href='tg://user?id={user_id}'>فرستنده</a> مبلغ **${amount:,}** به <a href='tg://user?id={target_id}'>گیرنده</a> داد. ✅", parse_mode="HTML")


@dp.message(F.text.lower() == "بیمه")
async def buy_insurance(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط گروه!")
    user_id, now = message.from_user.id, int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[2] < 500000:
            return await message.reply("❌ نیاز به ۵۰۰,۰۰۰ دلار!")
        prot = await (await db.execute("SELECT insurance_expiry FROM protections WHERE user_id = ?", (user_id,))).fetchone()
        if prot and prot[0] > now:
            return await message.reply("⚠️ از قبل بیمه داری!")
        await db.execute("UPDATE users SET balance = balance - 500000 WHERE user_id = ?", (user_id,))
        await db.execute("INSERT INTO protections (user_id, insurance_expiry) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET insurance_expiry = excluded.insurance_expiry", (user_id, now + WEEK_SECONDS))
        await db.commit()
    await message.reply("🛡️ **بیمه فعال شد!** (۷ روز)")


async def hire_attack(message: Message, *, cost, cd_col, expiry_col, uses_col, block_threshold,
                      success_chance, steal_pct, trans_label, block_text, success_icon, success_name):
    """منطق مشترک «اجیر هکر» و «اجیر قاتل». ستون‌ها از ثابت‌های داخلی میان، نه از ورودی کاربر."""
    if message.chat.type == "private" or not message.reply_to_message:
        return await message.reply("❌ ریپلای کن!")
    target_id, user_id = message.reply_to_message.from_user.id, message.from_user.id
    if user_id == target_id:
        return await message.reply("❌ خودت رو نه!")
    now = int(time.time())
    cd_upsert = f"INSERT INTO attack_cooldown (user_id, {cd_col}) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET {cd_col} = excluded.{cd_col}"
    async with aiosqlite.connect(DB_NAME) as db:
        cd = await (await db.execute(f"SELECT {cd_col} FROM attack_cooldown WHERE user_id = ?", (user_id,))).fetchone()
        if cd and now - cd[0] < 3600:
            return await message.reply("⏳ یک ساعت صبر کن!")
        if (await get_user(user_id))[2] < cost:
            return await message.reply(f"❌ نیاز به ${cost:,}!")

        prot = await (await db.execute(f"SELECT {expiry_col}, {uses_col} FROM protections WHERE user_id = ?", (target_id,))).fetchone()
        if prot and prot[0] > now and prot[1] > 0 and random.randint(1, 100) > block_threshold:
            new_uses = prot[1] - 1
            await db.execute(f"UPDATE protections SET {uses_col} = ? WHERE user_id = ?", (new_uses, target_id))
            if new_uses <= 0:
                await db.execute(f"UPDATE protections SET {expiry_col} = 0 WHERE user_id = ?", (target_id,))
            await db.commit()
            left = "(سوخت)" if new_uses <= 0 else f"({new_uses} بار)"
            return await message.reply(f"🛡️ {block_text} {left} ❌")

        victim = await get_user(target_id)
        if not victim:
            return await message.reply("❌ عضو نیست!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, user_id))
        if random.randint(1, 100) <= success_chance:
            steal = int(victim[2] * steal_pct)
            if steal <= 0:
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (cost, user_id))
                await db.commit()
                return await message.reply("🤷 پولی نداشت! هزینه برگشت.")
            ins = await (await db.execute("SELECT insurance_expiry FROM protections WHERE user_id = ?", (target_id,))).fetchone()
            v_loss = steal // 2 if (ins and ins[0] > now) else steal
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (v_loss, target_id))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (steal, user_id))
            await db.execute("INSERT INTO transactions (sender_id, receiver_id, amount, trans_type, trans_time) VALUES (?, ?, ?, ?, ?)", (target_id, user_id, steal, trans_label, now))
            await db.execute(cd_upsert, (user_id, now))
            await db.commit()
            await message.reply(f"{success_icon} **{success_name} موفق بود!** ${steal:,} دزدید. (قربانی ${v_loss:,} ضرر کرد) ✅", parse_mode="Markdown")
        else:
            await db.execute(cd_upsert, (user_id, now))
            await db.commit()
            await message.reply(f"🚨 **شکست خورد!** ${cost:,} پرید. ❌")


@dp.message(F.text.lower().startswith("اجیر هکر"))
async def hire_hacker(message: Message):
    await hire_attack(
        message, cost=200000, cd_col="last_hacker_time",
        expiry_col="ethical_hacker_expiry", uses_col="ethical_hacker_uses", block_threshold=20,
        success_chance=70, steal_pct=0.30, trans_label="هکر اجیری",
        block_text="هکر اخلاقی جلوش رو گرفت!", success_icon="💻", success_name="هکر")


@dp.message(F.text.lower().startswith("اجیر قاتل"))
async def hire_assassin(message: Message):
    await hire_attack(
        message, cost=100000, cd_col="last_assassin_time",
        expiry_col="bodyguard_expiry", uses_col="bodyguard_uses", block_threshold=10,
        success_chance=60, steal_pct=0.15, trans_label="قاتل اجیری",
        block_text="بادیگارد جلوش رو گرفت!", success_icon="🔪", success_name="قاتل")


@dp.message(F.text.lower().startswith("شلیک "))
async def fire_missile(message: Message):
    if message.chat.type == "private" or not message.reply_to_message:
        return await message.reply("❌ ریپلای کن!")
    target_id, user_id = message.reply_to_message.from_user.id, message.from_user.id
    if user_id == target_id:
        return await message.reply("❌ خودت رو نه!")
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[4] < 30:
            return await message.reply("🔐 فقط لول ۳۰+!")
        missiles = await (await db.execute("SELECT id, item_name FROM inventory WHERE user_id = ? AND item_type LIKE 'missile_%'", (user_id,))).fetchall()
        if not missiles:
            return await message.reply("❌ موشک نداری!")
        m_id, m_name = missiles[0]
        def_p = await (await db.execute("SELECT defense_expiry FROM protections WHERE user_id = ?", (target_id,))).fetchone()
        if def_p and def_p[0] > int(time.time()) and random.randint(1, 100) <= 20:
            await db.execute("DELETE FROM inventory WHERE id = ?", (m_id,))
            await db.commit()
            return await message.reply("🛡️ **پدافند موشک رو منهدم کرد!** 🚀💥")
        await db.execute("DELETE FROM inventory WHERE id = ?", (m_id,))
        dmg = random.randint(5, 30) / 100
        damages = []
        victim = await get_user(target_id)
        lost = int(victim[2] * dmg) if victim else 0
        if lost > 0:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (lost, target_id))
            damages.append(f"💰 پول: ${lost:,}")
        props = await (await db.execute("SELECT id FROM user_properties WHERE user_id = ?", (target_id,))).fetchall()
        destroyed = int(len(props) * dmg)
        if destroyed > 0:
            for p in props[:destroyed]:
                await db.execute("DELETE FROM user_properties WHERE id = ?", (p[0],))
            damages.append(f"🏠 ملک: {destroyed} عدد")
        await db.commit()
    res = f"💥 **{m_name} به {message.reply_to_message.from_user.first_name} شلیک شد!**\n\n📉 آسیب ({int(dmg * 100)}٪):\n"
    res += "🤷 هیچی!" if not damages else "\n".join(damages)
    await message.reply(res, parse_mode="Markdown")


# ==========================================
# 16. دعوا
# ==========================================
@dp.callback_query(F.data == "duel_menu")
async def duel_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚔️ **دعوا**\n\nفرمت: `دعوا [آیدی] [مبلغ]`\nمثال: `دعوا 123456789 1000`",
        reply_markup=back_kb(), parse_mode="Markdown")


@dp.message(F.text.lower().startswith("دعوا "))
async def process_duel(message: Message):
    target_id, bet = parse_amount(message.text, 1), parse_amount(message.text, 2)
    if target_id is None or bet is None:
        return await message.reply("❌ فرمت اشتباه! `دعوا 123456789 1000`")
    user_id = message.from_user.id
    if user_id == target_id:
        return await message.reply("❌ خطا!")
    async with aiosqlite.connect(DB_NAME) as db:
        p1, p2 = await get_user(user_id), await get_user(target_id)
        if not p1 or not p2 or p1[2] < bet or p2[2] < bet:
            return await message.reply("❌ یکی پول کافی نداره!")

        async def duel_power(uid):
            items = await (await db.execute("SELECT item_name FROM inventory WHERE user_id = ? AND item_type = 'duel_item'", (uid,))).fetchall()
            return sum(DUEL_POWER.get(i[0], 0) for i in items)

        pow1, pow2 = await duel_power(user_id), await duel_power(target_id)
        winner = user_id if pow1 > pow2 else (target_id if pow2 > pow1 else random.choice([user_id, target_id]))
        if winner == user_id:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bet, user_id))
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, target_id))
            await add_xp(user_id, 100, db)
            await db.commit()
            await message.reply(f"⚔️ **نتیجه:**\nقدرت تو: {pow1} | حریف: {pow2}\n\n🏆 **تو بردی!** ${bet:,} گرفتی.")
        else:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bet, target_id))
            await db.commit()
            await message.reply(f"⚔️ **نتیجه:**\nقدرت تو: {pow1} | حریف: {pow2}\n\n💀 **تو باختی!** ${bet:,} دادی.")


# ==========================================
# 17. بازی‌های گروهی: سنگ کاغذ قیچی
# ==========================================
@dp.message(F.text.lower().startswith("سنگ کاغذ قیچی "))
async def start_rps(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    bet = parse_amount(message.text, 3)
    if bet is None:
        return await message.reply("❌ فرمت: `سنگ کاغذ قیچی 5000`")
    user_id = message.from_user.id
    game_id = f"rps_{message.chat.id}_{message.message_id}"
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[2] < bet:
            return await message.reply("❌ پول نداری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
        await db.commit()
    rps_games[game_id] = {"creator_id": user_id, "bet": bet, "status": "waiting", "players": {}, "chat_id": message.chat.id}
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 جوین", callback_data=f"join_rps_{game_id}")]])
    await message.reply(f"✂️📄🪨 **سنگ کاغذ قیچی**\n\nمیزبان: {message.from_user.first_name}\n💰 شرط: ${bet:,}", reply_markup=kb)


@dp.callback_query(F.data.startswith("join_rps_"))
async def join_rps(callback: CallbackQuery):
    game_id = callback.data.replace("join_rps_", "")
    game = rps_games.get(game_id)
    user_id = callback.from_user.id
    if not game or game["status"] != "waiting" or user_id == game["creator_id"]:
        return await callback.answer("❌ خطا!", show_alert=True)
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[2] < game["bet"]:
            return await callback.answer("❌ پول نداری!", show_alert=True)
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (game["bet"], user_id))
        await db.commit()
    game["status"] = "playing"
    game["players"] = {game["creator_id"]: None, user_id: None}
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🪨", callback_data=f"rps_rock_{game_id}"),
        InlineKeyboardButton(text="📄", callback_data=f"rps_paper_{game_id}"),
        InlineKeyboardButton(text="✂️", callback_data=f"rps_scissors_{game_id}"),
    ]])
    await callback.message.edit_text("✂️ **بازی شروع شد!** انتخاب کنید (مخفی).", reply_markup=kb)


@dp.callback_query(F.data.startswith("rps_"))
async def rps_choice(callback: CallbackQuery):
    data = callback.data.split("_")
    choice, game_id = data[1], "_".join(data[2:])
    game = rps_games.get(game_id)
    user_id = callback.from_user.id
    if not game or user_id not in game["players"] or game["players"][user_id] is not None:
        return await callback.answer("❌ خطا!", show_alert=True)
    game["players"][user_id] = choice
    await callback.answer("✅ ثبت شد (مخفی).", show_alert=True)
    if all(v is not None for v in game["players"].values()):
        p1, p2 = list(game["players"].keys())
        c1, c2 = game["players"][p1], game["players"][p2]
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        async with aiosqlite.connect(DB_NAME) as db:
            if c1 == c2:
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id IN (?, ?)", (game["bet"], p1, p2))
                result = f"🤝 **مساوی!**\nهر دو {emojis[c1]}."
            else:
                beats = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
                winner_id = p1 if beats[c1] == c2 else p2
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (game["bet"] * 2, winner_id))
                result = f"🏆 **برنده: <a href='tg://user?id={winner_id}'>{winner_id}</a>** — ${game['bet'] * 2:,}\n({emojis[c1]} vs {emojis[c2]})"
            for pid in (p1, p2):
                await track_mission(pid, "rps", 1, db)
            await db.commit()
        try:
            await bot.send_message(game["chat_id"], f"✂️📄🪨 **نتیجه**\n\n{result}", parse_mode="HTML")
        except Exception:
            pass
        del rps_games[game_id]


# ==========================================
# 18. بازی‌های گروهی: دوز (XO)
# ==========================================
def build_ttt_board(board, game_id):
    kb = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            if board[idx] == "X":
                row.append(InlineKeyboardButton(text="❌", callback_data="noop"))
            elif board[idx] == "O":
                row.append(InlineKeyboardButton(text="⭕️", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton(text="⬜️", callback_data=f"ttt_move_{game_id}_{idx}"))
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)


@dp.message(F.text.lower().startswith("دوز "))
async def start_ttt(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    bet = parse_amount(message.text, 1)
    if bet is None:
        return await message.reply("❌ فرمت: `دوز 100`")
    user_id = message.from_user.id
    game_id = f"ttt_{message.chat.id}_{message.message_id}"
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[2] < bet:
            return await message.reply("❌ پول نداری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
        await db.commit()
    tictactoe_games[game_id] = {"creator_id": user_id, "creator_name": message.from_user.first_name, "bet": bet, "status": "waiting", "chat_id": message.chat.id}
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⭕️ جوین XO", callback_data=f"join_ttt_{game_id}")]])
    await message.reply(f"❌⭕️ **بازی XO**\n\nمیزبان: {message.from_user.first_name}\n💰 شرط: ${bet:,}", reply_markup=kb)


@dp.callback_query(F.data.startswith("join_ttt_"))
async def join_ttt(callback: CallbackQuery):
    game_id = callback.data.replace("join_ttt_", "")
    game = tictactoe_games.get(game_id)
    user_id = callback.from_user.id
    if not game or game["status"] != "waiting" or user_id == game["creator_id"]:
        return await callback.answer("❌ خطا!", show_alert=True)
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[2] < game["bet"]:
            return await callback.answer("❌ پول نداری!", show_alert=True)
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (game["bet"], user_id))
        await db.commit()
    game.update({
        "status": "playing", "players": {game["creator_id"]: "X", user_id: "O"},
        "board": [""] * 9, "turn": "X", "joiner_name": callback.from_user.first_name,
    })
    await callback.message.edit_text(
        f"❌⭕️ **XO**\n\n❌ {game['creator_name']} vs ⭕️ {callback.from_user.first_name}\n💰 شرط: ${game['bet']:,}",
        reply_markup=build_ttt_board(game["board"], game_id), parse_mode="HTML")


@dp.callback_query(F.data.startswith("ttt_move_"))
async def ttt_move(callback: CallbackQuery):
    parts = callback.data.split("_")
    idx, game_id = int(parts[-1]), "_".join(parts[2:-1])
    game = tictactoe_games.get(game_id)
    user_id = callback.from_user.id
    if not game or game["status"] != "playing" or game["players"].get(user_id) != game["turn"] or game["board"][idx] != "":
        return await callback.answer("❌ حرکت غیرمجاز!", show_alert=True)
    game["board"][idx] = game["turn"]
    win_patterns = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    board = game["board"]
    winner = next((board[a] for a, b, c in win_patterns if board[a] == board[b] == board[c] != ""), None)
    if winner or "" not in board:
        game["status"] = "finished"
        p_ids = list(game["players"].keys())
        async with aiosqlite.connect(DB_NAME) as db:
            if winner:
                w_id = p_ids[0] if game["players"][p_ids[0]] == winner else p_ids[1]
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (game["bet"] * 2, w_id))
                res = f"🏆 **برنده: <a href='tg://user?id={w_id}'>اینجا</a>** — ${game['bet'] * 2:,}"
            else:
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id IN (?, ?)", (game["bet"], p_ids[0], p_ids[1]))
                res = "🤝 **مساوی!**"
            await db.commit()
        await callback.message.edit_text(f"❌⭕️ **نتیجه XO**\n\n{res}", reply_markup=build_ttt_board(board, game_id), parse_mode="HTML")
        del tictactoe_games[game_id]
    else:
        game["turn"] = "O" if game["turn"] == "X" else "X"
        nxt = game["creator_name"] if game["turn"] == "X" else game["joiner_name"]
        await callback.message.edit_text(
            f"❌⭕️ **XO**\n\n❌ {game['creator_name']} vs ⭕️ {game['joiner_name']}\n🎯 نوبت: **{nxt}**",
            reply_markup=build_ttt_board(board, game_id), parse_mode="HTML")


# ==========================================
# 19. بازی‌های گروهی: انفجار
# ==========================================
@dp.message(F.text.lower().startswith("انفجار "))
async def start_bomb(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    bet = parse_amount(message.text, 1)
    if bet is None:
        return await message.reply("❌ فرمت: `انفجار 5000`")
    user_id = message.from_user.id
    game_id = f"bomb_{message.chat.id}_{message.message_id}"
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[2] < bet:
            return await message.reply("❌ پول نداری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
        await db.commit()
    grid = [False] * 7 + [True] * 5
    random.shuffle(grid)
    active_games[game_id] = {"type": "bomb", "user_id": user_id, "bet": bet, "grid": grid, "revealed": [False] * 12, "multiplier": 1, "status": "playing"}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓", callback_data=f"bomb_click_{game_id}_{i}") for i in range(j, j + 4)] for j in range(0, 12, 4)
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="💰 برداشت (Cashout)", callback_data=f"bomb_cashout_{game_id}")])
    await message.reply(
        f"💣 **انفجار**\n\nبازی‌کن: **{message.from_user.first_name}**\n💰 شرط: ${bet:,}\nخانه‌ها: 12 | بمب: 5\n📈 ضریب فعلی: **1x**",
        reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("bomb_click_"))
async def bomb_click(callback: CallbackQuery):
    parts = callback.data.split("_")
    game_id, idx = "_".join(parts[2:-1]), int(parts[-1])
    game = active_games.get(game_id)
    if not game or game["status"] != "playing" or callback.from_user.id != game["user_id"] or game["revealed"][idx]:
        return await callback.answer("❌ خطا!", show_alert=True)
    game["revealed"][idx] = True
    if game["grid"][idx]:
        game["status"] = "lost"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💥" if game["grid"][i] else "✅", callback_data="noop") for i in range(j, j + 4)] for j in range(0, 12, 4)
        ])
        async with aiosqlite.connect(DB_NAME) as db:
            await track_mission(game["user_id"], "bomb", 1, db)
            await db.commit()
        await callback.message.edit_text(f"💥 **بمب! باختی ${game['bet']:,}.**", reply_markup=kb)
        del active_games[game_id]
    else:
        game["multiplier"] *= 2
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅" if game["revealed"][i] else "❓",
                callback_data="noop" if game["revealed"][i] else f"bomb_click_{game_id}_{i}") for i in range(j, j + 4)]
            for j in range(0, 12, 4)
        ])
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"💰 برداشت (${game['bet'] * game['multiplier']:,})", callback_data=f"bomb_cashout_{game_id}")])
        await callback.message.edit_text(f"💣 **انفجار**\n\n📈 ضریب فعلی: **{game['multiplier']}x**", reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("bomb_cashout_"))
async def bomb_cashout(callback: CallbackQuery):
    game_id = callback.data.replace("bomb_cashout_", "")
    game = active_games.get(game_id)
    if not game or game["status"] != "playing":
        return await callback.answer("❌ فعال نیست!", show_alert=True)
    if callback.from_user.id != game["user_id"]:
        return await callback.answer("❌ این بازی مال تو نیست!", show_alert=True)
    win_amount = game["bet"] * game["multiplier"]
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win_amount, game["user_id"]))
        await track_mission(game["user_id"], "bomb", 1, db)
        await db.commit()
    del active_games[game_id]
    await callback.message.edit_text(f"💰 **برداشت موفق!**\n${win_amount:,} اضافه شد. ✅")


# ==========================================
# 20. تسک‌های پس‌زمینه
# ==========================================
async def crypto_updater():
    while True:
        await asyncio.sleep(300)
        async with aiosqlite.connect(DB_NAME) as db:
            for coin, price in await (await db.execute("SELECT coin, price FROM crypto_prices")).fetchall():
                new_price = round(price * random.uniform(0.95, 1.05), 4)
                if coin == "DOGE" and new_price < 0.01:
                    new_price = 0.01
                await db.execute("UPDATE crypto_prices SET price = ? WHERE coin = ?", (new_price, coin))
            await db.commit()


async def children_income_updater():
    while True:
        await asyncio.sleep(86400)
        async with aiosqlite.connect(DB_NAME) as db:
            adults = await (await db.execute("SELECT parent1_id, parent2_id FROM children WHERE stage = 3")).fetchall()
            income_map = {}
            for p1, p2 in adults:
                if p1:
                    income_map[p1] = income_map.get(p1, 0) + 200
                if p2:
                    income_map[p2] = income_map.get(p2, 0) + 200
            for parent_id, total_income in income_map.items():
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (total_income, parent_id))
                try:
                    await bot.send_message(parent_id, f"💼 **درآمد فرزندان:** ${total_income:,} به حساب شما اضافه شد.")
                except Exception:
                    pass
            await db.commit()


# ==========================================
# فایت پت (با باگ‌فیکس)
# ==========================================
@dp.message(F.text.lower().startswith("فایت "))
async def start_pet_fight(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    bet = parse_amount(message.text, 1)
    if bet is None:
        return await message.reply("❌ فرمت: `فایت 5000`", parse_mode="Markdown")

    user_id = message.from_user.id
    game_id = f"petfight_{message.chat.id}_{message.message_id}"
    async with aiosqlite.connect(DB_NAME) as db:
        if (await get_user(user_id))[2] < bet:
            return await message.reply("❌ پول نداری!")
        pet = await (await db.execute(
            "SELECT id, pet_name, power FROM user_pets WHERE user_id = ? ORDER BY power DESC LIMIT 1",
            (user_id,))).fetchone()
        if not pet:
            return await message.reply("❌ تو هیچ پتی نداری! اول از بازار سیاه بخر.")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
        await db.commit()

    active_games[game_id] = {
        "type": "pet_fight", "creator_id": user_id, "bet": bet,
        "status": "waiting", "chat_id": message.chat.id,
        "creator_pet": pet, "created_at": time.time()
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🥊 جوین فایت", callback_data=f"join_petfight_{game_id}")
    ]])
    await message.reply(
        f"⚔️ **فایت پت**\n\nسازنده: {message.from_user.first_name} (پت: {pet[1]} - قدرت {pet[2]:,})\n💰 شرط: ${bet:,}\n\nیکی جوین بزنه!",
        reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("join_petfight_"))
async def join_pet_fight(callback: CallbackQuery):
    game_id = callback.data.replace("join_petfight_", "")
    game = active_games.get(game_id)
    user_id = callback.from_user.id

    if not game or game["status"] != "waiting" or user_id == game["creator_id"]:
        return await callback.answer("❌ خطا!", show_alert=True)
    game["status"] = "running"

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            if (await get_user(user_id))[2] < game["bet"]:
                game["status"] = "waiting"
                return await callback.answer("❌ پول نداری!", show_alert=True)
            pet = await (await db.execute(
                "SELECT id, pet_name, power FROM user_pets WHERE user_id = ? ORDER BY power DESC LIMIT 1",
                (user_id,))).fetchone()
            if not pet:
                game["status"] = "waiting"
                return await callback.answer("❌ تو هیچ پتی نداری!", show_alert=True)
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (game["bet"], user_id))
            await db.commit()
    except Exception:
        game["status"] = "waiting"
        return await callback.answer("❌ خطای دیتابیس!", show_alert=True)

    creator_pet, joiner_pet = game["creator_pet"], pet
    if creator_pet[2] > joiner_pet[2]:
        winner_id, winner_pet = game["creator_id"], creator_pet
    elif joiner_pet[2] > creator_pet[2]:
        winner_id, winner_pet = user_id, joiner_pet
    else:
        winner_id = random.choice([game["creator_id"], user_id])
        winner_pet = creator_pet if winner_id == game["creator_id"] else joiner_pet

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (game["bet"] * 2, winner_id))
        await db.commit()
    del active_games[game_id]

    await callback.message.edit_text(
        f"🥊 <b>نتیجه فایت پت</b>\n\n"
        f"{creator_pet[1]} (قدرت {creator_pet[2]:,}) vs {joiner_pet[1]} (قدرت {joiner_pet[2]:,})\n\n"
        f"🏆 <b>برنده: <a href='tg://user?id={winner_id}'>{winner_pet[1]}</a></b> — ${game['bet'] * 2:,} برد!",
        parse_mode="HTML")


# ==========================================
# مسابقه ماشین (با باگ‌فیکس)
# ==========================================
@dp.message(F.text.lower().startswith("مسابقه "))
async def start_race(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ فقط توی گروه!")
    bet = parse_amount(message.text, 1)
    if bet is None:
        return await message.reply("❌ فرمت: `مسابقه 5000`", parse_mode="Markdown")

    user_id = message.from_user.id
    game_id = f"race_{message.chat.id}_{message.message_id}"
    async with aiosqlite.connect(DB_NAME) as db:
        car = await (await db.execute(
            "SELECT id, car_name, power FROM user_cars WHERE user_id = ? ORDER BY power DESC LIMIT 1",
            (user_id,))).fetchone()
        if not car:
            return await message.reply("❗ اول از منو ماشین بخر.")
        if (await get_user(user_id))[2] < bet:
            return await message.reply("❌ پول نداری!")
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
        await db.commit()

    active_games[game_id] = {
        "type": "race", "creator_id": user_id, "bet": bet,
        "status": "waiting", "creator_car": car, "chat_id": message.chat.id,
        "created_at": time.time()
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏎️ جوین مسابقه", callback_data=f"join_race_{game_id}")
    ]])
    await message.reply(
        f"🏁 **مسابقه ماشین**\n\nسازنده: {message.from_user.first_name}\n🚗 {car[1]} (قدرت: {car[2]:,})\n💰 شرط: ${bet:,}\n\nیکی جوین بزنه!",
        reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("join_race_"))
async def join_race(callback: CallbackQuery):
    game_id = callback.data.replace("join_race_", "")
    game = active_games.get(game_id)
    user_id = callback.from_user.id

    if not game or game["status"] != "waiting" or user_id == game["creator_id"]:
        return await callback.answer("❌ خطا!", show_alert=True)
    game["status"] = "running"

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            joiner_car = await (await db.execute(
                "SELECT id, car_name, power FROM user_cars WHERE user_id = ? ORDER BY power DESC LIMIT 1",
                (user_id,))).fetchone()
            if not joiner_car:
                game["status"] = "waiting"
                return await callback.answer("❗ ماشین نداری!", show_alert=True)
            if (await get_user(user_id))[2] < game["bet"]:
                game["status"] = "waiting"
                return await callback.answer("❌ پول نداری!", show_alert=True)
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (game["bet"], user_id))
            await db.commit()
    except Exception:
        game["status"] = "waiting"
        return await callback.answer("❌ خطای دیتابیس!", show_alert=True)

    p1, p2 = game["creator_car"][2], joiner_car[2]
    winner_id = game["creator_id"] if p1 > p2 else (user_id if p2 > p1 else random.choice([game["creator_id"], user_id]))
    w_car = game["creator_car"][1] if winner_id == game["creator_id"] else joiner_car[1]

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (game["bet"] * 2, winner_id))
        await db.commit()
    del active_games[game_id]

    await callback.message.edit_text(
        f"🏁 <b>نتیجه مسابقه</b>\n\n"
        f"🚗 {game['creator_car'][1]} (قدرت {p1:,})\n"
        f"🏎️ {joiner_car[1]} (قدرت {p2:,})\n\n"
        f"🏆 <b>برنده: <a href='tg://user?id={winner_id}'>{w_car}</a></b> — ${game['bet'] * 2:,} برد!",
        parse_mode="HTML")


# ==========================================
# برگشت پول بازی‌های بدون جوین
# ==========================================
async def game_timeout_cleaner():
    while True:
        await asyncio.sleep(60)
        now = time.time()
        expired = [gid for gid, g in list(active_games.items())
                   if g.get("status") == "waiting" and g.get("created_at") and now - g["created_at"] > 300]
        for gid in expired:
            game = active_games.get(gid)
            if not game or game["status"] != "waiting":
                continue
            game["status"] = "expired"
            try:
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?",
                                     (game["bet"], game["creator_id"]))
                    await db.commit()
            except Exception:
                game["status"] = "waiting"
                continue
            active_games.pop(gid, None)
            try:
                await bot.send_message(game["chat_id"], f"⏰ بازی منقضی شد و ${game['bet']:,} به سازنده برگشت.")
            except Exception:
                pass


# ==========================================
# اجرا
# ==========================================
async def main():
    await init_db()
    background_tasks = [
        asyncio.create_task(crypto_updater()),
        asyncio.create_task(children_income_updater()),
        asyncio.create_task(game_timeout_cleaner()),
    ]
    print("🚀 ربات با موفقیت روشن شد و در حال اجراست...")
    try:
        await dp.start_polling(bot)
    finally:
        for task in background_tasks:
            task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
