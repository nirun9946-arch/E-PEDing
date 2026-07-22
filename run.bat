@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===============================================
echo   E-peding for Nation
echo   กำลังดึงประกาศจัดซื้อจัดจ้างจากระบบ e-GP ...
echo   (ใช้เวลา 3-8 นาที ขึ้นกับความเร็วเว็บ e-GP)
echo ===============================================
python egp_fetcher.py --days 21
if errorlevel 1 (
  echo.
  echo เกิดข้อผิดพลาด - ตรวจสอบอินเทอร์เน็ตแล้วลองใหม่
  pause
  exit /b 1
)
start "" index.html
echo เสร็จแล้ว - เปิด dashboard ในเบราว์เซอร์
timeout /t 5 >nul
