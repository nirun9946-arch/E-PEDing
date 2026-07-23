# -*- coding: utf-8 -*-
"""
EGP Bid Finder for Nation
ดึงประกาศจัดซื้อจัดจ้างจากระบบ e-GP (กรมบัญชีกลาง) แล้วกรองเฉพาะงานที่
เนชั่น (สื่อ/ทีวี/PR/อีเวนต์/คอนเทนต์) มีศักยภาพเข้าประมูลได้

ใช้: python egp_fetcher.py [--days 21]
ผลลัพธ์: data.js + data.json แล้วเปิด index.html ดู dashboard
"""
import argparse
import datetime
import html as htmlmod
import io
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "https://process3.gprocurement.go.th"
SEARCH_URL = BASE + "/egp2procmainWeb/jsp/procsearch.sch"

# ---------------------------------------------------------------- ค้นหา
# ประเภทประกาศที่ยังเข้าประมูลได้
ANNOUNCE_TYPES = {
    "1": "ร่าง TOR/ร่างเอกสารประกวดราคา",
    "2": "ประกาศเชิญชวน",
}

# คำค้นที่ตรงกับธุรกิจของเนชั่น (สื่อ ทีวี ข่าว PR อีเวนต์ คอนเทนต์)
KEYWORDS = [
    "ประชาสัมพันธ์",
    "ผลิตสื่อ",
    "เผยแพร่",
    "โทรทัศน์",
    "สื่อออนไลน์",
    "โฆษณา",
    "วีดิทัศน์",
    "สารคดี",
    "จัดกิจกรรม",
    "จัดงาน",
    "นิทรรศการ",
    "คอนเทนต์",
    "การตลาดดิจิทัล",
    "สกู๊ป",
    "ออกอากาศ",
    "สื่อสารการตลาด",
]

# ---------------------------------------------------------------- คะแนนความเหมาะสม
# คำที่บ่งว่าเป็นงานสายสื่อ/PR จริง (บวก)
POSITIVE = {
    "ประชาสัมพันธ์": 3, "ผลิตสื่อ": 4, "สื่อโทรทัศน์": 5, "โทรทัศน์": 3,
    "ออกอากาศ": 4, "เผยแพร่": 2, "วีดิทัศน์": 3, "สารคดี": 4, "สกู๊ป": 5,
    "รายการ": 2, "โฆษณา": 3, "สื่อออนไลน์": 3, "โซเชียลมีเดีย": 3,
    "สื่อสังคมออนไลน์": 3, "คอนเทนต์": 3, "เนื้อหา": 1, "ข่าว": 2,
    "แถลงข่าว": 3, "จัดกิจกรรม": 2, "จัดงาน": 2, "อีเวนต์": 3, "event": 3,
    "นิทรรศการ": 2, "การตลาดดิจิทัล": 4, "digital": 2, "influencer": 4,
    "สื่อมวลชน": 3, "ภาพลักษณ์": 3, "แคมเปญ": 3, "สปอต": 4, "สื่อสิ่งพิมพ์": 2,
    "วารสาร": 2, "สื่อสารองค์กร": 3, "รณรงค์": 2, "สร้างการรับรู้": 3,
    "ถ่ายทอดสด": 3, "คลิป": 2, "วิดีโอ": 2, "มัลติมีเดีย": 2, "โซเชียล": 2,
}

# คำที่บ่งว่าไม่ใช่งานของเนชั่น (ลบ)
NEGATIVE = {
    "ก่อสร้าง": -8, "ปรับปรุงอาคาร": -6, "ซ่อมแซม": -6, "ถนน": -8,
    "ประปา": -8, "ไฟฟ้าแสงสว่าง": -6, "ครุภัณฑ์": -5, "ทำความสะอาด": -8,
    "รักษาความปลอดภัย": -8, "ป้ายไวนิล": -4, "ติดตั้งป้าย": -4,
    "เช่าเครื่อง": -5, "ยานพาหนะ": -6, "ระบบคอมพิวเตอร์": -3,
    "เครื่องปรับอากาศ": -8, "วัสดุ": -4, "อาหาร": -3, "ตรวจสุขภาพ": -8,
    "ประกันภัย": -8, "ขุดลอก": -8, "ปุ๋ย": -8, "เมล็ดพันธุ์": -8,
    "ป้าย": -5, "LED": -4, "จอแสดงผล": -4, "เสียงตามสาย": -6,
    "หอกระจายข่าว": -6, "กล้องโทรทัศน์วงจรปิด": -8, "วงจรปิด": -8, "CCTV": -8,
}


def score_project(title: str) -> tuple[int, list[str]]:
    """ให้คะแนนความเหมาะสมกับเนชั่น พร้อมรายการคำที่แมตช์"""
    score = 0
    hits = []
    for word, w in POSITIVE.items():
        if word.lower() in title.lower():
            score += w
            hits.append(word)
    for word, w in NEGATIVE.items():
        if word in title:
            score += w
    # งาน "ซื้อ" (จัดหาของ) ไม่ใช่งานบริการสื่อ
    if title.startswith("ประกวดราคาซื้อ") or title.startswith("ซื้อ"):
        score -= 6
    return score, hits


