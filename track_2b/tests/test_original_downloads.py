"""Original-byte integrity QA; software-only inputs, never procurement data."""
from hashlib import sha256
import base64
import pytest
from fastapi.testclient import TestClient
from tenderproof.api import create_app


def empty_pdf():
    """Generate a complete empty PDF using no optional document dependencies."""
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << >> /Contents 4 0 R >>',
               b'<< /Length 0 >>\nstream\n\nendstream']
    content = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content.extend(f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(content)
    content.extend(b'xref\n0 5\n0000000000 65535 f \n')
    for offset in offsets[1:]:
        content.extend(f'{offset:010d} 00000 n \n'.encode())
    content.extend(f'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(content)


@pytest.fixture
def original_case(tmp_path, monkeypatch):
    runtime = tmp_path / 'runtime'
    monkeypatch.setenv('RUNTIME_DIR', str(runtime))
    app = create_app(database_url='sqlite:///' + str(tmp_path / 'originals.db'), principals={
        'member': {'actor': 'qa-reader', 'role': 'engineer', 'projects': ['default']},
        'outside': {'actor': 'qa-outside', 'role': 'engineer', 'projects': ['other']},
    })
    service = app.state.service
    content = empty_pdf()
    record = {'id': 'qa-original', 'name': 'software-input.pdf', 'sha256': sha256(content).hexdigest(),
              'spans': [{'id': 'qa-original:1', 'page': 1, 'text': 'Software OCR must never be delivered as the original PDF.'}]}
    service.add_document('default', record, service.get('default')['snapshot_hash'], 'qa-reader')
    path = runtime / 'objects' / record['sha256']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return TestClient(app), service, record, path, content


def download(client, record, token='member'):
    return client.get('/api/projects/default/documents/' + record['id'] + '/content',
                      headers={'Authorization': 'Bearer ' + token} if token else {})


def test_missing_original_is_not_ocr_downloaded_under_pdf_filename(original_case):
    client, service, record, path, _ = original_case
    path.unlink()
    before = service.get('default')
    response = download(client, record)
    assert response.status_code == 404
    assert 'original' in response.json()['detail'].lower()
    assert 'content-disposition' not in response.headers
    assert b'Software OCR' not in response.content
    assert service.get('default') == before


def test_original_download_preserves_valid_bytes_and_source_identity(original_case):
    client, service, record, path, content = original_case
    before = service.get('default')
    response = download(client, record)
    assert response.status_code == 200 and response.content == content
    assert response.headers['content-type'] == 'application/octet-stream'
    assert 'software-input.pdf' in response.headers['content-disposition']
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['x-source-sha256'] == record['sha256']
    assert response.headers['cache-control'] == 'private, no-store'
    assert path.read_bytes() == content and service.get('default') == before


def test_corrupted_original_returns_hash_error_without_a_file_substitute(original_case):
    client, service, record, path, _ = original_case
    path.write_bytes(b'Software corrupted object.')
    before = service.get('default')
    response = download(client, record)
    assert response.status_code == 409
    assert 'hash' in response.json()['detail'].lower()
    assert 'content-disposition' not in response.headers
    assert service.get('default') == before and path.read_bytes() == b'Software corrupted object.'


@pytest.mark.parametrize('invalid_hash', ['../private', 'short', None])
def test_only_validated_content_hashes_can_select_original_object_paths(original_case, invalid_hash):
    client, service, _, path, _ = original_case
    record = {'id': 'qa-invalid-hash', 'name': 'software-input.pdf', 'sha256': invalid_hash,
              'spans': [{'id': 'qa-invalid-hash:1', 'page': 1, 'text': 'No original is available.'}]}
    service.add_document('default', record, service.get('default')['snapshot_hash'], 'qa-reader')
    private = path.parent.parent / 'private'
    private.write_bytes(b'Software path-isolation marker.')
    before = service.get('default')
    response = download(client, record)
    assert response.status_code == 404
    assert b'Software path-isolation marker' not in response.content
    assert service.get('default') == before


def test_oversized_original_is_not_loaded_or_downloaded(original_case):
    client, service, _, path, _ = original_case
    content = b'x' * (15 * 1024 * 1024 + 1)
    record = {'id': 'qa-oversized', 'name': 'software-input.pdf', 'sha256': sha256(content).hexdigest(), 'spans': []}
    service.add_document('default', record, service.get('default')['snapshot_hash'], 'qa-reader')
    (path.parent / record['sha256']).write_bytes(content)
    before = service.get('default')
    assert download(client, record).status_code == 413
    assert service.get('default') == before


@pytest.mark.parametrize('token,status', [(None, 401), ('invalid', 401), ('outside', 403)])
def test_original_download_still_requires_authenticated_project_access(original_case, token, status):
    client, service, record, _, _ = original_case
    before = service.get('default')
    assert download(client, record, token).status_code == status
    assert service.get('default') == before


@pytest.mark.parametrize('corrupt', [False, True, 'invalid-base64'])
def test_inline_image_original_is_retained_only_when_it_matches_source_hash(original_case, corrupt):
    client, service, _, _, _ = original_case
    encoded = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a0ioAAAAASUVORK5CYII='
    content = base64.b64decode(encoded)
    payload = 'invalid!base64' if corrupt == 'invalid-base64' else base64.b64encode(b'Corrupted software image.' if corrupt else content).decode()
    record = {'id': 'qa-inline-image', 'name': 'software-pixel.png', 'sha256': sha256(content).hexdigest(),
              'image_data_url': 'data:image/png;base64,' + payload, 'spans': []}
    service.add_document('default', record, service.get('default')['snapshot_hash'], 'qa-reader')
    before = service.get('default')
    response = download(client, record)
    if corrupt:
        assert response.status_code == 409
        assert response.headers['content-type'].startswith('application/json')
    else:
        assert response.status_code == 200 and response.content == content
        assert response.headers['content-type'] == 'image/png'
        assert response.headers['x-source-sha256'] == record['sha256']
    assert service.get('default') == before
