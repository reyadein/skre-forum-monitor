# 🎮 Seven Knights Rebirth Forum Monitor

Automated monitoring system for Seven Knights Rebirth official forum. Sends instant Telegram notifications for new English posts from official boards (Notices, Updates, Developer Notes).

## ✨ Features

- **🌍 English Only Filter** - Automatically filters English posts from multi-language boards
- **📢 Multi-Board Monitoring** - Monitors 3 official boards:
  - Notices (Official Announcements)
  - Updates (Game Updates)
  - Developer Notes (Developer Communication)
- **📱 Telegram Notifications** - Instant notifications with formatted messages
- **💾 Duplicate Prevention** - Tracks seen posts in Supabase database
- **⏰ Scheduled Checks** - Automatic checks every 3 minutes via cron-job.org
- **🆓 100% Free** - Uses free tiers: Render, Supabase, Telegram, Cron-job.org

## 🏗️ Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│ Cron-job.org│         │    Render    │         │  Supabase   │
│  (Trigger)  │────────▶│ Web Service  │────────▶│  Database   │
└─────────────┘         └──────────────┘         └─────────────┘
   Every 3 min               Flask API              Seen Posts
                                 │
                                 ▼
                          ┌──────────────┐
                          │  Netmarble   │
                          │    Forum     │
                          │  (3 Boards)  │
                          └──────────────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │   Telegram   │
                          │     Bot      │
                          └──────────────┘
```

## 📋 Prerequisites

- **Telegram Bot** - Create via [@BotFather](https://t.me/BotFather)
- **Supabase Account** - Free tier at [supabase.com](https://supabase.com)
- **Render Account** - Free tier at [render.com](https://render.com)
- **Cron-job.org Account** - Free tier at [cron-job.org](https://cron-job.org)
- **GitHub Account** - For code repository

## 🚀 Quick Start

See **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** for detailed step-by-step setup instructions.

**Summary:**
1. Create Telegram bot and get token + chat ID
2. Setup Supabase database and table
3. Push code to GitHub
4. Deploy to Render with environment variables
5. Setup cron-job.org to trigger every 3 minutes

**Total setup time:** ~30 minutes

## 📁 Project Structure

```
sk-forum-monitor/
├── main.py                 # Core monitoring logic
├── app.py                  # Flask web service
├── requirements.txt        # Python dependencies
├── render.yaml            # Render configuration
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── DEPLOYMENT_GUIDE.md    # Step-by-step tutorial
└── test_api.py            # Test/debug script
```

## 🔧 Environment Variables

Required environment variables (set in Render dashboard):

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
RENDER=true
```

## 📊 Monitored Boards

| Board | Menu Seq | Description | Language |
|-------|----------|-------------|----------|
| Notices | 10 | Official announcements | EN only |
| Updates | 11 | Game updates | EN only |
| Developer Notes | 13 | Dev communication | EN only |

**Note:** Original boards have multi-language posts (EN/KO/TH), but bot filters English only via `languageTypeCd`.

## 🔔 Notification Format

```
🆕 Seven Knights Rebirth - Updates

📝 12/31 Update Details

📅 December 31, 2024 at 10:00
✍️ By Seven Knights
🔗 Read Full Post
```

## 🛠️ Development

### Local Testing

```bash
# Clone repository
git clone https://github.com/yourusername/sk-forum-monitor.git
cd sk-forum-monitor

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export SUPABASE_URL="your_url"
export SUPABASE_KEY="your_key"

# Run Flask app
python app.py

# Test in another terminal
curl http://localhost:10000/check
```

### Test API Endpoints

```bash
# Health check
curl https://your-app.onrender.com/health

# Trigger forum check
curl https://your-app.onrender.com/check
```

### Debug Script

Use `test_api.py` to inspect forum API responses:

```bash
python test_api.py
```

## 📦 Database Schema

Supabase table: `seen_posts`

```sql
CREATE TABLE seen_posts (
  id BIGSERIAL PRIMARY KEY,
  post_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  board TEXT,
  notified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_post_id ON seen_posts(post_id);
CREATE INDEX idx_notified_at ON seen_posts(notified_at DESC);
```

## 🔄 How It Works

1. **Cron-job.org** triggers `/check` endpoint every 3 minutes
2. **Render service** receives request and starts forum check
3. **Fetch posts** from 3 boards (10 posts each = 30 total)
4. **Filter English** via `languageTypeCd == "en_US"`
5. **Deduplicate** posts by ID
6. **Check Supabase** for already-notified posts
7. **Send Telegram** notifications for new posts
8. **Save to database** after successful notification
9. **Cleanup old posts** (keep last 100)

## 🐛 Troubleshooting

### No notifications received

- ✅ Check Telegram bot is started (send `/start`)
- ✅ Verify `TELEGRAM_CHAT_ID` is numeric (not @username)
- ✅ Check Render logs for errors
- ✅ Test manually: `curl your-app.onrender.com/check`

### Service sleeping on Render

- ✅ Keep-alive mechanism should prevent this
- ✅ Check `RENDER` env var is set to `"true"`
- ✅ Verify health check path is `/health`

### API not returning posts

- ✅ Check forum is accessible
- ✅ Run `test_api.py` to debug API responses
- ✅ Verify menuSeq values are correct (10, 11, 13)

### Duplicate notifications

- ✅ Check Supabase connection
- ✅ Verify `seen_posts` table exists
- ✅ Check database credentials in env vars

## 📝 License

MIT License - feel free to use and modify!

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📞 Support

For issues or questions:
1. Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. Review Render logs
3. Test with `test_api.py`
4. Open GitHub issue

## 🔗 Links

- [Seven Knights Rebirth Forum](https://forum.netmarble.com/sk_rebirth_gl)
- [Render Documentation](https://render.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

Made with ❤️Sonnet❤️ for Seven Knights Rebirth community