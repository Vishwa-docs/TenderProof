"""Read-only preview QA with software-generated blank PDFs, never business data."""
from copy import deepcopy
from io import BytesIO
import hashlib
import pytest
pdfium = pytest.importorskip('pypdfium2')
Image = pytest.importorskip('PIL.Image')
from fastapi.testclient import TestClient
from tenderproof.api import create_app


def software_pdf(sizes=((100, 200), (300, 100))):
    output = BytesIO()
    with pdfium.PdfDocument.new() as doc:
        for width, height in sizes:
            page = doc.new_page(width, height)
            page.close()
        doc.save(output)
    return output.getvalue()


@pytest.fixture
def preview_case(tmp_path, monkeypatch):
    runtime = tmp_path / 'runtime'
    monkeypatch.setenv('RUNTIME_DIR', str(runtime))
    app = create_app(database_url='sqlite:///' + str(tmp_path / 'preview.db'), principals={
        'member': {'actor': 'qa-reader', 'role': 'engineer', 'projects': ['default', 'other']},
        'outside': {'actor': 'qa-outside', 'role': 'engineer', 'projects': ['unrelated']},
        'commercial': {'actor': 'qa-commercial', 'role': 'commercial', 'projects': ['default']},
    })
    service = app.state.service
    content = software_pdf()
    source_hash = hashlib.sha256(content).hexdigest()
    record = {'id': 'qa-software-pdf', 'name': 'software-input.pdf', 'sha256': source_hash,
              'revision': 'unreviewed', 'authority': 'unreviewed_source', 'language': 'und',
              'spans': [{'id': 'qa-software-pdf:1', 'page': 1, 'text': 'Software QA locator only.'}]}
    service.add_document('default', record, service.get('default')['snapshot_hash'], 'qa-reader')
    other = deepcopy(service.get('default'))
    other.update(id='other', documents=[])
    with service.engine.begin() as conn:
        conn.execute(service.projects.insert().values(id='other', state=other))
    object_path = runtime / 'objects' / source_hash
    object_path.parent.mkdir(parents=True, exist_ok=True)
    object_path.write_bytes(content)
    return TestClient(app), service, record, object_path


def endpoint(record, page='2', project='default'):
    return f'/api/projects/{project}/documents/{record["id"]}/pages/{page}/preview'


def test_preview_renders_the_requested_original_page_and_never_changes_project(preview_case):
    client, service, record, original = preview_case
    before = service.get('default')
    original_bytes = original.read_bytes()
    response = client.get(endpoint(record) + '?max_dimension=600', headers={'Authorization': 'Bearer member'})
    assert response.status_code == 200, response.text
    assert response.headers['content-type'] == 'image/png'
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['x-source-sha256'] == record['sha256']
    assert response.headers['x-source-page'] == '2'
    with Image.open(BytesIO(response.content)) as image:
        assert image.format == 'PNG'
        assert 1 <= image.width <= 600 and 1 <= image.height <= 600
        assert 2.9 < image.width / image.height < 3.1  # Page 2, not page 1.
    assert original.read_bytes() == original_bytes
    assert service.get('default') == before


@pytest.mark.parametrize('token,status', [(None, 401), ('invalid', 401), ('outside', 403), ('commercial', 200)])
def test_preview_requires_authenticated_project_membership_but_is_read_only_for_members(preview_case, token, status):
    client, service, record, _ = preview_case
    before = service.get('default')
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    assert client.get(endpoint(record), headers=headers).status_code == status
    assert service.get('default') == before


def test_document_cannot_be_resolved_from_a_different_authorized_project(preview_case):
    client, service, record, _ = preview_case
    before = service.get('other')
    response = client.get(endpoint(record, project='other'), headers={'Authorization': 'Bearer member'})
    assert response.status_code == 404
    assert service.get('other') == before


@pytest.mark.parametrize('page', ['0', '-1', '1.5', 'not-a-page', '3', '10001'])
def test_preview_rejects_invalid_page_numbers_against_original_pdf(preview_case, page):
    client, service, record, _ = preview_case
    before = service.get('default')
    response = client.get(endpoint(record, page), headers={'Authorization': 'Bearer member'})
    assert response.status_code == 422
    assert service.get('default') == before


@pytest.mark.parametrize('dimension', ['0', '255', '2401', '-10', 'not-a-size'])
def test_preview_rejects_out_of_bound_dimensions(preview_case, dimension):
    client, service, record, _ = preview_case
    before = service.get('default')
    assert client.get(endpoint(record) + '?max_dimension=' + dimension,
                      headers={'Authorization': 'Bearer member'}).status_code == 422
    assert service.get('default') == before


def replace_record(service, content, name='software-input.pdf'):
    source_hash = hashlib.sha256(content).hexdigest()
    record = {'id': 'qa-additional-file', 'name': name, 'sha256': source_hash,
              'spans': [{'id': 'qa-additional-file:1', 'page': 1, 'text': 'Never a page-preview substitute.'}]}
    service.add_document('default', record, service.get('default')['snapshot_hash'], 'qa-reader')
    return record


