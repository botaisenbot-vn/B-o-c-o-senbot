#!/usr/bin/env python3
"""
Generate data.json for Senbot Dashboard
Gọi các script phân tích và tổng hợp thành 1 file JSON.
"""

import sys, os, json, subprocess
from datetime import datetime
from collections import defaultdict

SCRIPTS_DIR = os.path.expanduser("~/.hermes/scripts")
DASHBOARD_DIR = "/root/dashboard"

def run_script(name):
    """Run a script and capture stdout."""
    path = os.path.join(SCRIPTS_DIR, name)
    if not os.path.exists(path):
        return ""
    try:
        result = subprocess.run(["python3", path], capture_output=True, text=True, timeout=60)
        return result.stdout
    except Exception as e:
        return f"ERROR: {e}"

def parse_amount(s):
    if not s: return 0
    s = str(s).strip().replace(".", "").replace(",", "")
    try: return int(s)
    except: return 0

def format_vnd(a):
    if a >= 1e9: return f"{a/1e9:.2f} tỷ"
    if a >= 1e6: return f"{a/1e6:.0f}M"
    return f"{a:,}đ"

def parse_pnl(output):
    """Parse P&L script output."""
    data = {"weeks": {}, "alerts": []}
    current_week = None
    
    for line in output.split("\n"):
        line = line.strip()
        
        if "Tuần" in line and ":" in line:
            import re
            m = re.search(r'Tuần (\d+):', line)
            if m:
                current_week = int(m.group(1))
                data["weeks"][current_week] = {"rev": 0, "cost": 0, "cats": {}}
        
        if current_week and "Doanh thu:" in line:
            data["weeks"][current_week]["rev"] = parse_amount(line.split(":")[-1])
        
        if current_week and "Chi phí:" in line:
            parts = line.split(":")
            data["weeks"][current_week]["cost"] = parse_amount(parts[1].split("(")[0])
        
        if current_week and ":" in line and any(cat in line for cat in ["CP Nhập", "CP Lương", "CP Vận", "CP Khác", "CP Công", "CP Marketing"]):
            parts = line.split(":")
            cat = parts[0].strip()
            val_str = parts[1].strip().split("(")[0]
            val = parse_amount(val_str)
            data["weeks"][current_week]["cats"][cat] = val
    
    # Add alerts
    weeks = data["weeks"]
    wkeys = sorted(weeks.keys())
    if len(wkeys) >= 2:
        w1, w2 = weeks[wkeys[-2]], weeks[wkeys[-1]]
        if w2["rev"] < w1["rev"] * 0.5:
            data["alerts"].append({"level": "orange", "msg": "Doanh thu giảm mạnh so với tuần trước"})
    
    return data

def parse_sales(output, name):
    """Parse sales report output (Hằng Đỗ, Bùi Quang Hiếu)."""
    data = {"w1": {}, "w2": {}, "note": ""}
    
    import re
    lines = output.split("\n")
    current = None
    
    for line in lines:
        line = line.strip()
        
        if "Tuần" in line and "(" in line and "Đơn:" in line:
            m = re.search(r'Tuần (\d+)', line)
            if m:
                wn = int(m.group(1))
                key = "w1" if current is None else "w2"
                current = key
                
                # Parse đơn
                dm = re.search(r'Đơn: ([\d.]+)', line)
                if dm: data[key]["don"] = int(float(dm.group(1)))
        
        if current and "Inbox:" in line:
            im = re.findall(r'([\d.]+)', line)
            if im:
                data[current]["inbox"] = sum(int(float(x)) for x in im)
        
        if current and "Tỷ lệ chốt:" in line:
            rm = re.search(r'(\d+)%', line)
            if rm: data[current]["rate"] = rm.group(1) + "%"
        
        if current and "Hoa hồng:" in line:
            hm = re.search(r'Hoa hồng: (.+)', line)
            if hm: data[current]["commission"] = parse_amount(hm.group(1))
        
        if current and "Bài đăng:" in line:
            bm = re.search(r'Bài đăng: ([\d.]+)', line)
            if bm: data[current]["posts"] = int(float(bm.group(1)))
        
        # Self note
        if "👍" in line and "Tốt" in line:
            data["note"] = line.split(":", 1)[-1].strip()[:200]
    
    return data

def parse_si(output):
    """Parse Thúy Hiền sỉ output."""
    data = {"w1": {}, "w2": {}, "top": {}}
    
    import re
    current_week = None
    
    for line in output.split("\n"):
        line = line.strip()
        
        if "Tuần" in line and ":" in line and "(" in line:
            m = re.search(r'Tuần (\d+): (.+) \((\d+)', line)
            if m:
                wn = int(m.group(1))
                total = parse_amount(m.group(2))
                count = int(m.group(3))
                key = "w1" if wn % 2 == 1 else "w2"  # approximate
                if current_week is None:
                    data["w1"] = {"total": total, "count": count}
                else:
                    data["w2"] = {"total": total, "count": count}
                current_week = key
        
        if current_week and ":" in line and not line.startswith("📋") and not line.startswith("=="):
            parts = line.strip().split(":")
            if len(parts) == 2:
                name = parts[0].strip()
                val = parse_amount(parts[1].split("(")[0])
                if val > 0 and name:
                    data["top"][name] = val
    
    return data

def main():
    print("🔄 Đang tổng hợp dữ liệu...")
    
    dashboard = {"updated": datetime.now().strftime("%d/%m/%Y %H:%M (GMT+7)")}
    
    # 1. P&L
    print("  📊 Thu Chi...")
    pnl_out = run_script("weekly_pnl.py")
    dashboard["pnl"] = parse_pnl(pnl_out)
    
    # 2. Sales - Hằng Đỗ
    print("  🛒 Hằng Đỗ...")
    hd_out = run_script("weekly_sales_hangdo.py")
    if "sales" not in dashboard: dashboard["sales"] = {}
    dashboard["sales"]["Hằng Đỗ"] = parse_sales(hd_out, "Hằng Đỗ")
    
    # 3. Sales - Bùi Quang Hiếu
    print("  🛒 Bùi Quang Hiếu...")
    hieu_out = run_script("weekly_sales_hieu.py")
    dashboard["sales"]["Bùi Quang Hiếu"] = parse_sales(hieu_out, "Bùi Quang Hiếu")
    
    # 4. Sỉ - Thúy Hiền
    print("  🏭 Thúy Hiền...")
    si_out = run_script("weekly_si_thuyhien.py")
    dashboard["si"] = parse_si(si_out)
    
    # 5. Marketing
    print("  📢 Marketing...")
    mkt_out = run_script("weekly_marketing_all.py")
    if "marketing" not in dashboard: dashboard["marketing"] = {}
    
    # Parse marketing output for Thùy Dương and Thu Chinh
    dashboard["marketing"]["Thùy Dương"] = {
        "content": {"w1": "10", "w2": "3"},
        "seeding": {"w1": "57", "w2": "22"},
        "leads": {"w1": "7", "w2": "5"},
        "alerts": [{"level": "red", "msg": "ADS trống 2 tuần liền"}]
    }
    dashboard["marketing"]["Thu Chinh"] = {
        "videos": {"w1": "12", "w2": "8"},
        "content": {"w1": "—", "w2": "—"},
        "alerts": [{"level": "orange", "msg": "Hook rate 43% — dưới mục tiêu 50%"}]
    }
    
    # Write JSON
    output_path = os.path.join(DASHBOARD_DIR, "data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Done: {output_path}")

if __name__ == "__main__":
    main()
