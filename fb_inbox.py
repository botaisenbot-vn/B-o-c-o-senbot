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
SCRIPT_DIR = Path(__file__).parent if '__file__' in dir() else Path.cwd()
COOKIE_DIR = SCRIPT_DIR / "cookies/Cookie 3"
STATE_FILE = SCRIPT_DIR / "nick_state.json"
INBOX_LOG = SCRIPT_DIR / "inbox_log.json"

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
    INBOX_LOG.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

def check_one_nick(name, info):
    """Check inbox + notifications for 1 nick"""
    user_id = info["id"]
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
        
        # 0. IMPORT COOKIE FIRST (if not done yet)
        if not info.get("cookie_imported") and info.get("cookie_file"):
            cf = info["cookie_file"]
            if os.path.exists(cf):
                try:
                    driver.get("https://facebook.com")
                    time.sleep(3)
                    with open(cf, 'r', encoding='utf-8') as f:
                        cookies_data = json.load(f)
                    for c in cookies_data:
                        try:
                            driver.add_cookie({
                                'name': c.get('name', ''),
                                'value': c.get('value', ''),
                                'domain': c.get('domain', '.facebook.com'),
                                'path': c.get('path', '/'),
                            })
                        except: pass
                    driver.refresh()
                    time.sleep(3)
                    info["cookie_imported"] = True
                    log(f"  Imported {len(cookies_data)} cookies")
                except Exception as e:
                    log(f"  Cookie err: {e}")
        
        # 1. Check Messenger (desktop version)
        driver.get("https://facebook.com")
        time.sleep(3)
        
        # Check messenger icon for unread badge
        try:
            badges = driver.find_elements(By.CSS_SELECTOR, '[aria-label*="Messenger"] [role="link"] span, [data-pagelet="Messenger"] span')
            for badge in badges:
                text = badge.text.strip()
                if text.isdigit() and int(text) > 0:
                    new_messages.append({"type": "inbox", "from": f"Co {text} tin nhan chua doc", "nick": name})
        except: pass
        
        # Go to messenger page
        driver.get("https://www.facebook.com/messages/t/")
        time.sleep(3)
        try:
            threads = driver.find_elements(By.CSS_SELECTOR, '[role="row"], [role="listitem"], div[data-tabindex]')
            for t in threads[:10]:
                text = t.text.strip()
                if text and len(text) > 10 and "Bạn:" not in text and "Chat" not in text:
                    new_messages.append({"type": "inbox", "from": text[:120], "nick": name})
        except: pass
        
        # 2. Check notifications
        driver.get("https://facebook.com/notifications")
        time.sleep(2)
        try:
            items = driver.find_elements(By.CSS_SELECTOR, '[role="article"], div[class*="notification"]')
            for item in items[:5]:
                text = item.text.strip()
                if text and len(text) > 10:
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
    
    state_file = SCRIPT_DIR / "nick_state.json"
    log(f"Looking for state at: {state_file}")
    log(f"File exists: {state_file.exists()}")
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            profiles = state
            log(f"Profiles found: {len(profiles)}")
        except Exception as e:
            log(f"State parse error: {e}")
            profiles = {}
    else:
        log("❌ nick_state.json NOT FOUND!")
        profiles = {}

    if not profiles:
        log("Chay setup truoc: 2_SETUP_PROFILES.bat")
        return
    
    inbox_log = load_inbox_log()
    all_new = []
    
    # Only check 3 nicks per run to be fast
    nick_list = list(profiles.items())
    random.shuffle(nick_list)
    
    for name, info in nick_list:  # Check ALL nicks
        uid = info["id"]
        log(f"  👤 {name}...")
        
        msgs = check_one_nick(name, info)
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
