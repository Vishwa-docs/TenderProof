from copy import deepcopy
import pytest
from tenderproof.domain import assess_requirement, assess_evidence, compare_options, witness_for
from support.fixtures import qa_package


def test_cooling_conditions_prevent_false_acceptance():
    p = qa_package()
    r = p['requirements'][0]
    r['status'] = 'approved'
    bad = assess_requirement(r, p['suppliers'][0])
    good = assess_requirement(r, p['suppliers'][1])
    assert bad['status'] == 'contradicted'
    assert bad['counterexample']
    assert good['status'] == 'supported'


def test_unreviewed_meaning_and_missing_conditions_are_unknown():
    p = qa_package()
    r = p['requirements'][0]
    assert assess_requirement(r, p['suppliers'][1])['status'] == 'unknown'
    r['status'] = 'approved'
    s = p['suppliers'][1]
    s['facts'] = [x for x in s['facts'] if x['conditions'].get('cooling') != 'ONAN']
    assert assess_requirement(r, s)['status'] == 'unknown'


def test_conflicting_supplier_facts_do_not_vacuously_pass():
    p = qa_package(); r = p['requirements'][0]; r['status'] = 'approved'
    s = p['suppliers'][1]
    other = deepcopy(s['facts'][0]); other['value'] = '21'; s['facts'].append(other)
    assert assess_requirement(r, s)['status'] == 'conflicting'


def test_unit_conversion_preserves_dimension():
    p = qa_package(); r = p['requirements'][0]; r['status'] = 'approved'
    s = p['suppliers'][1]; s['facts'][0].update(value='25000', unit='kVA')
    assert assess_requirement(r, s)['status'] == 'supported'
    s['facts'][0]['unit'] = 'kW'
    assert assess_requirement(r, s)['status'] == 'unknown'


def test_wrong_revision_and_routine_serial_are_rejected():
    p = qa_package(); s = p['suppliers'][1]; e = p['evidence'][1]
    assert assess_evidence(e, s, p['requirements'])['status'] == 'contradicted'
    e['revision'] = s['revision']; e['serial'] = 'wrong'
    assert assess_evidence(e, s, p['requirements'])['status'] == 'contradicted'


def test_type_evidence_requires_explicit_family_and_revision_coverage():
    p = qa_package(); s = p['suppliers'][1]; e = p['evidence'][1]
    for r in p['requirements']: r['status'] = 'approved'
    e.update(kind='type', revision=s['revision'], serial='different', family=s['family'])
    e['approved_family_coverage'] = True
    assert assess_evidence(e, s, p['requirements'])['status'] == 'supported'
    e['approved_family_coverage'] = False
    assert assess_evidence(e, s, p['requirements'])['status'] == 'unknown'


@pytest.mark.parametrize('review_status', ['pending', 'rejected'])
def test_evidence_cannot_support_an_unapproved_acceptance_criterion(review_status):
    p = qa_package(); s = p['suppliers'][1]; e = p['evidence'][1]
    e['revision'] = s['revision']
    for r in p['requirements']: r['status'] = 'approved'
    p['requirements'][0]['status'] = review_status

    result = assess_evidence(e, s, p['requirements'])

    assert result['status'] == 'unknown'
    assert p['requirements'][0]['status'] == review_status


def test_costs_and_schedule_use_literal_baseline_not_llm():
    p = qa_package()
    for r in p['requirements']: r['status'] = 'approved'
    rows = compare_options(p)
    good = next(x for x in rows if x['supplier_id'] == 'helvetic')
    assert good['total_cents'] == 136000000
    assert good['delay_weeks'] == 0
    assert good['status'] == 'feasible'
    assert next(x for x in rows if x['supplier_id'] == 'atlas')['status'] == 'rejected'


def test_witness_exposes_operating_condition_difference():
    p = qa_package()
    w = witness_for(p['requirements'][0])
    assert w['expected'] is False
    assert w['configuration']['ONAN'] == '20'


@pytest.mark.parametrize('missing',['price_cents','currency','delivery_weeks'])
def test_unknown_commercial_values_never_make_an_offer_feasible(missing):
    p=qa_package()
    for requirement in p['requirements']:requirement['status']='approved'
    p['suppliers'][1][missing]=None
    p['suppliers']=[p['suppliers'][1]]
    result=next(row for row in compare_options(p) if row['supplier_id']=='helvetic')
    assert result['status']=='conditional'
    if missing=='price_cents':assert result['total_cents'] is None
    if missing=='delivery_weeks':assert result['delay_weeks'] is None


@pytest.mark.parametrize('missing',['revision','serial'])
def test_unknown_selected_identity_cannot_establish_routine_applicability(missing):
    p=qa_package();supplier=p['suppliers'][1];evidence=p['evidence'][1]
    for requirement in p['requirements']:requirement['status']='approved'
    evidence['revision']='B';supplier[missing]=None
    assert assess_evidence(evidence,supplier,p['requirements'])['status']=='unknown'


def test_report_conditions_cannot_be_hidden_by_measurement_overrides():
    from tenderproof.service import Service, Conflict
    p=qa_package();s=p['suppliers'][1];e=p['evidence'][1]
    for r in p['requirements']:r['status']='approved'
    e['revision']=s['revision'];e['conditions']={'temperature_c':'85'}
    before=deepcopy(e)
    assert assess_evidence(e,s,p['requirements'])['status']=='conflicting'
    assert e==before
    with pytest.raises(Conflict):Service._gate(None,p,s['id'],'shipment')


@pytest.mark.parametrize('report,measurement,expected',[
    ({'temperature_c':'75'},{},'supported'),
    ({},{'temperature_c':'75'},'supported'),
    ({'temperature_c':'75'},{'temperature_c':'75'},'supported'),
    ({'temperature_c':'85'},{'temperature_c':'75'},'conflicting'),
    ({'temperature_c':'85'},{},'unknown'),
    ({},{},'unknown'),
    ({'temperature_c':'75','cooling':'ONAN'},{},'unknown'),
])
def test_report_conditions_apply_without_inventing_or_erasing_scope(report,measurement,expected):
    p=qa_package();s=p['suppliers'][1];e=p['evidence'][1]
    criterion=p['requirements'][2];criterion['status']='approved'
    e.update(revision=s['revision'],conditions=report)
    e['measurements']=[e['measurements'][-1]]
    e['measurements'][0]['conditions']=measurement
    assert assess_evidence(e,s,[criterion])['status']==expected
