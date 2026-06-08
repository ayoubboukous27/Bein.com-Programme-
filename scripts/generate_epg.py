from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

# عدد الأيام
EPG_DAYS = 10

BASE_DIR = Path(__file__).resolve().parent.parent

CHANNELS_FILE = BASE_DIR / "channels" / "bein.com.channels.full.logo.xml"
OUTPUT_FILE = BASE_DIR / "output" / "guide.xml"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# قراءة القنوات
tree = ET.parse(CHANNELS_FILE)
root = tree.getroot()

channels = {}

for ch in root.findall("channel"):

    site_id = ch.attrib.get("site_id")

    channels[site_id] = {
        "name": (ch.text or site_id).strip(),
        "logo": ch.attrib.get("logo", "")
    }

# XMLTV
tv = ET.Element(
    "tv",
    {
        "generator-info-name": "beIN GitHub EPG"
    }
)

# إضافة القنوات
for site_id, info in channels.items():

    channel = ET.SubElement(
        tv,
        "channel",
        id=site_id
    )

    ET.SubElement(
        channel,
        "display-name"
    ).text = info["name"]

    if info["logo"]:
        ET.SubElement(
            channel,
            "icon",
            src=info["logo"]
        )

# جلب EPG
for day in range(EPG_DAYS):

    current_date = (
        datetime.utcnow() +
        timedelta(days=day)
    )

    date_str = current_date.strftime(
        "%Y-%m-%d"
    )

    url = (
        "https://www.bein.com/en/epg-ajax-template/"
        "?action=epg_fetch"
        "&offset=-2"
        "&category=sports"
        "&serviceidentity=bein.net"
        "&mins=00"
        f"&cdate={date_str}"
        "&language=EN"
        "&postid=25356"
        "&loadindex=0"
    )

    print(f"Fetching {date_str}")

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=60
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    programmes = soup.select(
        "li[data-start]"
    )

    for item in programmes:

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

        category = ""

        if category_tag:
            category = category_tag.get_text(
                strip=True
            )

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

        except Exception:
            continue

        channel_id = item.get(
            "channel",
            "beINSPORTS1"
        )

        if channel_id not in channels:
            channel_id = list(
                channels.keys()
            )[0]

        start_dt = datetime(
            current_date.year,
            current_date.month,
            current_date.day,
            start_hour,
            start_min,
            0
        )

        end_dt = datetime(
            current_date.year,
            current_date.month,
            current_date.day,
            end_hour,
            end_min,
            0
        )

        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        programme = ET.SubElement(
            tv,
            "programme",
            {
                "channel": channel_id,
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
            "title",
            lang="en"
        ).text = title

        if category:
            ET.SubElement(
                programme,
                "category"
            ).text = category

        if description:
            ET.SubElement(
                programme,
                "desc",
                lang="en"
            ).text = description

ET.ElementTree(tv).write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print(
    f"Guide saved to: {OUTPUT_FILE}"
    )
