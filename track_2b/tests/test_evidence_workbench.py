"""Isolated software QA for read-only evidence views; never live seed data."""
from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update

from tenderproof.api import create_app
from tenderproof.service import digest, snapshot


@pytest.fixture
def workbench(tmp_path, monkeypatch):
    monkeypatch.setenv('RUNTIME_DIR', str(tmp_path / 'runtime'))
    app = create_app(database_url='sqlite:///' + str(tmp_path / 'qa.db'), principals={
        'owner': {'actor': 'qa-owner', 'role': 'engineer', 'projects': ['default']},
        'outside': {'actor': 'qa-outside', 'role': 'engineer', 'projects': ['other']},
        'both': {'actor': 'qa-both', 'role': 'inspector', 'projects': ['default', 'other']},
    })
    s = app.state.service
    with s.engine.connect() as conn:
        p = deepcopy(conn.execute(select(s.projects.c.state)).scalar_one())
    p.update(name='Constructed QA package', equipment='QA transformer', version=2)
    p['documents'] = [
        {'id': 'qa-spec', 'name': 'QA specification', 'sha256': 'a' * 64, 'spans': [
            {'id': 'qa-spec:0', 'page': 1, 'text': 'Constructed test source, preceding context.'},
            {'id': 'qa-spec:1', 'page': 1, 'text': 'The transformer is rated 750 kVA.'},
            {'id': 'qa-spec:2', 'page': 1, 'text': 'Delivery is 24 weeks after drawing approval.'},
            {'id': 'qa-spec:3', 'page': 2, 'text': 'Offer price USD 37,105.50 per unit.'},
        ]},
        {'id': 'qa-annex', 'name': 'QA duplicate annex', 'sha256': 'b' * 64, 'spans': [
            {'id': 'qa-annex:1', 'page': 1, 'text': 'The transformer is rated 750 kVA.'},
            {'id': 'qa-annex:2', 'page': 1, 'text': 'Delivery schedule: approval is required.'},
        ]},
    ]
    p['requirements'] = [{'id': 'qa-r1', 'title': 'QA rating', 'property': 'rated_power',
        'operator': 'ge', 'value': '750', 'unit': 'kVA', 'conditions': {},
        'phase': 'purchase', 'equipment_type': 'transformer', 'source_ids': ['qa-spec:1'],
        'status': 'pending', 'reviewer': None, 'witness_expected': None}]
    p['proposals'] = [{'id': 'qa-p1', 'kind': 'supplier', 'document_id': 'qa-spec',
        'supplier_id': None, 'source_ids': ['qa-spec:2', 'qa-spec:3'], 'status': 'pending',
        'data': {'name': 'QA offer', 'configuration': None, 'revision': None,
                 'price_cents': 3710550, 'currency': 'USD', 'delivery_weeks': 24,
                 'delivery_basis': 'after_drawing_approval', 'price_basis': 'unit',
                 'expedite_cents': None, 'rework_cents': None, 'facts': [],
                 'source_ids': ['qa-spec:3']},
        'trace': {'request': {'api_key': 'qa-SECRET-NEVER-EXPORT'}, 'raw_output': 'qa-secret-body'}}]
    p['extraction_runs'] = [{'id': 'qa-run1', 'document_id': 'qa-spec', 'kind': 'requirements',
        'status': 'incomplete', 'conditions': ['Complete source-span coverage is unverified.'],
        'trace': {'raw_output': 'qa-secret-body'}, 'legacy': False, 'event_id': None}]
    p['snapshot_hash'] = snapshot(p)
    before = deepcopy(p)
    p['version'] = 3
    q = p['proposals'][0]
    q['original_data'] = deepcopy(q['data'])
    q['data']['price_cents'] = 3710500
    q['price_corrections'] = [{'id': 'qa-c1', 'at': '2026-10-16T00:00:00+00:00',
        'actor': 'qa-owner', 'document_id': 'qa-spec', 'source_id': 'qa-spec:3', 'page': 2,
        'reason': 'QA original cell review', 'before': {'price_cents': 3710550, 'currency': 'USD'},
        'after': {'price_cents': 3710500, 'currency': 'USD'}}]
    p['snapshot_hash'] = snapshot(p)
    foreign = deepcopy(before)
    foreign.update(id='other', name='Private other project')
    foreign['snapshot_hash'] = snapshot(foreign)
    with s.engine.begin() as conn:
        conn.execute(update(s.projects).where(s.projects.c.id == 'default').values(state=p))
        conn.execute(insert(s.projects).values(id='other', state=foreign))
        for record in [before, p, foreign]:
            conn.execute(insert(s.snapshots).values(project_id=record['id'], hash=record['snapshot_hash'], state=record))
    return s, TestClient(app, headers={'Authorization': 'Bearer owner'}), before, p, foreign


