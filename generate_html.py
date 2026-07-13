#!/usr/bin/env python3
"""Generate dashboard HTML from data.json — now with 4 tabs including Inbox."""
import json

with open('/root/dashboard/data.json', 'r') as f:
    data = json.load(f)

def gen_section(d):
    t = d.get('type','')
    h = f'<div class="report"><div class="rtitle">{d.get("title","")}</div><div class="rbody">\n'
    
    kpis = d.get('kpis', [])
    if kpis:
        h += '<div class="split">\n'
        for k in kpis:
            h += f'<div><div style="font-size:22px;font-weight:700">{k.get("val","—")}</div><div class="small">{k.get("label","")}</div></div>\n'
        h += '</div>\n'
    
    for tbl in d.get('tables', []):
        h += f'<h3>{tbl.get("title","")}</h3>\n<table>\n<tr>'
        for th in tbl.get('headers', []):
            h += f'<th>{th}</th>'
        h += '</tr>\n'
        for row in tbl.get('rows', []):
            h += '<tr>'
            for i, cell in enumerate(row):
                cls = 'num' if i > 0 else ''
                h += f'<td class="{cls}">{cell}</td>'
            h += '</tr>\n'
        h += '</table>\n'
    
    if d.get('conclusion'):
        h += f'<div class="conclusion">{d["conclusion"]}</div>\n'
    
    h += '</div></div>\n'
    return h

# Group sections by type into tabs
tabs = {
    'tai_chinh': {'icon': '💰', 'name': 'Tai chinh', 'sections': []},
    'kinh_doanh': {'icon': '🛒', 'name': 'Kinh doanh', 'sections': []},
    'marketing': {'icon': '📢', 'name': 'Marketing', 'sections': []},
    'inbox': {'icon': '📬', 'name': 'Inbox', 'sections': []},
}

for s in data.get('sections', []):
    t = s.get('type', '')
    if t == 'pnl':
        tabs['tai_chinh']['sections'].append(s)
    elif t in ('sales', 'si'):
        tabs['kinh_doanh']['sections'].append(s)
    elif t == 'marketing':
        tabs['marketing']['sections'].append(s)
    elif t == 'inbox':
        tabs['inbox']['sections'].append(s)

# Build HTML
tab_buttons = []
tab_contents = []
first = True
for tab_id, tab_data in tabs.items():
    active = ' active' if first else ''
    display = 'style="display:block"' if first else ''
    tab_buttons.append(f'<button class="tab{active}" onclick="openTab(event,\'{tab_id}\')">{tab_data["icon"]} {tab_data["name"]}</button>')
    
    content = f'<div id="{tab_id}" class="tab-content" {display}>\n'
    if tab_data['sections']:
        for s in tab_data['sections']:
            content += gen_section(s)
    else:
        content += '<div style="text-align:center;padding:40px;color:#999">Chua co du lieu</div>\n'
    content += '</div>\n'
    tab_contents.append(content)
    first = False

html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Senbot Dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#f5f6fa;color:#1a1a2e;line-height:1.6}}
.header{{background:linear-gradient(135deg,#1a1a2e,#2E86AB);color:#fff;padding:18px 24px;text-align:center}}
.header h1{{font-size:22px}}.header span{{font-size:12px;opacity:.7}}
.container{{max-width:900px;margin:0 auto;padding:0 16px 40px}}
.tabs{{display:flex;background:#fff;border-radius:12px 12px 0 0;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-top:20px}}
.tab{{flex:1;padding:16px 8px;border:none;background:#f8f9fb;font-size:14px;font-weight:600;cursor:pointer;color:#888;transition:all .2s;border-bottom:3px solid transparent;font-family:inherit}}
.tab:hover{{background:#f0f0f0;color:#555}}
.tab.active{{background:#fff;color:#2E86AB;border-bottom:3px solid #2E86AB}}
.tab-content{{background:#fff;padding:20px 24px;border-radius:0 0 12px 12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:20px}}
.report{{margin-bottom:24px}}
.rtitle{{font-size:16px;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0f0f0;margin-bottom:14px}}
h3{{font-size:15px;margin:16px 0 8px;color:#2E86AB}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0 14px}}
th{{text-align:left;padding:8px 10px;background:#f0f4f8;border-bottom:2px solid #dde;font-weight:600;color:#555;font-size:11px}}
td{{padding:8px 10px;border-bottom:1px solid #f0f0f0}}
.num{{text-align:right;font-weight:600}}
.g{{color:#27AE60}}.r{{color:#C0392B}}
.alert{{padding:8px 12px;border-radius:6px;margin:4px 0;font-size:12px}}
.ar{{background:#ffeaea;color:#C0392B;border-left:3px solid #C0392B}}
.ao{{background:#fff8ee;color:#E67E22;border-left:3px solid #E67E22}}
.split{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px 0}}
.split>div{{background:#f8f9fb;border-radius:8px;padding:10px 14px;font-size:13px}}
.good b{{color:#27AE60}}.bad b{{color:#C0392B}}
.conclusion{{background:#f0f7ff;border-left:3px solid #2E86AB;padding:12px 16px;border-radius:6px;margin-top:12px;font-size:13px}}
.small{{font-size:12px;color:#888}}
</style>
</head>
<body>
<div class="header"><h1>Senbot Dashboard</h1><span>{data.get("updated","")}</span></div>
<div class="container">
<div class="tabs">{''.join(tab_buttons)}</div>
{''.join(tab_contents)}
</div>
<script>
function openTab(evt, id) {{
    var tabs = document.getElementsByClassName('tab');
    for (var i = 0; i < tabs.length; i++) tabs[i].classList.remove('active');
    evt.currentTarget.classList.add('active');
    var contents = document.getElementsByClassName('tab-content');
    for (var i = 0; i < contents.length; i++) contents[i].style.display = 'none';
    document.getElementById(id).style.display = 'block';
}}
</script>
</body>
</html>'''

with open('/root/dashboard/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Generated with {len(tab_buttons)} tabs")
for t in tabs:
    print(f"  {tabs[t]['icon']} {tabs[t]['name']}: {len(tabs[t]['sections'])} sections")
