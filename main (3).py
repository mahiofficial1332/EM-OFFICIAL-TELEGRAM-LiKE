#!/usr/bin/env python3
"""
MAHI OFFICIAL Discord AI Bot - Complete Bot with Gemini AI Integration

This is the complete Discord AI chatbot with all features:
- Multi-language AI conversations
- Image generation with Gemini AI
- Admin commands and controls
- Welcome messages with timestamps
"""

import os
import sys
import logging
import discord
from discord.ext import commands
import asyncio
from pathlib import Path
from datetime import datetime
from gemini_client import GeminiClient
from config import settings, AllSettings

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ])


def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['DISCORD_TOKEN', 'GEMINI_API_KEY', 'ADMIN_ID']
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        return False

    return True


def main():
    """Main function to start the Discord bot"""
    print("🤖 MAHI OFFICIAL Discord AI Bot")
    print("=" * 40)

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Check environment variables
    if not check_environment():
        sys.exit(1)

    logger.info("Starting MAHI OFFICIAL Discord AI Bot...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")

    try:
        # Discord bot intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        # Bot configuration
        bot = commands.Bot(command_prefix="!", intents=intents)

        # Get configuration from environment variables
        DISCORD_TOKEN = os.getenv("MTM5NTYyODA4MTY5OTYyMzAwMg.Gr4btP.8R_rX4dczpMDIXuQWQitXVuhw25QIXy0pAARsw")
        GEMINI_API_KEY = os.getenv("AIzaSyDjWvMqLf3UvrOHsP1k1NsBV2nPSXOSvQw")
        ADMIN_ID = int(os.getenv("1380183114109947924"))

        # Initialize Gemini client
        gemini_client = GeminiClient(GEMINI_API_KEY)

        # Global state
        active_channel_id = None

        # Welcome message template
        WELCOME_MESSAGE = """💠 MAHI OFFICIAL BOT 💠
🔹 A smart & multi-language AI chatbot for your Discord server!
🔹 Powered by GEMINI AI for natural conversations
🔹 Auto-reply, moderation, welcome messages & more
🔹 Bengali, English & other languages supported
🔹 24/7 active — no downtime!

👑 Owner: EM MAHIM
📌 Invite now and make your server smarter!

**COMMANDS:**
!all - Show all commands
!editor <prompt> - AI Image Generator
!set - Set active channel
!guide - User help guide
💬 **Chat AI auto reply** - Just text in active channel for AI responses!

🕐 Bot active since: {timestamp}
"""

        @bot.event
        async def on_ready():
            """Event triggered when bot is ready"""
            logger.info(f'{bot.user} has logged in to Discord!')
            logger.info(f'Bot is in {len(bot.guilds)} guilds')

            # Set bot activity
            activity = discord.Activity(type=discord.ActivityType.watching,
                                        name="for AI conversations")
            await bot.change_presence(activity=activity)

        @bot.event
        async def on_member_join(member):
            """Send welcome message to new members"""
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
                welcome_msg = WELCOME_MESSAGE.format(timestamp=current_time)
                await member.send(welcome_msg)
                logger.info(f"Sent welcome message to {member.name}")
            except discord.Forbidden:
                logger.warning(
                    f"Could not send DM to {member.name} - DMs disabled")
            except Exception as e:
                logger.error(
                    f"Error sending welcome message to {member.name}: {e}")

        @bot.command(name='set')
        async def set_active_channel(ctx):
            """Set the active channel for AI responses (Admin only)"""
            nonlocal active_channel_id

            if ctx.author.id != ADMIN_ID:
                await ctx.send("❌ Only admin can set active channel.")
                return

            active_channel_id = ctx.channel.id
            await ctx.send(f"✅ Bot is now active in: #{ctx.channel.name}")
            logger.info(
                f"Active channel set to #{ctx.channel.name} by {ctx.author.name}"
            )

        @bot.command(name='editor')
        async def editor_command(ctx, *, prompt=None):
            """AI Image generation command (Admin only)"""
            if ctx.author.id != ADMIN_ID:
                await ctx.send("❌ You are not allowed to use this command.")
                return

            if not prompt:
                await ctx.send(
                    "🖼️ **AI Image Generator**\nUsage: `!editor <description>`\n\nExample: `!editor a beautiful sunset over mountains`"
                )
                return

            try:
                await ctx.send("🎨 Generating image... This may take a moment.")

                # Generate unique filename
                import uuid
                filename = f"generated_image_{uuid.uuid4().hex[:8]}.png"

                # Generate image using Gemini
                from google.genai import types
                response = gemini_client.client.models.generate_content(
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']))

                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            # Save image
                            with open(filename, 'wb') as f:
                                f.write(part.inline_data.data)

                            # Send image to Discord
                            with open(filename, 'rb') as f:
                                discord_file = discord.File(f, filename)
                                await ctx.send(
                                    f"🎨 **Generated Image:** {prompt}",
                                    file=discord_file)

                            # Clean up
                            os.remove(filename)
                            break
                    else:
                        await ctx.send(
                            "⚠️ Could not generate image. Please try a different prompt."
                        )
                else:
                    await ctx.send(
                        "⚠️ Image generation failed. Please try again.")

                logger.info(
                    f"Image generated for prompt: {prompt} by {ctx.author.name}"
                )

            except Exception as e:
                await ctx.send(
                    "❌ Image generation failed. Please try again later.")
                logger.error(f"Image generation error: {e}")

        @bot.command(name='all')
        async def list_commands(ctx):
            """List all available commands (Admin only)"""
            if ctx.author.id != ADMIN_ID:
                await ctx.send("❌ You are not allowed to use this command.")
                return

            commands_list = f"""📜 **Available Commands:**
            
**Admin Commands:**
• `!set` - Set active channel for AI responses
• `!editor <prompt>` - AI Image Generator (generate images from text)
• `!all` - Show this command list
• `!status` - Show bot status
• `!deactivate` - Deactivate AI responses
• `!info` - Bot information and features

**User Commands:**
• `!guide` - Show user guide for regular users
• Just type a message in the active channel for AI reply!
• Bot supports multiple languages including English and Bengali

**Current Status:**
• Active Channel: {f"<#{active_channel_id}>" if active_channel_id else "None"}
• AI Model: Gemini 2.5 Flash
• Image Generation: Gemini 2.0 Flash (Preview)"""

            await ctx.send(commands_list)
            logger.info(f"Commands list requested by {ctx.author.name}")

        @bot.command(name='status')
        async def bot_status(ctx):
            """Show bot status (Admin only)"""
            if ctx.author.id != ADMIN_ID:
                await ctx.send("❌ You are not allowed to use this command.")
                return

            guild_count = len(bot.guilds)
            user_count = sum(guild.member_count for guild in bot.guilds)

            status_embed = discord.Embed(title="🤖 Bot Status", color=0x00ff00)
            status_embed.add_field(name="Servers",
                                   value=guild_count,
                                   inline=True)
            status_embed.add_field(name="Users", value=user_count, inline=True)
            status_embed.add_field(name="Active Channel",
                                   value=f"<#{active_channel_id}>"
                                   if active_channel_id else "None",
                                   inline=True)
            status_embed.add_field(name="AI Model",
                                   value="Gemini 2.5 Flash",
                                   inline=True)
            status_embed.add_field(name="Latency",
                                   value=f"{round(bot.latency * 1000)}ms",
                                   inline=True)

            await ctx.send(embed=status_embed)
            logger.info(f"Status command used by {ctx.author.name}")

        @bot.command(name='deactivate')
        async def deactivate_bot(ctx):
            """Deactivate AI responses (Admin only)"""
            nonlocal active_channel_id

            if ctx.author.id != ADMIN_ID:
                await ctx.send("❌ You are not allowed to use this command.")
                return

            active_channel_id = None
            await ctx.send("✅ AI responses have been deactivated.")
            logger.info(f"Bot deactivated by {ctx.author.name}")

        @bot.command(name='info')
        async def bot_info(ctx):
            """Show detailed bot information (Admin only)"""
            if ctx.author.id != ADMIN_ID:
                await ctx.send("❌ You are not allowed to use this command.")
                return

            info_embed = discord.Embed(
                title="💠 MAHI OFFICIAL BOT",
                description="Advanced AI-powered Discord chatbot",
                color=0x00ff00)
            info_embed.add_field(
                name="🤖 AI Features",
                value=
                "• Multi-language conversations\n• Context-aware responses\n• Image generation\n• Content moderation",
                inline=False)
            info_embed.add_field(
                name="🛠️ Technical Details",
                value=
                f"• Model: Gemini 2.5 Flash\n• Image Gen: Gemini 2.0 Flash\n• Latency: {round(bot.latency * 1000)}ms\n• Uptime: Online",
                inline=False)
            info_embed.add_field(
                name="📊 Server Stats",
                value=
                f"• Servers: {len(bot.guilds)}\n• Users: {sum(guild.member_count for guild in bot.guilds)}\n• Active Channel: {'Set' if active_channel_id else 'None'}",
                inline=False)
            info_embed.set_footer(
                text="Owner: EM MAHIM | Powered by Google Gemini AI")

            await ctx.send(embed=info_embed)
            logger.info(f"Info command used by {ctx.author.name}")

        @bot.command(name='guide')
        async def guide_command(ctx):
            """Show help guide for regular users"""
            help_embed = discord.Embed(
                title="💠 MAHI OFFICIAL BOT - User Guide",
                description="How to use the AI chatbot",
                color=0x0099ff)
            help_embed.add_field(
                name="💬 Chat with AI",
                value=
                "Just type your message in the active channel and I'll respond with AI-powered answers!",
                inline=False)
            help_embed.add_field(
                name="🌍 Languages Supported",
                value="• English\n• Bengali (বাংলা)\n• And many more!",
                inline=False)
            help_embed.add_field(
                name="✨ Features",
                value=
                "• Natural conversations\n• Context awareness\n• Multi-language support\n• Instant responses",
                inline=False)
            help_embed.set_footer(
                text="For admin commands, contact the server owner")

            await ctx.send(embed=help_embed)

        @bot.event
        async def on_message(message):
            """Handle incoming messages and generate AI responses"""
            nonlocal active_channel_id

            # Ignore bot messages
            if message.author.bot:
                return

            # Process commands first
            await bot.process_commands(message)

            # Only respond in active channel and to non-command messages
            if (active_channel_id and message.channel.id == active_channel_id
                    and not message.content.startswith("!")):

                # Show typing indicator
                async with message.channel.typing():
                    try:
                        # Generate AI response
                        response = await gemini_client.generate_response(
                            message.content)

                        # Split long messages if needed
                        if len(response) > 2000:
                            chunks = [
                                response[i:i + 2000]
                                for i in range(0, len(response), 2000)
                            ]
                            for chunk in chunks:
                                await message.channel.send(chunk)
                        else:
                            await message.channel.send(response)

                        logger.info(
                            f"AI response sent to {message.author.name} in #{message.channel.name}"
                        )

                    except Exception as e:
                        error_message = "⚠️ Sorry, I'm having trouble generating a response right now. Please try again later."
                        await message.channel.send(error_message)
                        logger.error(f"Error generating AI response: {e}")

        @bot.event
        async def on_command_error(ctx, error):
            """Handle command errors"""
            if isinstance(error, commands.CommandNotFound):
                return  # Ignore unknown commands
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("❌ Missing required arguments for this command."
                               )
            elif isinstance(error, commands.BadArgument):
                await ctx.send("❌ Invalid arguments provided.")
            else:
                await ctx.send(
                    "❌ An error occurred while executing the command.")
                logger.error(f"Command error: {error}")

        # Run the bot
        bot.run(DISCORD_TOKEN)

    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        print(
            "❌ Error: Could not import required modules. Make sure all dependencies are installed."
        )
        sys.exit(1)

    except discord.LoginFailure:
        logger.error("Invalid Discord token provided")
        print("❌ Error: Invalid Discord token provided")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
        print("\n👋 Bot shutdown gracefully")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
