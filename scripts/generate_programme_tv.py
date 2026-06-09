from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent

CHANNELS_FILE = BASE_DIR / "channels" / "programme-tv.net.channels.xml"
OUTPUT_FILE = BASE_DIR / "output" / "guide_programme_tv.xml"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# تحميل القنوات
tree = ET.parse(CHANNELS_FILE)
root = tree.getroot()

channels = {}
for ch in root.findall("channel"):
    site_id = ch.attrib.get("site_id")
    channels[site_id] = {
        "name": (ch.text or site_id).strip(),
        "logo": ch.attrib.get("logo", "")
    }

tv = ET.Element("tv", {"generator-info-name": "Programme TV Net EPG"})

# إضافة القنوات
for site_id, info in channels.items():
    ch_elem = ET.SubElement(tv, "channel", id=site_id)
    ET.SubElement(ch_elem, "display-name").text = info["name"]
    if info["logo"]:
        ET.SubElement(ch_elem, "icon", src=info["logo"])

# سحب بيانات EPG لمدة 7 أيام
for day in range(7):
    current_date = datetime.utcnow() + timedelta(days=day)
    date_str = current_date.strftime("%Y-%m-%d")

    url = f"https://www.programme-tv.net/epg-ajax/?date={date_str}"
    print("Fetching:", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all("div", class_="programme-row")
    for row in rows:
        site_id = row.get("data-channel-id")
        if site_id not in channels:
            continue

        title_tag = row.find("span", class_="programme-title")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        # DESC
        desc_tag = row.find("span", class_="programme-desc")
        description = desc_tag.get_text(strip=True) if desc_tag else row.get("data-desc", "")

        category_tag = row.find("span", class_="programme-category")
        category = category_tag.get_text(strip=True) if category_tag else ""

        start_time = row.get("data-start")
        end_time = row.get("data-end")
        if not start_time or not end_time:
            continue

        start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        programme = ET.SubElement(tv, "programme", {
            "channel": site_id,
            "start": start_dt.strftime("%Y%m%d%H%M%S +0000"),
            "stop": end_dt.strftime("%Y%m%d%H%M%S +0000")
        })

        ET.SubElement(programme, "title").text = title
        if description:
            ET.SubElement(programme, "desc").text = description
        if category:
            ET.SubElement(programme, "category").text = category

        # Poster إذا كان موجود في الصفحة
        img_tag = row.find("img")
        poster = img_tag.get("src") if img_tag else None
        if poster:
            ET.SubElement(programme, "icon", src=poster)

ET.ElementTree(tv).write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print("Saved:", OUTPUT_FILE)
