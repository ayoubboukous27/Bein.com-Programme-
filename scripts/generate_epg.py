from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

EPG_DAYS = 10

BASE_DIR = Path(__file__).resolve().parent.parent
CHANNELS_FILE = BASE_DIR / "channels" / "bein.com.channels.full.logo.xml"
OUTPUT_FILE = BASE_DIR / "output" / "guide.xml"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Poster URLs
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

# Create XMLTV
tv = ET.Element("tv", {"generator-info-name": "beIN GitHub EPG"})

# Add channels
for site_id, info in channels.items():
    ch_elem = ET.SubElement(tv, "channel", id=site_id)
    ET.SubElement(ch_elem, "display-name").text = info["name"]
    if info["logo"]:
        ET.SubElement(ch_elem, "icon", src=info["logo"])

# Fetch EPG for next 10 days
for day in range(EPG_DAYS):
    current_date = datetime.utcnow() + timedelta(days=day)
    date_str = current_date.strftime("%Y-%m-%d")
    url = (
        f"https://www.bein.com/en/epg-ajax-template/"
        f"?action=epg_fetch&offset=-2&category=sports&serviceidentity=bein.net&mins=00"
        f"&cdate={date_str}&language=EN&postid=25356&loadindex=0"
    )
    print(f"Fetching {date_str}")
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.find_all("li", attrs={"data-start": True})
    for item in items:
        # Extract channel id
        parent_div = item.find_parent("div", id=lambda x: x and x.startswith("channels_"))
        if not parent_div:
            continue
        channel_id = parent_div.get("id", "beINSPORTS1").split("_")[-1]
        if "MAX" in channel_id or "4KHDR" in channel_id or channel_id.upper().startswith("BEINSPORTSMAX") or channel_id.upper() == "BEINSPORTS4KHDR":
            poster = MAX_POSTER
        else:
            poster = DEFAULT_POSTER

        # Title & description
        title_tag = item.find("p", class_="title")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        description = item.get("data-desc", "")
        desc_tag = item.find("p", class_="description")
        if desc_tag:
            description = desc_tag.get_text(" ", strip=True)
        if not description:
            description = f"Watch {title} live on beIN Sports."

        category_tag = item.find("p", class_="format")
        category = category_tag.get_text(strip=True) if category_tag else ""

        try:
            start_hour = int(item.get("data-start", "0"))
            start_min = int(item.get("data-start-m", "0"))
            end_hour = int(item.get("data-end", "0"))
            end_min = int(item.get("data-end-m", "0"))
        except:
            continue

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
        ET.SubElement(prog, "desc", lang="ar").text = description
        if category:
            ET.SubElement(prog, "category", lang="ar").text = category
        if poster:
            ET.SubElement(prog, "icon", src=poster)

# Save XML
ET.ElementTree(tv).write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
print(f"Guide saved to: {OUTPUT_FILE}")
