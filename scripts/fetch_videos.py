#!/usr/bin/env python3
"""Fetch latest videos from configured YouTube channels and save to data/videos.json."""

import os
import json
import requests
from datetime import datetime, timezone

API_KEY = os.environ.get('YOUTUBE_API_KEY')
if not API_KEY:
    raise SystemExit("ERROR: YOUTUBE_API_KEY environment variable is not set.")

BASE = 'https://www.googleapis.com/youtube/v3'
CHANNELS_FILE = 'channels.txt'
OUTPUT_FILE = 'data/videos.json'
MAX_VIDEOS = 50


def yt(endpoint, **params):
    params['key'] = API_KEY
    r = requests.get(f'{BASE}/{endpoint}', params=params)
    r.raise_for_status()
    return r.json()


def resolve_channel(identifier):
    if identifier.startswith('@'):
        data = yt('channels', part='id,snippet,contentDetails', forHandle=identifier)
    elif identifier.startswith('UC'):
        data = yt('channels', part='id,snippet,contentDetails', id=identifier)
    else:
        data = yt('channels', part='id,snippet,contentDetails', forUsername=identifier)

    if not data.get('items'):
        print(f"  WARNING: Channel not found: {identifier}")
        return None

    item = data['items'][0]
    thumbs = item['snippet']['thumbnails']
    thumb = thumbs.get('default', {}).get('url', '')

    return {
        'id': item['id'],
        'name': item['snippet']['title'],
        'thumbnail': thumb,
        'uploads_playlist': item['contentDetails']['relatedPlaylists']['uploads'],
    }


def fetch_videos(playlist_id):
    data = yt('playlistItems', part='snippet', playlistId=playlist_id, maxResults=MAX_VIDEOS)
    videos = []
    for item in data.get('items', []):
        snippet = item['snippet']
        video_id = snippet['resourceId']['videoId']
        thumbs = snippet.get('thumbnails', {})
        thumb = (
            thumbs.get('medium') or
            thumbs.get('high') or
            thumbs.get('default') or {}
        ).get('url', '')
        videos.append({
            'id': video_id,
            'title': snippet['title'],
            'thumbnail': thumb,
            'published_at': snippet['publishedAt'],
            'url': f'https://www.youtube.com/watch?v={video_id}',
        })
    return videos


def read_identifiers():
    try:
        with open(CHANNELS_FILE) as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.startswith('#')
            ]
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {CHANNELS_FILE} not found.")


def main():
    identifiers = read_identifiers()
    if not identifiers:
        print("No channels configured. Add channels to channels.txt.")
        return

    channels_data = []
    for ident in identifiers:
        print(f"Processing: {ident}")
        try:
            channel = resolve_channel(ident)
            if not channel:
                continue
            videos = fetch_videos(channel['uploads_playlist'])
            channels_data.append({
                'id': channel['id'],
                'name': channel['name'],
                'thumbnail': channel['thumbnail'],
                'videos': videos,
            })
            print(f"  → {channel['name']}: {len(videos)} videos")
        except Exception as e:
            print(f"  ERROR processing {ident}: {e}")

    output = {
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'channels': channels_data,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDone. Saved {len(channels_data)} channels to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