def test_missing_original_returns_an_error_instead_of_reconstructed_source_text(preview_case):
    client, service, record, path = preview_case
    path.unlink()
    before = service.get('default')
    response = client.get(endpoint(record, '1'), headers={'Authorization': 'Bearer member'})
    assert response.status_code == 404
    assert 'original' in response.json()['detail'].lower()
    assert b'Software QA locator only' not in response.content
    assert service.get('default') == before


@pytest.mark.parametrize('content,name,status', [(b'plain software input', 'software-input.pdf', 415),
                                                (b'%PDF-1.7\ninvalid PDF structure', 'software-input.pdf', 422),
                                                (b'%PDF-1.7\n', 'software-input.txt', 415)])
def test_unsupported_or_unrenderable_original_has_no_preview_substitute(preview_case, content, name, status):
    client, service, _, path = preview_case
    record = replace_record(service, content, name)
    (path.parent / record['sha256']).write_bytes(content)
    before = service.get('default')
    response = client.get(endpoint(record, '1'), headers={'Authorization': 'Bearer member'})
    assert response.status_code == status
    assert 'detail' in response.json()
    assert service.get('default') == before


def test_stored_object_integrity_is_checked_before_rendering(preview_case):
    client, service, record, path = preview_case
    path.write_bytes(software_pdf(((400, 400),)))
    before = service.get('default')
    response = client.get(endpoint(record, '1'), headers={'Authorization': 'Bearer member'})
    assert response.status_code == 409
    assert 'hash' in response.json()['detail'].lower()
    assert service.get('default') == before


def test_large_square_page_is_bounded_by_dimensions_and_pixel_count(preview_case):
    client, service, _, path = preview_case
    content = software_pdf(((10000, 10000),))
    record = replace_record(service, content)
    (path.parent / record['sha256']).write_bytes(content)
    before = service.get('default')
    response = client.get(endpoint(record, '1') + '?max_dimension=2400', headers={'Authorization': 'Bearer member'})
    assert response.status_code == 200, response.text
    with Image.open(BytesIO(response.content)) as image:
        assert max(image.size) <= 2400 and image.width * image.height <= 4_000_000
    assert service.get('default') == before


def test_oversized_original_is_rejected_before_pdfium(preview_case):
    client, service, _, path = preview_case
    content = b'%PDF-1.7\n' + b' ' * (15 * 1024 * 1024)
    record = replace_record(service, content)
    (path.parent / record['sha256']).write_bytes(content)
    before = service.get('default')
    assert client.get(endpoint(record, '1'), headers={'Authorization': 'Bearer member'}).status_code == 413
    assert service.get('default') == before


def test_preview_cannot_enter_pdfium_while_api_pdf_parsing_is_active(preview_case, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import tenderproof.api as api

    client, service, record, original = preview_case
    started, finish = Event(), Event()
    before = service.get('default')
    native_calls = []
    actual_pdf_document = pdfium.PdfDocument

    def observed_pdf_document(*args, **kwargs):
        native_calls.append(True)
        return actual_pdf_document(*args, **kwargs)

    def controlled_parser(name, content):
        started.set()
        assert finish.wait(timeout=3), 'Software QA parser was not released.'
        return deepcopy(record)

    monkeypatch.setattr(pdfium, 'PdfDocument', observed_pdf_document)
    monkeypatch.setattr(api, 'parse_document', controlled_parser)
    with ThreadPoolExecutor(max_workers=1) as executor:
        upload = executor.submit(lambda: client.post('/api/projects/default/documents',
            headers={'Authorization': 'Bearer member'}, data={'snapshot_hash': before['snapshot_hash']},
            files={'file': ('software-input.pdf', original.read_bytes(), 'application/pdf')}))
        try:
            assert started.wait(timeout=2)
            response = client.get(endpoint(record), headers={'Authorization': 'Bearer member'})
            assert response.status_code == 503
            assert 'busy' in response.json()['detail'].lower()
            assert native_calls == []
            assert service.get('default') == before
        finally:
            finish.set()
        assert upload.result(timeout=2).status_code == 200
    assert service.get('default') == before


def test_failed_api_pdf_parse_releases_access_without_writing_a_document(preview_case, monkeypatch):
    import tenderproof.api as api
    client, service, record, original = preview_case
    before = service.get('default')
    original_bytes = original.read_bytes()

    def failed_parser(name, content):
        raise ValueError('Software QA conversion failure.')

    monkeypatch.setattr(api, 'parse_document', failed_parser)
    response = client.post('/api/projects/default/documents', headers={'Authorization': 'Bearer member'},
        data={'snapshot_hash': before['snapshot_hash']}, files={'file': ('software-input.pdf', original_bytes, 'application/pdf')})
    assert response.status_code == 422
    assert service.get('default') == before and original.read_bytes() == original_bytes
    assert client.get(endpoint(record), headers={'Authorization': 'Bearer member'}).status_code == 200
    assert service.get('default') == before
