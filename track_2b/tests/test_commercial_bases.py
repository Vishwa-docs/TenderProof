"""Delivery and price bases: isolated software QA with constructed inputs, not a model evaluation.

Real-run defect: the model put 24 into delivery_weeks for a source that says 24 weeks AFTER
approval of drawings. The schema had nowhere to say what the weeks are counted from, so the
number looked comparable with a project-week milestone.
"""
import pytest
from pydantic import ValidationError
from tenderproof.domain import compare_options
from tenderproof.models import Supplier
from support.fixtures import qa_package
from test_integrations import invoke_controlled_response, price_only_offer


def approved_helvetic():
    p = qa_package()
    for requirement in p['requirements']:
        requirement['status'] = 'approved'
    p['suppliers'] = [p['suppliers'][1]]
    return p, p['suppliers'][0]


def helvetic_row(p):
    return next(row for row in compare_options(p) if row['supplier_id'] == 'helvetic')


def test_project_start_delivery_still_compares_with_the_milestone():
    p, s = approved_helvetic()
    s['delivery_weeks'], s['delivery_basis'] = 30, 'project_start'
    row = helvetic_row(p)
    assert row['delay_weeks'] == 6 and row['delivery_basis'] == 'project_start'


@pytest.mark.parametrize('basis,wording', [
    ('after_drawing_approval', 'approval of drawings'),
    ('after_order', 'order'),
    ('other', 'another'),
    (None, 'not stated'),
])
def test_delivery_counted_from_another_event_is_never_compared_with_a_project_week(basis, wording):
    p, s = approved_helvetic()
    s['delivery_weeks'], s['delivery_basis'] = 30, basis
    row = helvetic_row(p)
    assert row['delay_weeks'] is None and row['delivery_weeks'] == 30 and row['delivery_basis'] == basis
    assert row['status'] == 'conditional'
    assert any(wording in issue and 'cannot be compared' in issue for issue in row['issues'])
    assert not any('misses the required milestone' in issue for issue in row['issues'])


def test_delivery_basis_is_bounded_and_defaults_to_unstated():
    assert Supplier.model_validate({'name': 'QA'}).delivery_basis is None
    with pytest.raises(ValidationError):
        Supplier.model_validate({'name': 'QA', 'delivery_basis': 'next tuesday'})


def priced(p, **fields):
    other = {**p['suppliers'][0], 'id': 'second', 'name': 'Second QA supplier'}
    p['suppliers'][0].update(fields.get('first', {}))
    other.update(fields.get('second', {}))
    p['suppliers'].append(other)
    return {row['supplier_id']: row for row in compare_options(p)}


@pytest.mark.parametrize('first,second', [('unit', 'lot_total'), ('lot_total', 'unit'), ('unit', None), (None, 'lot_total')])
def test_prices_with_different_or_partly_unstated_bases_are_not_compared_like_for_like(first, second):
    p, _ = approved_helvetic()
    rows = priced(p, first={'price_basis': first}, second={'price_basis': second})
    for row in rows.values():
        assert row['status'] == 'conditional'
        assert any('price basis' in issue.lower() and 'like-for-like' in issue for issue in row['issues'])


@pytest.mark.parametrize('basis', ['unit', 'lot_total'])
def test_prices_on_one_shared_basis_keep_their_ordering_and_expose_it(basis):
    p, _ = approved_helvetic()
    rows = priced(p, first={'price_basis': basis, 'price_cents': 100}, second={'price_basis': basis, 'price_cents': 200})
    assert all(row['price_basis'] == basis for row in rows.values())
    assert not any('price basis' in issue.lower() for row in rows.values() for issue in row['issues'])


def test_suppliers_without_a_price_do_not_trigger_a_basis_conflict():
    p, _ = approved_helvetic()
    rows = priced(p, first={'price_basis': 'unit'}, second={'price_basis': 'lot_total', 'price_cents': None})
    assert not any('price basis' in issue.lower() for issue in rows['helvetic']['issues'])


def test_supplier_prompt_asks_for_the_counting_event_and_price_basis_without_forcing_values():
    _, requests, _, _ = invoke_controlled_response('supplier', {'suppliers': [price_only_offer()]})
    prompt = requests[1]['messages'][0]['content']
    assert '"delivery_basis": "project_start" or "after_order" or "after_drawing_approval" or "other" or null' in prompt
    assert '"price_basis": "unit" or "lot_total" or null' in prompt
    assert 'approval of drawings' in prompt and 'never convert' in prompt.lower()


def test_delivery_weeks_with_an_offer_citation_and_basis_survive_extraction_unchanged():
    offer = price_only_offer(delivery_weeks=24, delivery_basis='after_drawing_approval', price_basis='unit')
    result, _, _, _ = invoke_controlled_response('supplier', {'suppliers': [offer]})
    row = result['data'][0]
    assert (row['delivery_weeks'], row['delivery_basis'], row['price_basis']) == (24, 'after_drawing_approval', 'unit')


@pytest.mark.parametrize('count',[1,2])
def test_all_unknown_price_bases_remain_conditional_even_when_shared(count):
    p,s=approved_helvetic();s['price_basis']=None
    if count==2:p['suppliers'].append({**s,'id':'second','price_cents':1})
    for row in compare_options(p):
        assert row['status']=='conditional'
        assert any('price basis' in issue.lower() and 'not stated' in issue for issue in row['issues'])
