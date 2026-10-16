"""Build the supporting engineering deck without importing application narration.

The HTML embeds verified captures, font data, theme CSS, and the controller.
Optional slide_notes.json is a mapping of slide numbers to reference notes.
It is independent of demo.md, which defines the application recording sequence.
"""
from pathlib import Path
import base64
import hashlib
import html
import json

root = Path(__file__).resolve().parents[1]
source = root / 'source'
output = root / 'output'
output.mkdir(exist_ok=True)
font_css = (source / 'presentation-fonts.css').read_text()
base_css = (source / 'viewport-base.css').read_text()
theme_css = (source / 'frontend-slides-theme.css').read_text()
controller = (source / 'frontend-slides-controller.js').read_text()
notes_path = source / 'slide_notes.json'
notes = json.loads(notes_path.read_text()) if notes_path.exists() else {}

# Preserve the existing capture provenance; never redraw application evidence.
evidence = json.loads((root / 'REAL_SOURCE_EVIDENCE.json').read_text())
capture_names = ['workbench-search.png', 'workbench-overview.png']
for name in capture_names:
    capture = next(item for item in evidence['browser_captures'] if item['path'] == 'captures/' + name)
    assert hashlib.sha256((root / capture['path']).read_bytes()).hexdigest() == capture['sha256']

slides = []

def bullets(items, classes=''):
    return '<ul class="mechanism-list ' + classes + '">' + ''.join(
        f'<li data-edit><strong>{html.escape(mechanism)}</strong>: {html.escape(claim)}</li>'
        for mechanism, claim in items
    ) + '</ul>'

def slide(number, title, content, classes=''):
    note = html.escape(notes.get(str(number), ''))
    slides.append(f'''<!-- === SLIDE {number}: {html.escape(title)} === -->
<section class="slide {classes}" aria-label="{number}. {html.escape(title)}">
<header><span data-edit>TENDERPROOF</span><span data-edit>SWISSCHIVERS / HACK APERTUS</span></header>
{content}
<footer><span data-edit>SUPPORTING ENGINEERING MATERIAL</span><span>{number:02} / 10</span></footer>
<aside class="speaker-notes" hidden>{note}</aside>
</section>''')

slide(1, 'Review gates bind releases to reviewed evidence', '''
<div class="cover-rule"></div>
<div class="cover-copy"><h1 class="reveal" data-edit>Review gates bind releases<br>to reviewed evidence.</h1>
<p class="cover-sub reveal" data-edit>Transformer procurement review with Apertus.</p></div>
''' + bullets([
    ('Apertus', 'Proposes source-linked claims.'),
    ('Review gates', 'Bind approvals to the package revision.'),
], 'cover-bullets'), 'cover')

slide(2, 'Package scope selects three 750 kVA transformers', '''
<h2 class="reveal" data-edit>Package scope selects three<br>750 kVA transformers.</h2>
<div class="case-left"><div class="eyebrow" data-edit>GUAM POWER AUTHORITY / OP34276 / ITEM 2</div>
<div class="case-number" data-edit>3 × 750 <small>kVA</small></div>
<p class="spec" data-edit>13.8 kV primary<br>120/208 V secondary</p>
<p class="source-note" data-edit>The scope excludes the separate 300 kVA item 1.</p></div>
<table class="source-table"><thead><tr><th>Original</th><th>Pages</th></tr></thead><tbody>
<tr><td data-edit>Full tender</td><td data-edit>57</td></tr>
<tr><td data-edit>E-004 specification</td><td data-edit>20</td></tr>
<tr><td data-edit>Bid abstract</td><td data-edit>5</td></tr>
<tr><td data-edit>Amendments / issuance</td><td data-edit>4</td></tr>
<tr><td data-edit>Purchase order</td><td data-edit>9</td></tr>
</tbody></table>
<p class="source-overlap" data-edit>95 attachment pages include overlapping material.</p>
''', 'paper')