def test_analysis_lists_actionable_issues_with_real_source_ids_and_coverage(workbench):
    _, c, _, p, _ = workbench
    response = c.get('/api/projects/default/analysis')
    assert response.status_code == 200, response.text
    analysis = response.json()
    assert analysis['snapshot_hash'] == p['snapshot_hash']
    assert analysis['summary']['pending_requirement_count'] == 1
    assert analysis['summary']['pending_offer_count'] == 1
    assert analysis['summary']['correction_count'] == 1
    assert analysis['summary']['approval_count'] == 0
    issues = {i['type']: i for i in analysis['issues']}
    assert {'pending_requirement', 'pending_offer', 'extraction_gap', 'missing_evidence', 'price_correction'} <= set(issues)
    assert issues['pending_requirement']['source_ids'] == ['qa-spec:1']
    assert issues['pending_requirement']['next_action']['record_id'] == 'qa-r1'
    assert issues['price_correction']['source_ids'] == ['qa-spec:3']
    assert issues['price_correction']['severity'] == 'info'
    assert all(g['status'] == 'blocked' for g in analysis['release_gates'])
    docs = {d['document_id']: d for d in analysis['documents']}
    assert docs['qa-spec']['span_count'] == 4
    assert docs['qa-spec']['cited_span_count'] == 3
    assert docs['qa-spec']['citation_coverage'] == .75
    assert docs['qa-annex']['citation_coverage'] == 0
    assert 'completeness' not in docs['qa-spec']
    assert 'qa-SECRET' not in response.text and 'qa-secret-body' not in response.text


def test_lineage_is_deterministic_and_has_no_dangling_edges(workbench):
    _, c, _, _, _ = workbench
    first = c.get('/api/projects/default/analysis').json()
    assert 'lineage' in first
    graph = first['lineage']
    assert graph == c.get('/api/projects/default/analysis').json()['lineage']
    ids = {n['id'] for n in graph['nodes']}
    assert {'document:qa-spec', 'requirement:qa-r1', 'proposal:qa-p1', 'correction:qa-c1', 'run:qa-run1'} <= ids
    assert all(e['source'] in ids and e['target'] in ids for e in graph['edges'])
    assert any(e == {'source': 'document:qa-spec', 'target': 'requirement:qa-r1', 'relation': 'cites'} for e in graph['edges'])


def test_search_ranks_real_spans_and_returns_bounded_same_page_context(workbench):
    _, c, _, p, _ = workbench
    response = c.get('/api/projects/default/search', params={'q': '24 weeks drawing approval', 'limit': 2})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['snapshot_hash'] == p['snapshot_hash']
    assert result['retrieval_method'] == 'BM25 lexical retrieval'
    assert 'confidence' in result['score_meaning']
    assert result['results'][0]['source_id'] == 'qa-spec:2'
    hit = result['results'][0]
    assert hit['text'] == 'Delivery is 24 weeks after drawing approval.'
    assert hit['document_id'] == 'qa-spec' and hit['page'] == 1
    assert hit['sha256'] == 'a' * 64
    assert hit['score'] > result['results'][1]['score']
    assert [span['source_id'] for span in hit['context']] == ['qa-spec:1']
    assert all(span['page'] == hit['page'] for span in hit['context'])
    assert 'answer' not in result


