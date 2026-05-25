import os
from pathlib import Path
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

from config import PATH_TO_EPISODES, SCRIPT_DIR, NAMESPACES

PATH_TO_RSS_FEED = SCRIPT_DIR.parent / 'feed.xml'

def xml_pprint(element: ET.Element):
    raw_string = ET.tostring(element, 'utf-8')
    reparsed = minidom.parseString(raw_string)
    pretty_xml_string = reparsed.toprettyxml(indent='  ')
    clean_pretty_xml = '\n'.join(
        [line for line in pretty_xml_string.splitlines() if line.strip()]
    )

    return clean_pretty_xml

def add_to_feed():
    # Parse feed.xml
    xml_tree = ET.parse(PATH_TO_RSS_FEED)
    xml_channel = xml_tree.getroot().find('channel')
    xml_episodes = [ep for ep in xml_channel.findall('item')]

    xml_episode_ids = [ep.find('itunes:episode', NAMESPACES).text for ep in xml_episodes]

    # Check for discrepancies between folder and xml
    episode_folders = sorted(os.listdir(PATH_TO_EPISODES))
    missing_xml_episode_ids = list(filter(
        lambda folder_id: folder_id not in xml_episode_ids,
        episode_folders
    ))

    # Add folder/podcast metadata to feed.xml
    for folder in missing_xml_episode_ids:
        metadata_path = PATH_TO_EPISODES / folder / 'metadata.xml'
        metadata = ET.parse(metadata_path).find('item')
        xml_channel.append(metadata)


    ET.register_namespace('itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
    pretty_xml_string = xml_pprint(xml_tree.getroot())


    with open(PATH_TO_RSS_FEED, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_string)

    print(f'Successfully added {len(missing_xml_episode_ids)} episode(s) to {PATH_TO_RSS_FEED.resolve()}')
