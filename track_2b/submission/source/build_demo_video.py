"""Build a narrated sequence of verified actual UI captures after evidence review.

This script never generates application data, model output or a synthetic scene.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {command[0]}\n{result.stderr[-2500:]}')
    return result


def probe(path, ffprobe):
    return json.loads(run([ffprobe, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]).stdout)


def audio_level(path, ffmpeg):
    result = run([ffmpeg, '-hide_banner', '-i', str(path), '-af', 'volumedetect', '-f', 'null', '-'])
    match = re.search(r'max_volume:\s*(-?inf|[-\d.]+) dB', result.stderr)
    if not match or match.group(1) == '-inf':
        raise RuntimeError(f'Audio is silent or its level cannot be verified: {path.name}')
    return float(match.group(1))


def timestamp(seconds):
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def wrap_pixels(text, face, width, max_lines, field):
    """Keep readable fixed-size type; reject copy that cannot fit its frame."""
    lines = []
    for paragraph in text.splitlines():
        line = ''
        for word in paragraph.split():
            if face.getlength(word) > width:
                raise ValueError(f'{field} has a word wider than its frame')
            proposed = f'{line} {word}'.strip()
            if face.getlength(proposed) > width:
                lines.append(line)
                line = word
            else:
                line = proposed
        if line:
            lines.append(line)
    if not lines or len(lines) > max_lines:
        raise ValueError(f'{field} must fit {max_lines} readable line(s); shorten the copy')
    return lines


def resolve_trace_path(value):
    if not value:
        raise ValueError('Actual inference request/raw-response path is missing')
    raw = Path(value)
    choices = [raw] if raw.is_absolute() else [REPO / raw, ROOT / raw]
    for choice in choices:
        candidate = choice.resolve()
        if candidate.is_file() and (candidate == REPO or REPO in candidate.parents):
            return candidate
    raise ValueError(f'Actual inference artifact is absent: {value}')


def validate_inputs(evidence, scenes):
    if not evidence.get('ready_for_artifact_render'):
        raise ValueError('Real inference/captures are not reviewed; video rendering remains disabled')
    successful = [r for r in evidence.get('inference_runs', []) if r.get('status') == 'succeeded' and r.get('model')]
    if not successful:
        raise ValueError('Actual successful Apertus execution is required')
    actual_run = successful[-1]
    request = resolve_trace_path(actual_run.get('request_path'))
    resolve_trace_path(actual_run.get('raw_response_path'))
    if sha256(request) != actual_run.get('input_sha256'):
        raise ValueError('Actual inference request hash does not match its manifest')
    if not scenes:
        raise ValueError('No verified actual-capture scenes exist')
    sources = {s['url'] for s in evidence['sources'] if s.get('verified_real_document')}
    captures = {c['id']: c for c in evidence.get('browser_captures', [])}
    total = 0
    checked = []
    for index, scene in enumerate(scenes, 1):
        seconds = scene.get('seconds')
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 4 <= seconds <= 25:
            raise ValueError(f'Scene {index}: duration must be 4–25 seconds')
        if not scene.get('verified_real_source') or scene.get('source_url') not in sources:
            raise ValueError(f'Scene {index}: verified real-source URL required')
        capture = captures.get(scene.get('capture_id'))
        if not capture:
            raise ValueError(f'Scene {index}: use a registered actual capture_id')
        image_path = (ROOT / capture['path']).resolve()
        relative = image_path.relative_to(ROOT)
        if relative.parts[0] in {'.runtime', '.build'} or not image_path.is_file():
            raise ValueError(f'Scene {index}: archived/build media cannot be used')
        if not capture.get('sha256') or sha256(image_path) != capture['sha256']:
            raise ValueError(f'Scene {index}: actual capture hash mismatch')
        for field in ['title', 'caption', 'narration']:
            if not isinstance(scene.get(field), str) or not scene[field].strip():
                raise ValueError(f'Scene {index}: {field} is required')
        title = wrap_pixels(scene['title'], font(42, True), 1776, 1, f'Scene {index} title')
        caption = wrap_pixels(scene['caption'], font(36), 1776, 2, f'Scene {index} caption')
        with Image.open(image_path) as source:
            crop = scene.get('crop', [0, 0, source.width, source.height])
            if len(crop) != 4 or any(isinstance(v, bool) or not isinstance(v, int) for v in crop):
                raise ValueError(f'Scene {index}: crop must contain four integer pixel bounds')
            left, top, right, bottom = crop
            if not (0 <= left < right <= source.width and 0 <= top < bottom <= source.height):
                raise ValueError(f'Scene {index}: crop lies outside the actual capture')
        checked.append((scene, capture, image_path, crop, title, caption))
        total += seconds
    if not 110 <= total <= 118:
        raise ValueError(f'Timeline must be 110–118 seconds with export headroom; got {total}')
    return checked, total


def write_narration_inputs(checked, build):
    for index, (scene, *_rest) in enumerate(checked, 1):
        text_path = build / f'narration-{index:02}.txt'
        desired = scene['narration'].strip() + '\n'
        if not text_path.exists() or text_path.read_text() != desired:
            text_path.write_text(desired)
            # A new script must never reuse speech from an earlier outcome.
            (build / f'narration-{index:02}.aiff').unlink(missing_ok=True)
            (build / f'narration-{index:02}.voice.json').unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--voice', default='Samantha')
    parser.add_argument('--speech-rate', type=int, default=175)
    parser.add_argument('--reuse-narration', action='store_true')
    parser.add_argument('--prepare-narration-only', action='store_true')
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--ffprobe', default=shutil.which('ffprobe'))
    args = parser.parse_args()
    if not args.ffmpeg or not args.ffprobe:
        parser.error('Known local ffmpeg and ffprobe are required')
    if not 160 <= args.speech_rate <= 190:
        parser.error('Use a readable neutral speech rate of 160–190 words/minute')
    evidence = json.loads((ROOT / 'REAL_SOURCE_EVIDENCE.json').read_text())
    scenes = json.loads((ROOT / 'source/video_scenes.json').read_text())
    try:
        checked, total = validate_inputs(evidence, scenes)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    build = ROOT / '.build/video'
    build.mkdir(parents=True, exist_ok=True)
    write_narration_inputs(checked, build)
    if args.prepare_narration_only:
        print(f'Prepared {len(checked)} actual narration inputs in {build}; no media rendered')
        return
    segments, captions, script = [], [], []
    elapsed = 0
    for index, (scene, capture, image_path, crop_box, title, caption) in enumerate(checked, 1):
        voice = build / f'narration-{index:02}.aiff'
        text_path = build / f'narration-{index:02}.txt'
        if args.reuse_narration:
            if not voice.is_file() or voice.stat().st_mtime < text_path.stat().st_mtime:
                raise RuntimeError(f'Scene {index}: current-script narration must be generated before reuse')
        else:
            run(['/usr/bin/say', '-v', args.voice, '-r', str(args.speech_rate), '-o', str(voice), '-f', str(text_path)])
        audio = probe(voice, args.ffprobe)
        duration = float(audio['format'].get('duration', 0))
        if not 0 < duration <= scene['seconds'] - .5:
            raise RuntimeError(f'Scene {index}: narration {duration:.2f}s needs at least 0.5s pause; shorten actual script. Empty macOS audio may require authorized native speech, then --reuse-narration.')
        peak = audio_level(voice, args.ffmpeg)
        speech = {'voice': args.voice, 'rate_words_per_minute': args.speech_rate, 'duration_seconds': duration,
                  'max_volume_db': peak, 'narration_sha256': sha256(text_path), 'audio_sha256': sha256(voice)}
        (build / f'narration-{index:02}.voice.json').write_text(json.dumps(speech, indent=2) + '\n')
        frame = Image.new('RGB', (1920, 1080), '#F5F2EA')
        draw = ImageDraw.Draw(frame)
        draw.rectangle((0, 0, 1920, 92), fill='#142D3C')
        draw.text((72, 24), 'TenderProof  /  SwissChivers', font=font(34, True), fill='#F5F2EA')
        draw.text((1140, 31), 'Actual document workflow', font=font(25), fill='#BAD7D0')
        draw.text((72, 117), title[0], font=font(42, True), fill='#142D3C')
        with Image.open(image_path) as source:
            crop = source.convert('RGB').crop(tuple(crop_box))
        scale = min(1776 / crop.width, 650 / crop.height)
        crop = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS)
        frame.paste(crop, ((1920 - crop.width) // 2, 186 + (650 - crop.height) // 2))
        draw.rectangle((0, 864, 1920, 1080), fill='#142D3C')
        for line_index, line in enumerate(caption):
            draw.text((72, 899 + line_index * 53), line, font=font(36), fill='#F5F2EA')
        draw.text((72, 1029), f'{index:02} / {len(checked):02}    SwissChivers | real sources | actual captured application states', font=font(22), fill='#BAD7D0')
        image = build / f'scene-{index:02}.png'
        frame.save(image)
        segment = build / f'scene-{index:02}.mp4'
        run([args.ffmpeg, '-y', '-loop', '1', '-i', str(image), '-i', str(voice), '-t', str(scene['seconds']),
             '-r', '30', '-vf', 'format=yuv420p', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-af', 'apad',
             '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', str(segment)])
        segments.append(segment)
        caption_text = '\n'.join(caption)
        captions.append(f'{index}\n{timestamp(elapsed)} --> {timestamp(elapsed + scene["seconds"])}\n{caption_text}\n')
        script.append({'start_seconds': elapsed, 'end_seconds': elapsed + scene['seconds'], **scene,
                       'capture': capture, 'speech': speech, 'caption_lines': caption})
        elapsed += scene['seconds']
        print(f'Scene {index}/{len(checked)} rendered ({elapsed}s timeline)', flush=True)
    concat = build / 'concat.txt'
    # Fixed local build filenames avoid arbitrary paths inside ffmpeg's list grammar.
    concat.write_text(''.join(f"file 'scene-{index:02}.mp4'\n" for index in range(1, len(segments) + 1)))
    candidate = build / 'TenderProof_Demo.candidate.mp4'
    run([args.ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', '-movflags', '+faststart', str(candidate)])
    final_probe = probe(candidate, args.ffprobe)
    actual = float(final_probe['format']['duration'])
    videos = [s for s in final_probe['streams'] if s['codec_type'] == 'video']
    audios = [s for s in final_probe['streams'] if s['codec_type'] == 'audio']
    if not 110 <= actual <= 120 or len(videos) != 1 or len(audios) != 1:
        raise RuntimeError('Final duration/stream validation failed; candidate retained privately')
    if videos[0]['codec_name'] != 'h264' or (videos[0]['width'], videos[0]['height']) != (1920, 1080) or audios[0]['codec_name'] != 'aac':
        raise RuntimeError('Final codec/resolution validation failed')
    audio_level(candidate, args.ffmpeg)
    out = ROOT / 'output'
    out.mkdir(exist_ok=True)
    final = out / 'TenderProof_Demo.mp4'
    shutil.copyfile(candidate, final)
    (out / 'TenderProof_Demo.srt').write_text('\n'.join(captions))
    (ROOT / 'VIDEO_TIMELINE.json').write_text(json.dumps({'duration_seconds': actual, 'planned_duration_seconds': total,
        'method': 'actual_UI_capture_sequence', 'application_dummy_data': False,
        'narration': 'local macOS text-to-speech', 'scenes': script}, indent=2) + '\n')
    print(f'Created {final}: {actual:.3f}s; full playback and source/text review still required')


if __name__ == '__main__':
    main()