def test_search_groups_duplicate_sources_and_normalizes_numeric_punctuation(workbench):
    _, c, _, _, _ = workbench
    response = c.get('/api/projects/default/search', params={'q': '750 kVA'})
    assert response.status_code == 200
    found = response.json()
    assert found['total_matches'] == 1
    assert len(found['results']) == 1
    hit = found['results'][0]
    assert hit['duplicate_count'] == 1
    assert {hit['source_id'], *[d['source_id'] for d in hit['duplicate_citations']]} == {'qa-spec:1', 'qa-annex:1'}
    for query in ['37,105.50', '37105.50', '37105.5']:
        response = c.get('/api/projects/default/search', params={'q': query})
        assert response.status_code == 200
        assert [r['source_id'] for r in response.json()['results']] == ['qa-spec:3']
    filtered = c.get('/api/projects/default/search', params={'q': '750 kVA', 'document_id': 'qa-spec'}).json()
    assert filtered['results'][0]['source_id'] == 'qa-spec:1'
    assert filtered['results'][0]['duplicate_count'] == 0
    assert c.get('/api/projects/default/search', params={'q': 'doesnotexist'}).json()['results'] == []


@pytest.mark.parametrize('params', [{'q': ''}, {'q': ' '}, {'q': 'x' * 301}, {'q': 'a', 'limit': 0}, {'q': 'a', 'limit': 51}])
def test_search_rejects_unbounded_or_empty_requests(workbench, params):
    _, c, _, _, _ = workbench
    assert c.get('/api/projects/default/search', params=params).status_code == 422


def test_unknown_document_does_not_silently_search_every_document(workbench):
    _, c, _, _, _ = workbench
    assert c.get('/api/projects/default/search', params={'q': '750', 'document_id': 'unknown'}).status_code == 404


def test_snapshot_diff_reports_exact_price_change_and_related_source(workbench):
    _, c, before, after, _ = workbench
    response = c.get('/api/projects/default/snapshots')
    assert response.status_code == 200
    history = response.json()
    assert history['current_snapshot_hash'] == after['snapshot_hash']
    assert history['snapshots'][0]['snapshot_hash'] == after['snapshot_hash']
    assert history['snapshots'][0]['summary']['pending_offer_count'] == 1
    response = c.get('/api/projects/default/diff', params={'from_hash': before['snapshot_hash'], 'to_hash': after['snapshot_hash']})
    assert response.status_code == 200, response.text
    diff = response.json()
    assert diff['changed'] and diff['summary'] == {'added': 0, 'removed': 0, 'modified': 1}
    change = diff['changes'][0]
    assert change['collection'] == 'proposals' and change['record_id'] == 'qa-p1'
    assert {'path': '/data/price_cents', 'before': 3710550, 'after': 3710500} in change['fields']
    assert change['source_ids'] == ['qa-spec:2', 'qa-spec:3']
    assert change['document_ids'] == ['qa-spec']
    assert diff['impacted_records'] == [{'type': 'proposal', 'id': 'qa-p1', 'source_ids': ['qa-spec:2', 'qa-spec:3']}]
    assert 'qa-SECRET' not in response.text and 'qa-secret-body' not in response.text
    same = c.get('/api/projects/default/diff', params={'from_hash': after['snapshot_hash'], 'to_hash': after['snapshot_hash']}).json()
    assert same['changes'] == [] and same['changed'] is False


@pytest.mark.parametrize('endpoint', ['analysis', 'search?q=750', 'snapshots', 'dossier'])
def test_new_views_require_identity_and_project_membership(workbench, endpoint):
    _, c, _, _, _ = workbench
    url = '/api/projects/default/' + endpoint
    assert c.get(url, headers={'Authorization': ''}).status_code == 401
    assert c.get(url, headers={'Authorization': 'Bearer outside'}).status_code == 403
    assert c.get(url.replace('/default/', '/missing/'), headers={'Authorization': 'Bearer both'}).status_code == 403


