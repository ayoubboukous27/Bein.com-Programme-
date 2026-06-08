from pathlib import Path
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

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
        "name": ch.text or site_id,
        "logo": ch.attrib.get("logo", "")
    }

tv = ET.Element("tv")

for site_id, info in channels.items():
    channel = ET.SubElement(tv, "channel", id=site_id)

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

for day in range(7):

    date = (
        datetime.utcnow() +
        timedelta(days=day)
    ).strftime("%Y-%m-%d")

    url = (
        "https://www.bein.com/en/epg-ajax-template/"
        "?action=epg_fetch"
        "&offset=-2"
        "&category=sports"
        "&serviceidentity=bein.net"
        "&mins=00"
        f"&cdate={date}"
        "&language=EN"
        "&postid=25356"
        "&loadindex=0"
    )

    print("Fetching:", url)

    html = requests.get(
        url,
        timeout=60
    ).text

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for slider in soup.find_all(
        id=lambda x: x and x.startswith("channels_")
    ):

        link = slider.find(
            "a",
            href=True
        )

        if not link:
            continue

        site_id = (
            link["href"]
            .split("/")[-1]
            .strip()
        )

        if site_id not in channels:
            continue

        for item in slider.select(
            "li[data-start]"
        ):

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

            try:
                start_hour = int(
                    item["data-start"]
                )

                start_min = int(
                    item["data-start-m"]
                )

                end_hour = int(
                    item["data-end"]
                )

                end_min = int(
                    item["data-end-m"]
                )

            except:
                continue

            start_dt = datetime.strptime(
                date,
                "%Y-%m-%d"
