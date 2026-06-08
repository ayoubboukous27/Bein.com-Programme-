from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

EPG_DAYS = 15
BASE_DIR = Path(__file__).resolve().parent.parent

HTML_FILE = BASE_DIR / "epg_2026-06-10.html"
CHANNELS_FILE = BASE_DIR / "channels" / "bein.com.channels.full.logo.xml"
OUTPUT_FILE = BASE_DIR / "output" / "guide.xml"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

MAX_POSTER = "https://github.com/ayoubboukous27/Multi-providers-EPG-/raw/refs/heads/main/OG_FB_1200x630_ar.jpg"
DEFAULT_POSTER = "https://github.com/ayoubboukous27/Multi-providers-EPG-/raw/refs/heads/main/maxresdefault.jpg"

# Load channels
tree = ET.parse(CHANNELS_FILE)
root = tree.getroot()
channels = {}
for ch in root.findall("channel"):
    site_id = ch.attrib.get("id") or ch.attrib.get("site_id")
    channels[site_id] = {
        "name": (ch.text or site_id).strip(),
        "logo": ch.attrib.get("logo", "")
    }

# XMLTV root
tv = ET.Element("tv", {"generator-info-name": "beIN GitHub EPG"})

# Add channels
for site_id, info in channels.items():
    ch_elem = ET.SubElement(tv, "channel", id=site_id)
    ET.SubElement(ch_elem, "display-name").text = info["name"]
    if info["logo"]:
        ET.SubElement(ch_elem, "icon", src=info["logo"])

# Parse HTML
with open(HTML_FILE, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

items = soup.find_all("li", attrs={"data-start": True})

for item in items:
    parent_div = item.find_parent("div", id=lambda x: x and x.startswith("channels_"))
    if not parent_div:
        continue
    channel_id = parent_div.get("id", "beINSPORTS1")
    # Poster selection
    if channel_id.upper() in ["BEINSPORTSMAX1","BEINSPORTSMAX2","BEINSPORTSMAX3","BEINSPORTSMAX4","BEINSPORTSMAX5","BEINSPORTSMAX6","BEINSPORTS4KHDR"]:
        poster = MAX_POSTER
    else:
        poster = DEFAULT_POSTER

    title_tag = item.find("p", class_="title")
    if not title_tag:
        continue
    title = title_tag.get_text(strip=True)

    # Description
    description = item.get("data-desc", "")
    desc_tag = item.find("p", class_="description")
    if desc_tag:
        description = desc_tag.get_text(" ", strip=True)
    if not description:
        description = f"Watch {title} live on beIN Sports."

    # Category
    category_tag = item.find("p", class_="format")
    category = category_tag.get_text(strip=True) if category_tag else ""

    # Start / End
    try:
        start_hour = int(item.get("data-start", "0"))
        start_min = int(item.get("data-start-m", "0"))
        end_hour = int(item.get("data-end", "0"))
        end_min = int(item.get("data-end-m", "0"))
    except:
        continue

    current_date = datetime.utcnow()
    start_dt = datetime(current_date.year, current_date.month, current_date.day, start_hour, start_min)
    end_dt = datetime(current_date.year, current_date.month, current_date.day, end_hour, end_min)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    prog = ET.SubElement(tv, "programme", {
        "channel": channel_id,
        "start": start_dt.strftime("%Y%m%d%H%M%S +0000"),
        "stop": end_dt.strftime("%Y%m%d%H%M%S +0000")
    })
    ET.SubElement(prog, "title", lang="ar").text = title
    ET.SubElement(prog, "desc").text = description  # <- بدون lang
    if category:
        ET.SubElement(prog, "category").text = category
    if poster:
        ET.SubElement(prog, "icon", src=poster)

# Save XML
ET.ElementTree(tv).write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
print(f"Guide saved to: {OUTPUT_FILE}")
