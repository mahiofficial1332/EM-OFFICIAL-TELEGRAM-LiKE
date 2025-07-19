import discord
from discord.ext import commands
import os
import google.generativeai as genai

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

@bot.command()
async def ask(ctx, *, question: str):
    try:
        response = model.generate_content(question)
        await ctx.send(response.text[:1900])
    except Exception as e:
        await ctx.send("❌ Error occurred while getting AI response.")

@bot.command()
async def editor(ctx):
    await ctx.send("🛠️ Photo editing feature coming soon!")

bot.run(DISCORD_TOKEN)