def test_diff_never_reads_another_projects_snapshot_even_for_multi_project_user(workbench):
    _, c, before, _, foreign = workbench
    params = {'from_hash': before['snapshot_hash'], 'to_hash': foreign['snapshot_hash']}
    endpoint = '/api/projects/default/diff'
    assert c.get(endpoint, params=params, headers={'Authorization': ''}).status_code == 401
    assert c.get(endpoint, params=params, headers={'Authorization': 'Bearer outside'}).status_code == 403
    assert c.get(endpoint, params=params, headers={'Authorization': 'Bearer both'}).status_code == 404
    assert c.get(endpoint, params={**params, 'to_hash': 'c' * 64}).status_code == 404
    assert c.get(endpoint, params={**params, 'to_hash': 'bad'}).status_code == 422


def test_dossier_is_reproducible_pending_review_packet_with_original_sources_and_corrections(workbench):
    _, c, _, p, _ = workbench
    response = c.get('/api/projects/default/dossier')
    assert response.status_code == 200, response.text
    packet = response.json()
    assert packet['packet_type'] == 'draft_review_dossier' and packet['status'] == 'draft'
    assert packet['snapshot_hash'] == p['snapshot_hash']
    assert packet['requirements'][0]['status'] == 'pending'
    assert packet['proposals'][0]['status'] == 'pending'
    assert packet['suppliers'] == [] and packet['decisions'] == []
    assert packet['corrections'][0]['source_id'] == 'qa-spec:3'
    assert packet['source_catalog'][0]['spans'] == p['documents'][0]['spans']
    assert packet['source_catalog'][0]['sha256'] == 'a' * 64
    assert packet['proposals'][0]['original_data']['price_cents'] == 3710550
    assert packet['proposals'][0]['data']['price_cents'] == 3710500
    assert packet == c.get('/api/projects/default/dossier').json()
    assert packet['packet_hash'] == digest({k: v for k, v in packet.items() if k != 'packet_hash'})
    assert 'qa-SECRET' not in response.text and 'qa-secret-body' not in response.text


def test_all_read_views_leave_every_database_row_unchanged(workbench):
    s, c, before, after, _ = workbench
    def database_rows():
        with s.engine.connect() as conn:
            return {t.name: conn.execute(select(t)).all() for t in [s.projects, s.snapshots, s.operations, s.artifacts]}
    initial = database_rows()
    for endpoint in ['analysis', 'search?q=750', 'snapshots', 'dossier',
                     'diff?from_hash=' + before['snapshot_hash'] + '&to_hash=' + after['snapshot_hash']]:
        response = c.get('/api/projects/default/' + endpoint)
        assert response.status_code == 200, response.text
    assert database_rows() == initial


def test_long_search_excerpt_contains_all_nearby_query_terms_and_exact_offsets(workbench):
    from tenderproof.evidence_workbench import search
    _, _, _, p, _ = workbench
    p = deepcopy(p)
    text = ('background ' * 1500) + 'Unique rating 750 kVA and price 37,105.5000.' + (' appendix' * 1500)
    p['documents'][0]['spans'][1]['text'] = text
    hit = search(p, '37,105.50', document_id='qa-spec')['results'][1]
    assert hit['source_id'] == 'qa-spec:1'
    assert len(hit['text']) <= 1400 and hit['text_truncated'] is True
    assert '37,105.5000' in hit['text']
    assert hit['text'] == text[hit['text_start']:hit['text_end']]
    assert all(len(context['text']) <= 700 for context in hit['context'])


def test_numeric_search_does_not_round_distinct_large_numbers_into_false_matches(workbench):
    from tenderproof.evidence_workbench import search
    _, _, _, p, _ = workbench
    p = deepcopy(p)
    p['documents'][0]['spans'][0]['text'] = 'Reference 1234567890123456789012345678901.'
    p['documents'][0]['spans'][1]['text'] = 'Reference 1234567890123456789012345678902.'
    result = search(p, '1234567890123456789012345678901')
    assert [r['source_id'] for r in result['results']] == ['qa-spec:0']


