import requests
import json
import os
from datetime import datetime
import time

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


def fetch_forum_posts_api(menu_seq, rows=15, english_only=True):
    """
    Fetch posts from forum using API
    
    Args:
        menu_seq: Menu sequence (10=Notices, 11=Updates, 13=Developer Notes)
        rows: Number of posts to fetch
        english_only: Filter only English posts (via languageTypeCd)
    
    Returns:
        List of parsed posts
    """
    try:
        session = requests.Session()
        
        # Visit main page for cookies
        main_url = f"https://forum.netmarble.com/sk_rebirth_gl/list/{menu_seq}/1"
        session.get(main_url, timeout=15)
        
        # API endpoint
        api_url = "https://forum.netmarble.com/api/game/tskgb/official/forum/sk_rebirth_gl/article/list"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': main_url,
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        # Fetch more rows to account for filtering
        fetch_rows = rows * 3 if english_only else rows
        
        params = {
            'rows': fetch_rows,
            'start': 0,
            'viewType': 'pv',
            'menuSeq': menu_seq,
            'sort': 'NEW',
            '_': int(time.time() * 1000)
        }
        
        print(f"Requesting: {api_url}")
        print(f"Params: {params}")
        
        response = session.get(api_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        posts = []
        
        if 'articleList' in data and data['articleList']:
            print(f"API returned {len(data['articleList'])} articles")
            
            for item in data['articleList']:
                try:
                    # Get language code - CLEAN IT!
                    lang_cd = (item.get('languageTypeCd', '') or '').strip().lower()
                    title = item.get('articleTitle', '').strip()
                    
                    # Skip if no title
                    if not title:
                        continue
                    
                    # Filter English ONLY
                    if english_only:
                        is_english = lang_cd in ['en_us', 'en', 'en-us'] or lang_cd.startswith('en')
                        
                        if not is_english:
                            print(f"⏭️  Skipping {lang_cd}: {title[:50]}")
                            continue
                        else:
                            print(f"✅ English ({lang_cd}): {title[:50]}")
                    
                    # Parse article
                    post = parse_article(item, menu_seq)
                    
                    if not post['title'] or not post['id']:
                        print(f"⏭️  Skipping - missing title/ID")
                        continue
                    
                    posts.append(post)
                    
                    # Stop when we have enough
                    if len(posts) >= rows:
                        break
                        
                except Exception as e:
                    print(f"Error parsing article: {e}")
                    continue
        else:
            print(f"API response structure: {data.keys() if isinstance(data, dict) else 'not a dict'}")
        
        return posts[:rows]
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return []
    except Exception as e:
        print(f"Error fetching forum via API: {e}")
        return []


def fetch_forum_posts_api(menu_seq, rows=15, english_only=True):
    """
    Fetch posts from forum using API
    
    Args:
        menu_seq: Menu sequence (10=Notices, 11=Updates, 13=Developer Notes)
        rows: Number of posts to fetch
        english_only: Filter only English posts (via languageTypeCd)
    
    Returns:
        List of parsed posts
    """
    try:
        session = requests.Session()
        
        # Visit main page for cookies
        main_url = f"https://forum.netmarble.com/sk_rebirth_gl/list/{menu_seq}/1"
        session.get(main_url, timeout=15)
        
        # API endpoint
        api_url = "https://forum.netmarble.com/api/game/tskgb/official/forum/sk_rebirth_gl/article/list"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': main_url,
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        # Fetch more rows to account for filtering
        fetch_rows = rows * 3 if english_only else rows
        
        params = {
            'rows': fetch_rows,
            'start': 0,
            'viewType': 'pv',
            'menuSeq': menu_seq,
            'sort': 'NEW',
            '_': int(time.time() * 1000)
        }
        
        print(f"Requesting: {api_url}")
        print(f"Params: {params}")
        
        response = session.get(api_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        posts = []
        
        if 'articleList' in data and data['articleList']:
            print(f"API returned {len(data['articleList'])} articles")
            
            for item in data['articleList']:
                try:
                    # Filter English ONLY
                    lang_cd = item.get('languageTypeCd', '')
                    title = item.get('articleTitle', '').strip()
                    
                    if english_only and lang_cd not in ['en_US', 'en', 'EN']:
                        print(f"⏭️  Skipping {lang_cd}: {title[:50]}")
                        continue
                    
                    # Parse article
                    post = parse_article(item, menu_seq)
                    
                    if not post['title'] or not post['id']:
                        print(f"⏭️  Skipping - missing title/ID")
                        continue
                    
                    print(f"✅ Processing English post: {post['title'][:60]}")
                    posts.append(post)
                    
                    # Stop when we have enough
                    if len(posts) >= rows:
                        break
                        
                except Exception as e:
                    print(f"Error parsing article: {e}")
                    continue
        else:
            print(f"API response structure: {data.keys() if isinstance(data, dict) else 'not a dict'}")
        
        return posts[:rows]
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
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