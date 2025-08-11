import discord
from discord.ext import commands, tasks
import random
import json
import os
from datetime import datetime, timedelta
from PIL import Image
import requests
from io import BytesIO
import asyncio
import logging
from dotenv import load_dotenv


 #Указываешь свой путь к .env
dotenv_path = r"C:\\Users\\SIM SIM\\OneDrive\\Desktop\\Новая папка\\confing.env"
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)

DATA_FILE = "economy.json"
STORE_FILE = "store.json"
BANNER_PATH = "static/banners"
os.makedirs(BANNER_PATH, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

class DataManager:
    def __init__(self):
        self.economy = {"users": {}, "guilds": {}}
        self.store = {}
        self.lock = asyncio.Lock()

    async def load(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.economy = json.load(f)
        else:
            self.economy = {"users": {}, "guilds": {}}

        if os.path.exists(STORE_FILE):
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                self.store = json.load(f)
        else:
            self.store = {}

    async def save(self):
        async with self.lock:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.economy, f, ensure_ascii=False, indent=4)
            with open(STORE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.store, f, ensure_ascii=False, indent=4)

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


store_items = load_json(STORE_FILE, {})

data_manager = DataManager()

# Асинхронное сохранение с буфером
save_task = None

def schedule_save():
    global save_task
    if save_task is None or save_task.done():
        save_task = asyncio.create_task(data_manager.save())

# --- Обработка баннера ---

def format_banner(image_bytes):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    target_width = 900
    target_height = 300
    target_ratio = target_width / target_height

    width, height = img.size
    current_ratio = width / height

    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        right = left + new_width
        img = img.crop((left, 0, right, height))
    elif current_ratio < target_ratio:
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        bottom = top + new_height
        img = img.crop((0, top, width, bottom))

    img = img.resize((target_width, target_height), Image.LANCZOS)

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output

# --- Вспомогательные функции ---

def today_str():
    return datetime.utcnow().date().isoformat()

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None

def cooldown_left(last_str, cooldown_days=1):
    if not last_str:
        return 0
    last_date = parse_date(last_str)
    if not last_date:
        return 0
    delta = datetime.utcnow().date() - last_date
    left = cooldown_days - delta.days
    return max(left, 0)

def format_time_left(days):
    if days == 0:
        return "можно использовать"
    else:
        return f"осталось ждать {days} д."
        
# функция для проверки времени
def time_left(last_time_str, cooldown_hours):
    if not last_time_str:
        return None
    try:
        last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # если дата без времени
        last_time = datetime.strptime(last_time_str, "%Y-%m-%d")
        last_time = last_time.replace(hour=0, minute=0, second=0)

    now = datetime.utcnow()
    cooldown = timedelta(hours=cooldown_hours)
    if now < last_time + cooldown:
        remaining = (last_time + cooldown) - now
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60
        return f"{hours} ч {minutes} мин"
    return None

# --- Команды ---

@bot.event
async def on_ready():
    await data_manager.load()
    print(f"✅ Бот запущен как {bot.user}")

# !баланс
@bot.command()
async def баланс(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].setdefault(user_id, {
        "balance": 0, "guild": None, "items": [], "last_work": None, "last_daily": None
    })

    embed = discord.Embed(
        title=f"💰 Баланс {ctx.author.display_name}",
        description=f"**{user['balance']} FFCoin**",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Free Fire United 💙 by TheDodo")
    await ctx.send(embed=embed)
    schedule_save()

# !работа
@bot.command()
async def работа(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].setdefault(user_id, {
        "balance": 0, "guild": None, "items": [], "last_work": None
    })

    cooldown_hours = 24
    left = time_left(user.get("last_work"), cooldown_hours)
    if left:
        embed = discord.Embed(
            title="💼 Работа",
            description=f"🕒 Ты уже работал сегодня!\n⏳ Осталось: **{left}**",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    reward = random.randint(99, 159)
    user["balance"] += reward
    user["last_work"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    schedule_save()

    embed = discord.Embed(
        title="💼 Работа",
        description=f"Ты поработал и получил **{reward} FFCoin**!",
        color=discord.Color.gold()
    )
    embed.add_field(name="Текущий баланс", value=f"**{user['balance']} FFCoin**", inline=False)
    embed.add_field(name="⏳ Следующая работа", value=f"**{cooldown_hours} ч**", inline=False)
    embed.set_footer(text="Free Fire United 💙 by TheDodo")
    await ctx.send(embed=embed)


@bot.command()
async def лидеры(ctx):
    top_users = sorted(
        economy["users"].items(),
        key=lambda x: x[1].get("balance", 0),
        reverse=True
    )[:10]

    embed = discord.Embed(
        title="🏆 Топ-10 богатейших игроков",
        description="Самые богатые участники сервера по FFCoin",
        color=discord.Color.gold()
    )

    for i, (uid, data) in enumerate(top_users, 1):
        user_mention = f"<@{uid}>"
        balance = data.get("balance", 0)
        embed.add_field(
            name=f"{i}. {user_mention}",
            value=f"💰 Баланс: **{balance} FFCoin**",
            inline=False
        )

    embed.set_footer(text="Free Fire United 💙 by TheDodo")
    await ctx.send(embed=embed) 


@bot.command()
async def создать(ctx, *, название: str):
    user_id = str(ctx.author.id)
    user = economy["users"].setdefault(user_id, {"balance": 0, "guild": None})

    if user["guild"]:
        await ctx.send("❌ Ты уже состоишь в гильдии.")
        return
    if user["balance"] < 10000:
        await ctx.send("💸 У тебя недостаточно FFCoin (нужно 10,000).")
        return
    if название in economy["guilds"]:
        await ctx.send("⚠️ Гильдия с таким названием уже существует.")
        return

    embed = discord.Embed(
        title="🔒 Приватность гильдии",
        description=(
            "Выбери тип приватности для своей гильдии:\n"
            "🔓 — **Открытая** (вступить может любой)\n"
            "📝 — **По заявке** (вступление только после одобрения владельца)\n"
            "🔒 — **Закрытая** (только по приглашению владельца)"
        ),
        color=discord.Color.gold()
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🔓")
    await msg.add_reaction("📝")
    await msg.add_reaction("🔒")

    def check(reaction, user_check):
        return (
            user_check == ctx.author and
            str(reaction.emoji) in ["🔓", "📝", "🔒"] and
            reaction.message.id == msg.id
        )

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("⏰ Время ожидания истекло. Создание гильдии отменено.")
        return

    if str(reaction.emoji) == "🔓":
        privacy = "open"
        privacy_text = "Открытая"
    elif str(reaction.emoji) == "📝":
        privacy = "request"
        privacy_text = "По заявке"
    else:
        privacy = "closed"
        privacy_text = "Закрытая"

    user["balance"] -= 10000
    user["guild"] = название
    economy["guilds"][название] = {
        "owner": user_id,
        "banner": None,
        "avatar": None,
        "members": [user_id],
        "privacy": privacy
    }

    await ctx.send(f"🏰 Гильдия **{название}** создана! Тип: **{privacy_text}**")
    schedule_save()

# Команда для установки баннера
# Команда для установки баннера (только лидер)
BANNER_PATH = "static/banners"  # папка для баннеров
os.makedirs(BANNER_PATH, exist_ok=True)

def format_banner(url):
    # Загружаем изображение с URL
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))

    # Целевой размер баннера
    target_width = 900
    target_height = 300
    target_ratio = target_width / target_height

    # Обрезка под соотношение 3:1
    width, height = img.size
    current_ratio = width / height

    if current_ratio > target_ratio:
        # Слишком широкое — обрезаем по ширине
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        right = left + new_width
        img = img.crop((left, 0, right, height))
    elif current_ratio < target_ratio:
        # Слишком высокое — обрезаем по высоте
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        bottom = top + new_height
        img = img.crop((0, top, width, bottom))

    # Меняем размер на 900x300
    img = img.resize((target_width, target_height), Image.LANCZOS)

    # Сохраняем в память
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output


# Обновлённая команда гильдии
# Загружаем данные
try:
    with open("economy.json", "r", encoding="utf-8") as f:
        economy = json.load(f)
except FileNotFoundError:
    economy = {"users": {}, "guilds": {}}

# Функция для сохранения
def save_economy():
    with open("economy.json", "w", encoding="utf-8") as f:
        json.dump(economy, f, ensure_ascii=False, indent=4)

# Команда для просмотра гильдии
@bot.command()
async def гильдия(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].get(user_id)

    # Если пользователь не в гильдии — показываем список всех гильдий
    if not user or not user.get("guild"):
        if not economy["guilds"]:
            await ctx.send("😢 На сервере ещё нет ни одной гильдии.")
            return

        embed = discord.Embed(
            title="🏰 Список гильдий сервера",
            description="**Выбери гильдию для вступления с помощью команды:**\n`!вступить [название]`",
            color=discord.Color.gold()
        )

        for name, гильдия in economy["guilds"].items():
            members_count = len(гильдия.get("members", []))
            level = гильдия.get("level", 1)
            messages = гильдия.get("messages", 0)
            voice_minutes = гильдия.get("voice_minutes", 0)
            voice_hours = int(voice_minutes // 60)
            embed.add_field(
                name=f"🏷️ {name} (ур. {level})",
                value=(
                    f"👥 **Участников:** {members_count}\n"
                    f"💬 **Сообщений:** {messages}\n"
                    f"🕒 **Войс:** {voice_hours} ч."
                ),
                inline=False
            )
        embed.set_footer(text="Free Fire United 💙 by TheDodo")
        await ctx.send(embed=embed)
        return

    # Если пользователь в гильдии — стандартная информация о его гильдии
    название = user["guild"]
    гильдия = economy["guilds"].get(название)

    if not гильдия:
        await ctx.send("❌ Гильдия не найдена.")
        return

    owner_id = гильдия["owner"]
    avatar_url = гильдия.get("avatar")

    embed = discord.Embed(
        title=f"🏰 Гильдия: {название}",
        color=discord.Color.gold()
    )

    embed.add_field(name="👑 Владелец", value=f"<@{owner_id}>", inline=True)

    guild_level = гильдия.get("level", 1)
    guild_exp = гильдия.get("exp", 0)
    exp_needed = guild_level * 1000
    embed.add_field(
        name="📈 Уровень гильдии",
        value=f"Уровень: **{guild_level}**\nОпыт: {guild_exp}/{exp_needed}",
        inline=False
    )

    members_info = []
    for member_id in гильдия["members"]:
        member_data = economy["users"].get(str(member_id), {})
        упоминание = f"<@{member_id}>"
        voice_hours = member_data.get("voice_time", 0) // 3600
        messages_count = member_data.get("messages", 0)
        members_info.append(f"{упоминание} — 🕒 {voice_hours} ч в войсе | 💬 {messages_count} сообщений")

    if members_info:
        embed.add_field(
            name="📜 Участники",
            value="\n".join(members_info),
            inline=False
        )


    # В цикле по гильдиям:
    requests_count = len(гильдия.get("requests", [])) if гильдия.get("privacy") == "request" else 0
    requests_line = f"\n📨 **Заявок:** {requests_count}" if requests_count else ""
    privacy = гильдия.get("privacy", "open")
    privacy_text = {
        "open": "Открытая",
        "request": "По заявке",
        "closed": "Закрытая"
    }.get(privacy, "Открытая")
     # ...existing code...
    members_count = len(гильдия.get("members", []))
    level = гильдия.get("level", 1)
    messages = гильдия.get("messages", 0)
    voice_minutes = гильдия.get("voice_minutes", 0)
    voice_hours = int(voice_minutes // 60)
    requests_count = len(гильдия.get("requests", [])) if гильдия.get("privacy") == "request" else 0
    requests_line = f"\n📨 **Заявок:** {requests_count}" if requests_count else ""
    privacy = гильдия.get("privacy", "open")
    privacy_text = {
        "open": "Открытая",
        "request": "По заявке",
        "closed": "Закрытая"
    }.get(privacy, "Открытая")
    embed.add_field(
        name=f"🔒 **Тип:** {privacy_text}{requests_line}",
        value="\u200b",
        inline=False
    )
# ...existing code...

    embed.set_footer(text="Free Fire United 💙 by TheDodo")

    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    await ctx.send(embed=embed)


@bot.command()
async def заявки(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].get(user_id)
    if not user or not user.get("guild"):
        await ctx.send("❌ Ты не в гильдии.")
        return
    название = user["guild"]
    гильдия = economy["guilds"].get(название)
    if not гильдия or str(гильдия["owner"]) != user_id:
        await ctx.send("❌ Только владелец гильдии может просматривать заявки.")
        return
    if гильдия.get("privacy") != "request":
        await ctx.send("❌ Ваша гильдия не принимает заявки.")
        return
    заявки = гильдия.get("requests", [])
    if not заявки:
        await ctx.send("📭 Нет новых заявок.")
        return
    embed = discord.Embed(
        title=f"📨 Заявки в гильдию {название}",
        color=discord.Color.gold()
    )
    for i, uid in enumerate(заявки, 1):
        embed.add_field(
            name=f"{i}. <@{uid}>",
            value=f"Принять: `!принять {uid} {название}`\nОтклонить: `!отклонить {uid} {название}`",
            inline=False
        )
    await ctx.send(embed=embed)

    
@bot.command()
async def установить_аву(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].get(user_id)

    if not user or not user["guild"]:
        await ctx.send("😢 Ты не состоишь в гильдии.")
        return

    guild_name = user["guild"]
    гильдия = economy["guilds"].get(guild_name)

    if гильдия["owner"] != user_id:
        await ctx.send("❌ Только владелец гильдии может менять аву.")
        return

    # Проверка вложений
    if not ctx.message.attachments:
        await ctx.send("❗ Пожалуйста, прикрепи изображение для аватарки.")
        return

    attachment = ctx.message.attachments[0]

    # Проверка на формат файла
    if not attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        await ctx.send("📁 Только изображения (.png, .jpg, .jpeg, .gif) принимаются как аватарка.")
        return

    гильдия["avatar"] = attachment.url
    schedule_save()
    await ctx.send(f"🖼 Аватарка гильдии успешно обновлена!\n{attachment.url}")


@bot.command()
async def удалить_аву(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].get(user_id)

    if not user or not user.get("guild"):
        await ctx.send("😢 Ты не состоишь ни в одной гильдии.")
        return

    название = user["guild"]
    гильдия = economy["guilds"].get(название)

    if str(ctx.author.id) != str(гильдия["owner"]):
        await ctx.send("🚫 Только владелец гильдии может удалить аватарку!")
        return

    if not гильдия.get("avatar"):
        await ctx.send("🚫 У гильдии нет аватарки.")
        return

    гильдия["avatar"] = None
    save_economy()
    await ctx.send(f"🗑 Аватарка для гильдии **{название}** удалена!")



@bot.command()
async def вступить(ctx, *, номер_или_название: str):
    user_id = str(ctx.author.id)
    user = economy["users"].setdefault(user_id, {"balance": 0, "guild": None, "items": []})

    if user["guild"]:
        await ctx.send("❌ Ты уже в гильдии. Выйди из неё, чтобы вступить в другую.")
        return

    # Поиск по номеру из списка
    guilds_list = list(economy["guilds"].items())
    if номер_или_название.isdigit():
        idx = int(номер_или_название) - 1
        if idx < 0 or idx >= len(guilds_list):
            await ctx.send("❌ Гильдия с таким номером не найдена.")
            return
        название, гильдия = guilds_list[idx]
    else:
        название = номер_или_название
        гильдия = economy["guilds"].get(название)
        if not гильдия:
            await ctx.send("❌ Гильдия с таким названием не найдена.")
            return

    privacy = гильдия.get("privacy", "open")
    if privacy == "closed":
        await ctx.send("🔒 В эту гильдию можно вступить только по приглашению владельца.")
        return
    if privacy == "request":
        # Добавляем заявку
        гильдия.setdefault("requests", [])
        if user_id in гильдия["requests"]:
            await ctx.send("📝 Ты уже отправил заявку в эту гильдию.")
            return
        гильдия["requests"].append(user_id)
        schedule_save()
        await ctx.send(f"📝 Заявка на вступление в **{название}** отправлена владельцу.")
        return

    # Открытая гильдия
    гильдия["members"].append(user_id)
    user["guild"] = название
    schedule_save()
    await ctx.send(f"✅ Ты вступил в гильдию **{название}**!")


@bot.command()
async def принять(ctx, user_id: int, *, название: str):
    гильдия = economy["guilds"].get(название)
    if not гильдия or str(ctx.author.id) != str(гильдия["owner"]):
        await ctx.send("❌ Только владелец может принимать заявки.")
        return
    user = economy["users"].get(str(user_id))
    if not user or user["guild"]:
        await ctx.send("❌ Пользователь уже в гильдии или не найден.")
        return
    гильдия["members"].append(str(user_id))
    user["guild"] = название
    schedule_save()
    await ctx.send(f"✅ Пользователь <@{user_id}> принят в гильдию **{название}**!")

@bot.command()
async def отклонить(ctx, user_id: int, *, название: str):
    гильдия = economy["guilds"].get(название)
    if not гильдия or str(ctx.author.id) != str(гильдия["owner"]):
        await ctx.send("❌ Только владелец может отклонять заявки.")
        return
    await ctx.send(f"❌ Заявка пользователя <@{user_id}> отклонена.") 



@bot.command()
async def выйти(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].get(user_id)

    if not user or not user["guild"]:
        await ctx.send("❌ Ты не состоишь в гильдии.")
        return

    guild_name = user["guild"]
    guild = economy["guilds"].get(guild_name)

    if guild["owner"] == user_id:
        await ctx.send("❌ Ты — владелец гильдии. Сначала передай права или удали гильдию.")
        return

    guild["members"].remove(user_id)
    user["guild"] = None
    schedule_save()
    await ctx.send("🚪 Ты покинул гильдию.")


@bot.command()
async def удалить_гильдию(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].get(user_id)

    if not user or not user["guild"]:
        await ctx.send("❌ Ты не в гильдии.")
        return

    guild_name = user["guild"]
    guild = economy["guilds"].get(guild_name)

    if guild["owner"] != user_id:
        await ctx.send("❌ Только владелец может удалить гильдию.")
        return

    embed = discord.Embed(
        title="⚠️ Подтверждение удаления гильдии",
        description=f"Ты уверен, что хочешь удалить гильдию **{guild_name}**?\nЭто действие нельзя отменить!\n\nНажми ✅ чтобы подтвердить или ❌ чтобы отменить.",
        color=discord.Color.red()
    )
    confirm_msg = await ctx.send(embed=embed)
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    def check(reaction, user_check):
        return (
            user_check == ctx.author and
            str(reaction.emoji) in ["✅", "❌"] and
            reaction.message.id == confirm_msg.id
        )

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await confirm_msg.edit(content="⏰ Время ожидания истекло. Удаление гильдии отменено.")
        return

    if str(reaction.emoji) == "✅":
        for member_id in guild["members"]:
            if member_id in economy["users"]:
                economy["users"][member_id]["guild"] = None
        del economy["guilds"][guild_name]
        schedule_save()
        await ctx.send(embed=discord.Embed(
            title="🗑️ Гильдия удалена",
            description=f"Гильдия **{guild_name}** успешно удалена.",
            color=discord.Color.red()
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="❌ Удаление отменено",
            description="Удаление гильдии отменено.",
            color=discord.Color.gold()
        ))


@bot.command()
async def список_гильдии(ctx):
    if not economy["guilds"]:
        await ctx.send("😢 На сервере ещё нет ни одной гильдии.")
        return

    embed = discord.Embed(
        title="🏰 Список гильдий сервера",
        description="**Вступить: !вступить [номер или название]**",
        color=discord.Color.gold()
    )

    for idx, (name, гильдия) in enumerate(economy["guilds"].items(), 1):
        members_count = len(гильдия.get("members", []))
        level = гильдия.get("level", 1)
        messages = гильдия.get("messages", 0)
        voice_minutes = гильдия.get("voice_minutes", 0)
        voice_hours = int(voice_minutes // 60)
        requests_count = len(гильдия.get("requests", [])) if гильдия.get("privacy") == "request" else 0
        requests_line = f"\n📨 **Заявок:** {requests_count}" if requests_count else ""
        privacy = гильдия.get("privacy", "open")
        privacy_text = {
            "open": "Открытая",
            "request": "По заявке",
            "closed": "Закрытая"
        }.get(privacy, "Открытая")
        embed.add_field(
            name=f"{idx}. {name} (ур. {level})",
            value=(
                f"👥 **Участников:** {members_count}\n"
                f"💬 **Сообщений:** {messages}\n"
                f"🕒 **Войс:** {voice_hours} ч.\n"
                f"🔒 **Тип:** {privacy_text}"
                f"{requests_line}"
            ),
            inline=False
        )
    embed.set_footer(text="Free Fire United 💙 by TheDodo")
    await ctx.send(embed=embed)


@bot.command()
async def магазин(ctx):
    embed = discord.Embed(title="🛒 Магазин предметов", color=discord.Color.gold())
    for item in store_items.values():
        embed.add_field(
            name=f"{item['name']} — {item['price']} FFCoin",
            value=item['description'],
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def купить(ctx, *, название: str):
    user_id = str(ctx.author.id)
    user = economy["users"].setdefault(user_id, {"balance": 0, "guild": None, "items": []})

    item = store_items.get(название.lower())
    if not item:
        await ctx.send("❌ Такого предмета нет в магазине.")
        return

    price = item["price"]
    if user["balance"] < price:
        await ctx.send("💸 Недостаточно монет.")
        return

    # Если это роль
    if item.get("type") == "роль":
        role_name = item["name"]
        role = discord.utils.get(ctx.guild.roles, name=role_name)

        if not role:
            await ctx.send(f"❌ Роль `{role_name}` не найдена на сервере.")
            return
        
        try:
            await ctx.author.add_roles(role)
        except discord.Forbidden:
            await ctx.send("❌ У меня нет прав выдать эту роль.")
            return

        await ctx.send(f"🎉 Ты купил роль **{role.name}** за {price} FFCoin!")

    # Если это обычный предмет
    else:
        user.setdefault("items", []).append(item["name"])
        await ctx.send(f"✅ Ты купил **{item['name']}** за {price} FFCoin!")

    # Баланс списывается только ПОСЛЕ успешной выдачи
    user["balance"] -= price
    schedule_save()


@bot.command()
async def инвентарь(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].setdefault(user_id, {"balance": 0, "guild": None, "items": []})
    items = user.get("items", [])

    if not items:
        await ctx.send("🎒 Твой инвентарь пуст...")
        return

    inventory_text = "\n".join([f"• {item}" for item in items])
    await ctx.send(f"🎒 **Инвентарь {ctx.author.display_name}:**\n{inventory_text}")

@bot.command(name="добавить_товар")
@commands.has_permissions(administrator=True)
async def добавить_товар(ctx, *, сообщение):
    try:
        # Преобразуем параметры из строки в словарь
        части = dict(часть.split("=", 1) for часть in сообщение.split(" ") if "=" in часть)
        тип = части.get("тип", "").lower()
        название = части.get("название", "").lower()
        цена_str = части.get("цена", "0")
        описание = части.get("описание", "")

        # Проверка типа
        if тип not in ["предмет", "роль"]:
            await ctx.send("❗ `тип` должен быть либо `предмет`, либо `роль`.")
            return

        # Проверка обязательных параметров
        if not название or not описание:
            await ctx.send("❗ Не хватает параметров. Формат:\n`!добавить_товар тип=роль|предмет название=имя цена=число описание=текст`")
            return

        # Пробуем преобразовать цену в число
        try:
            цена = int(цена_str)
        except ValueError:
            await ctx.send("❗ Укажи **числовую цену**. Пример: `цена=1000`")
            return

        # Добавляем товар в магазин
        store_items[название] = {
            "type": тип,
            "name": название.capitalize(),
            "price": цена,
            "description": описание
        }

        schedule_save()
        await ctx.send(f"✅ {тип.capitalize()} **{название.capitalize()}** добавлен в магазин за {цена} монет.")
        
    except Exception as e:
        await ctx.send(f"❌ Ошибка при добавлении товара: {e}")




@bot.command(name="хелп")
async def help_command(ctx):
    embed = discord.Embed(
        title="📜 Команды TheDodo Bot",
        description="Вот список всех доступных команд:",
        color=discord.Color.gold()
    )
    embed.add_field(name="ЭКОНОМИКА", value="", inline=False)
    embed.add_field(name="💼 !работа", value="Получить зарплату (1 раз в день)", inline=False)
    embed.add_field(name="🎁 !ежедневный", value="Получить ежедневный бонус", inline=False)
    embed.add_field(name="💰 !баланс", value="Показать текущий баланс", inline=False)
    embed.add_field(name="🏆 !лидеры", value="Топ-10 игроков по балансу", inline=False)

    embed.add_field(name="МАГАЗИН", value="", inline=False)
    embed.add_field(name="🏪 !магазин", value="Открыть магазин предметов", inline=False)
    embed.add_field(name="🛒 !купить [название]", value="Купить предмет из магазина", inline=False)
    embed.add_field(name="🎒 !инвентарь", value="Посмотреть свой инвентарь", inline=False)

    embed.add_field(name="ГИЛЬДИЯ", value="", inline=False)
    embed.add_field(name="🏰 !создать [название]", value="Создать гильдию (10,000 монет)", inline=False)
    embed.add_field(name="🏘 !гильдия", value="Инфо о твоей гильдии", inline=False)
    embed.add_field(name="➕ !вступить [название]", value="Вступить в гильдию", inline=False)
    embed.add_field(name="🚪 !выйти", value="Покинуть текущую гильдию", inline=False)
    embed.add_field(name="🗑️ !удалить_гильдию", value="Удалить свою гильдию (только владелец)", inline=False)
    embed.add_field(name="🖼 !установить_аву", value="Установить аватарку гильдии", inline=False)
    embed.add_field(name="⚔️ !битва", value="Прогресс битвы гильдий", inline=False)
    embed.add_field(name="📊 !топ_гильдий", value="Топ активных гильдий по сообщениям и голосовым", inline=False)

    
    embed.set_footer(text="Free Fire United 💙 by TheDodo")

    await ctx.send(embed=embed)


@bot.command(name="админ")
@commands.has_permissions(administrator=True)
async def help_command(ctx):
    embed = discord.Embed(
        title="📜 Админ управление",
        description="список доступных команд для администраторов:",
        color=discord.Color.blue()
    )

 # ⚙️ Админ
    embed.add_field(name="🛍️ !добавить_товар", value="(Админ) Добавить товар в магазин", inline=False)
    embed.add_field(name="🗑️ !удалить_товар [название]", value="(Админ) Удалить товар", inline=False)
    embed.add_field(name="🎁 !управление [выдать|отнять] @пользователь сумма", value="(Админ) Изменить баланс игрока", inline=False)
    embed.add_field(name="🏆 !наградить_гильдию [название]", value="(Админ) Выдать награду всей гильдии", inline=False)

    embed.set_footer(text="Admins Team")

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def удалить_товар(ctx, *, название: str):
    название = название.lower()
    
    if название not in store_items:
        await ctx.send("❌ Такого товара нет в магазине.")
        return

    del store_items[название]
    schedule_save()
    await ctx.send(f"🗑️ Товар **{название}** удалён из магазина.")


@bot.command()
@commands.has_permissions(administrator=True)
async def управление(ctx, действие: str, участник: discord.Member, сумма: int):
    user_id = str(участник.id)
    user = economy["users"].setdefault(user_id, {"balance": 0, "guild": None, "items": []})

    if действие.lower() == "выдать":
        user["balance"] += сумма
        await ctx.send(f"💸 {участник.mention} получил **+{сумма} FFCoin**.")

    elif действие.lower() == "отнять":
        user["balance"] = max(0, user["balance"] - сумма)
        await ctx.send(f"💸 У {участник.mention} отнято **-{сумма} FFCoin**.")

    else:
        await ctx.send("❗ Используй `выдать` или `отнять`.\nПример: `!управление выдать @user 1000`")


# !ежедневный
@bot.command()
async def ежедневный(ctx):
    user_id = str(ctx.author.id)
    user = economy["users"].setdefault(user_id, {
        "balance": 0, "guild": None, "items": [], "last_daily": None
    })

    cooldown_hours = 24
    left = time_left(user.get("last_daily"), cooldown_hours)
    if left:
        embed = discord.Embed(
            title="🎁 Ежедневный бонус",
            description=f"📅 Ты уже получал бонус сегодня!\n⏳ Осталось: **{left}**",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    reward = random.randint(200, 400)
    user["balance"] += reward
    user["last_daily"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    schedule_save()

    embed = discord.Embed(
        title="🎁 Ежедневный бонус",
        description=f"Ты получил ежедневный бонус: **{reward} FFCoin**!",
        color=discord.Color.gold()
    )
    embed.add_field(name="Текущий баланс", value=f"**{user['balance']} FFCoin**", inline=False)
    embed.add_field(name="⏳ Следующая ежедневка", value=f"**{cooldown_hours} ч**", inline=False)
    embed.set_footer(text="Free Fire United 💙 by TheDodo")
    await ctx.send(embed=embed)

     

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    user = economy["users"].setdefault(user_id, {"balance": 0, "guild": None, "items": []})

    if user["guild"]:
        guild_name = user["guild"]
        гильдия = economy["guilds"].setdefault(guild_name, {"owner": None, "members": [], "messages": 0, "voice_minutes": 0})
        гильдия["messages"] = гильдия.get("messages", 0) + 1

    await bot.process_commands(message)


voice_times = {}

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = str(member.id)
    user = economy["users"].get(user_id)
    if not user or not user["guild"]:
        return

    guild_name = user["guild"]
    гильдия = economy["guilds"].setdefault(guild_name, {"owner": None, "members": [], "messages": 0, "voice_minutes": 0})

    if before.channel is None and after.channel is not None:
        # Зашёл в голосовой
        voice_times[user_id] = datetime.utcnow()

    elif before.channel is not None and after.channel is None:
        # Вышел из голосового
        if user_id in voice_times:
            duration = (datetime.utcnow() - voice_times[user_id]).total_seconds() / 60
            гильдия["voice_minutes"] = гильдия.get("voice_minutes", 0) + duration
            del voice_times[user_id]
            schedule_save()


@bot.command()
async def битва(ctx):
    лидеры = []
    for name, гильдия in economy["guilds"].items():
        messages = гильдия.get("messages", 0)
        minutes = гильдия.get("voice_minutes", 0)
        выполнено = messages >= 5000 and minutes >= 400 * 60

        лидеры.append((name, messages, minutes, выполнено))

    лидеры.sort(key=lambda x: (x[3], x[1] + x[2]), reverse=True)

    lines = []
    for i, (name, msg, mins, done) in enumerate(лидеры, 1):
        status = "✅" if done else "❌"
        lines.append(f"**{i}. {name}** — {msg} сообщений, {int(mins/60)} ч. в войсе {status}")

    await ctx.send("⚔️ **Прогресс битвы гильдий:**\n" + "\n".join(lines))


@bot.command()
@commands.has_permissions(administrator=True)
async def наградить_гильдию(ctx, *, название: str):
    гильдия = economy["guilds"].get(название)
    if not гильдия:
        await ctx.send("❌ Гильдия не найдена.")
        return

    for member_id in гильдия["members"]:
        user = economy["users"].get(member_id)
        if user:
            user["balance"] += 5000  # или сколько нужно

    schedule_save()
    await ctx.send(f"🏆 Гильдия **{название}** награждена, все участники получили 5000 FFCoin!")


@bot.command()
async def топ_гильдий(ctx):
    топ = sorted(
        economy["guilds"].items(),
        key=lambda x: x[1].get("messages", 0) + x[1].get("voice_minutes", 0),
        reverse=True
    )[:10]

    embed = discord.Embed(
        title="📊 Топ гильдий по активности",
        description="Рейтинг по сумме сообщений и часов в войсе",
        color=discord.Color.gold()
    )

    for i, (name, гильдия) in enumerate(топ, 1):
        messages = гильдия.get('messages', 0)
        voice_hours = int(гильдия.get('voice_minutes', 0) // 60)
        embed.add_field(
            name=f"{i}. {name}",
            value=f"💬 Сообщений: **{messages}**\n🕒 Войс: **{voice_hours} ч.**",
            inline=False
        )

    embed.set_footer(text="Free Fire United 💙 by TheDodo")
    await ctx.send(embed=embed)


 # Запуск бота
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Ошибка: не найден токен в переменных окружения DISCORD_TOKEN")
else:
    bot.run(TOKEN)


