from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent

CHANNELS_FILE = BASE_DIR / "channels" / "bein.com.channels.full.logo.xml"
OUTPUT_FILE = BASE_DIR / "output" / "guide.xml"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

tree = ET.parse(CHANNELS_FILE)
root = tree.getroot()

channels = {}
for ch in root.findall("channel"):
    site_id = ch.attrib.get("site_id")
    channels[site_id] = {
        "name": (ch.text or site_id).strip(),
        "logo": ch.attrib.get("logo", "")
    }

tv = ET.Element("tv")

# إضافة القنوات
for site_id, info in channels.items():
    channel = ET.SubElement(tv, "channel", id=site_id)
    ET.SubElement(channel, "display-name").text = info["name"]
    if info["logo"]:
        ET.SubElement(channel, "icon", src=info["logo"])

# سحب بيانات EPG لمدة 10 أيام
for day in range(10):
    current_date = datetime.utcnow() + timedelta(days=day)
    date_str = current_date.strftime("%Y-%m-%d")

    url = (
        f"https://www.bein.com/en/epg-ajax-template/"
        f"?action=epg_fetch"
        f"&offset=-2"
        f"&category=sports"
        f"&serviceidentity=bein.net"
        f"&mins=00"
        f"&cdate={date_str}"
        f"&language=EN"
        f"&postid=25356"
        f"&loadindex=0"
    )

    print("Fetching:", url)

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all(
        "div",
        id=lambda x: x and x.startswith("channels_")
    )

    for row in rows:

        link = row.find("a", href=True)

        if not link:
            continue

        site_id = (
            link["href"]
            .split("/")[-1]
            .strip()
        )

        if site_id not in channels:
            continue

        items = row.select("li[data-start]")

        for item in items:

            title_tag = item.find(
                "p",
                class_="title"
            )

            if not title_tag:
                continue

            title = title_tag.get_text(
                strip=True
            )

            category_tag = item.find(
                "p",
                class_="format"
            )

            category = (
                category_tag.get_text(strip=True)
                if category_tag else ""
            )

            # DESC
            description = ""

            desc_tag = item.find(
                "p",
                class_="description"
            )

            if desc_tag:
                description = desc_tag.get_text(
                    " ",
                    strip=True
                )

            if not description:
                description = item.get(
                    "data-desc",
                    ""
                ).strip()

            try:
                start_hour = int(
                    item.get("data-start", "0")
                )

                start_min = int(
                    item.get("data-start-m", "0")
                )

                end_hour = int(
                    item.get("data-end", "0")
                )

                end_min = int(
                    item.get("data-end-m", "0")
                )

            except:
                continue

            start_dt = datetime(
                current_date.year,
                current_date.month,
                current_date.day,
                start_hour,
                start_min
            )

            end_dt = datetime(
                current_date.year,
                current_date.month,
                current_date.day,
                end_hour,
                end_min
            )

            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

            programme = ET.SubElement(
                tv,
                "programme",
                {
                    "channel": site_id,
                    "start": start_dt.strftime(
                        "%Y%m%d%H%M%S +0000"
                    ),
                    "stop": end_dt.strftime(
                        "%Y%m%d%H%M%S +0000"
                    )
                }
            )

            ET.SubElement(
                programme,
                "title"
            ).text = title

            if description:
                ET.SubElement(
                    programme,
                    "desc"
                ).text = description

            if category:
                ET.SubElement(
                    programme,
                    "category"
                ).text = category

            # بوستر البرامج
            if site_id in [
                "beINSPORTSMAX1",
                "beINSPORTSMAX2",
                "beINSPORTSMAX3",
                "beINSPORTSMAX4",
                "beINSPORTSMAX5",
                "beINSPORTSMAX6",
                "beINSPORTS4KHDR"
            ]:
                poster = "https://github.com/ayoubboukous27/Multi-providers-EPG-/raw/refs/heads/main/OG_FB_1200x630_ar.jpg"
            else:
                poster = "https://github.com/ayoubboukous27/Multi-providers-EPG-/raw/refs/heads/main/maxresdefault.jpg"

            ET.SubElement(
                programme,
                "icon",
                src=poster
            )

ET.ElementTree(tv).write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print("Saved:", OUTPUT_FILE)
