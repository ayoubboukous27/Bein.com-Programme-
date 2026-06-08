from pathlib import Path
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

# ── إعدادات ──────────────────────────────────────────────
EPG_DAYS   = 10
EPG_OFFSET = -2   # offset المستخدم في API

BASE_DIR       = Path(__file__).resolve().parent.parent
CHANNELS_FILE  = BASE_DIR / "channels" / "bein.com.channels.full.logo.xml"
OUTPUT_FILE    = BASE_DIR / "output" / "guide.xml"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

POSTER_MAX     = "https://github.com/ayoubboukous27/Multi-providers-EPG-/raw/refs/heads/main/OG_FB_1200x630_ar.jpg"
POSTER_DEFAULT = "https://github.com/ayoubboukous27/Multi-providers-EPG-/raw/refs/heads/main/maxresdefault.jpg"

MAX_CHANNELS = {
    "BEINSPORTSMAX1", "BEINSPORTSMAX2", "BEINSPORTSMAX3",
    "BEINSPORTSMAX4", "BEINSPORTSMAX5", "BEINSPORTSMAX6",
    "BEINSPORTS4KHDR",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ── تحميل ملف القنوات ────────────────────────────────────
def load_channels(path: Path) -> dict:
    tree = ET.parse(path)
    channels = {}
    for ch in tree.getroot().findall("channel"):
        site_id = (ch.attrib.get("id") or ch.attrib.get("site_id", "")).strip()
        if not site_id:
            continue
        channels[site_id] = {
            "name": (ch.text or site_id).strip(),
            "logo": ch.attrib.get("logo", ""),
        }
    return channels

# ── بناء عنصر القناة في XMLTV ────────────────────────────
def build_channel_elements(tv_root, channels: dict):
    for site_id, info in channels.items():
        ch_elem = ET.SubElement(tv_root, "channel", id=site_id)
        ET.SubElement(ch_elem, "display-name").text = info["name"]
        if info["logo"]:
            ET.SubElement(ch_elem, "icon", src=info["logo"])

# ── سحب صفحة يوم واحد ───────────────────────────────────
def fetch_day_html(date_str: str) -> str:
    url = (
        "https://www.bein.com/en/epg-ajax-template/"
        f"?action=epg_fetch&offset={EPG_OFFSET}&category=sports"
        "&serviceidentity=bein.net&mins=00"
        f"&cdate={date_str}&language=EN&postid=25356&loadindex=0"
    )
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.text

# ── استخراج channel_id من div الأب ──────────────────────
def extract_channel_id(item) -> str | None:
    parent = item.find_parent("div", id=lambda x: x and x.startswith("channels_"))
    if not parent:
        return None
    # "channels_BEINSPORTS1"  →  "BEINSPORTS1"
    raw_id = parent["id"].replace("channels_", "", 1).strip().upper()
    return raw_id or None

# ── تحويل ساعة + دقيقة إلى datetime مع تطبيق الـ offset ─
def make_dt(base_date: datetime, hour: int, minute: int) -> datetime:
    """
    API يرسل أوقاتاً بحسب offset.
    نحوّلها إلى UTC الحقيقي: نطرح الـ offset (offset=-2 → نضيف 2 ساعة)
    """
    local_dt = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    utc_dt   = local_dt - timedelta(hours=EPG_OFFSET)   # -(-2) = +2
    return utc_dt

# ── معالجة برنامج واحد ──────────────────────────────────
def parse_programme(item, base_date: datetime) -> dict | None:
    channel_id = extract_channel_id(item)
    if not channel_id:
        return None

    title_tag = item.find("p", class_="title")
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)
    if not title:
        return None

    # وصف: نفضّل desc_tag على data-desc
    desc_tag    = item.find("p", class_="description")
    description = (
        desc_tag.get_text(" ", strip=True)
        if desc_tag
        else item.get("data-desc", "").strip()
    ) or f"Watch {title} live on beIN Sports."

    # تصنيف
    cat_tag  = item.find("p", class_="format")
    category = cat_tag.get_text(strip=True) if cat_tag else ""

    # توقيت
    try:
        start_h = int(item["data-start"])
        start_m = int(item.get("data-start-m", "0"))
        end_h   = int(item["data-end"])
        end_m   = int(item.get("data-end-m", "0"))
    except (KeyError, ValueError):
        return None

    start_dt = make_dt(base_date, start_h, start_m)
    end_dt   = make_dt(base_date, end_h,   end_m)

    # برنامج يتخطى منتصف الليل
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    poster = POSTER_MAX if channel_id in MAX_CHANNELS else POSTER_DEFAULT

    return {
        "channel_id":  channel_id,
        "title":       title,
        "description": description,
        "category":    category,
        "start_dt":    start_dt,
        "end_dt":      end_dt,
        "poster":      poster,
    }

# ── إضافة برنامج إلى XMLTV ──────────────────────────────
FMT = "%Y%m%d%H%M%S +0000"

def add_programme(tv_root, prog: dict):
    elem = ET.SubElement(tv_root, "programme", {
        "channel": prog["channel_id"],
        "start":   prog["start_dt"].strftime(FMT),
        "stop":    prog["end_dt"].strftime(FMT),
    })
    ET.SubElement(elem, "title", lang="ar").text = prog["title"]
    ET.SubElement(elem, "desc").text               = prog["description"]
    if prog["category"]:
        ET.SubElement(elem, "category").text = prog["category"]
    ET.SubElement(elem, "icon", src=prog["poster"])

# ── الحلقة الرئيسية ──────────────────────────────────────
def main():
    channels = load_channels(CHANNELS_FILE)

    tv = ET.Element("tv", {"generator-info-name": "beIN GitHub EPG"})
    build_channel_elements(tv, channels)

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    for day in range(EPG_DAYS):
        base_date = today + timedelta(days=day)
        date_str  = base_date.strftime("%Y-%m-%d")
        print(f"[{day+1}/{EPG_DAYS}] Fetching {date_str} …")

        try:
            html = fetch_day_html(date_str)
        except requests.RequestException as e:
            print(f"  ⚠ فشل جلب {date_str}: {e}")
            continue

        soup  = BeautifulSoup(html, "html.parser")
        items = soup.find_all("li", attrs={"data-start": True})
        count = 0

        for item in items:
            prog = parse_programme(item, base_date)
            if prog:
                add_programme(tv, prog)
                count += 1

        print(f"  ✓ {count} برنامج")

    ET.ElementTree(tv).write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
    print(f"\nتم الحفظ في: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
