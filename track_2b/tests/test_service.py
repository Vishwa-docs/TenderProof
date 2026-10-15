import pytest
from tenderproof.service import Service, Conflict, Forbidden
from support.fixtures import qa_service, add_corrected_evidence


@pytest.fixture
def svc(tmp_path):
    return qa_service('sqlite:///'+str(tmp_path/'test.db'))


def approved(svc):
    for r in svc.get('default')['requirements']:
        p=svc.get('default')
        svc.review('default',r['id'],p['snapshot_hash'],True,r.get('witness_expected'),'eng','engineer')
    return svc.get('default')


def test_unreviewed_or_noncompliant_purchase_is_blocked(svc):
    p=svc.get('default')
    with pytest.raises(Conflict): svc.create_decision('default','helvetic','purchase',p['snapshot_hash'],'eng')
    p=approved(svc)
    with pytest.raises(Conflict): svc.create_decision('default','atlas','purchase',p['snapshot_hash'],'eng')


def test_release_needs_two_roles_and_is_idempotent(svc):
    p=approved(svc); h=p['snapshot_hash']
    d=svc.create_decision('default','helvetic','purchase',h,'eng')
    svc.approve('default',d['id'],h,'eng','engineer')
    with pytest.raises(Conflict): svc.release('default',d['id'],h,'key','buyer','commercial')
    svc.approve('default',d['id'],h,'buyer','commercial')
    a=svc.release('default',d['id'],h,'key','buyer','commercial')
    assert a == svc.release('default',d['id'],h,'key','buyer','commercial')
    assert a['snapshot_hash']==h
    assert a['simulator'] is True
    assert 'reviewed encoded numeric requirements' in a['meaning']
    assert 'unencoded obligations require engineering review' in a['meaning']
    assert len([e for e in svc.get('default')['events'] if e['type']=='released'])==1


def test_schedule_change_invalidates_approval_and_stale_write(svc):
    p=approved(svc); h=p['snapshot_hash']
    d=svc.create_decision('default','helvetic','purchase',h,'eng')
    svc.approve('default',d['id'],h,'eng','engineer')
    svc.set_schedule('default',h,25,'owner:5','eng','engineer')
    after=svc.get('default')
    assert after['snapshot_hash']!=h
    assert after['decisions'][0]['status']=='stale'
    with pytest.raises(Conflict): svc.approve('default',d['id'],h,'buyer','commercial')


def test_wrong_revision_blocks_shipment_until_new_evidence(svc):
    p=approved(svc)
    with pytest.raises(Conflict): svc.create_decision('default','helvetic','shipment',p['snapshot_hash'],'inspector')
    add_corrected_evidence(svc)
    p=svc.get('default')
    d=svc.create_decision('default','helvetic','shipment',p['snapshot_hash'],'inspector')
    assert d['status']=='pending'


def test_wrong_role_and_wrong_witness_cannot_approve(svc):
    p=svc.get('default')
    with pytest.raises(Forbidden): svc.review('default','req-rating',p['snapshot_hash'],True,False,'buyer','commercial')
    with pytest.raises(Conflict): svc.review('default','req-rating',p['snapshot_hash'],True,True,'eng','engineer')


def test_restart_preserves_snapshot_and_approvals(svc):
    p=approved(svc)
    again=Service(svc.database_url,mode='live')
    assert again.get('default')['snapshot_hash']==p['snapshot_hash']
    assert all(r['status']=='approved' for r in again.get('default')['requirements'])


def test_unknown_project_never_resolves_another_package(svc):
    with pytest.raises(KeyError): svc.get('other')
