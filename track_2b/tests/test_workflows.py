import asyncio
import pytest
from tenderproof.workflows import persist_extraction
from tenderproof.service import Service, Conflict
from support.fixtures import qa_service


def test_durable_persist_retries_do_not_duplicate_requirements(tmp_path,monkeypatch):
    url='sqlite:///'+str(tmp_path/'worker.db');monkeypatch.setenv('DATABASE_URL',url);monkeypatch.setenv('APP_MODE','live')
    s=qa_service(url);p=s.get('default')
    request={'pid':'default','docid':'owner','body':{'snapshot_hash':p['snapshot_hash'],'kind':'requirements'},'actor':'eng',
             'workflow_id':'extract-1','result':{'data':[{'title':'New clause','property':'rated_power','operator':'ge','value':'26','unit':'MVA','conditions':{'cooling':'ONAN'},'phase':'purchase','source_ids':['owner:2']}],'trace':{'inference':'test'}}}
    first=asyncio.run(persist_extraction(request))
    second=asyncio.run(persist_extraction(request))
    assert first==second
    assert len(s.get('default')['requirements'])==4
