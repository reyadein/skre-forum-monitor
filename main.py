import requests
import json
import os
from datetime import datetime
import time
import re
import traceback

# --- 1. SETUP REGEX UNTUK FILTER BAHASA ---
def is_actually_english(text):
    """
    Return True jika teks bersih dari karakter CJK (China/Jepang/Korea) dan Thai.
    """
    if not text: return False
    
    # Regex range untuk:
    # CJK (China/Jepang/Hanzi): \u4e00-\u9fff
    # Hangul (Korea): \uac00-\ud7af
    # Hiragana/Katakana: \u3040-\u30ff
    # Thai (Thailand): \u0e00-\u0e7f  <-- Tadi nongol di log kamu
    non_english_pattern = re.compile(r'[\u4e00-\u9fff\uac00-\ud7af\u3040-\u30ff\u0e00-\u0e7f]')
    
    if non_english_pattern.search(text):
        return False # Ada huruf asing
    return True

# --- 2. SUPABASE CLIENT (TETAP SAMA) ---
class SupabaseClient:
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
    
    def get_seen_posts(self):
        try:
            response = requests.get(
                f"{self.url}/rest/v1/seen_posts?select=post_id",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return [item['post_id'] for item in data]
        except Exception as e:
            print(f"Error getting seen posts: {e}")
            return []
    
    def add_seen_post(self, post_id, title, board):
        try:
            data = {
                'post_id': post_id,
                'title': title,
                'board': board,
                'notified_at': datetime.now().isoformat()
            }
            response = requests.post(
                f"{self.url}/rest/v1/seen_posts",
                headers=self.headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error adding seen post: {e}")
            return False
    
    def cleanup_old_posts(self, keep_count=100):
        try:
            response = requests.get(
                f"{self.url}/rest/v1/seen_posts?select=id,notified_at&order=notified_at.desc",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            posts = response.json()
            if len(posts) > keep_count:
                old_posts = posts[keep_count:]
                for post in old_posts:
                    requests.delete(
                        f"{self.url}/rest/v1/seen_posts?id=eq.{post['id']}",
                        headers=self.headers,
                        timeout=10
                    )
            return True
        except Exception as e:
            print(f"Error cleaning up: {e}")
            return False

# --- 3. PARSE ARTICLE (DISESUAIKAN DENGAN STRUKTUR BARU) ---
def parse_article(item, menu_seq):
    # Mapping Key Baru berdasarkan Log User
    article_id = str(item.get('id', ''))
    title = item.get('title', '').strip()
    
    # Date handling (bisa timestamp int atau string ISO)
    reg_date = item.get('regDate') 
    
    try:
        # Biasanya regDate itu string ISO "2024-01-05T..." di struktur baru
        # Tapi kalau timestamp (ms), kita handle juga
        if isinstance(reg_date, int):
             date_obj = datetime.fromtimestamp(reg_date / 1000)
        elif isinstance(reg_date, str):
             # Coba parse ISO format sederhana
             date_obj = datetime.fromisoformat(reg_date.replace('Z', '+00:00'))
        else:
             date_obj = datetime.now() # Fallback
             
        date = date_obj.strftime('%Y-%m-%d %H:%M')
    except:
        date = 'N/A'

    # URL Builder
    post_url = f"https://forum.netmarble.com/sk_rebirth_gl/view/{menu_seq}/{article_id}"
    
    # Map Board Name Manual karena 'menuName' hilang dari JSON
    board_map = {10: 'Notices', 11: 'Updates', 13: 'Developer Notes'}
    board_name = board_map.get(int(menu_seq), 'General')
    
    return {
        'id': article_id,
        'title': title,
        'url': post_url,
        'date': date,
        'board': board_name,
        'author': item.get('nickname', 'Admin'),
        'view_count': item.get('viewCount', 0),
        'reply_count': item.get('replyCount', 0),
        'is_pinned': False # Struktur baru tidak ada flag pinned yang jelas di root
    }

# --- 4. FETCH FUNCTION (UPDATE TOTAL) ---
def fetch_forum_posts_api(menu_seq, rows=10, english_only=True):
    try:
        session = requests.Session()
        main_url = f"https://forum.netmarble.com/sk_rebirth_gl/list/{menu_seq}/1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': main_url,
            'Accept': 'application/json'
        }
        
        api_url = "https://forum.netmarble.com/api/game/tskgb/official/forum/sk_rebirth_gl/article/list"
        
        # Parameter API
        params = {
            'rows': rows * 2, # Ambil lebih banyak untuk cadangan filter
            'start': 0,
            'menuSeq': menu_seq,
            '_': int(time.time() * 1000)
        }
        
        print(f"Requesting API Menu {menu_seq}...")
        response = session.get(api_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        posts = []
        
        if 'articleList' in data and data['articleList']:
            raw_list = data['articleList']
            print(f"  > API returned {len(raw_list)} items.")
            
            for item in raw_list:
                try:
                    # Ambil Title (Key Baru)
                    title = item.get('title', '').strip()
                    if not title: continue

                    # --- LOGIKA FILTER JUDUL (REGEX) ---
                    if english_only:
                        if not is_actually_english(title):
                            # print(f"    Skip Non-English: {title[:30]}...")
                            continue
                    
                    # Kalau lolos filter
                    post = parse_article(item, menu_seq)
                    if post['id']:
                        posts.append(post)
                    
                    if len(posts) >= rows:
                        break
                        
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
            
            print(f"  > Collected {len(posts)} valid posts.")
            return posts
            
        return []
        
    except Exception as e:
        print(f"Error fetching forum: {e}")
        return []

# --- 5. HELPERS LAINNYA ---
def deduplicate_posts(posts):
    seen_ids = set()
    unique = []
    for post in posts:
        if post['id'] not in seen_ids:
            seen_ids.add(post['id'])
            unique.append(post)
    return unique

def fetch_multiple_boards(rows_per_board=10):
    # Menu IDs: 10=Notices, 11=Updates, 13=Dev Notes
    boards = [10, 11, 13]
    all_posts = []
    
    for menu_seq in boards:
        posts = fetch_forum_posts_api(menu_seq, rows=rows_per_board, english_only=True)
        all_posts.extend(posts)
            
    return deduplicate_posts(all_posts)

def send_telegram_message(bot_token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': False}
        requests.post(url, json=payload, timeout=10)
        return True
    except:
        return False

def format_telegram_message(post):
    icons = {'Notices': '📢', 'Updates': '🆕', 'Developer Notes': '💬'}
    icon = icons.get(post['board'], '📝')
    return f"{icon} <b>Seven Knights Rebirth - {post['board']}</b>\n\n<b>{post['title']}</b>\n\n📅 {post['date']}\n🔗 <a href=\"{post['url']}\">Read Post</a>"

# --- MAIN ---
if __name__ == "__main__":
    print("🚀 Starting Monitor (New JSON Structure)...")
    
    # Load Env
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # 1. Fetch
    new_posts = fetch_multiple_boards(rows_per_board=5)
    
    if new_posts:
        print(f"\nFound {len(new_posts)} potential posts.")
        
        # 2. Database Check
        seen_ids = []
        if SUPABASE_URL and SUPABASE_KEY:
            db = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
            seen_ids = db.get_seen_posts()
        
        # 3. Send & Save
        sent_count = 0
        for post in reversed(new_posts):
            if post['id'] not in seen_ids:
                print(f"Sending: {post['title']}")
                msg = format_telegram_message(post)
                
                success = True
                if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
                    success = send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)
                    time.sleep(1)
                
                if success and SUPABASE_URL:
                    db.add_seen_post(post['id'], post['title'], post['board'])
                    sent_count += 1
        
        print(f"Done. Sent {sent_count} new notifications.")
        if SUPABASE_URL: db.cleanup_old_posts()
    else:
        print("No posts found.")