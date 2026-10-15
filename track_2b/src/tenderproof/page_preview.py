"""Bounded rasterization of immutable original PDFs; no parsed-text substitute."""
from hashlib import sha256
from contextlib import contextmanager
from io import BytesIO
import math
from pathlib import Path
from threading import Lock

MAX_ORIGINAL_BYTES = 15 * 1024 * 1024
MAX_PREVIEW_PIXELS = 4_000_000
PDF_ACCESS_LOCK = Lock()  # Shared by API PDF ingestion and page preview operations.


class PreviewProblem(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        super().__init__(detail)


@contextmanager
def _preview_pdf_access():
    if not PDF_ACCESS_LOCK.acquire(blocking=False):
        raise PreviewProblem(503, 'PDF access is busy with ingestion or another page preview. Retry after it finishes.')
    try:
        yield
    finally:
        PDF_ACCESS_LOCK.release()


def verify_original_bytes(content: bytes, expected_hash: str) -> bytes:
    if len(content) > MAX_ORIGINAL_BYTES:
        raise PreviewProblem(413, 'The stored original exceeds the 15 MiB source limit.')
    if sha256(content).hexdigest() != expected_hash:
        raise PreviewProblem(409, 'The stored original does not match its source hash.')
    return content


def read_original_bytes(path: Path, expected_hash: str) -> bytes:
    try:
        if path.stat().st_size > MAX_ORIGINAL_BYTES:
            raise PreviewProblem(413, 'The stored original exceeds the 15 MiB source limit.')
        with path.open('rb') as original:
            content = original.read(MAX_ORIGINAL_BYTES + 1)
    except FileNotFoundError as exc:
        raise PreviewProblem(404, 'The original source file is unavailable. It cannot be reconstructed from extracted text.') from exc
    except OSError as exc:
        raise PreviewProblem(503, 'The stored original source file cannot be read.') from exc
    return verify_original_bytes(content, expected_hash)


def render_original_pdf_page(path: Path, expected_hash: str, page_number: int,
                             max_dimension: int = 1800) -> tuple[bytes, int, int]:
    content = read_original_bytes(path, expected_hash)
    if not content.startswith(b'%PDF-'):
        raise PreviewProblem(415, 'Only an original PDF can be rendered as a page preview.')
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise PreviewProblem(503, 'PDF preview requires the installed document-rendering dependencies.') from exc

    with _preview_pdf_access():
        try:
            with pdfium.PdfDocument(content) as document:
                if not 1 <= page_number <= len(document):
                    raise PreviewProblem(422, f'Page number must be between 1 and {len(document)} for this original PDF.')
                document.init_forms()
                page = document[page_number - 1]
                try:
                    width, height = page.get_size()
                    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                        raise PreviewProblem(422, 'The original PDF page has invalid dimensions.')
                    # Leave room for PDFium's upward integer rounding in both axes.
                    pixel_budget = MAX_PREVIEW_PIXELS - 2 * max_dimension - 1
                    scale = min((max_dimension - 1) / width, (max_dimension - 1) / height,
                                math.sqrt(pixel_budget / width / height))
                    bitmap = page.render(scale=scale, draw_annots=True)
                    try:
                        if max(bitmap.width, bitmap.height) > max_dimension or bitmap.width * bitmap.height > MAX_PREVIEW_PIXELS:
                            raise PreviewProblem(422, 'The original PDF page exceeded the preview raster limits.')
                        image = bitmap.to_pil()
                        try:
                            output = BytesIO()
                            image.save(output, format='PNG')
                            return output.getvalue(), bitmap.width, bitmap.height
                        finally:
                            image.close()
                    finally:
                        bitmap.close()
                finally:
                    page.close()
        except PreviewProblem:
            raise
        except Exception as exc:
            raise PreviewProblem(422, 'The stored original PDF page could not be rendered. Download the original to inspect it.') from exc
