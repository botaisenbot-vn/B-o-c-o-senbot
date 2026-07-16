#!/usr/bin/env python3
"""
TikTok Scraper Local — Chạy trên máy Đại Ca (AdPower Chrome)
Scrape: followers, videos, views, comments → gửi lên VPS Dashboard
"""
import json, time, re, os, requests
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TIKTOK_USER = "nhasachcungsenbot"
VPS_URL = "http://72.60.232.73:8765/tiktok"
DATA_FILE = Path(__file__).parent / "tiktok_data.json"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def scrape():
    log(f"🎵 Scraping @{TIKTOK_USER}...")
    
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        driver.get(f"https://www.tiktok.com/@{TIKTOK_USER}")
        time.sleep(8)
        
        data = {"user": TIKTOK_USER, "updated": datetime.now().isoformat()}
        
        # Method 1: Extract from UNIVERSAL_DATA
        html = driver.page_source
        m = re.search(r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html)
        
        if m:
            import json as j
            ud = j.loads(m.group(1))
            ui = ud['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']
            
            data["followers"] = ui['stats']['followerCount']
            data["total_likes"] = ui['stats']['heartCount']
            data["video_count"] = ui['stats']['videoCount']
            data["nickname"] = ui['user']['nickname']
            
            log(f"  👥 {data['followers']:,} followers | ❤️ {data['total_likes']:,} likes | 🎬 {data['video_count']} videos")
            
            # Method 2: Scroll to load videos, then get from page
            for i in range(6):
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
            
            # Get all video links + aria labels
            videos = []
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
            seen = set()
            
            for link in links:
                href = link.get_attribute("href")
                aria = link.get_attribute("aria-label") or link.text or ""
                
                if href and href not in seen:
                    seen.add(href)
                    # Parse views from aria
                    views = 0
                    vm = re.search(r'([\d,.]+[KMB]?)\s*(views|view|lượt|lượt xem)', aria, re.IGNORECASE)
                    if vm:
                        vs = vm.group(1).replace(',', '')
                        if 'K' in vs: views = int(float(vs.replace('K','')) * 1000)
                        elif 'M' in vs: views = int(float(vs.replace('M','')) * 1000000)
                        elif 'B' in vs: views = int(float(vs.replace('B','')) * 1000000000)
                        else: views = int(vs)
                    
                    videos.append({"link": href, "views": views, "desc": aria[:80]})
            
            videos.sort(key=lambda x: x['views'], reverse=True)
            data["videos"] = videos[:15]
            
            total_views = sum(v['views'] for v in videos)
            data["total_views"] = total_views
            
            log(f"  📹 {len(videos)} videos scraped | 👁️ {total_views:,} total views")
            for v in videos[:5]:
                log(f"    👁️{v['views']:,} | {v['desc'][:60]}")
        
        # Save local
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Send to VPS
        try:
            r = requests.post(VPS_URL, json=data, timeout=10)
            log(f"  📤 Sent to dashboard! ({r.status_code})")
        except Exception as e:
            log(f"  ⚠️ VPS not reachable: {e}")
        
        return data
        
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape()
