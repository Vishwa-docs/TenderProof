"""Inspect a reviewed real-capture export; full playback/link review stays manual."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('video', type=Path)
    parser.add_argument('--ffprobe', default=shutil.which('ffprobe'))
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--url', help='Actual uploaded URL; accessibility is verified separately')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root / 'REAL_SOURCE_EVIDENCE.json').read_text())
    if not evidence.get('ready_for_artifact_render'):
        parser.error('Actual inference/capture review is pending; no final video can be validated')
    if not args.ffprobe or not args.ffmpeg:
        parser.error('Known local ffprobe and ffmpeg are required')
    if not args.video.is_file():
        parser.error('Actual recording does not exist')
    result = subprocess.run([args.ffprobe, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(args.video)], check=True, capture_output=True, text=True)
    probe = json.loads(result.stdout)
    duration = float(probe['format']['duration'])
    video = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    audio = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
    if video is None or audio is None or not 0 < duration <= 120:
        raise SystemExit('Invalid duration or missing audio/video stream')
    if video['codec_name'] != 'h264' or audio['codec_name'] != 'aac' or (video['width'], video['height']) != (1920, 1080):
        raise SystemExit('Expected H.264/AAC 1920x1080 export')
    level = subprocess.run([args.ffmpeg, '-hide_banner', '-i', str(args.video), '-af', 'volumedetect', '-f', 'null', '-'], check=True, capture_output=True, text=True)
    match = re.search(r'max_volume:\s*(-?inf|[-\d.]+) dB', level.stderr)
    if not match or match.group(1) == '-inf':
        raise SystemExit('Audio level is silent or unverifiable')
    digest = hashlib.sha256(args.video.read_bytes()).hexdigest()
    metadata = json.loads((root / 'VIDEO_METADATA.json').read_text())
    if metadata.get('sha256') != digest:
        metadata.update(playback_reviewed=False, caption_legibility_reviewed=False, actual_content_reviewed=False, public_url_verified=False)
    metadata.update(status='media_inspected_playback_review_pending', local_path=str(args.video.resolve()), duration_seconds=duration,
                    sha256=digest, video_codec=video['codec_name'], audio_codec=audio['codec_name'],
                    resolution=f"{video['width']}x{video['height']}", max_audio_volume_db=float(match.group(1)),
                    media_inspected_at=datetime.now(timezone.utc).isoformat(), duration_within_limit=True)
    if args.url:
        metadata['public_or_judge_accessible_url'] = args.url
    (root / 'VIDEO_METADATA.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({key: metadata[key] for key in ['duration_seconds', 'duration_within_limit', 'video_codec', 'audio_codec', 'resolution', 'sha256']}, indent=2))


if __name__ == '__main__':
    main()