slide(3, 'Evidence workspaces connect source inspection with revision review', '''
<h2 class="reveal" data-edit>Evidence workspaces connect source<br>inspection with revision review.</h2>
<div class="flow-diagram" aria-label="Source spans flow through Apertus proposals, human review, and snapshot-bound checks">
<div><span>01 / SOURCE</span><h3 data-edit>Docling spans</h3><p data-edit>Original PDF + page locator</p></div><b>→</b>
<div><span>02 / INTERPRETATION</span><h3 data-edit>Apertus proposals</h3><p data-edit>Four bounded roles</p></div><b>→</b>
<div><span>03 / REVIEW</span><h3 data-edit>Human decisions</h3><p data-edit>Meaning + applicability</p></div><b>→</b>
<div><span>04 / VERIFICATION</span><h3 data-edit>Snapshot checks</h3><p data-edit>Z3 + commercial rules</p></div>
</div>
''' + bullets([
    ('BM25 search', 'Ranks retained source passages without claiming confidence.'),
    ('Lineage', 'Links documents, claims, corrections, and recorded runs.'),
    ('Snapshot diff', 'Exposes changed fields and affected source references.'),
    ('Draft dossier', 'Exports snapshot-bound review records without granting approval.'),
], 'flow-bullets'))

slide(4, 'Price corrections preserve the original model output', '''
<h2 class="reveal" data-edit>Price corrections preserve<br>the original model output.</h2>
<div class="price-grid"><div><div class="eyebrow" data-edit>MODEL PROPOSAL / THREE-UNIT TOTAL</div>
<div class="amount wrong" data-edit>$111,316.50</div><p data-edit>The model used the unit-price field.</p></div>
<div><div class="eyebrow" data-edit>ASSISTANT CORRECTION / PER UNIT</div>
<div class="amount correct" data-edit>$37,105.50</div><p data-edit>Purchase order PDF page 4.</p></div></div>
''' + bullets([
    ('Correction', 'Preserves raw output; qualified review remains pending.'),
], 'price-bullet'), 'paper')

slide(5, 'Source search locates the original purchase order price', '''
<h2 class="reveal" data-edit>Source search locates<br>the original purchase order price.</h2>
<div class="workbench-search-frame"><img src="../captures/workbench-search.png" alt="Deployed Safari search returns purchase order page 4 first, with the retained unit price and three-unit total."></div>
''' + bullets([
    ('Exact retrieval', 'Ranks purchase order page 4 first for $37,105.50.'),
    ('Source inspection', 'Opens the cited passage and original PDF page.'),
], 'workbench-search-bullets'))

slide(6, 'Incomplete evidence blocks purchase and shipment release', '''
<h2 class="reveal" data-edit>Incomplete evidence blocks<br>purchase and shipment release.</h2>
<div class="workbench-overview-frame"><img src="../captures/workbench-overview.png" alt="Deployed Safari overview shows 43 blocking issues, 35 pending requirements, four pending offers, and zero acceptance records."></div>
''' + bullets([
    ('Review state', '35 requirements and four offers remain pending.'),
    ('FAT evidence', 'No acceptance record exists; shipment remains blocked.'),
], 'workbench-overview-bullets'), 'paper')

slide(7, 'Trace archives preserve recorded GPU execution evidence', '''
<h2 class="reveal" data-edit>Trace archives preserve<br>recorded GPU execution evidence.</h2>
<div class="architecture"><div class="arch-model"><span class="eyebrow" data-edit>RECORDED MODEL EXECUTION</span>
<h3 data-edit>Apertus v1.5 / 8B</h3><p data-edit>Participant-controlled GPU host</p></div>
<div class="arch-line"></div><div class="arch-components">
<div><h3 data-edit>PostgreSQL</h3><p data-edit>Versioned package state</p></div>
<div><h3 data-edit>Temporal</h3><p data-edit>Durable extraction workflow</p></div>
<div><h3 data-edit>Relay</h3><p data-edit>Authenticated model access</p></div></div></div>
<div class="runtime-state"><div class="eyebrow" data-edit>CURRENT ENDPOINT STATE</div><h3 data-edit>Stopped</h3>
<p data-edit>Operator restored borrowed workloads after recording.</p></div>
''' + bullets([
    ('Deployment', 'Uses operator-controlled infrastructure; Swiss residency remains unverified.'),
], 'runtime-bullet'))

slide(8, 'Role gates require approvals for each package revision', '''
<h2 class="reveal" data-edit>Role gates require approvals<br>for each package revision.</h2>
<table class="approval-table"><thead><tr><th>Decision</th><th>Required authority</th><th>Recorded state</th></tr></thead><tbody>
<tr><td data-edit>Purchase release</td><td data-edit>Engineer + Commercial</td><td data-edit>Blocked</td></tr>
<tr><td data-edit>Shipment release</td><td data-edit>Inspector + Commercial</td><td data-edit>Blocked</td></tr>
</tbody></table>
''' + bullets([
    ('Revision change', 'Stales prior decisions and triggers full-package reassessment.'),
    ('Initial identity', 'Restricts the engineer principal to the default project.'),
    ('Acceptance', 'Leaves missing measurements and unit identity unknown.'),
], 'approval-bullets'), 'paper')

