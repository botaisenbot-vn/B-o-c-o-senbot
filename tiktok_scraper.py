#!/usr/bin/env python3
"""TikTok Scraper v3 — Bắt views từ HTML text thay vì aria-label"""
import json, time, re, os, requests
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

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
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        driver.get(f"https://www.tiktok.com/@{TIKTOK_USER}")
        time.sleep(8)
        
        data = {"user": TIKTOK_USER, "updated": datetime.now().isoformat()}
        
        # Get user data
        html = driver.page_source
        m = re.search(r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html)
        if m:
            ud = json.loads(m.group(1))
            ui = ud['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']
            data["followers"] = ui['stats']['followerCount']
            data["total_likes"] = ui['stats']['heartCount']
            data["video_count"] = ui['stats']['videoCount']
            data["nickname"] = ui['user']['nickname']
            log(f"  👥 {data['followers']:,} followers | 🎬 {data['video_count']} videos")
        
        # Scroll to load
        for i in range(6):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)
        
        # DEBUG: Print all aria-labels and text
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        log(f"  Found {len(links)} video links")
        
        # Get ALL text from the page
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        
        # Try to find view counts from the full page text
        # Pattern: "number views" or "numberK views" in the page
        view_matches = re.findall(r'([\d,.]+[KMB]?)\s*(views|view|lượt xem|lượt)', body_text, re.IGNORECASE)
        if view_matches:
            log(f"  Found {len(view_matches)} view counts in page text")
            for vm in view_matches[:5]:
                log(f"    Raw: {vm}")
        
        videos = []
        seen = set()
        
        for link in links:
            href = link.get_attribute("href")
            aria = link.get_attribute("aria-label")
            
            if not aria:
                # Try to get text from parent container
                try:
                    parent = link.find_element(By.XPATH, './ancestor::div[contains(@class,"DivItemContainer") or contains(@class,"wrapper")]')
                    aria = parent.text
                except:
                    aria = ""
            
            if href and href not in seen:
                seen.add(href)
                
                # Debug first 3
                if len(seen) <= 3:
                    log(f"    DEBUG link {len(seen)}: aria={repr(aria)[:150]}")
                
                views = 0
                # Try multiple patterns
                for pattern in [
                    r'([\d,.]+[KMB]?)\s*(views|view|lượt xem|lượt)',
                    r'([\d,.]+[KMB]?)\s*$',
                    r'play\s*([\d,.]+[KMB]?)',
                ]:
                    vm = re.search(pattern, aria, re.IGNORECASE)
                    if vm:
                        vs = vm.group(1).replace(',', '')
                        try:
                            if 'K' in vs.upper(): views = int(float(vs.upper().replace('K','')) * 1000)
                            elif 'M' in vs.upper(): views = int(float(vs.upper().replace('M','')) * 1000000)
                            elif 'B' in vs.upper(): views = int(float(vs.upper().replace('B','')) * 1000000000)
                            else: views = int(vs)
                        except: pass
                        break
                
                desc = (aria or '')[:80]
                videos.append({"link": href, "views": views, "desc": desc})
        
        videos.sort(key=lambda x: x['views'], reverse=True)
        data["videos"] = videos[:15]
        total_views = sum(v['views'] for v in videos)
        data["total_views"] = total_views
        
        log(f"  📹 {len(videos)} videos | 👁️ {total_views:,} total views")
        for v in videos[:5]:
            log(f"    👁️{v['views']:,} | {v['desc'][:60]}")
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        try:
            r = requests.post(VPS_URL, json=data, timeout=10)
            log(f"  📤 Sent! ({r.status_code})")
        except Exception as e:
            log(f"  ⚠️ {e}")
        
        return data
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape()
