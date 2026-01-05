import requests
import json
import os
from datetime import datetime
import time
import re

class SupabaseClient:
    """Simple Supabase client untuk REST API"""
    
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
        """Get all seen posts from Supabase"""
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
        """Add a seen post to Supabase"""
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
        """Keep only the most recent N posts"""
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
                print(f"Cleaned up {len(old_posts)} old posts")
            
            return True
        except Exception as e:
            print(f"Error cleaning up: {e}")
            return False


def parse_article(item, menu_seq):
    """Parse article from API response into structured format"""
    
    article_seq = item.get('articleSeq', '')
    title = item.get('articleTitle', '').strip()
    
    # Get date
    write_datetime = item.get('writeDatetime', 0)
    if write_datetime:
        date_obj = datetime.fromtimestamp(write_datetime / 1000)
        date = date_obj.strftime('%Y-%m-%d %H:%M')
        date_full = date_obj.strftime('%B %d, %Y at %H:%M')
    else:
        date = 'N/A'
        date_full = 'N/A'
    
    # Build post URL
    post_url = f"https://forum.netmarble.com/sk_rebirth_gl/view/{menu_seq}/{article_seq}"
    
    # Get board name from API response
    board_name = item.get('menuName', 'Unknown')
    
    # Get author
    author = item.get('writerNickName', 'Unknown')
    
    # Get counts
    view_count = item.get('viewCount', 0)
    like_count = item.get('likeCount', 0)
    reply_count = item.get('replyCount', 0)
    
    # Check if pinned
    is_pinned = item.get('topArticleYn', 'N') == 'Y'
    
    return {
        'id': str(article_seq),
        'title': title,
        'url': post_url,
        'date': date,
        'date_full': date_full,
        'board': board_name,
        'menu_seq': menu_seq,
        'author': author,
        'view_count': view_count,
        'like_count': like_count,
        'reply_count': reply_count,
        'is_pinned': is_pinned,
        'article_seq': article_seq
    }

def is_actually_english(text):
    """
    Cek apakah text mayoritas ASCII (English).
    Return False jika terdeteksi karakter CJK (China/Japan/Korea)
    """
    if not text: return False
    
    # Cek apakah ada karakter Hangul (Korea), Hiragana/Katakana (Jepang), atau Hanzi (China)
    # Range Unicode untuk CJK
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\uac00-\ud7af\u3040-\u309f\u30a0-\u30ff]')
    
    if cjk_pattern.search(text):
        return False # Ada huruf cacing, berarti bukan English
        
    return True

def fetch_forum_posts_api(menu_seq, rows=15, english_only=False): # <--- Default False dulu
    try:
        session = requests.Session()
        main_url = f"https://forum.netmarble.com/sk_rebirth_gl/list/{menu_seq}/1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': main_url
        }
        
        api_url = "https://forum.netmarble.com/api/game/tskgb/official/forum/sk_rebirth_gl/article/list"
        
        # Kita minta dikit aja dulu (rows=10) buat ngecek
        params = {
            'rows': 10, 
            'start': 0,
            'viewType': 'pv',
            'menuSeq': menu_seq,
            'sort': 'NEW',
            '_': int(time.time() * 1000)
        }
        
        print(f"\n[{menu_seq}] Requesting API RAW MODE...")
        response = session.get(api_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        posts = []
        
        if 'articleList' in data and data['articleList']:
            raw_list = data['articleList']
            print(f"[{menu_seq}] API returned {len(raw_list)} raw items.")
            
            for i, item in enumerate(raw_list):
                try:
                    title = item.get('articleTitle', '').strip()
                    lang_cd = item.get('languageTypeCd', 'NONE') # Biarin mentah
                    
                    # --- DEBUG PRINT (PENTING) ---
                    # Kita print 5 item pertama buat dilihat user
                    if i < 5:
                        print(f"  #{i+1} | Lang: [{lang_cd}] | Title: {title[:50]}...")
                    
                    # AMBIL SEMUA TANPA FILTER
                    post = parse_article(item, menu_seq)
                    if post['id']:
                        posts.append(post)
                        
                except Exception as e:
                    print(f"  ❌ Error parsing item #{i}: {e}")
                    continue
            
            print(f"[{menu_seq}] ✅ Total collected: {len(posts)}")
            return posts
            
        else:
            print(f"[{menu_seq}] ⚠️ Empty articleList!")
            return []
        
    except Exception as e:
        print(f"Error fetching forum via API: {e}")
        return []

def deduplicate_posts(posts):
    """Remove duplicate posts by ID"""
    seen_ids = set()
    unique = []
    
    for post in posts:
        post_id = post['id']
        if post_id not in seen_ids:
            seen_ids.add(post_id)
            unique.append(post)
        else:
            print(f"⏭️  Skipping duplicate: {post['title'][:50]}")
    
    return unique


def fetch_multiple_boards(rows_per_board=10):
    """
    Fetch English posts from multiple official boards
    
    Args:
        rows_per_board: Number of posts to fetch per board
    
    Returns:
        List of unique English posts from all boards
    """
    
    boards = [
        ('10', 'Notices'),
        ('11', 'Updates'),
        ('13', 'Developer Notes')
    ]
    
    all_posts = []
    
    for menu_seq, board_name in boards:
        print(f"\n{'='*60}")
        print(f"Fetching from: {board_name} (menuSeq: {menu_seq})")
        print(f"{'='*60}")
        
        try:
            # Fetch ENGLISH ONLY posts
            posts = fetch_forum_posts_api(
                menu_seq=menu_seq,
                rows=rows_per_board,
                english_only=True
            )
            
            print(f"✅ Found {len(posts)} English posts from {board_name}")
            all_posts.extend(posts)
            
        except Exception as e:
            print(f"❌ Error fetching {board_name}: {e}")
            continue
    
    # Deduplicate by post ID
    unique_posts = deduplicate_posts(all_posts)
    
    print(f"\n{'='*60}")
    print(f"Summary: Total {len(unique_posts)} unique English posts from {len(boards)} boards")
    print(f"{'='*60}")
    
    return unique_posts


def send_telegram_message(bot_token, chat_id, message):
    """Send message to Telegram with retry logic"""
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Always use HTTPS
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }
            
            print(f"Sending to Telegram (attempt {attempt + 1}/{max_retries})...")
            
            response = requests.post(url, json=payload, timeout=30)
            
            print(f"Telegram API Response: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Message sent successfully!")
                return True
            else:
                print(f"❌ Telegram error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error sending telegram (attempt {attempt + 1}): {e}")
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            
    print(f"❌ Failed to send message after {max_retries} attempts")
    return False


def format_telegram_message(post):
    """Format Telegram notification message"""
    
    # Board icon
    board_icons = {
        'Notices': '📢',
        'Updates': '🆕',
        'Developer Notes': '💬'
    }
    icon = board_icons.get(post['board'], '📝')
    
    # Pinned indicator
    pinned = '📌 <b>PINNED</b>\n' if post['is_pinned'] else ''
    
    message = f"""{icon} <b>Seven Knights Rebirth - {post['board']}</b>

{pinned}<b>{post['title']}</b>

📅 {post['date']}
✍️ By {post['author']}
🔗 <a href="{post['url']}">Read Full Post</a>
"""
    
    return message