slide(9, 'Recorded inference runs expose unresolved extraction limits', '''
<h2 data-edit>Recorded inference runs expose<br>unresolved extraction limits.</h2>
<div class="run-facts"><div><b data-edit>380 / 51</b><span data-edit>backend / frontend tests passed</span></div>
<div><b data-edit>5 / 64</b><span data-edit>completed runs / call traces</span></div>
<div><b data-edit>427 s</b><span data-edit>full 57-page tender</span></div></div>
''' + bullets([
    ('Software QA', 'Verifies behavior; model accuracy remains unmeasured.'),
    ('Execution history', 'Retains 15 attempts: five completed and ten failed.'),
    ('Recorded proposals', 'Include wrong bidder prices and out-of-scope requirements.'),
    ('Full tender', 'Retains one failed audit and one capped window.'),
], 'measurement-bullets') + '''
<div class="references"><a href="https://go.opengovguam.com/tenders/tender_details/gpa/GPA-070-25">GPA procurement sources</a><a href="https://huggingface.co/swiss-ai/Apertus-v1.5-8B">Apertus model</a><a href="https://github.com/Vishwa-docs/TenderProof/blob/main/track_2b/submission/VERIFICATION.md">Execution verification</a></div>
''')

roadmap = [
    ('Connect enterprise systems', ['ERP purchase orders', 'PLM synchronization', 'Supplier clarifications', 'Enterprise identity', 'Portfolio dashboard']),
    ('Broaden engineering schemas', ['Switchgear / protection', 'Battery / inverter packs', 'BIM / IFC linkage', 'Simulation adapters', 'Standards applicability']),
    ('Track equipment execution', ['Inspection hold points', 'Shipping readiness', 'Site commissioning', 'Change-order preparation', 'Warranty investigation']),
    ('Evaluate lifecycle decisions', ['Lifecycle energy losses', 'Supplier performance', 'Spare interchangeability', 'Expert feedback / evaluation', 'Cross-project sourcing']),
]
roadmap_columns = ''.join('<div><h3 data-edit>' + html.escape(title) + '</h3><table><tbody>' + ''.join(
    f'<tr><td>{5 + column * 5 + row:02}</td><td data-edit>{html.escape(item)}</td></tr>'
    for row, item in enumerate(items)
) + '</tbody></table></div>' for column, (title, items) in enumerate(roadmap))
slide(10, 'The roadmap puts qualified validation before planned extensions', '''
<h2 data-edit>The roadmap puts qualified validation<br>before planned extensions.</h2>
<div class="roadmap">''' + roadmap_columns + '''</div>
<p class="small-bottom" data-edit>Twenty planned extensions follow qualified validation of the transformer workflow.</p>
''', 'paper')

html_file = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TenderProof | Supporting engineering slides</title><style>
/* === EMBEDDED GOOGLE FONTS; LICENCES IN LICENSES/PRESENTATION-FONTS.txt === */
''' + font_css + '\n' + base_css + '\n' + theme_css + '''
</style></head><body><div class="deck-viewport"><main class="deck-stage" id="deckStage">
''' + ''.join(slides) + '''</main></div>
<nav class="deck-controls" aria-label="Slide controls"><button id="prev" aria-label="Previous slide">←</button><span id="count"></span><button id="next" aria-label="Next slide">→</button><button id="fullscreen">Full screen · F</button><button id="save">Save HTML</button><span>R: hide controls</span></nav>
<div class="edit-hotzone" aria-hidden="true"></div><button class="edit-toggle" id="editToggle" aria-label="Toggle text editing">Edit · E</button><script>
''' + controller + '</script></body></html>'
for name in capture_names:
    encoded = base64.b64encode((root / 'captures' / name).read_bytes()).decode()
    html_file = html_file.replace('../captures/' + name, 'data:image/png;base64,' + encoded)
(output / 'TenderProof_Slides.html').write_text(html_file)
print(f'Created {len(slides)} supporting slides; {len(html_file)} characters. Captures and fonts embedded; narration remains independent.')