def test_diff_detects_trace_change_without_exposing_provider_payload(workbench):
    from tenderproof.evidence_workbench import diff
    _, _, _, p, _ = workbench
    after = deepcopy(p)
    after['proposals'][0]['trace']['raw_output'] = 'different-private-provider-text'
    result = diff(p, after, p['snapshot_hash'])
    assert result['changed'] is True
    fields = result['changes'][0]['fields']
    assert fields == [{'path': '/trace/sha256', 'before': digest(p['proposals'][0]['trace']),
                       'after': digest(after['proposals'][0]['trace'])}]
    assert 'different-private-provider-text' not in json.dumps(result)


def test_diff_does_not_confuse_boolean_and_numeric_values(workbench):
    from tenderproof.evidence_workbench import diff
    _, _, _, p, _ = workbench
    before = deepcopy(p)
    before['requirements'][0]['witness_expected'] = False
    after = deepcopy(before)
    after['requirements'][0]['witness_expected'] = 0
    result = diff(before, after, p['snapshot_hash'])
    assert result['changed'] is True
    assert result['changes'][0]['fields'] == [{'path': '/witness_expected', 'before': False, 'after': 0}]


def test_source_change_identifies_dependent_claims_and_exact_changed_text(workbench):
    from tenderproof.evidence_workbench import diff
    _, _, _, p, _ = workbench
    after = deepcopy(p)
    after['documents'][0]['spans'][1]['text'] = 'Changed isolated QA source'
    result = diff(p, after, p['snapshot_hash'])
    assert result['changes'][0]['collection'] == 'documents'
    assert result['changes'][0]['fields'][0]['after'][1]['text'] == 'Changed isolated QA source'
    assert {'type': 'requirement', 'id': 'qa-r1', 'source_ids': ['qa-spec:1']} in result['impacted_records']


def test_graph_limits_keep_edges_valid_and_large_dossier_fails_explicitly(workbench):
    from tenderproof.evidence_workbench import analyze, dossier, ViewProblem
    _, _, _, p, _ = workbench
    expanded = deepcopy(p)
    expanded['requirements'] = [{**p['requirements'][0], 'id': 'qa-r' + str(i)} for i in range(510)]
    graph = analyze(expanded)['lineage']
    assert graph['truncated'] is True and len(graph['nodes']) == 500
    ids = {n['id'] for n in graph['nodes']}
    assert all(e['source'] in ids and e['target'] in ids for e in graph['edges'])
    expanded['documents'][0]['spans'][0]['text'] = 'x' * (8 * 1024 * 1024)
    with pytest.raises(ViewProblem) as problem:
        dossier(expanded)
    assert problem.value.status == 413


def test_snapshot_history_is_bounded_newest_first_and_excludes_other_projects(workbench):
    s, c, _, p, foreign = workbench
    with s.engine.begin() as conn:
        for version in range(4, 106):
            previous = {**p, 'version': version, 'name': 'QA revision ' + str(version)}
            previous['snapshot_hash'] = snapshot(previous)
            conn.execute(insert(s.snapshots).values(project_id='default', hash=previous['snapshot_hash'], state=previous))
    history = c.get('/api/projects/default/snapshots').json()
    assert len(history['snapshots']) == 100 and history['truncated'] is True
    assert history['snapshots'][0]['version'] == 105
    assert history['total_count'] == 105
    assert foreign['snapshot_hash'] not in {r['snapshot_hash'] for r in history['snapshots']}
    assert p['snapshot_hash'] in {r['snapshot_hash'] for r in history['snapshots']}


