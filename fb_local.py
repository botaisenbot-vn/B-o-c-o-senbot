#!/usr/bin/env python3
"""
FB Clone Manager — Local Script (chạy trên máy Đại Ca)
Kết nối AdPower Desktop localhost API, import cookie, nuôi nick tự động.
"""

import json, time, random, os, sys, requests, glob
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# ═══════════════ CONFIG ═══════════════
API_BASE = "http://local.adspower.net:50325"
COOKIE_DIR = Path("cookies/Cookie 3")
LOG_FILE = Path("nuoi_nick.log")
STATE_FILE = Path("nick_state.json")
TODAY_FILE = Path("today_ran.json")

INTERESTS = ["du lich","an uong","vui choi"]*4

CAPTIONS = {
    "du lich": [
        "Vua di {place} ve, met ma vui ghe! Ai muon review lich trinh thi comment nha 😊",
        "{place} dep qua troi, lan dau duoc tan huong khong khi trong lanh nhu nay 🌿",
        "Check-in {place} buoi sang som, vang hoe mot goc troi 📸",
        "Chuyen di {place} chi 2 trieu ma duoc an choi het minh 😎",
        "Di {place} ma quen mang theo cai nay la hoi han ca chuyen di luon 😅",
        "Mot minh balo len duong den {place}, tu do that su la lieu thuoc tuyet voi ✈️",
        "Sau chuyen di {place} moi thay yeu Viet Nam hon 🥰",
        "Nhung buc anh dep nhat tu chuyen di {place}, ai muon xem khong? 📸",
    ],
    "an uong": [
        "Sang nay tu lam banh mi op la, don gian ma ngon xu sac 🍳",
        "Phat hien ra quan bun rieu ngon nhat {place}, nuoc dung chuan vi mien Tay 🍜",
        "Cuoi tuan ru nhau di an lau Thai, cay xe long ma ghiền luon 🌶️",
        "Hom nay thu cong thuc tra sua tu lam, thanh cong my man luon day! 🧋",
        "Review quan cafe co view dep nhat {place}, song ao cuc dinh ☕",
        "Hom nay nau mon an tuoi tho: ca kho to, an voi com trang la het sach noi 🍚",
        "Bua toi healthy: salad ca hoi + nuoc cam, an xong thay nhe ca nguoi luon 🥗",
        "Mon an duong pho {place} ngon re ma it nguoi biet ne 🍢",
    ],
    "vui choi": [
        "Cuoi tuan cung hoi ban than di xem phim, cuoi vo bung voi phim moi nay 🎬",
        "Tap yoga buoi sang o cong vien gan nha, nang som trong lanh qua troi 🧘",
        "Moi mua bo Lego 3000 manh, do ca cuoi tuan moi xong mot nua 🤣",
        "Karaoke ca dem voi dam ban cap 3, hat toi khan ca tieng luon 🎤",
        "Shopping sale cuoi tuan, mua duoc ca dong do xinh ma gia hot 🛍️",
        "Lang thang pho di bo {place} buoi toi, den led dep nhu phim Han vay 🌃",
        "Vua tap duoc vai dong dan guitar, tay dau qua troi ma vui 🎸",
        "Di cong vien giai tri {place} ma choi tu sang toi toi moi chiu ve 🎢",
    ],
}
PLACES = ["Ha Noi", "Sai Gon", "Da Nang", "Da Lat", "Nha Trang", "Phu Quoc", "Sa Pa", "Hoi An", "Hue", "Vung Tau"]

# ═══════════════ HELPERS ═══════════════
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def api(method, path, data=None):
    url = f"{API_BASE}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=30)
        else:
            r = requests.post(url, json=data, timeout=30)
        if r.status_code == 200:
            try:
                return r.json()
            except:
                log(f"API non-JSON response: {r.text[:200]}")
                return None
        log(f"API {method} {path}: HTTP {r.status_code} - {r.text[:200]}")
        return None
    except Exception as e:
        log(f"API error: {e}")
        return None

def get_profiles():
    r = api("GET", "/api/v1/user/list?page=1&page_size=50")
    if r and r.get("code") == 0:
        return [p for p in r["data"]["list"] if p.get("name") != "Default Profile"]
    return []

def open_browser(user_id):
    return api("POST", "/api/v1/browser/start", {"user_id": user_id})

def close_browser(user_id):
    return api("POST", "/api/v1/browser/stop", {"user_id": user_id})

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=True))

def load_today():
    if TODAY_FILE.exists():
        d = json.loads(TODAY_FILE.read_text())
        if d.get("date") == datetime.now().strftime("%Y-%m-%d"):
            return d
    return {"date": datetime.now().strftime("%Y-%m-%d"), "ran": []}

def save_today(data):
    TODAY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def gen_caption(interest):
    t = random.choice(CAPTIONS.get(interest, CAPTIONS["du lich"]))
    return t.replace("{place}", random.choice(PLACES))

# ═══════════════ SETUP ═══════════════
def setup():
    profiles = get_profiles()
    cookie_files = sorted(glob.glob(str(COOKIE_DIR / "*.txt")))[:12]
    
    state = {}
    for i, p in enumerate(profiles):
        name = p.get("name", "")
        uid = p.get("user_id", "")
        interest = INTERESTS[i] if i < len(INTERESTS) else "du lich"
        cf = cookie_files[i] if i < len(cookie_files) else None
        
        state[name] = {
            "id": uid,
            "cookie_file": cf,
            "interest": interest,
            "day": 1,
            "cookie_imported": False,
        }
    
    save_state(state)
    log(f"Setup {len(state)} profiles!")
    return state

