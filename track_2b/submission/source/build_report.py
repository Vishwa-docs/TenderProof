"""Render only the TenderProof report and its diagrams; never mutate the deck or manifests.

Run with an environment containing reportlab and pypdf:
    python track_2b/submission/source/build_report.py --preflight
    python track_2b/submission/source/build_report.py

Diagram JSON files are editable sources shared by the vector SVG and PDF output.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)
from pypdf import PdfReader

SUBMISSION = Path(__file__).resolve().parents[1]
TRACK = SUBMISSION.parent
REPO = TRACK.parent
REPORT = TRACK / 'technical_report.md'
EVIDENCE = SUBMISSION / 'REAL_SOURCE_EVIDENCE.json'
DIAGRAMS = TRACK / 'docs' / 'diagrams'
BUILD = SUBMISSION / '.build' / 'report-20261016'
OUTPUT = SUBMISSION / 'output' / 'SwissChivers_Report.pdf'
COPY = TRACK / 'SwissChivers_Report.pdf'
SOURCE_COMMIT = re.search(r'Application source/code commit: `([^`]+)`', REPORT.read_text()).group(1)
DOC_ID = 'TP-TR-001'
WIDTH, HEIGHT = A4
MARGIN = 43
FRAME_WIDTH = WIDTH - 2 * MARGIN
FRAME_HEIGHT = HEIGHT - 103
NAVY = '#163448'
TEAL = '#116B67'
MUTED = '#536472'
LINE = '#BFCCD2'
PALE = '#F2F6F7'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fonts():
    system = Path('/System/Library/Fonts/Supplemental')
    bundled = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pdfjs-dist/standard_fonts'
    candidates = [
        (system / 'Arial.ttf', system / 'Arial Bold.ttf'),
        (bundled / 'LiberationSans-Regular.ttf', bundled / 'LiberationSans-Bold.ttf'),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont('TP', str(regular)))
            pdfmetrics.registerFont(TTFont('TPBold', str(bold)))
            pdfmetrics.registerFontFamily('TP', normal='TP', bold='TPBold', italic='TP', boldItalic='TPBold')
            return {'regular': str(regular), 'bold': str(bold)}
    raise RuntimeError('Arial or Liberation Sans fonts are required.')


def styles():
    common = dict(fontName='TP', fontSize=10.3, leading=14.0, textColor=colors.HexColor(NAVY))
    return {
        'body': ParagraphStyle('body', **common, spaceAfter=8),
        'title': ParagraphStyle('title', fontName='TPBold', fontSize=25, leading=30, textColor=colors.HexColor(NAVY), spaceAfter=14),
        'h2': ParagraphStyle('h2', fontName='TPBold', fontSize=15.5, leading=19, textColor=colors.HexColor(TEAL), spaceBefore=8, spaceAfter=8, keepWithNext=True),
        'h3': ParagraphStyle('h3', fontName='TPBold', fontSize=11.4, leading=15, textColor=colors.HexColor(NAVY), spaceBefore=7, spaceAfter=6, keepWithNext=True),
        'meta': ParagraphStyle('meta', **{**common, 'fontSize':9.5, 'leading':12.5}, spaceAfter=2),
        'item': ParagraphStyle('item', **common, spaceAfter=3, leftIndent=14, firstLineIndent=-14),
        'caption': ParagraphStyle('caption', fontName='TP', fontSize=8.8, leading=11.5, textColor=colors.HexColor(MUTED), spaceAfter=8),
        'cell': ParagraphStyle('cell', fontName='TP', fontSize=8.9, leading=11.8, textColor=colors.HexColor(NAVY)),
        'headcell': ParagraphStyle('headcell', fontName='TPBold', fontSize=8.9, leading=11.8, textColor=colors.white),
        'ref': ParagraphStyle('ref', fontName='TP', fontSize=9.4, leading=13.2, textColor=colors.HexColor(NAVY), spaceAfter=8),
    }


def inline(text):
    tokens = []
    def stash(markup):
        tokens.append(markup)
        return f'@@TOKEN{len(tokens) - 1}@@'
    def link(m):
        label, target = m.group(1), m.group(2)
        if target.startswith(('https://', 'http://')):
            return stash(f'<link href="{escape(target)}" color="{TEAL}"><u>{escape(label)}</u></link>')
        path = (TRACK / target).resolve()
        if not path.exists():
            raise ValueError(f'Missing local reference: {target}')
        display = path.relative_to(REPO).as_posix()
        return stash(f'{escape(label)} (<font size="8.9">{escape(display)}</font>)')
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)
    text = re.sub(r'`([^`]+)`', lambda m: stash(f'<font color="{TEAL}">{escape(m.group(1))}</font>'), text)
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    for i, markup in enumerate(tokens):
        text = text.replace(f'@@TOKEN{i}@@', markup)
    return text


def palette(kind):
    return {
        'boundary': ('#F8FAFB', '#9BAEB8'),
        'node': ('#FFFFFF', TEAL),
        'blocked': ('#FFF4E9', '#A66A26'),
        'note': ('#EEF4F6', '#9BAEB8'),
    }[kind]


def box_lines(element):
    lines = element['lines']
    gap = 23 if element.get('kind') != 'note' else 24
    first_y = element['y'] + element['h'] / 2 - (len(lines) - 1) * gap / 2 + 6
    return [(element['x'] + element['w'] / 2, first_y + n * gap, line, 19 if n else 20, n == 0)
            for n, line in enumerate(lines)]


def arrow_head(points):
    (x1, y1), (x2, y2) = points[-2:]
    angle = math.atan2(y2 - y1, x2 - x1)
    return [(x2, y2),
            (x2 - 10 * math.cos(angle - .43), y2 - 10 * math.sin(angle - .43)),
            (x2 - 10 * math.cos(angle + .43), y2 - 10 * math.sin(angle + .43))]


def save_svg(source, target):
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', viewBox=f"0 0 {source['width']} {source['height']}", role='img')
    ET.SubElement(svg, 'title').text = source['title']
    ET.SubElement(svg, 'desc').text = source['description']
    def label(x, y, text, size=18, bold=False, anchor='middle'):
        item = ET.SubElement(svg, 'text', x=str(x), y=str(y), fill=NAVY,
                             attrib={'font-family': 'Arial, Liberation Sans, sans-serif', 'font-size': str(size),
                                     'font-weight': '700' if bold else '400', 'text-anchor': anchor})
        item.text = text
    for e in source['elements']:
        if e['type'] == 'box':
            fill, stroke = palette(e.get('kind', 'node'))
            ET.SubElement(svg, 'rect', x=str(e['x']), y=str(e['y']), width=str(e['w']), height=str(e['h']), rx='5',
                          fill=fill, stroke=stroke, attrib={'stroke-width': '1.5'})
            for x, y, line, size, bold in box_lines(e):
                label(x, y, line, size, bold)
        elif e['type'] == 'text':
            label(e['x'], e['y'], e['text'], e.get('size', 18), e.get('bold', False), e.get('anchor', 'start'))
        elif e['type'] == 'arrow':
            pts = e['points']
            ET.SubElement(svg, 'polyline', points=' '.join(f'{x},{y}' for x,y in pts), fill='none', stroke=MUTED,
                          attrib={'stroke-width': '1.8', 'stroke-dasharray': '5 3' if e.get('dashed') else 'none'})
            for path in [pts] + ([list(reversed(pts))] if e.get('bidir') else []):
                ET.SubElement(svg, 'polygon', points=' '.join(f'{x},{y}' for x,y in arrow_head(path)), fill=MUTED)
            if e.get('label'):
                label(e['lx'], e['ly'], e['label'], 16)
    ET.indent(svg)
    ET.ElementTree(svg).write(target, encoding='utf-8', xml_declaration=True)


class Diagram(Flowable):
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.width = FRAME_WIDTH
        self.height = self.width * source['height'] / source['width']
    def draw(self):
        c = self.canv
        scale = self.width / self.source['width']
        c.saveState()
        c.scale(scale, scale)
        h = self.source['height']
        def label(x, y, text, size=18, bold=False, anchor='middle'):
            c.setFont('TPBold' if bold else 'TP', size)
            c.setFillColor(colors.HexColor(NAVY))
            fn = c.drawCentredString if anchor == 'middle' else c.drawString
            fn(x, h-y, text)
        for e in self.source['elements']:
            if e['type'] == 'box':
                fill, stroke = palette(e.get('kind','node'))
                c.setFillColor(colors.HexColor(fill)); c.setStrokeColor(colors.HexColor(stroke)); c.setLineWidth(1.5)
                c.roundRect(e['x'], h-e['y']-e['h'], e['w'], e['h'], 5, fill=1, stroke=1)
                for x,y,line,size,bold in box_lines(e): label(x,y,line,size,bold)
            elif e['type'] == 'text':
                label(e['x'],e['y'],e['text'],e.get('size',18),e.get('bold',False),e.get('anchor','start'))
            elif e['type'] == 'arrow':
                pts=e['points']; c.setStrokeColor(colors.HexColor(MUTED)); c.setFillColor(colors.HexColor(MUTED)); c.setLineWidth(1.8)
                c.setDash(5,3) if e.get('dashed') else c.setDash()
                p=c.beginPath(); p.moveTo(pts[0][0],h-pts[0][1])
                for x,y in pts[1:]: p.lineTo(x,h-y)
                c.drawPath(p)
                for path in [pts]+([list(reversed(pts))] if e.get('bidir') else []):
                    head=arrow_head(path); p=c.beginPath(); p.moveTo(head[0][0],h-head[0][1])
                    for x,y in head[1:]: p.lineTo(x,h-y)
                    p.close(); c.drawPath(p,fill=1,stroke=0)
                if e.get('label'): label(e['lx'],e['ly'],e['label'],16)
        c.restoreState()


def column_widths(header):
    if header[0] == 'Control': return [103, 223, FRAME_WIDTH-326]
    if header[0] == 'Phase': return [103, 242, FRAME_WIDTH-345]
    if header[0] == 'Setting': return [76, 197, FRAME_WIDTH-273]
    if header[0] == 'Complete source': return [170, 58, FRAME_WIDTH-228]
    if header[0] == 'Setup or task': return [100, 154, FRAME_WIDTH-254]
    raise ValueError(f'No reviewed column plan for {header}')


def story(style, diagrams):
    output=[]; lines=REPORT.read_text().splitlines(); i=0; references=False
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1; continue
        if line == '<!-- PAGEBREAK -->': output.append(PageBreak()); i+=1; continue
        if line.startswith('!['):
            match=re.fullmatch(r'!\[([^\]]+)\]\(([^)]+)\)',line)
            if not match: raise ValueError('Invalid diagram syntax')
            key=Path(match.group(2)).stem
            output.extend([Diagram(diagrams[key]),Spacer(1,5)])
            i+=1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',c) for c in row): rows.append(row)
                i+=1
            cells=[[Paragraph(inline(c),style['headcell' if n==0 else 'cell']) for c in row] for n,row in enumerate(rows)]
            table=Table(cells,colWidths=column_widths(rows[0]),hAlign='LEFT',repeatRows=1,splitByRow=0)
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor(NAVY)),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor(PALE)]),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor(NAVY)),
                ('LINEBELOW',(0,1),(-1,-1),.35,colors.HexColor(LINE)),
                ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ]))
            output.extend([table,Spacer(1,8)]); continue
        found=False
        for prefix,key in [('# ','title'),('## ','h2'),('### ','h3')]:
            if line.startswith(prefix):
                if line=='## References': references=True
                output.append(Paragraph(inline(line[len(prefix):]),style[key])); i+=1; found=True; break
        if found: continue
        key='ref' if references else 'caption' if line.startswith('Figure ') else 'meta' if line.startswith('- ') else 'item' if re.match(r'^\d+\. ',line) else 'body'
        if line.startswith('- '): line=line[2:]
        chunk=[line]; i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','<!--','![','- ')) and not re.match(r'^\d+\. ',lines[i]):
            chunk.append(lines[i].strip()); i+=1
        output.append(Paragraph(inline(' '.join(chunk)),style[key]))
    return output


def geometry(items):
    heights=[]; used=0
    for item in items:
        if isinstance(item,PageBreak): heights.append(round(used,2)); used=0; continue
        width,height=item.wrap(FRAME_WIDTH,10000)
        if width>FRAME_WIDTH+.1: raise ValueError(f'Content width overflow: {width}')
        used+=item.getSpaceBefore()+height+item.getSpaceAfter()
    heights.append(round(used,2))
    return heights


def page_decoration(canvas,doc):
    canvas.saveState(); canvas.setFillColor(colors.HexColor(MUTED)); canvas.setFont('TP',8)
    canvas.drawString(MARGIN,HEIGHT-27,f'{DOC_ID}  |  Rev 2  |  16 Oct 2026  |  Submission review')
    canvas.drawRightString(WIDTH-MARGIN,HEIGHT-27,'SwissChivers / Track 2B')
    canvas.setStrokeColor(colors.HexColor(TEAL)); canvas.setLineWidth(.8)
    canvas.line(MARGIN,HEIGHT-36,WIDTH-MARGIN,HEIGHT-36)
    canvas.setFont('TP',7.5)
    canvas.drawString(MARGIN,28,f"Source {sha256(REPORT)[:12]}  |  Evidence {sha256(EVIDENCE)[:12]}  |  Package v13")
    canvas.drawRightString(WIDTH-MARGIN,28,f'{doc.page} / 7')
    canvas.restoreState()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--preflight',action='store_true'); args=parser.parse_args()
    font_paths=fonts(); style=styles()
    evidence=json.loads(EVIDENCE.read_text())
    if evidence.get('current_version')!=13 or not evidence.get('ready_for_artifact_render'):
        raise ValueError('Evidence version or render readiness changed; review the report before rendering.')
    diagrams={p.stem:json.loads(p.read_text()) for p in sorted(DIAGRAMS.glob('*.json'))}
    items=story(style,diagrams); heights=geometry(items)
    plan={'page_count':len(heights),'content_pages':len(heights)-1,'frame_height_pt':round(FRAME_HEIGHT,2),'planned_heights_pt':heights}
    print(json.dumps(plan,indent=2))
    if len(heights)!=7 or len(heights)-1>6 or max(heights)>FRAME_HEIGHT:
        raise ValueError('Page plan exceeds the reviewed six-content-page geometry.')
    if args.preflight:return
    if not re.fullmatch(r'[0-9a-f]{40}',SOURCE_COMMIT) or '_PENDING' in REPORT.read_text():
        raise ValueError('Replace pending verification markers before final PDF rendering.')
    BUILD.mkdir(parents=True,exist_ok=True); OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    for name,data in diagrams.items(): save_svg(data,DIAGRAMS/f'{name}.svg')
    candidate=BUILD/'SwissChivers_Report.pdf'
    doc=BaseDocTemplate(str(candidate),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=49,bottomMargin=54,
                        title='Technical report - TenderProof',author='SwissChivers',subject='Hack Apertus Track 2B technical report; review revision 2',
                        allowSplitting=1,pageCompression=1)
    frame=Frame(MARGIN,54,FRAME_WIDTH,FRAME_HEIGHT,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id='report',frames=frame,onPage=page_decoration))
    doc.build(items)
    reader=PdfReader(candidate)
    if len(reader.pages)!=7:raise ValueError('Rendered page count differs from the reviewed plan.')
    page_text=[p.extract_text() for p in reader.pages]
    if 'References' not in page_text[-1]:raise ValueError('Reference page not last.')
    if SOURCE_COMMIT not in ''.join(page_text):raise ValueError('Exact source/code commit missing from PDF.')
    for p in [OUTPUT,COPY]:shutil.copyfile(candidate,p)
    if sha256(OUTPUT)!=sha256(COPY):raise ValueError('PDF copies differ.')
    report={**plan,'document_id':DOC_ID,'revision':2,'date':'2026-10-16','status':'submission_review',
            'source_code_commit':SOURCE_COMMIT,'evidence_version':13,'evidence_snapshot':evidence['current_snapshot_hash'],
            'report_source_sha256':sha256(REPORT),'evidence_sha256':sha256(EVIDENCE),'renderer_sha256':sha256(Path(__file__)),
            'pdf_sha256':sha256(OUTPUT),'pdf_bytes':OUTPUT.stat().st_size,'font_paths':font_paths,
            'outputs':[str(OUTPUT),str(COPY)],'diagram_sources':{p.name:sha256(p) for p in sorted(DIAGRAMS.iterdir())},
            'visual_review':'pending','page_text_characters':[len(t) for t in page_text]}
    (BUILD/'build_review.json').write_text(json.dumps(report,indent=2)+'\n')
    for n,t in enumerate(page_text,1):(BUILD/f'page-{n}.txt').write_text(t)
    print(json.dumps({'pdf':str(OUTPUT),'sha256':sha256(OUTPUT),'pages':len(reader.pages)}))


if __name__=='__main__':main()