def test_diff_exposes_stale_decision_and_approval_changes_with_supplier_citations(workbench):
    from tenderproof.evidence_workbench import diff
    _, _, _, p, _ = workbench
    before = deepcopy(p)
    before['suppliers'] = [{'id': 'qa-supplier', 'name': 'QA supplier', 'source_ids': ['qa-spec:3']}]
    before['decisions'] = [{'id': 'qa-decision', 'supplier_id': 'qa-supplier', 'gate': 'purchase',
        'status': 'pending', 'snapshot_hash': before['snapshot_hash'], 'approvals': []}]
    after = deepcopy(before)
    after['decisions'][0].update(status='stale', approvals=[{'actor': 'qa-owner', 'role': 'engineer'}])
    result = diff(before, after, p['snapshot_hash'])
    assert result['changed'] is True
    change = result['changes'][0]
    assert change['collection'] == 'decisions' and change['record_id'] == 'qa-decision'
    assert {'path': '/status', 'before': 'pending', 'after': 'stale'} in change['fields']
    assert {'path': '/approvals', 'before': [], 'after': [{'actor': 'qa-owner', 'role': 'engineer'}]} in change['fields']
    assert change['source_ids'] == ['qa-spec:3']
    assert change['document_ids'] == ['qa-spec']


@pytest.mark.parametrize('endpoint', ['analysis', 'search?q=750', 'snapshots', 'dossier'])
def test_current_views_reject_content_corruption_instead_of_exporting_old_identity(workbench, endpoint):
    s, c, _, p, _ = workbench
    c = TestClient(c.app, headers={'Authorization': 'Bearer owner'}, raise_server_exceptions=False)
    corrupt = deepcopy(p)
    corrupt['requirements'] = None  # Corrupt storage; the old snapshot hash is unchanged.
    with s.engine.begin() as conn:
        conn.execute(update(s.projects).where(s.projects.c.id == 'default').values(state=corrupt))
    response = c.get('/api/projects/default/' + endpoint)
    assert response.status_code == 409
    assert 'snapshot' in response.json()['detail'].lower()
    with s.engine.connect() as conn:
        assert conn.execute(select(s.projects.c.state).where(s.projects.c.id == 'default')).scalar_one() == corrupt


@pytest.mark.parametrize('corruption', ['content', 'identity'])
def test_diff_rejects_corrupted_stored_snapshot_content_and_identity(workbench, corruption):
    s, c, before, after, _ = workbench
    corrupt = deepcopy(before)
    if corruption == 'content':
        corrupt['name'] = 'Corrupted content under an earlier hash'
    else:
        corrupt['snapshot_hash'] = 'd' * 64
    with s.engine.begin() as conn:
        conn.execute(update(s.snapshots).where(s.snapshots.c.project_id == 'default',
            s.snapshots.c.hash == before['snapshot_hash']).values(state=corrupt))
    response = c.get('/api/projects/default/diff', params={'from_hash': before['snapshot_hash'], 'to_hash': after['snapshot_hash']})
    assert response.status_code == 409
    assert 'snapshot' in response.json()['detail'].lower()


def test_snapshot_verification_preserves_legacy_hash_basis_without_rewriting_history(workbench):
    from tenderproof.service import CONTENT_KEYS
    s, c, before, after, _ = workbench
    legacy = deepcopy(before)
    del legacy['extraction_runs']
    legacy['snapshot_hash'] = digest({key: legacy.get(key) for key in CONTENT_KEYS if key != 'extraction_runs'})
    with s.engine.begin() as conn:
        conn.execute(insert(s.snapshots).values(project_id='default', hash=legacy['snapshot_hash'], state=legacy))
    response = c.get('/api/projects/default/diff', params={'from_hash': legacy['snapshot_hash'], 'to_hash': after['snapshot_hash']})
    assert response.status_code == 200
    assert response.json()['from_hash'] == legacy['snapshot_hash']
    assert any(change['collection'] == 'extraction_runs' and change['change'] == 'added' for change in response.json()['changes'])
    with s.engine.connect() as conn:
        assert conn.execute(select(s.snapshots.c.state).where(s.snapshots.c.project_id == 'default',
            s.snapshots.c.hash == legacy['snapshot_hash'])).scalar_one() == legacy
