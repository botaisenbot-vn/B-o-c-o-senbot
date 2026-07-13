#!/usr/bin/env python3
"""
FB Inbox Monitor — Kiểm tra tin nhắn + comment từ 12 nick clone
Chạy độc lập, mỗi 15-30 phút check 1 lần.
"""
import json, time, random, os, sys, requests, re
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API_BASE = "http://local.adspower.net:50325"
STATE_FILE = Path("nick_state.json")
INBOX_LOG = Path("inbox_log.json")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def api(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=30)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None

def open_browser(user_id):
    return api(f"/api/v1/browser/start?user_id={user_id}")

def close_browser(user_id):
    return api(f"/api/v1/browser/stop?user_id={user_id}")

def load_inbox_log():
    if INBOX_LOG.exists():
        return json.loads(INBOX_LOG.read_text())
    return {}

def save_inbox_log(data):
    INBOX_LOG.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))

def check_one_nick(name, user_id):
    """Check inbox + notifications for 1 nick"""
    result = open_browser(user_id)
    if not result or result.get("code") != 0:
        log(f"❌ {name}: Open failed")
        return []
    
    ws = result.get("data", {}).get("ws", {})
    debug_port = result.get("data", {}).get("debug_port", "")
    webdriver_path = result.get("data", {}).get("webdriver", "")
    
    if not debug_port:
        puppeteer = ws.get("puppeteer", "")
        if puppeteer:
            m = re.search(r'127\.0\.0\.1:(\d+)', puppeteer)
            if m: debug_port = m.group(1)
    
    new_messages = []
    
    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
        service = Service(executable_path=webdriver_path) if webdriver_path and os.path.exists(webdriver_path) else Service()
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. Check Messenger
        driver.get("https://mbasic.facebook.com/messages/")
        time.sleep(3)
        
        try:
            # Check if there are unread messages
            threads = driver.find_elements(By.CSS_SELECTOR, '[role="row"], a[href*="/messages/read/"]')
            for t in threads[:5]:
                text = t.text.strip()
                if text and "Bạn:" not in text and text not in ["Messenger", "Xem tất cả"]:
                    new_messages.append({"type": "inbox", "from": text[:100], "nick": name})
        except: pass
        
        # 2. Check notifications
        driver.get("https://mbasic.facebook.com/notifications.php")
        time.sleep(2)
        try:
            items = driver.find_elements(By.CSS_SELECTOR, '[role="article"], div[class*="notification"]')
            for item in items[:5]:
                text = item.text.strip()
                if text and "đã" in text.lower() and len(text) > 10:
                    new_messages.append({"type": "notification", "content": text[:200], "nick": name})
        except: pass
        
        driver.quit()
        
    except Exception as e:
        log(f"⚠️ {name}: {e}")
        try: driver.quit()
        except: pass
    finally:
        close_browser(user_id)
    
    return new_messages

def main():
    log("🔍 Checking inbox...")
    
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    profiles = state.get("profiles", {})
    
    if not profiles:
        log("No profiles!")
        return
    
    inbox_log = load_inbox_log()
    all_new = []
    
    # Only check 3 nicks per run to be fast
    nick_list = list(profiles.items())
    random.shuffle(nick_list)
    
    for name, info in nick_list[:3]:
        uid = info["id"]
        log(f"  👤 {name}...")
        
        msgs = check_one_nick(name, uid)
        if msgs:
            for m in msgs:
                key = f"{name}_{m.get('type')}_{m.get('from','')[:50]}_{datetime.now().strftime('%Y%m%d%H')}"
                if key not in inbox_log:
                    inbox_log[key] = {"time": datetime.now().isoformat(), **m}
                    all_new.append(m)
        
        time.sleep(random.randint(5, 15))
    
    save_inbox_log(inbox_log)
    
    if all_new:
        log(f"\n📬 {len(all_new)} NEW!")
        for m in all_new:
            type_icon = "💬" if m["type"] == "inbox" else "🔔"
            msg = f"{type_icon} [{m['nick']}] {m.get('from', m.get('content',''))[:150]}"
            log(f"  {msg}")
            # GỬI VỀ VPS ĐỂ ĐẨY LÊN WEB
            try:
                import requests
                requests.post("http://72.60.232.73:8765", json={key: inbox_log[key]}, timeout=5)
            except:
                pass  # Server chưa chạy cũng ko sao
    else:
        log("✅ No new messages")

if __name__ == "__main__":
    main()
