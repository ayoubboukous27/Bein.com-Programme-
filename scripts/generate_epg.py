import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os

# Paths
channels_file = "../channels/bein.com.channels.full.logo.xml"
output_file = "../output/guide.xml"

# Base AJAX URL
base_url = "https://www.bein.com/en/epg-ajax-template/?action=epg_fetch&offset=-2&category=sports&serviceidentity=bein.net&mins=00&cdate={date}&language=EN&postid=25356&loadindex=0"

# Create output folder if not exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Load channels XML and extract info
tree = ET.parse(channels_file)
root = tree.getroot()
channels = {}
for ch in root.findall("channel"):
    site_id = ch.attrib.get("site_id")
    name = ch.text
    logo = ch.attrib.get("logo")
    channels[site_id] = {"name": name, "logo": logo}

# Create XMLTV root
tv = ET.Element("tv")

# Add channels to XMLTV
for site_id, info in channels.items():
    ch_elem = ET.SubElement(tv, "channel", id=site_id)
    ET.SubElement(ch_elem, "display-name").text = info["name"]
    if info["logo"]:
        ET.SubElement(ch_elem, "icon", src=info["logo"])

# Fetch EPG for next 7 days
for day_offset in range(7):
    date_obj = datetime.utcnow() + timedelta(days=day_offset)
    cdate = date_obj.strftime("%Y-%m-%d")
    url = base_url.format(date=cdate)
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for li in soup.find_all("li", {"data-start": True, "data-end": True}):
        channel_link = li.find("a", href=True)
        if not channel_link:
            continue
        site_id = channel_link['href'].split("/")[-1]
        if site_id not in channels:
            continue

        title_tag = li.find("p", class_="title")
        title = title_tag.text.strip() if title_tag else "Unknown"

        desc = li.get("data-desc", "")
        start_h = int(li['data-start'])
        start_m = int(li['data-start-m'])
        end_h = int(li['data-end'])
        end_m = int(li['data-end-m'])

        start_time = date_obj.replace(hour=start_h, minute=start_m, second=0)
        end_time = date_obj.replace(hour=end_h, minute=end_m, second=0)
        # Adjust for programs crossing midnight
        if end_time <= start_time:
            end_time += timedelta(days=1)

        programme = ET.SubElement(tv, "programme", {
            "start": start_time.strftime("%Y%m%d%H%M%S") + " +0000",
            "stop": end_time.strftime("%Y%m%d%H%M%S") + " +0000",
            "channel": site_id
        })
        ET.SubElement(programme, "title").text = title
        ET.SubElement(programme, "desc").text = desc

# Write XMLTV file
tree = ET.ElementTree(tv)
tree.write(output_file, encoding="UTF-8", xml_declaration=True)
print(f"EPG saved to {output_file}")