# ═══════════════ PROCESS ONE NICK ═══════════════
def process_nick(name, info):
    uid = info["id"]
    day = info.get("day", 1)
    interest = info.get("interest", "du lich")
    imported = info.get("cookie_imported", False)
    
    log(f"\n{'='*40}\n👤 {name} | Day {day}\n{'='*40}")
    
    # Open browser
    result = open_browser(uid)
    if not result:
        log("Open failed - API returned None")
        return False
    if result.get("code") != 0:
        log(f"Open failed - code={result.get('code')} msg={result.get('msg','?')}")
        return False
    
    ws = result.get("data", {}).get("ws", {})
    debug_port = ws.get("puppeteer", "")
    if not debug_port:
        debug_port = result.get("data", {}).get("debug_port", "")
    log(f"Browser: port={debug_port}")
    
    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
        driver = webdriver.Chrome(options=options)
        
        # GO TO FACEBOOK
        driver.get("https://facebook.com")
        time.sleep(random.uniform(3, 5))
        
        # IMPORT COOKIE FIRST TIME
        if not imported and info.get("cookie_file"):
            cf = info["cookie_file"]
            if os.path.exists(cf):
                try:
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
                    
                    info["cookie_imported"] = True
                    log(f"Imported {len(cookies_data)} cookies")
                    driver.refresh()
                    time.sleep(3)
                except Exception as e:
                    log(f"Cookie err: {e}")
        
        # ── NUÔI NICK ──
        for _ in range(random.randint(2, 5)):
            driver.execute_script(f"window.scrollBy(0, {random.randint(200,500)});")
            time.sleep(random.uniform(1.5, 4))
        
        if day <= 3:
            log("🌱 Day 1-3: U nick - watch")
            driver.get("https://facebook.com/watch")
            time.sleep(random.uniform(10, 20))
            
        elif day <= 7:
            log("🌿 Day 4-7: Like")
            try:
                likes = driver.find_elements(By.CSS_SELECTOR, '[aria-label="Like"], [aria-label="Thich"]')
                random.shuffle(likes)
                for btn in likes[:random.randint(1, 3)]:
                    try:
                        btn.click()
                        time.sleep(random.uniform(5, 12))
                    except: pass
            except: pass
            
        elif day <= 14:
            log("🌳 Day 8-14: Post + interact")
            if random.random() < 0.4:
                caption = gen_caption(interest)
                log(f"Posting: {caption[:60]}...")
                try:
                    driver.get("https://facebook.com")
                    time.sleep(random.uniform(3, 5))
                    
                    # Click create post
                    for b in driver.find_elements(By.CSS_SELECTOR, '[role="button"]'):
                        if b.text and "nghĩ" in b.text.lower():
                            b.click()
                            time.sleep(3)
                            editors = driver.find_elements(By.CSS_SELECTOR, '[contenteditable="true"]')
                            if editors:
                                for char in caption:
                                    editors[0].send_keys(char)
                                    time.sleep(random.uniform(0.02, 0.08))
                                time.sleep(2)
                                # Set public
                                try:
                                    for btn in driver.find_elements(By.CSS_SELECTOR, '[role="button"]'):
                                        if "công khai" in btn.text.lower():
                                            btn.click(); time.sleep(1)
                                            for opt in driver.find_elements(By.CSS_SELECTOR, '[role="menuitem"]'):
                                                if "công khai" in opt.text.lower():
                                                    opt.click(); break
                                            break
                                except: pass
                                # Click Post
                                for btn in driver.find_elements(By.CSS_SELECTOR, '[role="button"]'):
                                    if btn.text.strip() in ["Đăng", "Post"]:
                                        btn.click()
                                        log("Posted!")
                                        break
                            break
                except Exception as e:
                    log(f"Post err: {e}")
            
            driver.get("https://facebook.com/notifications")
            time.sleep(random.uniform(3, 6))
        
        driver.quit()
        info["day"] = day + 1
        return True
        
    except Exception as e:
        log(f"Error: {e}")
        try: driver.quit()
        except: pass
        return False
    finally:
        close_browser(uid)

# ═══════════════ MAIN ═══════════════
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
        sys.exit(0)
    
    state = load_state()
    if not state:
        log("Chay setup truoc: python fb_local.py setup")
        sys.exit(1)
    
    today = load_today()
    profiles = list(state.items())
    random.shuffle(profiles)
    
    available = [(n,i) for n,i in profiles if n not in today["ran"]]
    if not available:
        log("All done today!")
        save_today({"date": datetime.now().strftime("%Y-%m-%d"), "ran": []})
        sys.exit(0)
    
    batch = random.sample(available, random.randint(2, min(4, len(available))))
    log(f"Batch: {len(batch)}/{len(profiles)} nicks")
    
    for name, info in batch:
        time.sleep(random.randint(60, 600))
        process_nick(name, info)
        today["ran"].append(name)
    
    save_state(state)
    save_today(today)
    log(f"Done! {len(today['ran'])}/12 today")
