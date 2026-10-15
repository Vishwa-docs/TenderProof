"""Docling boundary QA: controlled conversion results, never model evaluation."""
from types import SimpleNamespace
import pytest

base=pytest.importorskip('docling.datamodel.base_models')
from tenderproof.integrations import parse_document


def conversion(monkeypatch,status,errors=(),page_numbers=(1,2)):
    import docling.document_converter as converter
    from tenderproof import integrations
    bbox=SimpleNamespace(model_dump=lambda **kwargs:{'l':0,'t':10,'r':20,'b':0})
    item=SimpleNamespace(text='QA scanned page content',prov=[SimpleNamespace(page_no=1,bbox=bbox)])
    document=SimpleNamespace(iterate_items=lambda:iter([(item,0)]),pages={n:object() for n in page_numbers})
    result=SimpleNamespace(status=status,errors=list(errors),document=document,
        pages=[SimpleNamespace(page_no=n) for n in page_numbers],input=SimpleNamespace(page_count=2))
    monkeypatch.setattr(converter,'DocumentConverter',lambda **kwargs:SimpleNamespace(convert=lambda *a,**kw:result))
    def supplement(doc,content):
        doc.setdefault('parsing',{}).update(page_count=2,pages_with_embedded_text=0,supplemental_page_spans=0)
    monkeypatch.setattr(integrations,'_supplement_pdf_text',supplement)


@pytest.mark.parametrize('status',[base.ConversionStatus.PARTIAL_SUCCESS,base.ConversionStatus.FAILURE,base.ConversionStatus.SKIPPED])
def test_incomplete_pdf_status_is_rejected_even_when_document_has_text(monkeypatch,status):
    error=SimpleNamespace(page_no=2,category='backend_failure',error_message='Page failed to parse.\n\x00'+('x'*2000))
    conversion(monkeypatch,status,[error])
    with pytest.raises(ValueError) as caught:parse_document('qa.pdf',b'qa conversion boundary')
    message=str(caught.value)
    assert status.value in message and '2' in message
    assert '\n' not in message and '\x00' not in message and len(message)<1200


def test_success_status_cannot_hide_conversion_errors_or_missing_page(monkeypatch):
    conversion(monkeypatch,base.ConversionStatus.SUCCESS,[SimpleNamespace(page_no=2,category='backend_failure',error_message='Unreadable page')])
    with pytest.raises(ValueError):parse_document('qa.pdf',b'qa conversion boundary')
    conversion(monkeypatch,base.ConversionStatus.SUCCESS,page_numbers=(1,))
    with pytest.raises(ValueError):parse_document('qa.pdf',b'qa conversion boundary')


def test_successful_pdf_records_status_and_actual_text_page_coverage(monkeypatch):
    conversion(monkeypatch,base.ConversionStatus.SUCCESS)
    doc=parse_document('qa.pdf',b'qa conversion boundary')
    assert doc['parsing']['docling_status']=='success'
    assert doc['parsing']['docling_errors']==[]
    assert doc['parsing']['converted_pages']==[1,2]
    assert doc['parsing']['pages_with_source_spans']==[1]
    assert doc['parsing']['pages_without_source_spans']==[2]
    assert doc['parsing']['visual_review_required'] is True
