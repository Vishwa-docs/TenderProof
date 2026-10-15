"""Create the reviewed report/deck PDFs; --preflight measures source only."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil
import time
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from PIL import Image
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT.parent / 'technical_report.md'
NAVY = colors.HexColor('#142D3C')
TEAL = colors.HexColor('#176F69')
MUTED = colors.HexColor('#53636B')
PAPER = colors.HexColor('#F5F2EA')
PAGE_HEIGHT = 735.89
PAGE_WIDTH = 507.28


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report_styles():
    pdfmetrics.registerFont(TTFont('TPArial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
    pdfmetrics.registerFont(TTFont('TPArialBold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
    pdfmetrics.registerFontFamily('TPArial', normal='TPArial', bold='TPArialBold', italic='TPArial', boldItalic='TPArialBold')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TPBody', fontName='TPArial', fontSize=10.5, leading=15.2, textColor=NAVY, spaceAfter=9))
    styles.add(ParagraphStyle(name='TPTitle', fontName='TPArialBold', fontSize=36, leading=41, textColor=NAVY, spaceAfter=16))
    styles.add(ParagraphStyle(name='TPHeading', fontName='TPArialBold', fontSize=17, leading=21, textColor=TEAL, spaceBefore=10, spaceAfter=10))
    styles.add(ParagraphStyle(name='TPSubheading', fontName='TPArialBold', fontSize=13, leading=17, textColor=TEAL, spaceBefore=8, spaceAfter=8))
    styles.add(ParagraphStyle(name='TPCell', fontName='TPArial', fontSize=9, leading=12, textColor=NAVY))
    styles.add(ParagraphStyle(name='TPHeadCell', fontName='TPArialBold', fontSize=9, leading=12, textColor=colors.white))
    styles.add(ParagraphStyle(name='TPRef', fontName='TPArial', fontSize=9, leading=12, textColor=NAVY, spaceAfter=6))
    return styles


def inline(text):
    text = escape(text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return re.sub(r'`([^`]+)`', r'<font color="#176F69">\1</font>', text)


def read_story(styles):
    story, lines, index = [], REPORT.read_text().splitlines(), 0
    reference = r'^(?:\d+|[GH]\d+)\. '
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line == '<!-- PAGEBREAK -->':
            story.append(PageBreak())
            index += 1
            continue
        if line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                values = [v.strip() for v in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch('[-: ]+', v) for v in values):
                    if len(values) != 3:
                        raise ValueError('Report tables must have exactly three columns')
                    rows.append(values)
                index += 1
            data = [[Paragraph(inline(v), styles['TPHeadCell' if row == 0 else 'TPCell']) for v in values] for row, values in enumerate(rows)]
            table = Table(data, colWidths=[112, 195, 200], hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), NAVY), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#C5CEC9')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PAPER])]))
            story.extend([table, Spacer(1, 10)])
            continue
        matched = False
        for prefix, style in [('# ', 'TPTitle'), ('## ', 'TPHeading'), ('### ', 'TPSubheading')]:
            if line.startswith(prefix):
                story.append(Paragraph(inline(line[len(prefix):]), styles[style]))
                index += 1
                matched = True
                break
        if matched:
            continue
        if re.match(reference, line):
            story.append(Paragraph(inline(line), styles['TPRef']))
            index += 1
            continue
        chunk = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not lines[index].startswith(('#', '|', '<!--')) and not re.match(reference, lines[index]):
            chunk.append(lines[index].strip())
            index += 1
        story.append(Paragraph(inline(' '.join(chunk)), styles['TPBody']))
    return story


def measure_story(story):
    heights, used = [], 0
    for item in story:
        if isinstance(item, PageBreak):
            heights.append(used)
            used = 0
        else:
            width, height = item.wrap(PAGE_WIDTH, 10000)
            if width > PAGE_WIDTH + .01:
                raise ValueError('Report content exceeds its usable width')
            used += item.getSpaceBefore() + height + item.getSpaceAfter()
    heights.append(used)
    return heights


def footer(can, doc):
    width, height = doc.pagesize
    can.setFillColor(TEAL)
    can.rect(44, height - 32, width - 88, 3, fill=1, stroke=0)
    can.setFont('TPArial', 8)
    can.setFillColor(MUTED)
    can.drawString(44, 25, 'TenderProof  |  Track 2B  |  15 October 2026  |  CC-BY-4.0')
    can.drawRightString(width - 44, 25, str(doc.page))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true', help='Read/measure report source; do not render or create outputs')
    args = parser.parse_args()
    evidence = json.loads((ROOT / 'REAL_SOURCE_EVIDENCE.json').read_text())
    if not args.preflight and not evidence.get('ready_for_artifact_render'):
        raise SystemExit('Final real-source evidence pending; no report or deck PDF rendered')
    styles = report_styles()
    heights = measure_story(read_story(styles))
    if len(heights) > 6 or max(heights) > PAGE_HEIGHT:
        raise SystemExit(f'Report source geometry exceeds six-page plan: {heights}')
    if args.preflight:
        print(json.dumps({'mode': 'source_geometry_only_no_render', 'planned_pages': len(heights),
            'conservative_height_pt': [round(v, 1) for v in heights], 'available_height_pt': PAGE_HEIGHT,
            'required_repository_filename': 'track_2b/SwissChivers_Report.pdf', 'render_guard': evidence['ready_for_artifact_render']}, indent=2))
        return
    if not any(r.get('status') == 'succeeded' and r.get('raw_response_path') and r.get('input_sha256') for r in evidence.get('inference_runs', [])):
        raise SystemExit('Actual completed inference is required')
    for capture in evidence.get('browser_captures', []):
        image = (ROOT / capture['path']).resolve()
        relative = image.relative_to(ROOT)
        if relative.parts[0] in {'.runtime', '.build'} or not capture.get('sha256') or sha256(image) != capture['sha256']:
            raise SystemExit('Registered capture is missing, archived or changed')
    out, previews = ROOT / 'output', ROOT / 'previews'
    pptx = out / 'TenderProof_Deck.pptx'
    with zipfile.ZipFile(pptx) as package:
        names = [n for n in package.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
        native_tables = sum(len(ET.fromstring(package.read(n)).findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}tbl')) for n in names)
    slides = sorted(previews.glob('slide-*.png'))
    if not slides or len(slides) != len(names) or native_tables < 2:
        raise SystemExit('Validated editable PPTX and matching current slide previews are required')
    build = ROOT / '.build' / f'pdf-candidates-{time.time_ns()}'
    build.mkdir(parents=True)
    report = build / 'SwissChivers_Report.pdf'
    # Frame padding adds6pt on each side, yielding visual44pt margins and507.28pt usable width.
    SimpleDocTemplate(str(report), pagesize=(595.28, 841.89), leftMargin=38, rightMargin=38,
        topMargin=46, bottomMargin=48, title='TenderProof Technical Report', author='SwissChivers').build(read_story(styles), onFirstPage=footer, onLaterPages=footer)
    pages = len(PdfReader(str(report)).pages)
    if not 1 <= pages <= 6:
        raise RuntimeError(f'Candidate report exceeds six total pages: {pages}; active output unchanged')
    deck = build / 'TenderProof_Deck.pdf'
    pdf = canvas.Canvas(str(deck), pagesize=(960, 540))
    pdf.setTitle('TenderProof - Hack Apertus Track 2B')
    pdf.setAuthor('SwissChivers')
    for image in slides:
        pdf.drawImage(str(image), 0, 0, width=960, height=540)
        pdf.showPage()
    pdf.save()
    if len(PdfReader(str(deck)).pages) != len(names):
        raise RuntimeError('Candidate deck page count does not match the editable PPTX')
    # Publish only validated local candidates; visual/content review still follows.
    out.mkdir(exist_ok=True)
    previews.mkdir(exist_ok=True)
    shutil.copyfile(report, out / 'SwissChivers_Report.pdf')
    repository_report = ROOT.parent / 'SwissChivers_Report.pdf'
    shutil.copyfile(report, repository_report)
    shutil.copyfile(deck, out / 'TenderProof_Deck.pdf')
    if sha256(repository_report) != sha256(out / 'SwissChivers_Report.pdf'):
        raise RuntimeError('Repository report copy differs from the verified report')
    for old in previews.glob('report-*.png'):
        old.unlink()
    document = pdfium.PdfDocument(str(report))
    for index, page in enumerate(document):
        page.render(scale=1.5).to_pil().save(previews / f'report-{index + 1}.png')
    thumbs = []
    for image in slides:
        thumb = Image.open(image).convert('RGB')
        thumb.thumbnail((480, 270))
        thumbs.append(thumb)
    sheet = Image.new('RGB', (1440, 270 * math.ceil(len(thumbs) / 3)), (240, 240, 240))
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % 3) * 480, (index // 3) * 270))
    sheet.save(previews / 'deck-overview.jpg', quality=92)
    prior = json.loads((ROOT / 'ARTIFACT_MANIFEST.json').read_text())
    manifest = {'status': 'local_documents_rendered_visual_and_video_review_pending', 'generated_on': '2026-10-15',
        'deck_slide_count': len(names), 'native_table_count': native_tables, 'report_page_count': pages,
        'deck_pdf_page_count': len(slides), 'submission_ready': False,
        'superseded_archive': prior.get('superseded_archive'),
        'checks': {'report_within_six_pages_total': pages <= 6, 'deck_page_count_matches': len(names) == len(slides),
                   'native_tables_editable': native_tables >= 2, 'required_repository_report_matches': True},
        'manual_review': {'report_visual': False, 'deck_visual': False, 'video_playback': False, 'public_urls': False},
        'repository_report': {'path': 'track_2b/SwissChivers_Report.pdf', 'sha256': sha256(repository_report), 'bytes': repository_report.stat().st_size},
        'artifacts': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in sorted(out.iterdir()) if p.is_file()]}
    (ROOT / 'ARTIFACT_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Report: {pages} pages; deck: {len(slides)} pages; required repository report copied. Visual review remains pending.')


if __name__ == '__main__':
    main()
