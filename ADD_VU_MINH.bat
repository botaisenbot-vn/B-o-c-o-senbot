@echo off
echo Them Vũ minh vao danh sach...
python -c "import json; s=json.load(open('nick_state.json')); s['FB_Vu_minh']={'id':'','cookie_file':'','interest':'vui choi','day':1,'cookie_imported':False}; json.dump(s,open('nick_state.json','w'),ensure_ascii=False,indent=2); print('Done! '+str(len(s))+' profiles')"
pause
