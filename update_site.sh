#!/bin/bash
# Auto-update Senbot Dashboard data
# Chạy từ cron job sau khi các script phân tích đã chạy xong

cd /root/dashboard

# Tạo data.json mới
python3 generate_data.py

# Push lên GitHub
git add data.json
git commit -m "📊 Update: $(date '+%d/%m/%Y %H:%M')" || true
git push origin main 2>&1

echo "✅ Dashboard updated!"
