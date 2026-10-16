"""Deterministic read models for reviewing preserved evidence, never authorizing release.

Search is lexical retrieval over original stored spans. Citation coverage measures
references to spans, not completeness of extracted obligations or factual support.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import re
import unicodedata


MAX_VIEW_BYTES = 8 * 1024 * 1024
MAX_GRAPH_NODES = 500
MAX_GRAPH_EDGES = 2000
MAX_ISSUES = 5000
MAX_SEARCH_SPANS = 50000
MAX_SEARCH_CHARACTERS = 20000000
SENSITIVE_KEYS = frozenset({'trace', 'image_data_url', 'raw_output', 'raw_response',
    'request', 'response', 'request_body', 'response_body', 'api_key', 'authorization',
    'credentials', 'headers', 'access_token', 'secret', 'password'})
COLLECTION_TYPES = {'documents': 'document', 'requirements': 'requirement',
    'proposals': 'proposal', 'suppliers': 'supplier', 'evidence': 'evidence',
    'extraction_runs': 'run', 'decisions': 'decision'}
TOKEN = re.compile(r'\d+(?:,\d{3})*(?:\.\d+)?|[^\W\d_]+', re.UNICODE)


class ViewProblem(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _hash(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _bounded(value):
    if len(_canonical(value).encode()) > MAX_VIEW_BYTES:
        raise ViewProblem(413, 'This evidence view exceeds the 8 MiB response limit; no partial packet was returned.')
    return value


def _safe(value):
    """Keep changes detectable while excluding provider payloads and inline images."""
    if isinstance(value, dict):
        return {key: ({'omitted': True, 'sha256': _hash(item)} if key.lower() in SENSITIVE_KEYS else _safe(item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return deepcopy(value)


def _refs(record):
    refs = set(record.get('source_ids') or [])
    if record.get('source_id'):
        refs.add(record['source_id'])
    for fact in (record.get('facts') or []) + (record.get('measurements') or []):
        refs.update(fact.get('source_ids') or [])
    if isinstance(record.get('data'), dict):
        refs.update(_refs(record['data']))
    for correction in record.get('price_corrections') or []:
        if correction.get('source_id'):
            refs.add(correction['source_id'])
    return sorted(refs)


def _source_index(package):
    return {span['id']: (doc, span) for doc in package.get('documents', []) for span in doc.get('spans', [])}


def _corrections(package):
    # Approved supplier records retain their originating proposal's correction history.
    # Count that audit fact once, not once for each copy.
    rows = {}
    for record in package.get('proposals', []) + package.get('suppliers', []):
        for correction in record.get('price_corrections') or []:
            key = correction.get('id') or _hash(correction)
            rows.setdefault(key, {**_safe(correction), 'proposal_id': record.get('proposal_id') or record['id']})
    return [rows[key] for key in sorted(rows)]


def counts(package):
    requirements = package.get('requirements', [])
    proposals = package.get('proposals', [])
    decisions = package.get('decisions', [])
    return dict(document_count=len(package.get('documents', [])),
        span_count=sum(len(d.get('spans', [])) for d in package.get('documents', [])),
        requirement_count=len(requirements),
        pending_requirement_count=sum(r.get('status') == 'pending' for r in requirements),
        approved_requirement_count=sum(r.get('status') == 'approved' for r in requirements),
        pending_offer_count=sum(q.get('kind') == 'supplier' and q.get('status') == 'pending' for q in proposals),
        pending_evidence_count=sum(q.get('kind') == 'evidence' and q.get('status') == 'pending' for q in proposals),
        supplier_count=len(package.get('suppliers', [])), evidence_count=len(package.get('evidence', [])),
        correction_count=len(_corrections(package)),
        approval_count=sum(len(d.get('approvals') or []) for d in decisions),
        release_count=sum(d.get('status') == 'released' for d in decisions))


def _lineage(package, source_index):
    nodes = {}; edges = set()

    def node(kind, row, label=None, document_id=None):
        identity = kind + ':' + row['id']
        nodes[identity] = dict(id=identity, type=kind, label=label or row.get('title') or row.get('name') or row['id'],
            record_id=row['id'], document_id=document_id, source_ids=_refs(row))
        return identity

    for doc in package.get('documents', []):
        node('document', doc, document_id=doc['id'])
    for collection, kind in COLLECTION_TYPES.items():
        if collection == 'documents':
            continue
        for row in package.get(collection, []):
            did = row.get('document_id')
            target = node(kind, row, label=(row.get('data') or {}).get('name'), document_id=did)
            document_ids = {source_index[ref][0]['id'] for ref in _refs(row) if ref in source_index}
            if did:
                document_ids.add(did)
            for docid in sorted(document_ids):
                edges.add(('document:' + docid, target, 'extracted_from' if kind == 'run' else 'cites'))
            if row.get('proposal_id'):
                edges.add(('proposal:' + row['proposal_id'], target, 'reviewed_as'))
            if kind == 'decision' and row.get('supplier_id'):
                edges.add(('supplier:' + row['supplier_id'], target, 'prepared_for'))
    for correction in _corrections(package):
        target = node('correction', correction, label='Recorded price correction', document_id=correction.get('document_id'))
        edges.add(('proposal:' + correction['proposal_id'], target, 'corrected_by'))
        if correction.get('document_id'):
            edges.add(('document:' + correction['document_id'], target, 'cites'))
    # Documents first ensures bounded graphs retain source anchors.
    ordered = sorted(nodes.values(), key=lambda n: (n['type'] != 'document', n['id']))
    chosen = ordered[:MAX_GRAPH_NODES]
    ids = {n['id'] for n in chosen}
    all_edges = sorted(e for e in edges if e[0] in nodes and e[1] in nodes)
    visible_edges = [dict(source=a, target=b, relation=r) for a, b, r in all_edges if a in ids and b in ids]
    return dict(nodes=chosen, edges=visible_edges[:MAX_GRAPH_EDGES],
        truncated=len(ordered) > MAX_GRAPH_NODES or len(all_edges) > len(visible_edges[:MAX_GRAPH_EDGES]),
        limit=MAX_GRAPH_NODES)


def analyze(package, eligible_gates=()):
    sources = _source_index(package)
    issues = []

    def issue(kind, row, title, detail, *, severity='blocking', target='sources', action='Inspect source', gates=('purchase', 'shipment'), suffix=''):
        refs = _refs(row)
        docids = sorted({sources[ref][0]['id'] for ref in refs if ref in sources})
        docid = row.get('document_id') or (docids[0] if len(docids) == 1 else None)
        record_id = row.get('id') or package['id']
        issues.append(dict(id=kind + ':' + record_id + suffix, type=kind, severity=severity,
            title=title, detail=detail, record_type={'requirements': 'requirement', 'suppliers': 'proposal',
                'evidence': 'evidence', 'workflow': 'project'}.get(target, 'source'),
            record_id=record_id, document_id=docid, source_ids=refs, gates=list(gates),
            next_action=dict(label=action, target=target, record_id=record_id,
                document_id=docid, source_id=refs[0] if refs else None)))

    if not package.get('equipment'):
        issue('missing_scope', {}, 'Define the equipment scope', 'An equipment scope is required before a decision can be prepared.', target='workflow', action='Define scope')
    for requirement in package.get('requirements', []):
        if requirement.get('status') != 'approved':
            status = requirement.get('status', 'pending')
            issue('pending_requirement' if status == 'pending' else 'unapproved_requirement', requirement,
                requirement.get('title', 'Review requirement'),
                'Engineering interpretation is ' + status + '; inspect the exact source and its operating conditions.',
                target='requirements', action='Review interpretation')
    for proposal in package.get('proposals', []):
        if proposal.get('status') == 'pending':
            supplier = proposal.get('kind') == 'supplier'
            issue('pending_offer' if supplier else 'pending_evidence', proposal,
                (proposal.get('data') or {}).get('name') or (proposal.get('data') or {}).get('title') or 'Review proposal',
                'This extracted ' + ('offer' if supplier else 'evidence proposal') + ' awaits separate human review.',
                severity='review', target='suppliers' if supplier else 'evidence', action='Review offer' if supplier else 'Review evidence', gates=())
    for run in package.get('extraction_runs', []):
        if run.get('status') != 'recorded' or run.get('conditions'):
            issue('extraction_gap', run, 'Resolve extraction assurance',
                ' '.join(run.get('conditions') or ['Extraction assurance is incomplete or unknown.']),
                action='Inspect source and extraction conditions')
    for correction in _corrections(package):
        issue('price_correction', {**correction, 'id': correction['proposal_id']}, 'Price correction recorded',
            correction.get('reason') or 'A human price correction is preserved; proposal approval remains separate.',
            severity='info', target='suppliers', action='Inspect price correction', gates=(), suffix=':' + correction['id'])
    if not package.get('suppliers'):
        issue('missing_supplier', {}, 'No reviewed supplier', 'Pending offers are not selected supplier records. Review source-backed offers before preparing a decision.', target='suppliers', action='Review pending offers')
    if package.get('required_delivery_week') is None:
        issue('missing_schedule', {}, 'Required delivery milestone is unresolved',
            'Set a source-linked required delivery milestone before comparing the delivery schedule.', target='suppliers', action='Review delivery basis')
    for comparison in package.get('comparisons', []):
        if comparison['status'] != 'feasible':
            supplier = next(s for s in package['suppliers'] if s['id'] == comparison['supplier_id'])
            issue('supplier_conditions', supplier, supplier.get('name', 'Supplier') + ': unresolved conditions',
                ' '.join(dict.fromkeys(comparison.get('issues') or [])), target='suppliers', action='Inspect comparison')
    active_evidence = [e for e in package.get('evidence', []) if not e.get('superseded')]
    if not active_evidence:
        issue('missing_evidence', {}, 'Acceptance evidence is missing',
            'Shipment requires applicable reviewed evidence for the selected equipment, configuration and revision.',
            target='evidence', action='Review acceptance evidence', gates=('shipment',))
    for assessment in package.get('evidence_assessments', []):
        evidence = next(e for e in package['evidence'] if e['id'] == assessment['evidence_id'])
        if not evidence.get('superseded') and assessment['status'] != 'supported':
            issue('evidence_condition', evidence, evidence.get('title', 'Evidence applicability'),
                assessment['reason'], target='evidence', action='Inspect evidence applicability', gates=('shipment',))
    if len(issues) > MAX_ISSUES:
        raise ViewProblem(413, 'This package exceeds the 5,000-issue review limit; no partial queue was returned.')
    issues.sort(key=lambda i: ({'blocking': 0, 'review': 1, 'info': 2}[i['severity']], i['type'], i['id']))

    cited = set()
    records = [r for collection in ('requirements', 'proposals', 'suppliers', 'evidence') for r in package.get(collection, [])]
    for record in records:
        cited.update(_refs(record))
    if package.get('schedule_source_id'):
        cited.add(package['schedule_source_id'])
    documents = []
    for doc in package.get('documents', []):
        span_ids = {s['id'] for s in doc.get('spans', [])}
        requirements = [r for r in package.get('requirements', []) if span_ids.intersection(_refs(r))]
        proposals = [q for q in package.get('proposals', []) if q.get('document_id') == doc['id'] or span_ids.intersection(_refs(q))]
        runs = [r for r in package.get('extraction_runs', []) if r.get('document_id') == doc['id']]
        covered = len(span_ids.intersection(cited))
        documents.append(dict(document_id=doc['id'], name=doc['name'], sha256=doc.get('sha256'),
            page_count=(doc.get('parsing') or {}).get('page_count') or len({s['page'] for s in doc.get('spans', [])}),
            span_count=len(span_ids), cited_span_count=covered, citation_coverage=covered / len(span_ids) if span_ids else 0,
            requirement_count=len(requirements), proposal_count=len(proposals),
            correction_count=sum(c.get('document_id') == doc['id'] for c in _corrections(package)),
            extraction_run_count=len(runs), pending_count=sum(r.get('status') == 'pending' for r in requirements + proposals),
            assurance_status='not_extracted' if not runs else 'incomplete' if any(r.get('status') != 'recorded' or r.get('conditions') for r in runs) else 'recorded'))
    summary = {**counts(package), 'issue_count': len(issues), 'blocking_issue_count': sum(i['severity'] == 'blocking' for i in issues)}
    return _bounded(dict(project_id=package['id'], snapshot_hash=package['snapshot_hash'], version=package['version'],
        summary=summary, release_gates=[dict(gate=gate, status='review_required' if gate in eligible_gates else 'blocked',
            issue_ids=[i['id'] for i in issues if i['severity'] == 'blocking' and gate in i['gates']]) for gate in ('purchase', 'shipment')],
        issues=issues, documents=documents, lineage=_lineage(package, sources)))


def _term(value):
    if value[0].isdigit():
        # Canonicalize exactly, without the decimal context rounding long IDs.
        whole, _, fraction = value.replace(',', '').partition('.')
        whole = whole.lstrip('0') or '0'
        fraction = fraction.rstrip('0')
        return whole + ('.' + fraction if fraction else '')
    return unicodedata.normalize('NFKC', value).casefold()


def _tokens(text):
    return [_term(m.group()) for m in TOKEN.finditer(text)]


def _excerpt(text, terms=(), limit=1400):
    position = next((m.start() for m in TOKEN.finditer(text) if _term(m.group()) in terms), 0)
    start = max(0, min(position - 180, len(text) - limit)) if len(text) > limit else 0
    end = min(len(text), start + limit)
    return dict(text=text[start:end], text_start=start, text_end=end, text_truncated=start > 0 or end < len(text))


def search(package, query, document_id=None, limit=12):
    if not isinstance(query, str) or not query.strip() or len(query) > 300 or not _tokens(query):
        raise ViewProblem(422, 'Search requires 1–300 characters containing words or numbers.')
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ViewProblem(422, 'Search limit must be between 1 and 50.')
    docs = package.get('documents', [])
    if document_id is not None:
        docs = [d for d in docs if d['id'] == document_id]
        if not docs:
            raise KeyError(document_id)
    if sum(len(d.get('spans', [])) for d in docs) > MAX_SEARCH_SPANS or sum(len(s['text']) for d in docs for s in d.get('spans', [])) > MAX_SEARCH_CHARACTERS:
        raise ViewProblem(413, 'This search exceeds the 50,000-span or 20-million-character limit; select a document.')
    # Duplicate exact text (allowing formatting whitespace) is one retrieval item.
    groups = {}
    for doc in docs:
        for index, span in enumerate(doc.get('spans', [])):
            key = ' '.join(span['text'].split())
            groups.setdefault(key, []).append((doc, span, index))
    terms = set(_tokens(query))
    corpus = [(rows, Counter(_tokens(rows[0][1]['text']))) for rows in groups.values()]
    document_frequency = Counter(t for _, frequencies in corpus for t in terms if t in frequencies)
    size = len(corpus)
    average = sum(sum(freq.values()) for _, freq in corpus) / max(size, 1) or 1
    ranked = []
    for rows, frequencies in corpus:
        matched = sorted(terms.intersection(frequencies))
        if not matched:
            continue
        length = sum(frequencies.values())
        score = sum(math.log(1 + (size - document_frequency[t] + .5) / (document_frequency[t] + .5)) *
            (frequencies[t] * 2.2) / (frequencies[t] + 1.2 * (.25 + .75 * length / average)) for t in matched)
        ranked.append((score, rows, matched))
    ranked.sort(key=lambda result: (-result[0], result[1][0][0]['id'], result[1][0][1]['page'], result[1][0][1]['id']))

    def citation(doc, span):
        return dict(source_id=span['id'], document_id=doc['id'], document_name=doc['name'], page=span['page'], sha256=doc.get('sha256'))

    results = []
    for score, rows, matched in ranked[:limit]:
        doc, span, index = rows[0]
        neighbors = [doc['spans'][i] for i in (index - 1, index + 1) if 0 <= i < len(doc['spans']) and doc['spans'][i]['page'] == span['page']]
        results.append({**citation(doc, span), **_excerpt(span['text'], terms), 'score': round(score, 8),
            'matched_terms': matched, 'context': [dict(source_id=s['id'], page=s['page'], **_excerpt(s['text'], terms, 700)) for s in neighbors],
            'duplicate_citations': [citation(d, s) for d, s, _ in rows[1:]], 'duplicate_count': len(rows) - 1})
    return _bounded(dict(project_id=package['id'], snapshot_hash=package['snapshot_hash'], query=query.strip(),
        retrieval_method='BM25 lexical retrieval', score_meaning='Lexical relevance only; not confidence, proof or independent corroboration.',
        limit=limit, total_matches=len(ranked), results=results))


def snapshot_metadata(package, current_hash):
    return dict(snapshot_hash=package['snapshot_hash'], version=package.get('version', 1),
        is_current=package['snapshot_hash'] == current_hash,
        created_at=next((e.get('at') for e in package.get('events', []) if e.get('at')), None), summary=counts(package))


def _field_changes(before, after, path=''):
    if _canonical(before) == _canonical(after):
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        return [change for key in sorted(set(before) | set(after))
                for change in (_field_changes(before[key], after[key], path + '/' + key.replace('~', '~0').replace('/', '~1'))
                    if key in before and key in after else [dict(path=path + '/' + key.replace('~', '~0').replace('/', '~1'),
                        before=before.get(key), after=after.get(key), operation='added' if key not in before else 'removed')])]
    return [dict(path=path or '/', before=deepcopy(before), after=deepcopy(after))]


def diff(before, after, current_hash):
    if before['id'] != after['id']:
        raise KeyError('Snapshot project mismatch')
    sources = {**_source_index(before), **_source_index(after)}
    changes = []
    for collection in COLLECTION_TYPES:
        old = {r['id']: r for r in before.get(collection, [])}
        new = {r['id']: r for r in after.get(collection, [])}
        for rid in sorted(set(old) | set(new)):
            if _canonical(old.get(rid)) == _canonical(new.get(rid)):
                continue
            row = new.get(rid) or old[rid]
            refs = sorted(set(_refs(old.get(rid, {}))) | set(_refs(new.get(rid, {}))))
            if collection == 'decisions':
                suppliers = {r.get('supplier_id') for r in (old.get(rid, {}), new.get(rid, {}))}
                refs = sorted(set(refs) | {ref for state in (before, after) for supplier in state.get('suppliers', [])
                    if supplier['id'] in suppliers for ref in _refs(supplier)})
            docids = {sources[ref][0]['id'] for ref in refs if ref in sources}
            for item in (old.get(rid, {}), new.get(rid, {})):
                if item.get('document_id'):
                    docids.add(item['document_id'])
            if collection == 'documents':
                docids.add(rid)
            changes.append(dict(collection=collection, record_id=rid,
                change='added' if rid not in old else 'removed' if rid not in new else 'modified',
                label=row.get('title') or row.get('name') or (row.get('data') or {}).get('name') or rid,
                fields=_field_changes(_safe(old.get(rid)), _safe(new.get(rid))), source_ids=refs, document_ids=sorted(docids)))
    metadata_fields = ('name', 'customer', 'equipment', 'mode', 'required_delivery_week', 'schedule_source_id')
    metadata = _field_changes({k: before.get(k) for k in metadata_fields}, {k: after.get(k) for k in metadata_fields})
    if metadata:
        changes.append(dict(collection='project', record_id=after['id'], change='modified', label='Project metadata',
            fields=metadata, source_ids=sorted({p['schedule_source_id'] for p in (before, after) if p.get('schedule_source_id')}), document_ids=[]))
    affected = {(COLLECTION_TYPES.get(c['collection'], 'project'), c['record_id']): set(c['source_ids']) for c in changes}
    changed_docs = {c['record_id'] for c in changes if c['collection'] == 'documents'}
    if changed_docs:
        for collection, kind in COLLECTION_TYPES.items():
            if collection == 'documents':
                continue
            for row in before.get(collection, []) + after.get(collection, []):
                refs = _refs(row)
                if row.get('document_id') in changed_docs or any(ref in sources and sources[ref][0]['id'] in changed_docs for ref in refs):
                    affected.setdefault((kind, row['id']), set()).update(refs)
    return _bounded(dict(project_id=after['id'], snapshot_hash=current_hash, from_hash=before['snapshot_hash'], to_hash=after['snapshot_hash'],
        from_version=before.get('version', 1), to_version=after.get('version', 1), changed=bool(changes),
        summary={kind: sum(c['change'] == kind for c in changes) for kind in ('added', 'removed', 'modified')},
        changes=changes, impacted_records=[dict(type=kind, id=rid, source_ids=sorted(refs)) for (kind, rid), refs in sorted(affected.items())],
        sensitive_content_omitted=True, comparison_scope='Stored content and decision lifecycle; audit event logs are excluded.'))


def dossier(package, eligible_gates=()):
    analysis = analyze(package, eligible_gates)
    packet = dict(schema_version='1.0', packet_type='draft_review_dossier', status='draft',
        meaning='Draft review packet. This export grants no approval and authorizes no purchase or shipment. Pending states and blocked gates are preserved. Citation coverage is not obligation completeness. Provider traces and inline image bytes are represented by hashes; original sources remain separately available.',
        project_id=package['id'], snapshot_hash=package['snapshot_hash'], version=package['version'],
        project={k: package.get(k) for k in ('name', 'customer', 'equipment', 'required_delivery_week', 'schedule_source_id')},
        summary=analysis['summary'], release_gates=analysis['release_gates'], issues=analysis['issues'],
        source_catalog=_safe(package.get('documents', [])), requirements=_safe(package.get('requirements', [])),
        proposals=_safe(package.get('proposals', [])), suppliers=_safe(package.get('suppliers', [])), evidence=_safe(package.get('evidence', [])),
        corrections=_corrections(package), extraction_runs=_safe(package.get('extraction_runs', [])),
        lineage=analysis['lineage'], decisions=[{k: _safe(d.get(k)) for k in ('id', 'supplier_id', 'gate', 'snapshot_hash', 'status', 'approvals', 'created_at')}
            for d in package.get('decisions', [])],
        source_coverage=analysis['documents'], sensitive_content_omitted=True)
    packet['packet_hash'] = _hash(packet)
    return _bounded(packet)
