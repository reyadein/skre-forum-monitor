from flask import Flask, jsonify, request
import os
from datetime import datetime
import threading
import time
import requests

# Import from main script
from main import (
    SupabaseClient,
    fetch_multiple_boards,
    send_telegram_message,
    format_telegram_message
)

app = Flask(__name__)


def check_forum():
    """Main function to check forum and send notifications"""
    try:
        print(f"\n{'='*60}")
        print(f"🎮 SK Rebirth Forum Monitor Starting...")
        print(f"Time: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")
        
        # Get environment variables
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not all([bot_token, chat_id, supabase_url, supabase_key]):
            error_msg = "Missing environment variables"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "missing": {
                    "bot_token": not bool(bot_token),
                    "chat_id": not bool(chat_id),
                    "supabase_url": not bool(supabase_url),
                    "supabase_key": not bool(supabase_key)
                }
            }
        
        # Initialize Supabase client
        db = SupabaseClient(supabase_url, supabase_key)
        
        # Load seen posts
        seen_posts = db.get_seen_posts()
        print(f"📚 Loaded {len(seen_posts)} seen posts from database\n")
        
        # Fetch English posts from multiple boards
        print("🔍 Fetching English posts from official boards...")
        posts = fetch_multiple_boards(rows_per_board=10)
        
        if not posts:
            return {
                "status": "success",
                "message": "No posts found",
                "posts_checked": 0,
                "new_posts": 0,
                "notifications_sent": 0
            }
        
        print(f"\n📊 Found {len(posts)} total English posts")
        
        # Check for new posts
        new_posts = []
        for post in posts:
            if post['id'] not in seen_posts:
                new_posts.append(post)
        
        # Send notifications
        notifications_sent = 0
        if new_posts:
            print(f"\n🆕 Found {len(new_posts)} new posts!")
            new_posts.reverse()  # Oldest first
            
            for post in new_posts:
                message = format_telegram_message(post)
                
                print(f"\n📤 Sending notification for: {post['title'][:60]}")
                print(f"   Board: {post['board']}")
                print(f"   Date: {post['date']}")
                
                if send_telegram_message(bot_token, chat_id, message):
                    # Save to database
                    if db.add_seen_post(post['id'], post['title'], post['board']):
                        notifications_sent += 1
                        print(f"   ✅ Successfully notified and saved")
                    else:
                        print(f"   ⚠️  Notified but failed to save to database")
                    
                    time.sleep(1)  # Delay between notifications
                else:
                    print(f"   ❌ Failed to send notification")
        else:
            print(f"\n✓ No new posts found")
        
        # Cleanup old posts
        print(f"\n🧹 Cleaning up old posts...")
        db.cleanup_old_posts(100)
        
        result = {
            "status": "success",
            "posts_checked": len(posts),
            "new_posts": len(new_posts),
            "notifications_sent": notifications_sent,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n{'='*60}")
        print(f"✅ Check Complete!")
        print(f"   Posts checked: {result['posts_checked']}")
        print(f"   New posts: {result['new_posts']}")
        print(f"   Notifications sent: {result['notifications_sent']}")
        print(f"{'='*60}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error in check_forum: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


def keep_alive():
    """Ping self every 10 minutes to prevent Render free tier sleep"""
    while True:
        time.sleep(600)  # 10 minutes
        try:
            url = os.getenv('RENDER_EXTERNAL_URL', '')
            if url:
                requests.get(f"{url}/health", timeout=5)
                print(f"[{datetime.now()}] 💓 Keep-alive ping sent")
        except Exception as e:
            print(f"Keep-alive error: {e}")


@app.route('/')
def home():
    """Home page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SK:R Forum Monitor</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #333; }
            .status { 
                color: #28a745; 
                font-weight: bold; 
            }
            ul { line-height: 2; }
            a { 
                color: #007bff; 
                text-decoration: none; 
            }
            a:hover { text-decoration: underline; }
            .info {
                background: #e7f3ff;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 Seven Knights Rebirth Forum Monitor</h1>
            <p class="status">✅ Status: Running</p>
            
            <h2>📡 Monitored Boards:</h2>
            <ul>
                <li>📢 Notices (Official Announcements)</li>
                <li>🆕 Updates (Game Updates)</li>
                <li>💬 Developer Notes (Dev Communication)</li>
            </ul>
            
            <h2>🔗 Endpoints:</h2>
            <ul>
                <li><a href="/health">/health</a> - Health check</li>
                <li><a href="/check">/check</a> - Trigger forum check manually</li>
            </ul>
            
            <div class="info">
                <strong>ℹ️ How it works:</strong><br>
                • Checks forum every 3 minutes via cron-job.org<br>
                • Filters English posts only<br>
                • Sends Telegram notifications for new posts<br>
                • Tracks seen posts in Supabase to avoid duplicates
            </div>
        </div>
    </body>
    </html>
    """


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "SK Rebirth Forum Monitor",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/check', methods=['GET', 'POST'])
def trigger_check():
    """Endpoint to trigger forum check (called by cron-job.org)"""
    
    print(f"\n{'='*60}")
    print(f"🔔 Check triggered at {datetime.now().isoformat()}")
    print(f"Method: {request.method}")
    print(f"{'='*60}")
    
    try:
        result = check_forum()
        status_code = 200 if result['status'] == 'success' else 500
        return jsonify(result), status_code
    except Exception as e:
        print(f"❌ Error in trigger_check: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


# Start keep-alive thread (only on Render)
if os.getenv('RENDER'):
    print("🚀 Running on Render - Starting keep-alive thread...")
    threading.Thread(target=keep_alive, daemon=True).start()
else:
    print("🏠 Running locally - Keep-alive disabled")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    
    print(f"\n{'='*60}")
    print(f"🎮 SK Rebirth Forum Monitor Starting...")
    print(f"Port: {port}")
    print(f"Environment: {'Render' if os.getenv('RENDER') else 'Local'}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)