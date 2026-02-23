#!/usr/bin/env python3
"""Fetch latest videos from configured YouTube channels and save to data/videos.json."""

import os
import json
from datetime import datetime, timezone
from googleapiclient.discovery import build

API_KEY = os.environ.get('YOUTUBE_API_KEY')
if not API_KEY:
    raise SystemExit("ERROR: YOUTUBE_API_KEY environment variable is not set.")

CHANNELS_FILE = 'channels.txt'
OUTPUT_FILE = 'data/videos.json'
MAX_VIDEOS = 50

youtube = build('youtube', 'v3', developerKey=API_KEY)


def resolve_channel(identifier):
    """Resolve a channel handle or ID to channel metadata."""
    identifier = identifier.strip()
    if identifier.startswith('@'):
        params = {'forHandle': identifier}
    elif identifier.startswith('UC'):
        params = {'id': identifier}
    else:
        params = {'forUsername': identifier}

    resp = youtube.channels().list(
        part='id,snippet,contentDetails',
        **params
    ).execute()

    if not resp.get('items'):
        print(f"  WARNING: Channel not found: {identifier}")
        return None

    item = resp['items'][0]
    thumbs = item['snippet']['thumbnails']
    thumb = thumbs.get('default', {}).get('url', '')

    return {
        'id': item['id'],
        'name': item['snippet']['title'],
        'thumbnail': thumb,
        'uploads_playlist': item['contentDetails']['relatedPlaylists']['uploads'],
    }


def fetch_videos(playlist_id):
    """Fetch the latest videos from an uploads playlist."""
    resp = youtube.playlistItems().list(
        part='snippet',
        playlistId=playlist_id,
        maxResults=MAX_VIDEOS,
    ).execute()

    videos = []
    for item in resp.get('items', []):
        snippet = item['snippet']
        video_id = snippet['resourceId']['videoId']
        thumbs = snippet.get('thumbnails', {})
        # Prefer medium, fall back to high or default
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
    """Read channel identifiers from channels.txt."""
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