def fit_label(score: int) -> str:
    if score >= 6:
        return "เหมาะมาก"
    if score >= 3:
        return "น่าสนใจ"
    return "เกี่ยวข้องน้อย"


# ---------------------------------------------------------------- HTTP
def build_opener():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    jar = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPSHandler(context=ctx),
    )
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
    ]
    return opener


def now_th() -> datetime.datetime:
    """เวลาไทย — เครื่อง GitHub Actions รันเป็น UTC ต้องบวก 7 ชม.เอง
    ไม่งั้นช่วงวันที่ที่ค้นจะเพี้ยนไปหนึ่งวัน"""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))


def thai_date(d: datetime.date) -> str:
    """dd/mm/yyyy แบบ พ.ศ."""
    return f"{d.day:02d}/{d.month:02d}/{d.year + 543}"


def search_egp(opener, keyword: str, announce_type: str, sdate: str, edate: str,
               beginrec: str = "", endrec: str = "", grouppage: str = "") -> str:
    params = {
        "servlet": "FPRO9965Servlet",
        "proc_id": "FPRO9965",
        "proc_name": "Procure",
        "processFlows": "Procure",
        "mode": "SEARCH",
        "homeflag": "A",
        "announceType": announce_type,
        "budgetYear": "",
        "govStatus": "A",
        "moiId": "", "deptId": "", "deptSubId": "", "provId": "",
        "methodId": "", "typeId": "", "project_id": "",
        "projectName": keyword,
        "announceSDate": sdate,
        "announceEDate": edate,
        "projectMoneyS": "", "projectMoneyE": "",
        "projectStatus": "", "priceBuild": "",
        "beginrec": beginrec, "endrec": endrec, "grouppage": grouppage,
    }
    body = urllib.parse.urlencode(
        {k: v.encode("cp874", errors="ignore") for k, v in params.items()})
    req = urllib.request.Request(SEARCH_URL, data=body.encode("ascii"), headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })
    for attempt in range(3):
        try:
            with opener.open(req, timeout=90) as r:
                return r.read().decode("cp874", errors="replace")
        except Exception as e:
            if attempt == 2:
                raise
            print(f"    ! retry ({e})")
            time.sleep(3)
    return ""


# ---------------------------------------------------------------- Parser
ROW_RE = re.compile(
    r'<tr id="trDetail\d+".*?<td align="left">(?P<dept>[^<]*)</td>.*?'
    r"(?P<func>showPopup\w*)\((?P<args>[^)]*)\)\">(?P<title>.*?)</span>.*?"
    r'<td align="center">(?P<date>[\d/]+)(?:<br>&nbsp;-&nbsp;(?P<date_end>[\d/]+))?&nbsp;</td>.*?'
    r'<td align="right">(?P<money>[\d,.]+|)&nbsp;?</td>.*?'
    r'<td align="center">(?P<status>[^<]*)</td>',
    re.S,
)

# หน้า e-GP เปิดประกาศผ่าน JS popup — เราจำลอง URL เดียวกันเพื่อให้ลิงก์คลิกเปิดประกาศจริงได้
# ร่าง TOR/ประกาศที่มี arg เดียว -> FPRO9951A_2.jsp ; ประกาศเชิญชวน (8 args) -> FPRO9951A_3.jsp
POPUP_A2 = {"showPopupFileNew", "showPopupFile"}
POPUP_A4 = {"showPopup150Type9", "showPopupFile3"}   # วงเงินสูง ใช้เทมเพลต A_4


def build_announce_link(func: str, args: list[str]) -> str:
    base = BASE + "/egp2procmainWeb/jsp/"
    pid = args[0] if args else ""
    if func in POPUP_A2 or len(args) < 8:
        return base + "FPRO9951A_2.jsp?tor_project_id=" + urllib.parse.quote(pid)
    jsp = "FPRO9951A_4.jsp" if func in POPUP_A4 else "FPRO9951A_3.jsp"
    q = urllib.parse.urlencode({
        "tor_project_id": args[0],
        "invite_templateType": args[1],
        "invite_announceFlag": args[2],
        "invite_itemNo": args[3],
        "invite_seqno": args[4],
        "invite_methodId": args[5],
        "intvite_docAnnounceType": args[6],   # (สะกดตามระบบ e-GP)
        "invite_announceId": args[7],
    })
    return base + jsp + "?" + q


def clean(s: str) -> str:
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).replace("\xa0", " ").strip()


