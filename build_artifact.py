# -*- coding: utf-8 -*-
"""
สร้างไฟล์หน้าเว็บแบบไฟล์เดียว (ฝัง data.js ไว้ข้างใน) สำหรับเอาขึ้นออนไลน์
ใช้: python build_artifact.py   ->  ได้ไฟล์ online.html
แล้วบอก Claude ว่า "อัปเดตหน้าออนไลน์" เพื่อ publish ทับลิงก์เดิม
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

here = Path(__file__).parent
html = (here / "index.html").read_text(encoding="utf-8")
data = (here / "data.js").read_text(encoding="utf-8")

# หน้า artifact ถูกครอบด้วย <html><head>...</head><body> ให้อยู่แล้ว
# จึงส่งเฉพาะเนื้อใน head + body และห้ามมี <meta>/<!doctype> ของตัวเอง
head = re.search(r"<head>(.*)</head>", html, re.S).group(1)
head = re.sub(r"<meta[^>]*>", "", head).strip()
body = re.search(r"<body>(.*)</body>", html, re.S).group(1)

# หน้า artifact เป็นภาพนิ่ง ไม่มีไฟล์ data.js ให้โหลดซ้ำ จึงตัดปุ่มที่ต้องใช้ไฟล์นั้นออก
body = re.sub(r"<!--live-only-->.*?<!--/live-only-->", "", body, flags=re.S)

# CSP ของ artifact บล็อกไฟล์ภายนอก ต้องฝัง data.js ลงในหน้าเดียว
body = body.replace('<script src="data.js"></script>', "<script>" + data + "</script>")
if "window.EGP_DATA" not in body:
    raise SystemExit("ฝังข้อมูลไม่สำเร็จ — ตรวจว่า index.html ยังอ้าง data.js อยู่")

out = here / "online.html"
out.write_text(head + "\n" + body, encoding="utf-8")
n = data.count('"pid"')
print(f"สร้าง {out.name} แล้ว ({out.stat().st_size:,} bytes, {n} โครงการ)")
print("ขั้นต่อไป: บอก Claude ว่า 'อัปเดตหน้าออนไลน์' เพื่อ publish ทับลิงก์เดิม")
