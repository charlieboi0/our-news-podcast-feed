import copy
import json
import datetime
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import requests
from pydub import AudioSegment
import internetarchive as ia
import config

SOURCE_FEED_URL = 'https://feed.podbean.com/ournewsbahamas/feed.xml'

def should_execute() -> bool:
    now = datetime.datetime.now(datetime.timezone.utc)

    target_today = now.replace(
        hour=config.TARGET_HOUR,
        minute=config.TARGET_MINUTE,
        second=0,
        microsecond=0
    )

    if now < target_today:
        window_start = target_today - datetime.timedelta(days=1)
    else:
        window_start = target_today

    window_end = window_start + datetime.timedelta(hours=12)

    if not (window_start <= now <= window_end):
        return False

    if not config.STATE_FILE.exists():
        return True

    with open(config.STATE_FILE, 'r') as f:
        state = json.load(f)

    last_success_str = state.get('last_success')
    next_allowed_str = state.get('next_allowed_attempt')

    last_success = (
        datetime.datetime.fromisoformat(last_success_str)
        if last_success_str else None
    )

    next_allowed_attempt = (
        datetime.datetime.fromisoformat(next_allowed_str)
        if next_allowed_str else now
    )

    if last_success and window_start <= last_success <= window_end:
        return False

    if now < next_allowed_attempt:
        return False

    return True

