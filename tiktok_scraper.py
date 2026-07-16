#!/usr/bin/env python3
"""TikTok Scraper via AdPower — Chống detect, dùng fingerprint thật"""
import json, time, re, os, requests
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

API_BASE = "http://local.adspower.net:50325"
TIKTOK_USER = "nhasachcungsenbot"
VPS_URL = "http://72.60.232.73:8765/tiktok"
SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "nick_state.json"
DATA_FILE = SCRIPT_DIR / "tiktok_data.json"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def api(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=30)
        if r.status_code == 200: return r.json()
    except: pass
    return None

def scrape():
    log(f"🎵 TikTok via AdPower: @{TIKTOK_USER}")
    
    # Pick first available profile (any nick works for TikTok)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    profiles = list(state.items())
    if not profiles:
        log("❌ No AdPower profiles found!")
        return
    
    name, info = profiles[0]
    uid = info.get("id", "")
    log(f"  Using profile: {name} ({uid})")
    
    # Open browser via AdPower
    result = api(f"/api/v1/browser/start?user_id={uid}")
    if not result or result.get("code") != 0:
        log("❌ Open failed")
        return
    
    webdriver_path = result.get("data", {}).get("webdriver", "")
    debug_port = result.get("data", {}).get("debug_port", "")
    if not debug_port:
        ws = result.get("data", {}).get("ws", {})
        m = re.search(r'127\.0\.0\.1:(\d+)', ws.get("puppeteer", ""))
        if m: debug_port = m.group(1)
    
    log(f"  Browser: port={debug_port}")
    
    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
        service = Service(executable_path=webdriver_path) if webdriver_path else Service()
        driver = webdriver.Chrome(service=service, options=options)
        
        # Go to TikTok
        driver.get(f"https://www.tiktok.com/@{TIKTOK_USER}")
        time.sleep(8)
        
        data = {"user": TIKTOK_USER, "updated": datetime.now().isoformat()}
        
        # Extract user info from page data
        html = driver.page_source
        m = re.search(r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html)
        if m:
            ud = json.loads(m.group(1))
            ui = ud['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']
            data["followers"] = ui['stats']['followerCount']
            data["total_likes"] = ui['stats']['heartCount']
            data["video_count"] = ui['stats']['videoCount']
            data["nickname"] = ui['user']['nickname']
            log(f"  👥 {data['followers']:,} | ❤️ {data['total_likes']:,} | 🎬 {data['video_count']}")
        
        # Scroll for videos
        for i in range(6):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)
        
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        log(f"  📹 {len(links)} video links found")
        
        videos = []
        seen = set()
        for link in links:
            href = link.get_attribute("href")
            aria = link.get_attribute("aria-label") or ""
            
            # Debug first 3
            if len(seen) < 3:
                log(f"    [{len(seen)+1}] aria: {repr(aria[:150])}")
                # Also try getting text from parent
                try:
                    parent = link.find_element(By.XPATH, './ancestor::div[1]')
                    log(f"         parent: {repr(parent.text[:100])}")
                except: pass
            
            if href and href not in seen:
                seen.add(href)
                
                views = 0
                # Parse from aria
                for pat in [r'([\d,.]+[KMB]?)\s*(views|view|lượt xem|lượt)', 
                           r'([\d,.]+[KMB]?)[\s\n]',
                           r'(\d+[\d,.]*[KMB]?)']:
                    vm = re.search(pat, aria, re.IGNORECASE)
                    if vm:
                        vs = vm.group(1).replace(',','').strip()
                        try:
                            vs_upper = vs.upper()
                            if 'K' in vs_upper: views = int(float(vs_upper.replace('K',''))*1000)
                            elif 'M' in vs_upper: views = int(float(vs_upper.replace('M',''))*1000000)
                            elif 'B' in vs_upper: views = int(float(vs_upper.replace('B',''))*1000000000)
                            else: views = int(float(vs))
                        except: pass
                        break
                
                videos.append({"link": href, "views": views, "desc": aria[:80]})
        
        videos.sort(key=lambda x: x['views'], reverse=True)
        data["videos"] = videos[:15]
        data["total_views"] = sum(v['views'] for v in videos)
        
        log(f"  👁️ {data['total_views']:,} total views | {len(videos)} videos")
        for v in videos[:5]:
            log(f"    👁️{v['views']:,} | {v['desc'][:60]}")
        
        # Save + send
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        try:
            r = requests.post(VPS_URL, json=data, timeout=10)
            log(f"  📤 Sent! ({r.status_code})")
        except: pass
        
        driver.quit()
        
    except Exception as e:
        log(f"❌ {e}")
        try: driver.quit()
        except: pass
    finally:
        api(f"/api/v1/browser/stop?user_id={uid}")

if __name__ == "__main__":
    scrape()
