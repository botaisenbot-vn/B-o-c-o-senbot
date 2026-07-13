@echo off
title Cai dat Auto Check Inbox
echo Dang cai lich check inbox moi 30 phut...

set SCRIPT=%~dp0fb_inbox.py

schtasks /delete /tn "FB_Check_Inbox" /f >nul 2>&1

schtasks /create /tn "FB_Check_Inbox" /tr "python %SCRIPT%" /sc minute /mo 30 /f

echo Xong! Moi 30 phut check 12 nick.
pause
