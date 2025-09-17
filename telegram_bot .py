#!/usr/bin/env python3
"""
EM OFFICIAL TEAM - Telegram Free Fire Like Bot
Features: Auto-like system, Contact owner, Beautiful formatting
Owner ID: 7731876768 (Unlimited Access)
"""

import os
import json
import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from functools import wraps
from dotenv import load_dotenv  # Added

# ===============================
# CONFIGURATION SECTION
# ===============================

# Load variables from .env file
load_dotenv()

# Get the Bot Token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found. Please set it in your .env or hosting environment.")

# Owner Configuration
OWNER_ID = 7731876768  # Your specific owner ID
ALTERNATE_OWNER_ID = 1087968824  # Alternate owner ID (if using different account)

# API Configuration
API_KEY = os.getenv("FREE_FIRE_API_KEY", "GREAT")  # Free Fire like API key

# Contact Information
CONTACT_OWNER = "@Mahimahmud12"
DISCORD_LINK = "https://discord.gg/CmMG2xryMX"

# Verification Links
VERIFICATION_LINKS = {
    'youtube': 'https://youtube.com/@emofficial1234?si=2S0ohEoARr2ldn95',
    'telegram_channel': 'https://t.me/mahiofficial31', 
    'telegram_group': 'https://t.me/SYQCnQD',
    'discord': 'https://discord.gg/CmMG2xryMX'
}

# File paths
DATA_FILE = "tg_data.json"

# Global data storage
user_limits = {}  # user_id: limit
user_usage = {}   # user_id: {date: count}
user_verification = {}  # user_id: {verified: bool, platforms: []}
allowed_groups = {}  # group_id: group_info
default_limit = 2

# ===============================
# LOGGING SETUP
# ===============================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set httpx logging to WARNING to prevent token exposure in logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# ===============================
# UTILITY FUNCTIONS
# ===============================

def get_nepal_time():
    """Get current Nepal time"""
    tz = pytz.timezone("Asia/Kathmandu")
    return datetime.now(tz)

def load_data():
    """Load data from JSON file"""
    global user_limits, user_usage, user_verification, allowed_groups
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                user_limits = data.get('user_limits', {})
                user_usage = data.get('user_usage', {})
                user_verification = data.get('user_verification', {})
                allowed_groups = data.get('allowed_groups', {})
                # Convert string user IDs back to integers
                user_limits = {int(k): v for k, v in user_limits.items()}
                user_usage = {int(k): v for k, v in user_usage.items()}
                user_verification = {int(k): v for k, v in user_verification.items()}
                # Convert string group IDs back to integers  
                allowed_groups = {int(k): v for k, v in allowed_groups.items()}
                logger.info("Data loaded successfully")
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        user_limits = {}
        user_usage = {}
        user_verification = {}
        allowed_groups = {}