def parse_rows(page_html: str) -> list[dict]:
    rows = []
    for m in ROW_RE.finditer(page_html):
        title = clean(re.sub(r"<[^>]+>", "", m.group("title")))
        # ตัด "(เลขที่โครงการ : xxx)" ท้ายชื่อ
        title = re.sub(r"\s*\(เลขที่โครงการ\s*:\s*\d+\)\s*$", "", title)
        money_s = m.group("money").replace(",", "")
        args = re.findall(r"'([^']*)'", m.group("args"))
        pid = args[0] if args else ""
        rows.append({
            "pid": pid,
            "dept": clean(m.group("dept")),
            "title": title,
            "date": m.group("date"),
            "date_end": m.group("date_end") or "",
            "budget": float(money_s) if money_s else 0.0,
            "status": clean(m.group("status")),
            "link": build_announce_link(m.group("func"), args),
        })
    return rows


# ---------------------------------------------------------------- Main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=21,
                    help="ย้อนหลังกี่วัน (ค่าเริ่มต้น 21)")
    ap.add_argument("--max-pages", type=int, default=3,
                    help="จำนวนหน้าสูงสุดต่อคำค้น (หน้าละ 50 รายการ)")
    args = ap.parse_args()

    today = now_th().date()
    sdate = thai_date(today - datetime.timedelta(days=args.days))
    edate = thai_date(today)
    print(f"ค้นหาประกาศ e-GP ช่วง {sdate} - {edate}")

    opener = build_opener()
    # เปิดหน้าแรกก่อนเพื่อรับ cookie
    try:
        opener.open(BASE + "/EGPWeb/jsp/index_new.jsp", timeout=60).read()
    except Exception:
        pass

    projects: dict[str, dict] = {}
    n_req = 0
    for atype, atype_name in ANNOUNCE_TYPES.items():
        for kw in KEYWORDS:
            found_kw = 0
            for page in range(args.max_pages):
                beginrec = "" if page == 0 else str(page * 50 + 1)
                endrec = "" if page == 0 else str((page + 1) * 50 + 1)
                grouppage = "" if page == 0 else str(page + 1)
                try:
                    page_html = search_egp(opener, kw, atype, sdate, edate,
                                           beginrec, endrec, grouppage)
                except Exception as e:
                    print(f"  x {atype_name} '{kw}' หน้า {page+1}: {e}")
                    break
                n_req += 1
                rows = parse_rows(page_html)
                found_kw += len(rows)
                for row in rows:
                    key = row["pid"] + "|" + atype
                    p = projects.get(key)
                    if p:
                        if kw not in p["matched_keywords"]:
                            p["matched_keywords"].append(kw)
                        continue
                    row["announce_type"] = atype_name
                    row["matched_keywords"] = [kw]
                    projects[key] = row
                if len(rows) < 50:
                    break
            print(f"  - {atype_name} | '{kw}' : {found_kw} รายการ")

    # ให้คะแนนและคัดกรอง
    def tor_still_open(p: dict) -> bool:
        """ร่าง TOR ที่เลยวันสิ้นสุดรับฟังคำวิจารณ์แล้ว ยื่นไม่ทัน ไม่เอาเข้าเว็บ"""
        if "TOR" not in p["announce_type"] or not p.get("date_end"):
            return True
        try:
            dd, mm, yy = (int(x) for x in p["date_end"].split("/"))
            return datetime.date(yy - 543, mm, dd) >= today
        except ValueError:
            return True

    items = []
    for p in projects.values():
        if not tor_still_open(p):
            continue
        score, hits = score_project(p["title"])
        for kw in p["matched_keywords"]:
            if kw not in hits:
                hits.append(kw)
        if score < 1:          # ตัดงานที่ไม่เกี่ยวออก
            continue
        p["score"] = score
        p["fit"] = fit_label(score)
        p["hits"] = hits
        items.append(p)

    items.sort(key=lambda x: (-x["score"], -x["budget"]))

    here = Path(__file__).parent
    # ถ้าวันไหน e-GP ล่ม/ถูกบล็อก จะได้ 0 รายการ — อย่าทับข้อมูลดีที่มีอยู่
    old = here / "data.json"
    if not items and old.exists():
        try:
            prev = json.loads(old.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prev = {}
        if prev.get("items"):
            print(f"ดึงข้อมูลไม่ได้เลย (0 รายการ) — คงข้อมูลเดิมไว้ "
                  f"{len(prev['items'])} โครงการ จาก {prev.get('fetched_at')}")
            return 2

    out = {
        "fetched_at": (lambda n: f"{n.day:02d}/{n.month:02d}/{n.year + 543} {n:%H:%M}")(now_th()),
        "range": {"from": sdate, "to": edate},
        "total": len(items),
        "requests": n_req,
        "items": items,
    }
    (here / "data.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (here / "data.js").write_text(
        "window.EGP_DATA = " + json.dumps(out, ensure_ascii=False) + ";",
        encoding="utf-8")
    print(f"\nสรุป: พบงานที่เนชั่นบิดได้ {len(items)} โครงการ "
          f"(จากการยิง {n_req} คำค้น) -> data.js / data.json")
    top = items[:5]
    for t in top:
        print(f"  [{t['fit']}] {t['title'][:80]}  งบ {t['budget']:,.0f} บ. ({t['dept'][:40]})")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
