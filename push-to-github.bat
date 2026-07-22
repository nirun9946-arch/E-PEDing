@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===============================================
echo   ส่ง E-peding ขึ้น GitHub
echo ===============================================
echo.
echo ก่อนรันต่อ ให้สร้าง repo เปล่าไว้ก่อนที่ https://github.com/new
echo   - ชื่อ repo: e-peding (หรือชื่ออื่นที่ชอบ)
echo   - เลือก Public  (เว็บ GitHub Pages ฟรีต้องเป็น Public)
echo   - อย่าติ๊ก Add a README / .gitignore / license
echo.
set /p GHUSER=พิมพ์ชื่อผู้ใช้ GitHub ของคุณ แล้วกด Enter:
set /p GHREPO=พิมพ์ชื่อ repo ที่เพิ่งสร้าง แล้วกด Enter:
echo.
echo กำลังส่งขึ้น https://github.com/%GHUSER%/%GHREPO% ...
echo (ถ้ามีหน้าต่างให้ล็อกอิน GitHub เด้งขึ้นมา ให้ล็อกอินตามปกติ)
echo.
git remote remove origin 2>nul
git remote add origin https://github.com/%GHUSER%/%GHREPO%.git
git push -u origin main
if errorlevel 1 (
  echo.
  echo ส่งไม่สำเร็จ - เช็คว่าสร้าง repo แล้ว และชื่อผู้ใช้/ชื่อ repo ถูกต้อง
  pause
  exit /b 1
)
echo.
echo ===============================================
echo   ส่งขึ้น GitHub สำเร็จแล้ว
echo ===============================================
echo.
echo เหลืออีก 2 อย่างให้ตั้งค่าในหน้าเว็บ repo:
echo.
echo  1) เปิดเว็บ: Settings -^> Pages
echo     Source = Deploy from a branch, Branch = main, โฟลเดอร์ = / (root) แล้วกด Save
echo     รอสัก 1-2 นาที เว็บจะขึ้นที่
echo     https://%GHUSER%.github.io/%GHREPO%/
echo.
echo  2) ให้ตัวดึงข้อมูลบันทึกผลได้: Settings -^> Actions -^> General
echo     หัวข้อ Workflow permissions เลือก "Read and write permissions" แล้วกด Save
echo.
echo จากนั้นข้อมูลจะอัปเดตเองทุกวัน 08:00 น. เวลาไทย
echo (กดรันเองได้ที่แท็บ Actions -^> ดึงข้อมูล e-GP ทุกวัน -^> Run workflow)
echo.
pause
