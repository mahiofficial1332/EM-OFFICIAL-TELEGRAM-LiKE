
import discord
from discord.ext import commands
import os
import requests
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://your-gemini-api-url.com/v1/chat")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

chat_channel_id = None  # Will be set by !set command

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

async def get_gemini_ai_response(user_message):
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "prompt": user_message,
        "language": "bn"
    }
    try:
        response = requests.post(GEMINI_API_URL, json=json_data, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "দুঃখিত, বুঝতে পারিনি।")
    except Exception as e:
        print("Gemini API error:", e)
        return "দুঃখিত, সিস্টেমে সমস্যা হয়েছে। পরে চেষ্টা করুন।"

@bot.event
async def on_ready():
    print(f"{bot.user} এখন অনলাইনে!")

@bot.event
async def on_message(message):
    global chat_channel_id

    if message.author == bot.user:
        return

    if chat_channel_id is None or message.channel.id != chat_channel_id:
        await bot.process_commands(message)
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    user_msg = message.content.strip()
    if not user_msg:
        return

    response_text = await asyncio.to_thread(get_gemini_ai_response, user_msg)
    await message.channel.send(response_text)

@bot.command(name="set")
@commands.check(is_admin)
async def set_channel(ctx):
    global chat_channel_id
    chat_channel_id = ctx.channel.id
    await ctx.send("✅ এই চ্যানেলটি বটের চ্যাট চ্যানেল হিসেবে সেট করা হয়েছে।\nCreated by Mahi")

@bot.command(name="all")
async def all_commands(ctx):
    commands_list = """
**MAHI Official Bot Commands:**

`!editor` - ছবি এডিটিং ও স্টাইল পরিবর্তন
`!set` - বটের চ্যাট চ্যানেল সেট করুন (Admin only)
`!all` - এই কমান্ডগুলো দেখুন

Created by Mahi
"""
    await ctx.send(commands_list)

@bot.command(name="editor")
async def editor_command(ctx, *, arg=None):
    if arg is None:
        await ctx.send("ছবি এডিট করতে কমান্ডের সাথে বিবরণ দিন।\nCreated by Mahi")
    else:
        await ctx.send(f"ছবির এডিটিং চলছে: `{arg}`\nCreated by Mahi")

@set_channel.error
async def set_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ এই কমান্ড ব্যবহার করতে অ্যাডমিন পারমিশন প্রয়োজন।\nCreated by Mahi")

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN environment variable is not set!")
        exit(1)
    bot.run(DISCORD_BOT_TOKEN)
