# Discord Gemini Bot (Render Ready)

This bot uses Google's Gemini API to answer questions in any language, including Bengali.  
It runs 24/7 on Render.com (free hosting option).

## 🛠 Setup Guide

### 1. Upload Files to GitHub
- Create a GitHub repo (public)
- Upload all these files (`main.py`, `requirements.txt`, etc.)

### 2. Deploy to Render
- Go to [https://render.com](https://render.com)
- New > Web Service > Connect your GitHub repo
- Set these Environment Variables:
  - `DISCORD_TOKEN`: Your Discord Bot Token
  - `GEMINI_API_KEY`: Your Gemini API Key

### 3. Start Command on Render
```
python main.py
```

✅ Done! Your bot will be online 24/7.