def update_state(success: bool):
    now = datetime.datetime.now(datetime.timezone.utc)
    if config.STATE_FILE.exists():
        with open(config.STATE_FILE, 'r') as f:
            state = json.load(f)
    else:
        state = {'last_success': (now - datetime.timedelta(days=1)).isoformat()}

    if success:
        state['last_success'] = now.isoformat()
        # Enforce waiting until the next expected 9:15 PM window tomorrow
        tomorrow_target = (now + datetime.timedelta(days=1)).replace(
            hour=config.TARGET_HOUR, minute=config.TARGET_MINUTE, second=0, microsecond=0
        )
        state['next_allowed_attempt'] = tomorrow_target.isoformat()
    else:
        # If failed within the window, let the next cron invocation (30 mins) run immediately
        state['next_allowed_attempt'] = now.isoformat()

    with open(config.STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def transcribe_audio(audio_path: Path) -> list:
    headers = {'X-API-Key': config.MODULATE_API_KEY}
    with open(audio_path, 'rb') as f:
        MINUTES = 60

        response = requests.post(
            'https://modulate-developer-apis.com/api/velma-2-stt-batch', 
            headers=headers, 
            files={'upload_file': f},
            data={'speaker_diarization': 'true'},
            timeout=8*MINUTES
        )
    response.raise_for_status()
    return response.json()

def get_new_title_and_edit_segments(word_timestamps: list) -> tuple[str | None, list]:
    """
    Returns a tuple of (new_title, list of segments to keep) based on the provided word timestamps.
    """
    prompt = (
        'You are an audio editor analyzing a local news podcast. \n'

        'Review the provided transcription json with utterances and their timestamps.'
        'Identify and exclude these segments: weather segments, the \'World Focus\' '
        'segment, the \'This day in history\' segment, duplicate sports segments, and '
        'commercials. Always start at timestamp 0.00. In addition, generate an new title '
        'for the edited podcast. The title should briefly summarize the most important '
        'stories and be no longer than 40 characters. Return a JSON object representing '
        'the new title and the valid content segments to KEEP. All timestamps should be '
        'in seconds and everything should be properly sorted. Format:\n'

        '{\n'
        '    "title": string,\n'
        '    "segments": [{"start": float, "end": float}]\n'
        '}\n'
    )
    
    headers = {
        'Authorization': f'Bearer {config.DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = {
        'model': 'deepseek-v4-flash',
        'messages': [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': json.dumps(word_timestamps)}
        ],
        'response_format': {'type': 'json_object'}
    }
    
    response = requests.post(
        'https://api.deepseek.com/chat/completions',
        headers=headers, json=payload, timeout=60
    )
    response.raise_for_status()
    result = response.json()
    
    content = result['choices'][0]['message']['content']
    parsed_content = json.loads(content)
    return parsed_content.get('title'), parsed_content.get('segments', [])

def edit_audio(input_path: Path, output_path: Path, segments: list):
    audio = AudioSegment.from_mp3(input_path)
    edited_audio = AudioSegment.empty()
    
    for seg in segments:
        start_ms = int(seg['start'] * 1000)
        end_ms = int(seg['end'] * 1000)
        edited_audio += audio[start_ms:end_ms]
        
    edited_audio.export(output_path, format='mp3')

def upload_to_archive_org(audio_path: Path, episode_num: str) -> tuple[str, int]:
    """
    Upload audio to archive.org and return (archive_url, file_size)
    """

    # ia.configure(config.IA_ACCESS_KEY, config.IA_SECRET_KEY)
    
    audio_filename = f'episode_{episode_num}.mp3'
    
    item = ia.get_item(config.IA_ITEM_NAME)
    
    # Upload the file
    r = item.upload_file(
        str(audio_path),
        key=audio_filename,
        access_key=config.IA_ACCESS_KEY,
        secret_key=config.IA_SECRET_KEY
    )
    
    r.raise_for_status()
    
    archive_url = f'https://archive.org/download/{config.IA_ITEM_NAME}/{audio_filename}'
    file_size = audio_path.stat().st_size
    
    return archive_url, file_size

def create_episode_artifact(episode_num: str, original_item: ET.Element, edited_audio_path: Path):
    folder_path = config.PATH_TO_EPISODES / episode_num
    
    # Upload audio to archive.org
    print(f'Uploading episode {episode_num} to archive.org...')
    archive_url, file_size = upload_to_archive_org(edited_audio_path, episode_num)

    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Construct isolated RSS item tag block
    rss_attrs = {'version': '2.0'} | {f'xmlns:{key}': val for key, val in config.NAMESPACES.items()}
    rss = ET.Element('rss', rss_attrs)

    item = copy.deepcopy(original_item)

    rss.append(item)

    for enc in item.findall('enclosure'):
        item.remove(enc)

    _enclosure = ET.SubElement(item, 'enclosure', {
        'url': archive_url,
        'type': 'audio/mpeg',
        'length': str(file_size)
    })

    audio = AudioSegment.from_mp3(edited_audio_path)
    duration_secs = len(audio) / 1000

    itunes_duration_elem = item.find('itunes:duration', config.NAMESPACES)
    if itunes_duration_elem is not None:
        item.remove(itunes_duration_elem)

    itunes_duration_elem = ET.SubElement(item, 'itunes:duration')
    itunes_duration_elem.text = f'{duration_secs:.0f}'

    tree = ET.ElementTree(rss)
    tree.write(folder_path / 'metadata.xml', encoding='utf-8', xml_declaration=True)

def process_latest_podcast(skip_execute_check: bool):
    if not skip_execute_check and not should_execute():
        print('Criteria skipped: Execution window inactive or 24h threshold already met.')
        return

    if skip_execute_check:
        print('Skipping execute check')

    if shutil.which('ffmpeg') is None:
        raise RuntimeError('ffmpeg is not installed')

    feed_response = requests.get(SOURCE_FEED_URL, timeout=60)
    feed_response.raise_for_status()
    feed = ET.fromstring(feed_response.content)

    channel = feed.find('channel')
    latest_entry = channel.find('item')

    if latest_entry is None:
        print('No episodes found in source feed.')
        update_state(success=False)
        return

    episode_num = latest_entry.findtext('itunes:episode', namespaces=config.NAMESPACES)
    
    if episode_num is None:
        print('Could not isolate an explicit itunes:episode tag identification.')
        update_state(success=False)
        return

    # Cancel if the directory exists (prevents duplicate compilation overhead)
    if (config.PATH_TO_EPISODES / str(episode_num)).exists():
        print(f'Episode {episode_num} has already been generated locally.')
        update_state(success=True)
        return

    enclosures = [
        enc for enc in latest_entry.findall('enclosure')
        if enc.get('type') == 'audio/mpeg'
    ]

    if not enclosures:
        print('No valid audio attachments discovered.')
        update_state(success=False)
        return
        
    audio_url = enclosures[0].get('url')
    temp_input = Path('temp_input.mp3')
    temp_output = Path('temp_output.mp3')
    
    error = None
    try:
        print(f'Downloading episode {episode_num}...')
        with requests.get(audio_url, stream=True, timeout=180) as r:
            r.raise_for_status()
            with open(temp_input, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        print('Transcribing via Modulate Velma API...')
        transcription = transcribe_audio(temp_input)
        utterances = [{
            'speaker': utterance['speaker'],
            'text': utterance['text'],
            'start_secs': utterance['start_ms'] / 1000,
            'duration_secs': utterance['duration_ms'] / 1000
        } for utterance in transcription.get('utterances', [])]

        print(str(utterances), '\n')

        if utterances == []:
            raise ValueError('Missing utterances in transcription response')

        print('Isolating content gaps with DeepSeek...')
        new_title, keep_segments = get_new_title_and_edit_segments(utterances)

        title_elem = latest_entry.find('title')
        itunes_title_elem = latest_entry.find('itunes:title', namespaces=config.NAMESPACES)
        title_elem.text = itunes_title_elem.text = new_title if new_title else title_elem.text

        if not keep_segments:
            raise ValueError('No valid segments returned from Deepseek')
        
        print(new_title)
        print(str(keep_segments), '\n')

        print('Slicing linear audio tracks...')
        edit_audio(temp_input, temp_output, keep_segments)

        print('Writing distribution files directly to target branch workspace...')
        create_episode_artifact(str(episode_num), latest_entry, temp_output)

        update_state(success=True)
        print(f'Successfully processed episode {episode_num}')
        
    except Exception as e:
        print(f'Pipeline error:')
        error = e
        update_state(success=False)
    finally:
        if temp_input.exists():
            temp_input.unlink()
        if temp_output.exists():
            temp_output.unlink()

    if error:
        raise error
