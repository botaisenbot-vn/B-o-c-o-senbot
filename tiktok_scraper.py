#!/usr/bin/env python3
"""
TikTok Scraper — Lấy chỉ số: followers, video views, comments
Chạy trên máy Đại Ca (cần Chrome + Selenium)
"""
import json, time, os, sys, requests, re
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

TIKTOK_USER = "nhasachcungsenbot"
TIKTOK_URL = f"https://www.tiktok.com/@{TIKTOK_USER}"
DATA_FILE = Path("tiktok_data.json")

def scrape_tiktok():
    print(f"🎵 Scraping TikTok: {TIKTOK_USER}...")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(TIKTOK_URL)
        time.sleep(5)
        
        data = {"user": TIKTOK_USER, "updated": datetime.now().isoformat()}
        
        # ── FOLLOWERS ──
        try:
            followers_el = driver.find_element(By.CSS_SELECTOR, '[data-e2e="followers-count"], strong[data-e2e*="followers"]')
            data["followers"] = followers_el.text.strip()
        except:
            try:
                # Fallback: find number near "Followers"
                text = driver.find_element(By.TAG_NAME, 'body').text
                m = re.search(r'(\d[\d,.]*[KMB]?)\s*Followers?', text)
                if m: data["followers"] = m.group(1)
            except: pass
        
        # ── LIKES (total) ──
        try:
            likes_el = driver.find_element(By.CSS_SELECTOR, '[data-e2e="likes-count"], strong[data-e2e*="likes"]')
            data["total_likes"] = likes_el.text.strip()
        except:
            try:
                text = driver.find_element(By.TAG_NAME, 'body').text
                m = re.search(r'(\d[\d,.]*[KMB]?)\s*Likes?', text)
                if m: data["total_likes"] = m.group(1)
            except: pass
        
        # ── VIDEOS ──
        videos = []
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(3)
        
        # Find video items
        video_items = driver.find_elements(By.CSS_SELECTOR, '[data-e2e="user-post-item"], div[class*="DivItemContainer"]')
        if not video_items:
            video_items = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        
        for item in video_items[:10]:
            try:
                # Get href
                href = item.get_attribute("href")
                link = href if href else item.find_element(By.TAG_NAME, 'a').get_attribute("href")
                
                # Get views from aria-label or nearby text
                aria = item.get_attribute("aria-label")
                if not aria:
                    aria = item.text
                
                views_match = re.search(r'([\d,.]+[KMB]?)\s*(views|view)', aria, re.IGNORECASE) if aria else None
                views = views_match.group(1) if views_match else "?"
                
                videos.append({"link": link, "views": views, "desc": (aria or "")[:100]})
            except:
                pass
        
        data["videos"] = videos
        data["video_count"] = len(videos)
        
        # Save
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Print summary
        print(f"  👥 Followers: {data.get('followers', '?')}")
        print(f"  ❤️ Total Likes: {data.get('total_likes', '?')}")
        print(f"  📹 Videos scraped: {len(videos)}")
        for v in videos:
            print(f"    👁️ {v['views']} | {v.get('desc','')[:60]}")
        
        # Send to VPS
        try:
            requests.post("http://72.60.232.73:8765/tiktok", json=data, timeout=10)
            print("  📤 Sent to dashboard!")
        except:
            print("  ⚠️ VPS not reachable")
        
        return data
        
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_tiktok()