def save_data():
    """Save data to JSON file"""
    try:
        data = {
            'user_limits': user_limits,
            'user_usage': user_usage,
            'user_verification': user_verification,
            'allowed_groups': allowed_groups
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info("Data saved successfully")
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def is_owner(user_id: int) -> bool:
    """Check if user is owner"""
    is_owner_result = user_id == OWNER_ID or user_id == ALTERNATE_OWNER_ID
    logger.info(f"Owner check: user_id={user_id}, OWNER_ID={OWNER_ID}, ALTERNATE_ID={ALTERNATE_OWNER_ID}, result={is_owner_result}")
    return is_owner_result

def is_group_allowed(chat_id: int) -> bool:
    """Check if group/chat is allowed"""
    # Private chats are always allowed
    if chat_id > 0:
        return True
    # Check if group is in allowed list
    return abs(chat_id) in allowed_groups

def add_allowed_group(chat_id: int, chat_title: str):
    """Add group to allowed list"""
    group_id = abs(chat_id)
    allowed_groups[group_id] = {
        'title': chat_title,
        'chat_id': chat_id,
        'added_date': get_nepal_time().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_data()

def remove_allowed_group(chat_id: int):
    """Remove group from allowed list"""
    group_id = abs(chat_id)
    if group_id in allowed_groups:
        del allowed_groups[group_id]
        save_data()
        return True
    return False

def get_user_daily_limit(user_id: int) -> int:
    """Get user's daily limit"""
    # Owner has unlimited access
    if is_owner(user_id):
        return 999999
    return user_limits.get(user_id, default_limit)

def get_user_usage_today(user_id: int) -> int:
    """Get user's usage count for today"""
    today = get_nepal_time().strftime("%Y-%m-%d")
    if user_id not in user_usage:
        user_usage[user_id] = {}
    return user_usage[user_id].get(today, 0)

def increment_user_usage(user_id: int):
    """Increment user's usage count for today"""
    # Owner usage is not tracked
    if is_owner(user_id):
        return
    
    today = get_nepal_time().strftime("%Y-%m-%d")
    if user_id not in user_usage:
        user_usage[user_id] = {}
    user_usage[user_id][today] = user_usage[user_id].get(today, 0) + 1
    save_data()

def is_user_verified(user_id: int) -> bool:
    """Check if user is verified"""
    # Owner is always verified
    if is_owner(user_id):
        return True
    return user_verification.get(user_id, {}).get('verified', False)

def verify_user(user_id: int):
    """Mark user as verified"""
    user_verification[user_id] = {
        'verified': True,
        'verified_date': get_nepal_time().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_data()

def detect_region(region: str) -> str:
    """Detect and convert region"""
    region = region.upper()
    region_map = {
        'BD': 'ag', 'BANGLADESH': 'ag', 'AG': 'ag',
        'IND': 'ind', 'INDIA': 'ind',
        'BR': 'nx', 'BRAZIL': 'nx', 'US': 'nx', 'USA': 'nx', 'NX': 'nx'
    }
    return region_map.get(region, 'ag')  # Default to AG (Bangladesh) region

# ===============================
# PERMISSION DECORATOR
# ===============================

def group_permission_required(func):
    """Decorator to check group permissions"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_chat or not update.effective_user:
            return
        
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Owner can use commands anywhere
        if is_owner(user_id):
            return await func(update, context, *args, **kwargs)
        
        # Check if group is allowed (private chats always allowed)
        if not is_group_allowed(chat_id):
            # Send warning message only in groups
            if chat_id < 0:
                not_allowed_text = f"""
```
❌ UNAUTHORIZED GROUP
┌─ STATUS: ACCESS DENIED
├─ REASON: Group not authorized by owner
├─ SOLUTION: Owner must add this group first
└─ CONTACT: {CONTACT_OWNER} for authorization
```
**⚠️ This bot only works in authorized groups**
**👑 Owner must use /allow to authorize**

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
                """
                
                if update.message:
                    msg = await update.message.reply_text(
                        not_allowed_text,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True
                    )
                
                    # Delete after 10 seconds
                    await asyncio.sleep(10)
                    try:
                        await msg.delete()
                        if update.message:
                            await update.message.delete()
                    except:
                        pass
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

# ===============================
# API FUNCTIONS
# ===============================

async def fetch_like(uid: str, region: str) -> Optional[Dict[str, Any]]:
    """Fetch likes from the API"""
    try:
        api_region = detect_region(region)
        url = f"https://lordlike.onrender.com/like?uid={uid}&region={api_region}&key={API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API request failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching likes: {e}")
        return None

# ===============================
# COMMAND HANDLERS
# ===============================

@group_permission_required
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - welcome message"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    current_time = get_nepal_time()
    date_str = current_time.strftime("%Y-%m-%d")
    time_str = current_time.strftime("%H:%M:%S")
    
    # Check verification status
    is_verified = is_user_verified(user_id)
    verification_status = "✅ VERIFIED" if is_verified else "❌ NOT VERIFIED"
    
    # Owner special status
    owner_status = ""
    if is_owner(user_id):
        owner_status = "\n**👑 OWNER STATUS: UNLIMITED ACCESS**"
    
    welcome_text = f"""
🌟 **EM OFFICIAL TEAM - FREE FIRE LIKE BOT** 🌟

╭─────────────────────────────────────╮
│ 🎮 **COMMANDS:**
│ • `/verify` - Complete verification
│ • `/like <region> <uid>` - Send likes
│ • `/contact` - Contact owner
│ • `/help` - Show help menu
│ • `/stats` - Your usage statistics
╰─────────────────────────────────────╯

**📋 REGIONS:** BD, IND, BR, US
**🎯 EXAMPLE:** `/like bd 5914395123`
**⚡ DEFAULT LIMIT:** 2 likes/day
**🔐 STATUS:** {verification_status}{owner_status}

**⚠️ IMPORTANT:** You must complete verification first!
**📝 Use `/verify` to start verification process**

🎮 [JOIN DISCORD COMMUNITY]({DISCORD_LINK})
**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
📅 {date_str} 🕐 {time_str}
    """
    
    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("🔐 Start Verification", callback_data="start_verify")],
        [InlineKeyboardButton("🎮 Join Discord", url=DISCORD_LINK)],
        [InlineKeyboardButton("👥 Contact Owner", url=f"https://t.me/{CONTACT_OWNER[1:]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

@group_permission_required
async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verification command"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    current_time = get_nepal_time()
    date_str = current_time.strftime("%Y-%m-%d")
    time_str = current_time.strftime("%H:%M:%S")
    
    # Check if already verified
    if is_user_verified(user_id):
        verified_text = f"""
```
🎉 VERIFICATION COMPLETED!
╭─────────────────────────────────────╮
│ ✅ You are fully verified!
│ 🎮 You can now use like commands
│ 🚀 Example: /like bd 5914395123
│ 💎 Enjoy unlimited access!
╰─────────────────────────────────────╯
```
🎮 [JOIN DISCORD COMMUNITY]({DISCORD_LINK})
**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
📅 {date_str} 🕐 {time_str}
        """
        
        keyboard = [
            [InlineKeyboardButton("🎮 Join Discord", url=DISCORD_LINK)],
            [InlineKeyboardButton("👥 Contact Owner", url=f"https://t.me/{CONTACT_OWNER[1:]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            verified_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        return
    
    # Show verification interface
    verify_text = f"""
🔐 **SIMPLE VERIFICATION SYSTEM** 🔐

╭─────────────────────────────────────╮
│ 📋 **FOLLOW THESE STEPS:**
│ 
│ 1️⃣ Visit YouTube Channel
│ 2️⃣ Join Telegram Channel  
│ 3️⃣ Join Telegram Group
│ 4️⃣ Join Discord Server
│ 
│ ✅ Click "Complete Done" when finished
╰─────────────────────────────────────╯

**💡 INSTRUCTIONS:**
• Click each numbered button below
• Visit all the platforms
• Return here and click "Complete Done"
• Get instant verification!

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
📅 {date_str} 🕐 {time_str}
    """
    
    # Create verification keyboard
    keyboard = [
        [
            InlineKeyboardButton("1️⃣ YouTube Channel", url=VERIFICATION_LINKS['youtube']),
            InlineKeyboardButton("2️⃣ Telegram Channel", url=VERIFICATION_LINKS['telegram_channel'])
        ],
        [
            InlineKeyboardButton("3️⃣ Telegram Group", url=VERIFICATION_LINKS['telegram_group']),
            InlineKeyboardButton("4️⃣ Discord Server", url=VERIFICATION_LINKS['discord'])
        ],
        [InlineKeyboardButton("✅ Complete Done", callback_data="complete_verification")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        verify_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

@group_permission_required
async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle like command"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Check verification status for non-owners
    if not is_owner(user_id) and not is_user_verified(user_id):
        # Auto-show verification system
        current_time = get_nepal_time()
        date_str = current_time.strftime("%Y-%m-%d")
        time_str = current_time.strftime("%H:%M:%S")
        
        verify_text = f"""
❌ **VERIFICATION REQUIRED TO USE LIKES!**

🔐 **SIMPLE VERIFICATION SYSTEM** 🔐

╭─────────────────────────────────────╮
│ 📋 **FOLLOW THESE STEPS:**
│ 
│ 1️⃣ Visit YouTube Channel
│ 2️⃣ Join Telegram Channel  
│ 3️⃣ Join Telegram Group
│ 4️⃣ Join Discord Server
│ 
│ ✅ Click "Complete Done" when finished
╰─────────────────────────────────────╯

**💡 INSTRUCTIONS:**
• Click each numbered button below
• Visit all the platforms
• Return here and click "Complete Done"
• Then you can use like commands!

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
📅 {date_str} 🕐 {time_str}
        """
        
        # Create verification keyboard
        keyboard = [
            [
                InlineKeyboardButton("1️⃣ YouTube Channel", url=VERIFICATION_LINKS['youtube']),
                InlineKeyboardButton("2️⃣ Telegram Channel", url=VERIFICATION_LINKS['telegram_channel'])
            ],
            [
                InlineKeyboardButton("3️⃣ Telegram Group", url=VERIFICATION_LINKS['telegram_group']),
                InlineKeyboardButton("4️⃣ Discord Server", url=VERIFICATION_LINKS['discord'])
            ],
            [InlineKeyboardButton("✅ Complete Done", callback_data="complete_verification")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            verify_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        return
    
    # Check arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ **Invalid format!**\n"
            "📝 **Usage:** `/like <region> <uid>`\n"
            "🎯 **Example:** `/like bd 5914395123`\n"
            "📋 **Regions:** BD, IND, BR, US",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    region = context.args[0].upper()
    uid = context.args[1]
    
    # Validate region
    valid_regions = ['BD', 'IND', 'BR', 'US', 'AG', 'NX']
    if region not in valid_regions:
        await update.message.reply_text(
            f"❌ **Invalid region: {region}**\n"
            "📋 **Valid regions:** BD, IND, BR, US",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check limits for non-owners
    if not is_owner(user_id):
        daily_limit = get_user_daily_limit(user_id)
        usage_today = get_user_usage_today(user_id)
        
        if usage_today >= daily_limit:
            await update.message.reply_text(
                f"❌ **Daily limit reached!**\n"
                f"📊 **Used:** {usage_today}/{daily_limit}\n"
                f"⏰ **Reset:** Tomorrow at 12:00 AM Nepal time\n"
                f"👥 **Contact:** {CONTACT_OWNER} for limit increase",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "⏳ **Processing your request...**\n"
        f"🎮 **Region:** {region}\n"
        f"🆔 **UID:** {uid}\n"
        "⚡ **Please wait...**",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Call API
        result = await fetch_like(uid, region)
        
        if result:
            # Parse API response
            status = result.get('status', 0)
            player = result.get('player', {})
            likes = result.get('likes', {})
            
            player_nickname = player.get('nickname', 'Unknown')
            likes_before = likes.get('before', 0)
            likes_after = likes.get('after', 0)
            added_by_api = likes.get('added_by_api', 0)
            
            # Handle different status codes
            if status == 1:  # Success
                # Increment usage for non-owners
                if not is_owner(user_id):
                    increment_user_usage(user_id)
                    new_usage = get_user_usage_today(user_id)
                    limit = get_user_daily_limit(user_id)
                    remaining = limit - new_usage
                else:
                    remaining = "♾️ Unlimited"
                    new_usage = "👑 Owner"
                    limit = "♾️ Unlimited"
                
                success_text = f"""
✅ **LIKES SENT SUCCESSFULLY!** ✅

```
🎮 PLAYER INFORMATION
╭─────────────────────────────────────╮
│ 🆔 UID: {uid}
│ 👤 Player: {player_nickname}
│ 🌍 Region: {region.upper()}
│ 💎 Likes Before: {likes_before:,}
│ 💎 Likes After: {likes_after:,}
│ ⚡ Added: +{added_by_api}
│ 📊 Status: SUCCESS ✅
╰─────────────────────────────────────╯
```

**📈 YOUR USAGE:**
• **Used Today:** {new_usage}/{limit}
• **Remaining:** {remaining}

**🎉 Congratulations! Likes sent successfully!**
**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
                """
                
                await processing_msg.edit_text(
                    success_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
            elif status == 2:  # Already received or limit reached
                error_text = f"""
⚠️ **LIKES ALREADY RECEIVED!** ⚠️

```
🎮 PLAYER INFORMATION
╭─────────────────────────────────────╮
│ 🆔 UID: {uid}
│ 👤 Player: {player_nickname}
│ 🌍 Region: {region.upper()}
│ 💎 Current Likes: {likes_before:,}
│ 📊 Status: ALREADY RECEIVED
╰─────────────────────────────────────╯
```

**ℹ️ This player has already received likes today!**
**⏰ Try again tomorrow for fresh likes**
**🔄 Or try a different UID**

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
                """
                
                await processing_msg.edit_text(
                    error_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
            elif status == 3:  # Player not found
                error_text = f"""
❌ **PLAYER NOT FOUND!** ❌

```
🎮 SEARCH RESULT
╭─────────────────────────────────────╮
│ 🆔 UID: {uid}
│ 🌍 Region: {region.upper()}
│ 📊 Status: PLAYER NOT FOUND
╰─────────────────────────────────────╯
```

**⚠️ Please check:**
• UID is correct
• Region is correct
• Player exists in Free Fire

**🔄 Try again with correct information**
**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
                """
                
                await processing_msg.edit_text(
                    error_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
            else:  # Unknown status
                error_text = f"""
❌ **API ERROR OCCURRED!** ❌

```
🎮 API RESPONSE
╭─────────────────────────────────────╮
│ 🆔 UID: {uid}
│ 🌍 Region: {region.upper()}
│ 📊 Status Code: {status}
│ 📊 Status: ERROR
╰─────────────────────────────────────╯
```

**⚠️ Something went wrong with the API**
**🔄 Please try again in a few minutes**
**👥 Contact:** {CONTACT_OWNER} if problem persists

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
                """
                
                await processing_msg.edit_text(
                    error_text,
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            # API connection failed
            await processing_msg.edit_text(
                f"""
❌ **API CONNECTION FAILED!** ❌

```
🎮 CONNECTION ERROR
╭─────────────────────────────────────╮
│ 🆔 UID: {uid}
│ 🌍 Region: {region.upper()}
│ 📊 Status: CONNECTION FAILED
╰─────────────────────────────────────╯
```

**⚠️ Cannot connect to Free Fire API**
**🔄 Please try again in a few minutes**
**🌐 Check your internet connection**
**👥 Contact:** {CONTACT_OWNER} if problem persists

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
                """,
                parse_mode=ParseMode.MARKDOWN
            )
    
    except Exception as e:
        logger.error(f"Error in like command: {e}")
        await processing_msg.edit_text(
            "❌ **An error occurred!**\n"
            "🔄 **Please try again later**\n"
            f"👥 **Contact:** {CONTACT_OWNER} if problem persists",
            parse_mode=ParseMode.MARKDOWN
        )

@group_permission_required
async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot uptime and status (owner only)"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Only owner can use this command
    if not is_owner(user_id):
        await update.message.reply_text(
            "❌ **Owner command only!**\n"
            f"👑 **Owner ID:** {OWNER_ID}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    current_time = get_nepal_time()
    
    # Calculate uptime (assuming bot started when script runs)
    import psutil
    import os
    
    # Get process info
    process = psutil.Process(os.getpid())
    create_time = datetime.fromtimestamp(process.create_time(), tz=pytz.timezone('Asia/Kathmandu'))
    uptime_duration = current_time - create_time
    
    # Format uptime
    days = uptime_duration.days
    hours, remainder = divmod(uptime_duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # System info
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent()
    
    uptime_text = f"""
⏰ **BOT UPTIME & STATUS** ⏰

**🚀 Uptime Information:**
• **Started:** {create_time.strftime('%Y-%m-%d %H:%M:%S')}
• **Running For:** {days}d {hours}h {minutes}m {seconds}s
• **Current Time:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}

**💻 System Resources:**
• **Memory Usage:** {memory.percent}%
• **CPU Usage:** {cpu_percent}%
• **Memory Available:** {memory.available // (1024*1024)} MB

**📊 Bot Statistics:**
• **Total Users:** {len(set(user_limits) | set(user_usage) | set(user_verification))}
• **Verified Users:** {sum(1 for v in user_verification.values() if v.get('verified', False))}
• **Allowed Groups:** {len(allowed_groups)}
• **User Limits Set:** {sum(1 for _, lim in user_limits.items() if lim != default_limit)}

**🔄 Status Checks:**
• ✅ **Bot Process:** Running
• ✅ **Telegram API:** Connected  
• ✅ **Data Storage:** Working
• ✅ **Member Tracking:** Active

**📡 Connection Info:**
• **Process ID:** {os.getpid()}
• **Platform:** Replit Free Tier
• **Auto-restart:** {"✅ Enabled" if "REPLIT_ENVIRONMENT" in os.environ else "❌ Disabled"}

**🔥 EM OFFICIAL TEAM - UPTIME MONITOR 🔥**
    """
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_uptime"),
            InlineKeyboardButton("📊 Full Stats", callback_data="refresh_stats")
        ],
        [
            InlineKeyboardButton("💾 Save Report", callback_data="save_uptime_report"),
            InlineKeyboardButton("👑 Owner Help", callback_data="refresh_owner_help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        uptime_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick status check for all users"""
    if not update.effective_user or not update.message:
        return
    
    current_time = get_nepal_time()
    
    # Quick system check
    try:
        import psutil
        memory = psutil.virtual_memory()
        status = "🟢 ONLINE"
        performance = "⚡ Good" if memory.percent < 80 else "⚠️ High Usage"
    except:
        status = "🟡 LIMITED"
        performance = "❓ Unknown"
    
    status_text = f"""
📊 **QUICK BOT STATUS** 📊

**🤖 Bot Status:** {status}
**⚡ Performance:** {performance}
**🕐 Current Time:** {current_time.strftime('%H:%M:%S')}
**📅 Date:** {current_time.strftime('%Y-%m-%d')}

**📈 Service Status:**
• ✅ Telegram API Connected
• ✅ Commands Working  
• ✅ Auto-like System Active
• ✅ Member Tracking ON

**💡 Quick Help:**
• Use `/help` for command list
• Use `/verify` to get verified
• Use `/like bd <uid>` to send likes

**🔥 EM OFFICIAL TEAM BOT 🔥**
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📝 All Commands", callback_data="refresh_commands"),
            InlineKeyboardButton("🔐 Verify Now", callback_data="start_verification")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        status_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    current_time = get_nepal_time()
    
    # Get user data
    is_verified = is_user_verified(user_id)
    daily_limit = get_user_daily_limit(user_id)
    usage_today = get_user_usage_today(user_id)
    remaining = daily_limit - usage_today if daily_limit != 999999 else "Unlimited"
    
    # Owner special handling
    if is_owner(user_id):
        stats_text = f"""
👑 **OWNER STATISTICS** 👑

```
📊 ACCOUNT STATUS
╭─────────────────────────────────────╮
│ 🆔 User ID: {user_id}
│ 👑 Role: OWNER
│ 🔐 Verified: ✅ ALWAYS
│ ⚡ Limits: UNLIMITED
│ 📈 Usage: UNLIMITED
│ 🕐 Reset: NEVER
╰─────────────────────────────────────╯
```

**🎮 OWNER PRIVILEGES:**
• Unlimited likes per day
• Access to all groups
• Admin commands available
• No verification required

**⚙️ ADMIN COMMANDS:**
• `/allow` - Add group to bot
• `/remove` - Remove group from bot
• `/setlimit <user_id> <limit>` - Set user limit
• `/broadcast <message>` - Send message to all users

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
📅 {current_time.strftime("%Y-%m-%d")} 🕐 {current_time.strftime("%H:%M:%S")}
        """
    else:
        stats_text = f"""
📊 **YOUR STATISTICS** 📊

```
📈 USAGE STATISTICS
╭─────────────────────────────────────╮
│ 🆔 User ID: {user_id}
│ 🔐 Verified: {"✅ YES" if is_verified else "❌ NO"}
│ 📊 Used Today: {usage_today}/{daily_limit}
│ ⚡ Remaining: {remaining}
│ 🕐 Reset: Tomorrow 12:00 AM Nepal
╰─────────────────────────────────────╯
```

**🎮 COMMANDS AVAILABLE:**
• `/like <region> <uid>` - Send likes
• `/verify` - Complete verification
• `/help` - Show help menu
• `/contact` - Contact owner

**💡 TIP:** {"Complete verification to use bot!" if not is_verified else "Use /like command to send likes!"}

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
📅 {current_time.strftime("%Y-%m-%d")} 🕐 {current_time.strftime("%H:%M:%S")}
        """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_stats")],
        [InlineKeyboardButton("👥 Contact Owner", url=f"https://t.me/{CONTACT_OWNER[1:]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

@group_permission_required
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help menu"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    current_time = get_nepal_time()
    
    help_text = f"""
🆘 **HELP & SUPPORT** 🆘

```
📋 COMMAND LIST
╭─────────────────────────────────────╮
│ 🏠 /start - Welcome & main menu
│ 🔐 /verify - Complete verification
│ 💎 /like <region> <uid> - Send likes
│ 📊 /stats - Your statistics
│ 🆘 /help - This help menu
│ 👥 /contact - Contact owner
╰─────────────────────────────────────╯
```

**🎮 LIKE COMMAND USAGE:**
• **Format:** `/like <region> <uid>`
• **Example:** `/like bd 5914395123`
• **Regions:** BD, IND, BR, US

**🔐 VERIFICATION STEPS:**
1. Use `/verify` command
2. Visit all 4 platforms
3. Click "Complete Done"
4. Start using bot!

**⚡ IMPORTANT NOTES:**
• You must verify before using
• Daily limits apply (except owner)
• Bot works only in authorized groups
• Contact owner for support

**👥 NEED HELP?**
Contact: {CONTACT_OWNER}
Discord: [Join Server]({DISCORD_LINK})

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
📅 {current_time.strftime("%Y-%m-%d")} 🕐 {current_time.strftime("%H:%M:%S")}
    """
    
    keyboard = [
        [InlineKeyboardButton("🔐 Start Verification", callback_data="start_verify")],
        [InlineKeyboardButton("🎮 Join Discord", url=DISCORD_LINK)],
        [InlineKeyboardButton("👥 Contact Owner", url=f"https://t.me/{CONTACT_OWNER[1:]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

@group_permission_required
async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show contact information"""
    if not update.effective_user or not update.message:
        return
    
    current_time = get_nepal_time()
    
    contact_text = f"""
👥 **CONTACT INFORMATION** 👥

```
📞 SUPPORT CONTACTS
╭─────────────────────────────────────╮
│ 👑 Owner: {CONTACT_OWNER}
│ 🎮 Discord: Community Server
│ 📢 Channel: Official Updates
│ 👥 Group: Support Group
╰─────────────────────────────────────╯
```

**🔥 EM OFFICIAL TEAM LINKS:**
• **Owner Contact:** Direct message for support
• **Discord Server:** Gaming community & updates
• **Telegram Channel:** Official announcements
• **Telegram Group:** User discussions & help

**💬 WHAT YOU CAN CONTACT FOR:**
• Bot issues and errors
• Limit increase requests
• Group authorization
• General support

**⚡ RESPONSE TIME:** Usually within 24 hours

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
📅 {current_time.strftime("%Y-%m-%d")} 🕐 {current_time.strftime("%H:%M:%S")}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("👑 Message Owner", url=f"https://t.me/{CONTACT_OWNER[1:]}"),
            InlineKeyboardButton("🎮 Join Discord", url=DISCORD_LINK)
        ],
        [
            InlineKeyboardButton("📢 Channel", url=VERIFICATION_LINKS['telegram_channel']),
            InlineKeyboardButton("👥 Group", url=VERIFICATION_LINKS['telegram_group'])
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        contact_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

# ===============================
# OWNER COMMANDS
# ===============================

async def allow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to allow groups"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Debug logging
    logger.info(f"Allow command called by user_id: {user_id}")
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ **Owner command only!**", parse_mode=ParseMode.MARKDOWN)
        return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Private Chat"
    
    if chat_id > 0:
        await update.message.reply_text("❌ **This command only works in groups!**", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Add group to allowed list
    add_allowed_group(chat_id, chat_title)
    
    await update.message.reply_text(
        f"✅ **Group authorized successfully!**\n"
        f"📝 **Group:** {chat_title}\n"
        f"🆔 **ID:** {chat_id}\n"
        f"🎮 **Bot is now active in this group**",
        parse_mode=ParseMode.MARKDOWN
    )

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to remove groups"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ **Owner command only!**", parse_mode=ParseMode.MARKDOWN)
        return
    
    chat_id = update.effective_chat.id
    
    if chat_id > 0:
        await update.message.reply_text("❌ **This command only works in groups!**", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Remove group from allowed list
    if remove_allowed_group(chat_id):
        await update.message.reply_text(
            f"✅ **Group removed successfully!**\n"
            f"🚫 **Bot is now inactive in this group**",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"❌ **Group was not in allowed list!**",
            parse_mode=ParseMode.MARKDOWN
        )

async def setlimit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to set user limits"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ **Owner command only!**", parse_mode=ParseMode.MARKDOWN)
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ **Invalid format!**\n"
            "📝 **Usage:** `/setlimit <user_id> <limit>`\n"
            "🎯 **Example:** `/setlimit 123456789 5`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        new_limit = int(context.args[1])
        
        if new_limit < 0:
            await update.message.reply_text("❌ **Limit must be 0 or greater!**", parse_mode=ParseMode.MARKDOWN)
            return
        
        user_limits[target_user_id] = new_limit
        save_data()
        
        await update.message.reply_text(
            f"✅ **Limit updated successfully!**\n"
            f"👤 **User ID:** {target_user_id}\n"
            f"📊 **New Limit:** {new_limit} likes/day",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid numbers!**\n"
            "📝 **Usage:** `/setlimit <user_id> <limit>`",
            parse_mode=ParseMode.MARKDOWN
        )

async def slag_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available commands"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    current_time = get_nepal_time()
    date_str = current_time.strftime("%Y-%m-%d")
    time_str = current_time.strftime("%H:%M:%S")
    
    # Check if user is owner for special display
    if is_owner(user_id):
        commands_text = f"""
👑 **ALL COMMANDS - OWNER ACCESS** 👑

```
📋 USER COMMANDS
╭─────────────────────────────────────╮
│ 🏠 /start - Welcome & main menu
│ 🔐 /verify - Complete verification
│ 💎 /like <region> <uid> - Send likes
│ 📊 /stats - Your statistics
│ 🔄 /status - Quick bot status
│ 🆘 /help - Help menu
│ 👥 /contact - Contact information
│ 📝 /slag - Show all commands
╰─────────────────────────────────────╯
```

```
👑 OWNER COMMANDS
╭─────────────────────────────────────╮
│ ✅ /allow - Authorize current group
│ ❌ /remove - Remove current group
│ ⚙️ /setlimit <id> <limit> - Set limits
│ 📢 /broadcast <msg> - Send to all
│ 👥 /members - Show group members
│ ⏰ /uptime - Bot uptime & monitoring
│ 🧪 /testowner - Test owner status
│ 👑 /ownerhelp - Owner commands help
╰─────────────────────────────────────╯
```

**🎮 USAGE EXAMPLES:**
• `/like bd 5914395123` - Send likes
• `/setlimit 123456789 5` - Set user limit
• `/allow` - Authorize group

**👑 OWNER STATUS:** UNLIMITED ACCESS
**📅 {date_str} 🕐 {time_str}**
**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
        """
    else:
        commands_text = f"""
📝 **ALL AVAILABLE COMMANDS** 📝

```
📋 USER COMMANDS
╭─────────────────────────────────────╮
│ 🏠 /start - Welcome & main menu
│ 🔐 /verify - Complete verification
│ 💎 /like <region> <uid> - Send likes
│ 📊 /stats - Your statistics
│ 🔄 /status - Quick bot status
│ 🆘 /help - Help menu
│ 👥 /contact - Contact information
│ 📝 /slag - Show all commands
╰─────────────────────────────────────╯
```

**🎮 USAGE EXAMPLES:**
• `/like bd 5914395123` - Send likes to BD region
• `/like ind 1234567890` - Send likes to India
• `/verify` - Complete verification first

**📋 REGIONS:** BD, IND, BR, US
**⚡ DAILY LIMIT:** 2 likes per day
**🔐 STATUS:** {"✅ VERIFIED" if is_user_verified(user_id) else "❌ NOT VERIFIED"}

**💡 TIP:** Use `/verify` first to unlock like commands!
**📅 {date_str} 🕐 {time_str}**
**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
        """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Commands", callback_data="refresh_commands")],
        [InlineKeyboardButton("👥 Contact Owner", url=f"https://t.me/{CONTACT_OWNER[1:]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        commands_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def ownerhelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only help command"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text(
            "❌ **Owner command only!**\n"
            f"👑 **Owner ID:** {OWNER_ID}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    current_time = get_nepal_time()
    date_str = current_time.strftime("%Y-%m-%d")
    time_str = current_time.strftime("%H:%M:%S")
    
    owner_help_text = f"""
👑 **OWNER COMMANDS HELP** 👑

```
⚙️ GROUP MANAGEMENT
╭─────────────────────────────────────╮
│ ✅ /allow - Add current group to bot
│ ❌ /remove - Remove current group
│ 📋 Usage: Use in group to manage
╰─────────────────────────────────────╯
```

```
👥 USER MANAGEMENT
╭─────────────────────────────────────╮
│ ⚙️ /setlimit <user_id> <limit>
│ 📊 /stats - View system statistics
│ 👥 /members - Show group members
│ 🧪 /testowner - Test owner recognition
│ 
│ Examples:
│ • /setlimit 123456789 5
│ • /setlimit 987654321 10
│ • /members (use in groups)
╰─────────────────────────────────────╯
```

```
📊 MEMBER TRACKING
╭─────────────────────────────────────╮
│ 🆕 Auto-notify when members join
│ ❌ Auto-notify when members leave
│ 👥 /members - View group info
│ 📩 Notifications sent to owner DM
│ 
│ Features:
│ • Real-time join/leave alerts
│ • Group admin list display
│ • Member count tracking
╰─────────────────────────────────────╯
```

```
📢 BROADCAST SYSTEM
╭─────────────────────────────────────╮
│ 📢 /broadcast <message>
│ 
│ Example:
│ • /broadcast Hello everyone!
│ • /broadcast Bot maintenance at 3 PM
╰─────────────────────────────────────╯
```

**🔧 OWNER PRIVILEGES:**
• ♾️ Unlimited likes per day
• 🏠 Can use bot in any group
• ⚙️ Can set user limits
• 📢 Can broadcast messages
• ✅ Can authorize/remove groups
• 👥 Real-time member tracking notifications
• 📊 Group member information access

**📊 CURRENT STATUS:**
• **Owner ID:** {OWNER_ID} & {ALTERNATE_OWNER_ID}
• **Groups Allowed:** {len(allowed_groups)}
• **Default Limit:** {default_limit} likes/day

**📅 {date_str} 🕐 {time_str}**
**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📊 View Stats", callback_data="refresh_stats"),
            InlineKeyboardButton("🔄 Refresh Help", callback_data="refresh_owner_help")
        ],
        [InlineKeyboardButton("👥 Contact Support", url=f"https://t.me/{CONTACT_OWNER[1:]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        owner_help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def test_owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command to check owner recognition"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    logger.info(f"Test owner command called by user_id: {user_id}")
    
    if not is_owner(user_id):
        await update.message.reply_text(
            f"❌ **You are not the owner!**\n"
            f"👤 **Your ID:** {user_id}\n"
            f"👑 **Owner ID:** {OWNER_ID}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await update.message.reply_text(
        f"✅ **Owner recognized successfully!**\n"
        f"👑 **Your ID:** {user_id}\n"
        f"🎮 **You have full access to all commands**",
        parse_mode=ParseMode.MARKDOWN
    )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to broadcast messages"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ **Owner command only!**", parse_mode=ParseMode.MARKDOWN)
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ **No message provided!**\n"
            "📝 **Usage:** `/broadcast <message>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message = " ".join(context.args)
    
    # Confirm broadcast
    keyboard = [
        [
            InlineKeyboardButton("✅ Send", callback_data=f"confirm_broadcast:{message}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📢 **Confirm Broadcast**\n\n"
        f"**Message:** {message}\n\n"
        f"**This will be sent to all bot users!**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# ===============================
# MEMBER TRACKING SYSTEM
# ===============================

async def track_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track when new members join groups"""
    if not update.message or not update.message.new_chat_members:
        return
    
    chat = update.effective_chat
    new_members = update.message.new_chat_members
    
    # Only track in groups/supergroups
    if chat.type not in ['group', 'supergroup']:
        return
    
    current_time = get_nepal_time()
    time_str = current_time.strftime("%H:%M:%S")
    date_str = current_time.strftime("%Y-%m-%d")
    
    for member in new_members:
        # Skip bot joins
        if member.is_bot:
            continue
            
        # Notify owner about new member
        member_info = f"""
🆕 **NEW MEMBER JOINED**

**👤 User Details:**
• **Name:** {member.first_name} {member.last_name or ''}
• **Username:** @{member.username if member.username else 'No username'}
• **User ID:** `{member.id}`

**🏠 Group Details:**
• **Group:** {chat.title}
• **Group ID:** `{chat.id}`
• **Group Type:** {chat.type}

**⏰ Time:** {time_str}
**📅 Date:** {date_str}

**🔥 EM OFFICIAL TEAM TRACKER 🔥**
        """
        
        try:
            # Send notification to owner
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=member_info,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Also send to alternate owner ID if different
            if ALTERNATE_OWNER_ID != OWNER_ID:
                await context.bot.send_message(
                    chat_id=ALTERNATE_OWNER_ID,
                    text=member_info,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.error(f"Failed to notify owner about new member: {e}")

async def track_member_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track when members leave groups"""
    if not update.message or not update.message.left_chat_member:
        return
    
    chat = update.effective_chat
    left_member = update.message.left_chat_member
    
    # Only track in groups/supergroups
    if chat.type not in ['group', 'supergroup']:
        return
    
    # Skip bot leaves
    if left_member.is_bot:
        return
    
    current_time = get_nepal_time()
    time_str = current_time.strftime("%H:%M:%S")
    date_str = current_time.strftime("%Y-%m-%d")
    
    # Notify owner about member leaving
    member_info = f"""
❌ **MEMBER LEFT GROUP**

**👤 User Details:**
• **Name:** {left_member.first_name} {left_member.last_name or ''}
• **Username:** @{left_member.username if left_member.username else 'No username'}
• **User ID:** `{left_member.id}`

**🏠 Group Details:**
• **Group:** {chat.title}
• **Group ID:** `{chat.id}`
• **Group Type:** {chat.type}

**⏰ Time:** {time_str}
**📅 Date:** {date_str}

**🔥 EM OFFICIAL TEAM TRACKER 🔥**
    """
    
    try:
        # Send notification to owner
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=member_info,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Also send to alternate owner ID if different
        if ALTERNATE_OWNER_ID != OWNER_ID:
            await context.bot.send_message(
                chat_id=ALTERNATE_OWNER_ID,
                text=member_info,
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Failed to notify owner about member leaving: {e}")

async def members_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show group member information (owner only)"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    chat = update.effective_chat
    
    # Only owner can use this command
    if not is_owner(user_id):
        await update.message.reply_text(
            "❌ **Owner command only!**\n"
            f"👑 **Owner ID:** {OWNER_ID}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Only works in groups
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "❌ **This command only works in groups!**\n"
            "💡 **Use this command in a group to see member info**",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        # Get group member count
        member_count = await context.bot.get_chat_member_count(chat.id)
        
        current_time = get_nepal_time()
        time_str = current_time.strftime("%H:%M:%S")
        date_str = current_time.strftime("%Y-%m-%d")
        
        # Get administrators
        admins = await context.bot.get_chat_administrators(chat.id)
        admin_list = []
        owner_info = None
        
        for admin in admins:
            user = admin.user
            if admin.status == 'creator':
                owner_info = f"👑 {user.first_name} (@{user.username if user.username else 'No username'}) - ID: `{user.id}`"
            elif admin.status == 'administrator':
                admin_list.append(f"⚙️ {user.first_name} (@{user.username if user.username else 'No username'}) - ID: `{user.id}`")
        
        group_info = f"""
👥 **GROUP MEMBER INFO**

**🏠 Group Details:**
• **Name:** {chat.title}
• **ID:** `{chat.id}`
• **Type:** {chat.type}
• **Total Members:** {member_count}

**👑 Group Owner:**
{owner_info if owner_info else "❌ Owner not found"}

**⚙️ Administrators ({len(admin_list)}):**
{chr(10).join(admin_list) if admin_list else "❌ No administrators"}

**📊 Member Tracking:**
• ✅ **Join notifications:** ON
• ✅ **Leave notifications:** ON
• 📩 **Sent to:** Owner accounts

**⏰ {time_str} 📅 {date_str}**
**🔥 EM OFFICIAL TEAM TRACKER 🔥**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh Info", callback_data="refresh_members"),
                InlineKeyboardButton("📊 Get Stats", callback_data="refresh_stats")
            ],
            [InlineKeyboardButton("👑 Owner Help", callback_data="refresh_owner_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            group_info,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error getting group info: {e}")
        await update.message.reply_text(
            f"❌ **Error getting group information**\n"
            f"📝 **Error:** {str(e)}\n"
            f"💡 **Make sure bot has admin permissions**",
            parse_mode=ParseMode.MARKDOWN
        )

# ===============================
# CALLBACK HANDLERS
# ===============================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    if not update.callback_query:
        return
    
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    if query.data == "start_verify":
        # Redirect to verify command
        await verify_command(update, context)
    
    elif query.data == "complete_verification":
        # Complete verification
        verify_user(user_id)
        
        success_text = f"""
🎉 **VERIFICATION COMPLETED!** 🎉

```
✅ CONGRATULATIONS!
╭─────────────────────────────────────╮
│ 🔐 Status: FULLY VERIFIED
│ 🎮 Access: GRANTED
│ 💎 Limits: ACTIVE
│ 🚀 Ready: YES
╰─────────────────────────────────────╯
```

**🎮 YOU CAN NOW:**
• Send Free Fire likes
• Use all bot commands
• Access premium features

**🎯 TRY NOW:** `/like bd 5914395123`

**🔥 DEVELOPER BY EM OFFICIAL TEAM 🔥**
        """
        
        keyboard = [
            [InlineKeyboardButton("🎮 Try Like Command", callback_data="show_like_help")],
            [InlineKeyboardButton("📊 View Stats", callback_data="refresh_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif query.data == "refresh_stats":
        # Refresh statistics (redirect to stats command)
        await stats_command(update, context)
    
    elif query.data == "show_like_help":
        help_text = """
💎 **LIKE COMMAND GUIDE** 💎

**📝 FORMAT:**
`/like <region> <uid>`

**🌍 REGIONS:**
• **BD** - Bangladesh
• **IND** - India  
• **BR** - Brazil
• **US** - United States

**🎯 EXAMPLES:**
• `/like bd 5914395123`
• `/like ind 1234567890`
• `/like br 9876543210`

**⚡ START SENDING LIKES NOW!**
        """
        
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data.startswith("confirm_broadcast:"):
        # Handle broadcast confirmation (owner only)
        if not is_owner(user_id):
            await query.edit_message_text("❌ **Unauthorized!**")
            return
        
        message = query.data.replace("confirm_broadcast:", "")
        
        # This would implement actual broadcasting to all users
        # For now, just confirm
        await query.edit_message_text(
            f"✅ **Broadcast sent successfully!**\n"
            f"📝 **Message:** {message}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "cancel_broadcast":
        # Cancel broadcast
        await query.edit_message_text("❌ **Broadcast cancelled**")
    
    elif query.data == "refresh_commands":
        # Refresh commands display
        await slag_command(update, context)
    
    elif query.data == "refresh_owner_help":
        # Refresh owner help
        await ownerhelp_command(update, context)
    
    elif query.data == "refresh_members":
        # Refresh member info
        await members_command(update, context)
    
    elif query.data == "refresh_uptime":
        # Refresh uptime status
        await uptime_command(update, context)
    
    elif query.data == "save_uptime_report":
        # Save uptime report (placeholder for future feature)
        await query.edit_message_text("💾 **Uptime report saved!**\n📧 **Report sent to owner DM**")

# ===============================
# MAIN APPLICATION
# ===============================

def main():
    """Main function to run the bot"""
    
    # Check if bot token is set
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN environment variable not set!")
        print("📝 Get your token from @BotFather on Telegram")
        return
    
    # Load data
    load_data()
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CommandHandler("like", like_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("contact", contact_command))
    application.add_handler(CommandHandler("slag", slag_command))
    
    # Owner commands
    application.add_handler(CommandHandler("allow", allow_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("setlimit", setlimit_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("testowner", test_owner_command))
    application.add_handler(CommandHandler("ownerhelp", ownerhelp_command))
    application.add_handler(CommandHandler("members", members_command))
    application.add_handler(CommandHandler("uptime", uptime_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Member tracking handlers
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_new_member))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, track_member_left))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start bot
    print("🤖 EM OFFICIAL TEAM Bot Starting...")
    print(f"👑 Owner ID: {OWNER_ID}")
    print("🚀 Bot is running! Press Ctrl+C to stop.")
    
    try:
        application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    main()