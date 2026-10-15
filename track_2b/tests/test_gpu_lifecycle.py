"""Lifecycle software QA: Docker/HTTP boundaries are mocked; no GPU or model runs."""
import importlib.util
import json
import os
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import pytest

SCRIPT=Path(__file__).resolve().parents[2]/'scripts/apertus_lifecycle.py'
spec=importlib.util.spec_from_file_location('apertus_lifecycle',SCRIPT)
lifecycle=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)


class DockerBoundary:
    def __init__(self):
        self.calls=[];self.fail_run=False;self.fail_restore=False;self.image_available=True
        self.containers={name:{'id':'id-'+name,'name':name,'running':True,'owner':None}
                         for name in ('llama-qwen35','visionx-triton-face-local','unrelated-workload')}
        self.networks={};self.ips=['172.30.5.2']
        self.log_content=b'QA stdout diagnostic\nQA stderr diagnostic\n';self.log_failure=False;self.log_timeout=False;self.log_read_failure=False
        self.log_processes=[];self.log_reads=[];self.log_waits=[]
    def run(self,argv,**kwargs):
        self.calls.append(argv)
        assert kwargs.get('shell',False) is False
        args=argv[1:];result='';code=0
        if args[:2]==['image','inspect']:result=json.dumps([lifecycle.IMAGE] if self.image_available else [])
        elif args[0]=='ps':result='\n'.join(k for k,v in self.containers.items() if v['running'])
        elif args[:2]==['container','inspect'] and any('IPAddress' in a for a in args):
            result=json.dumps(self.ips.pop(0) if len(self.ips)>1 else self.ips[0])
        elif args[:2]==['container','inspect']:
            item=next((v for v in self.containers.values() if args[-1] in (v['id'],v['name'])),None)
            if item:result=json.dumps(item)
            else:code=1
        elif args[:2]==['container','ls']:
            result='\n'.join(json.dumps({'id':v['id'],'name':v['name']}) for v in self.containers.values())
        elif args[:2]==['network','create']:
            name=args[-1];owner=args[args.index('--label')+1].split('=',1)[1]
            self.networks[name]={'id':'net-'+name,'owner':owner,'internal':True};result='net-'+name
        elif args[:2]==['network','inspect']:
            item=self.networks.get(args[-1])
            if item:result=json.dumps(item)
            else:code=1
        elif args[:2]==['network','ls']:
            result='\n'.join(json.dumps({'id':v['id'],'name':name}) for name,v in self.networks.items())
        elif args[:2]==['network','rm']:self.networks.pop(args[-1],None)
        elif args[0]=='stop':
            item=next(v for v in self.containers.values() if v['id']==args[-1]);item['running']=False
        elif args[0]=='start':
            if self.fail_restore:code=1
            else:next(v for v in self.containers.values() if v['id']==args[-1])['running']=True
        elif args[0]=='run':
            owner=args[args.index('--label')+1].split('=',1)[1]
            if self.fail_run:code=1
            else:
                self.containers[lifecycle.CONTAINER]={'id':'id-apertus','name':lifecycle.CONTAINER,'running':True,'owner':owner}
                result='id-apertus'
        elif args[0]=='rm':
            for name,item in list(self.containers.items()):
                if item['id']==args[-1]:del self.containers[name]
        else:raise AssertionError('Unexpected Docker command: '+repr(args))
        return SimpleNamespace(returncode=code,stdout=result,stderr='boundary diagnostic must never leak')


@pytest.fixture
def case(tmp_path,monkeypatch):
    model=tmp_path/'model';model.mkdir()
    data=b'isolated file-integrity QA, not model weights';(model/'config.json').write_bytes(data)
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'repo':lifecycle.REPOSITORY,'revision':lifecycle.REVISION,
        'files':[{'path':'config.json','bytes':len(data),'sha256':lifecycle.sha256(model/'config.json')}]}))
    monkeypatch.setattr(lifecycle,'MANIFEST_SHA256',lifecycle.sha256(manifest))
    auth=tmp_path/'model.env';auth.write_text('VLLM_API_KEY='+'q'*48+'\n');auth.chmod(0o600)
    docker=DockerBoundary();monkeypatch.setattr(lifecycle.subprocess,'run',docker.run)
    class LogProcess:
        def __init__(self):self.offset=0;self.returncode=None;self.killed=False;self.stdout=self
        def fileno(self):return 123
        def read1(self,size):
            docker.log_reads.append(size)
            if docker.log_read_failure:raise OSError('controlled pipe read failure')
            chunk=docker.log_content[self.offset:self.offset+size];self.offset+=len(chunk)
            if not chunk:self.returncode=0
            return chunk
        def poll(self):return self.returncode
        def kill(self):self.killed=True;self.returncode=-9
        def wait(self,timeout):docker.log_waits.append(timeout);return self.returncode
        def close(self):pass
    def popen(argv,**kwargs):
        docker.calls.append(argv)
        assert argv[:2]==['docker','logs'] and kwargs['stderr']==lifecycle.subprocess.STDOUT
        assert kwargs['stdin']==lifecycle.subprocess.DEVNULL and kwargs['stdout']==lifecycle.subprocess.PIPE
        if docker.log_failure:raise OSError('controlled log capture failure')
        process=LogProcess();docker.log_processes.append(process);return process
    class Selector:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def register(self,*args):pass
        def select(self,timeout):
            docker.log_waits.append(timeout)
            return [] if docker.log_timeout else [('ready',1)]
    monkeypatch.setattr(lifecycle.subprocess,'Popen',popen)
    monkeypatch.setattr(lifecycle.selectors,'DefaultSelector',Selector)
    run=lifecycle.Lifecycle(tmp_path/'state',probe=lambda key,base_url:True,sleep=lambda seconds:None)
    config=dict(manifest=manifest,model_dir=model,auth_env=auth,stop_workloads=['llama-qwen35','visionx-triton-face-local'])
    return run,docker,config


def test_start_stop_is_idempotent_and_restores_only_previously_running_authorized_workloads(case):
    run,docker,config=case
    docker.containers['visionx-triton-face-local']['running']=False
    run.prepare(**config);run.start();run.start()
    assert not docker.containers['llama-qwen35']['running']
    assert docker.containers['unrelated-workload']['running']
    assert sum(c[1]=='run' for c in docker.calls)==1
    state=run.load();assert 'unrelated-workload' in state['running_before']
    run.stop();run.stop()
    assert docker.containers['llama-qwen35']['running']
    assert not docker.containers['visionx-triton-face-local']['running']
    assert [c[-1] for c in docker.calls if c[1]=='stop']==['id-llama-qwen35']
    assert [c[-1] for c in docker.calls if c[1]=='start']==['id-llama-qwen35']


def test_start_failure_restores_workloads_and_keeps_recoverable_history(case):
    run,docker,config=case;run.prepare(**config);docker.fail_run=True
    with pytest.raises(lifecycle.LifecycleError):run.start()
    assert all(v['running'] for v in docker.containers.values())
    assert run.load()['phase']=='stopped'
    assert len([e for e in run.load()['events'] if e['type']=='workload_stopped'])==2
    assert lifecycle.CONTAINER not in docker.containers and docker.networks=={}


def test_failed_restore_can_be_retried_without_restarting_already_restored_workloads(case):
    run,docker,config=case;run.prepare(**config);run.start();docker.fail_restore=True
    with pytest.raises(lifecycle.LifecycleError):run.stop()
    assert run.load()['phase']=='restore_pending'
    docker.fail_restore=False;run.stop()
    assert run.load()['phase']=='stopped'
    assert all(v['running'] for v in docker.containers.values())


@pytest.mark.parametrize('listing_fails',[False,True])
def test_ambiguous_serving_inspect_failure_blocks_cleanup_and_workload_restoration(case,monkeypatch,listing_fails):
    run,docker,config=case;run.prepare(**config);run.start()
    previous=len(docker.calls)
    def ambiguous(argv,**kwargs):
        if argv[1:3]==['container','inspect'] and argv[-1]==lifecycle.CONTAINER:
            docker.calls.append(argv)
            return SimpleNamespace(returncode=1,stdout='',stderr='Transient Docker daemon failure')
        if listing_fails and argv[1:3]==['container','ls']:
            docker.calls.append(argv)
            return SimpleNamespace(returncode=1,stdout='',stderr='Docker daemon unavailable')
        return docker.run(argv,**kwargs)
    monkeypatch.setattr(lifecycle.subprocess,'run',ambiguous)
    with pytest.raises(lifecycle.LifecycleError):run.stop()
    assert run.load()['phase']=='restore_pending'
    assert docker.containers[lifecycle.CONTAINER]['running']
    assert not docker.containers['llama-qwen35']['running']
    assert not docker.containers['visionx-triton-face-local']['running']
    assert not any(c[1] in ('start','rm','logs') or c[1:3]==['network','rm'] for c in docker.calls[previous:])
    monkeypatch.setattr(lifecycle.subprocess,'run',docker.run);run.stop()
    assert lifecycle.CONTAINER not in docker.containers
    assert all(v['running'] for v in docker.containers.values())


def test_changed_weight_or_manifest_aborts_before_any_workload_stop(case):
    run,docker,config=case;run.prepare(**config)
    (config['model_dir']/'config.json').write_bytes(b'changed after prepare')
    with pytest.raises(lifecycle.LifecycleError,match='integrity'):run.start()
    assert not any(c[1]=='stop' for c in docker.calls)
    config['manifest'].write_text('{}')
    with pytest.raises(lifecycle.LifecycleError,match='manifest'):run.prepare(**config)


def test_absent_pinned_image_does_not_pull_or_stop_anything(case):
    run,docker,config=case;run.prepare(**config);docker.image_available=False
    with pytest.raises(lifecycle.LifecycleError,match='pinned'):run.start()
    assert not any(c[1] in ('stop','run','pull') for c in docker.calls)


@pytest.mark.parametrize('mutation',['missing_hash','escape'])
def test_integrity_verification_never_accepts_hashless_or_escaping_file(case,monkeypatch,mutation):
    run,docker,config=case;data=json.loads(config['manifest'].read_text())
    if mutation=='missing_hash':data['files'][0]['sha256']=None
    else:data['files'][0]['path']='../outside'
    config['manifest'].write_text(json.dumps(data))
    monkeypatch.setattr(lifecycle,'MANIFEST_SHA256',lifecycle.sha256(config['manifest']))
    with pytest.raises(lifecycle.LifecycleError):run.prepare(**config)
    assert not any(c[1] in ('stop','run','start') for c in docker.calls)


def test_gpu_memory_utilization_defaults_to_pinned_profile_and_is_configurable(case):
    # Real-host failure: other containers keep 2.4 GiB, so 0.9 of the card was not free.
    run,docker,config=case;run.prepare(**config);run.start()
    command=next(c for c in docker.calls if c[1]=='run')
    assert command[command.index('--gpu-memory-utilization')+1]=='0.9'
    run.stop();docker.calls.clear()
    summary=run.prepare(**config,gpu_memory_utilization=0.88);run.start()
    command=next(c for c in docker.calls if c[1]=='run')
    assert command[command.index('--gpu-memory-utilization')+1]=='0.88'
    assert summary['gpu_memory_utilization']==0.88 and run.load()['gpu_memory_utilization']==0.88


@pytest.mark.parametrize('change',['unknown_workload','insecure_auth','extra_secret','bad_context','bad_offload','bad_utilization','nan_utilization','bool_utilization'])
def test_unsafe_prepare_never_stops_or_launches(case,change):
    run,docker,config=case
    if change=='unknown_workload':config['stop_workloads']=['unrelated-workload']
    elif change=='insecure_auth':config['auth_env'].chmod(0o644)
    elif change=='extra_secret':config['auth_env'].write_text('VLLM_API_KEY='+'q'*48+'\nHF_TOKEN=never-pass-this\n')
    elif change=='bad_context':config['max_context']=100000
    elif change=='bad_utilization':config['gpu_memory_utilization']=0.99
    elif change=='nan_utilization':config['gpu_memory_utilization']=float('nan')
    elif change=='bool_utilization':config['gpu_memory_utilization']=True
    else:config['cpu_offload']=100
    with pytest.raises(lifecycle.LifecycleError):run.prepare(**config)
    assert not any(c[1] in ('stop','run','start') for c in docker.calls)


def test_prepare_generates_private_key_only_when_absent_and_never_records_it(case):
    run,docker,config=case;config['auth_env'].unlink()
    run.prepare(**config);key=lifecycle.read_key(config['auth_env'])
    assert len(key)==64 and config['auth_env'].stat().st_mode&0o777==0o600
    run.prepare(**config)
    assert lifecycle.read_key(config['auth_env'])==key
    assert key not in json.dumps(run.load())+json.dumps(docker.calls)


def test_prepare_never_writes_authentication_into_model_mount(case):
    run,docker,config=case;config['auth_env']=config['model_dir']/'secret.env'
    with pytest.raises(lifecycle.LifecycleError,match='outside'):run.prepare(**config)
    assert not config['auth_env'].exists()


def test_server_launch_has_pinned_image_private_auth_offline_loopback_and_readonly_weights(case):
    run,docker,config=case;run.prepare(**config);run.start()
    command=next(c for c in docker.calls if c[1]=='run')
    assert lifecycle.IMAGE in command
    # Docker ignores --publish on an internal network (observed on the real host).
    assert '--publish' not in command and not any(a.startswith('127.0.0.1:') for a in command)
    assert command[command.index('--env-file')+1]==str(config['auth_env'])
    assert command[command.index('--entrypoint')+1]=='/opt/venv/bin/vllm'
    assert any('dst=/models/apertus,readonly' in arg for arg in command)
    assert '--language-model-only' in command and '--read-only' in command
    assert '--no-enable-log-requests' in command and '--no-enable-log-outputs' in command
    assert '--pull' in command and command[command.index('--pull')+1]=='never'
    assert 'HF_HUB_OFFLINE=1' in command and 'TRANSFORMERS_OFFLINE=1' in command
    assert 'q'*48 not in json.dumps(docker.calls)+json.dumps(run.load())
    assert not any('HF_TOKEN=' in arg or 'HUGGING_FACE_HUB_TOKEN=' in arg for arg in command)
    assert any(c[1:3]==['network','create'] and '--internal' in c for c in docker.calls)


def test_server_runs_as_invoking_host_user_without_extra_capabilities(case):
    # Real-host failure: root with all capabilities dropped cannot read 0600
    # weights or write the 0700 cache owned by the invoking user (EACCES).
    run,docker,config=case;run.prepare(**config);run.start()
    command=next(c for c in docker.calls if c[1]=='run')
    assert command[command.index('--user')+1]==f'{os.getuid()}:{os.getgid()}'
    assert command[command.index('--cap-drop')+1]=='ALL'
    assert '--privileged' not in command
    # The image has no passwd entry for the host uid; torch calls getpass.getuser().
    assert 'USER=tenderproof' in command and 'LOGNAME=tenderproof' in command


def test_readiness_probes_the_internal_network_container_address_and_reports_it(case):
    run,docker,config=case;probed=[]
    run.probe=lambda key,base_url:probed.append(base_url) or True
    run.prepare(**config);summary=run.start()
    assert probed==['http://172.30.5.2:8000/v1']
    assert summary['endpoint']=='http://172.30.5.2:8000/v1' and run.load()['endpoint']==summary['endpoint']
    assert run.status()['endpoint']==summary['endpoint']
    run.stop();assert run.load()['endpoint'] is None


@pytest.mark.parametrize('ips',[['','172.30.5.2'],['not-an-ip','8.8.8.8','172.30.5.2']])
def test_probe_waits_for_a_private_container_address_and_never_probes_other_hosts(case,ips):
    run,docker,config=case;probed=[];docker.ips=list(ips)
    run.probe=lambda key,base_url:probed.append(base_url) or True
    run.prepare(**config);run.start()
    assert probed==['http://172.30.5.2:8000/v1']


def test_existing_unowned_serving_name_is_never_stopped(case):
    run,docker,config=case;run.prepare(**config)
    docker.containers[lifecycle.CONTAINER]={'id':'someone-else','name':lifecycle.CONTAINER,'owner':'another-task','running':True}
    with pytest.raises(lifecycle.LifecycleError,match='owned'):run.start()
    assert not any(c[1] in ('stop','rm','run') for c in docker.calls)


def test_recovery_restores_stop_requested_before_process_interruption(case):
    run,docker,config=case;run.prepare(**config);run.start()
    state=run.load();state['phase']='starting'
    for record in state['workloads']:record['stopped']=False
    run.save(state)
    run.stop()
    assert all(v['running'] for v in docker.containers.values())


def test_replacement_workload_name_cannot_redirect_restore(case):
    run,docker,config=case;run.prepare(**config);run.start()
    docker.containers['llama-qwen35']={'id':'replacement-id','name':'llama-qwen35','running':False,'owner':None}
    with pytest.raises(lifecycle.LifecycleError):run.stop()
    assert not docker.containers['llama-qwen35']['running']
    assert not any(c[1]=='start' and c[-1]=='replacement-id' for c in docker.calls)


def test_unauthenticated_endpoint_failure_rolls_back_without_exposing_key(case):
    run,docker,config=case;run.prepare(**config)
    def insecure(key,base_url):raise lifecycle.LifecycleError('Endpoint accepts unauthenticated model access')
    run.probe=insecure
    with pytest.raises(lifecycle.LifecycleError,match='unauthenticated'):run.start()
    assert all(v['running'] for v in docker.containers.values())
    assert lifecycle.CONTAINER not in docker.containers


def test_public_manifest_matches_script_pin_and_covers_complete_official_files():
    manifest=SCRIPT.parents[1]/'deploy/apertus-model-manifest.json'
    assert lifecycle.sha256(manifest)==lifecycle.MANIFEST_SHA256
    data=json.loads(manifest.read_text())
    assert data['repo']==lifecycle.REPOSITORY and data['revision']==lifecycle.REVISION
    assert len(data['files'])==23 and sum(f['bytes'] for f in data['files'])==18441320470
    assert all(len(f['sha256'])==64 for f in data['files'])


@pytest.mark.parametrize('anonymous_status',[401,200,403])
def test_actual_readiness_probe_requires_authenticated_model_and_401_without_key(monkeypatch,anonymous_status):
    calls=[]
    def request(req,timeout):
        calls.append(req)
        if req.get_header('Authorization'):
            return nullcontext(SimpleNamespace(read=lambda limit:json.dumps({'data':[{'id':lifecycle.REPOSITORY}]}).encode()))
        if anonymous_status!=200:raise lifecycle.HTTPError(req.full_url,anonymous_status,'controlled QA response',None,None)
        return nullcontext(SimpleNamespace(read=lambda limit:b'{}'))
    monkeypatch.setattr(lifecycle,'urlopen',request)
    if anonymous_status==401:assert lifecycle.probe_model('q'*48,'http://172.30.5.2:8000/v1') is True
    else:
        with pytest.raises(lifecycle.LifecycleError):lifecycle.probe_model('q'*48,'http://172.30.5.2:8000/v1')
    assert len(calls)==2 and calls[0].full_url=='http://172.30.5.2:8000/v1/models'
    assert calls[0].get_header('Authorization')=='Bearer '+'q'*48
    assert calls[1].get_header('Authorization') is None


def test_owned_diagnostics_are_private_redacted_and_captured_before_removal(case):
    run,docker,config=case;run.prepare(**config);run.start()
    key=lifecycle.read_key(config['auth_env'])
    docker.log_content=('QA stdout failure\nQA stderr key='+key+'\n').encode()
    summary=run.stop()
    logs=list((run.directory/'diagnostics').glob('*.log'))
    assert len(logs)==1
    text=logs[0].read_text()
    assert 'QA stdout failure' in text and 'QA stderr key=[REDACTED]' in text and key not in text
    assert logs[0].stat().st_mode&0o777==0o600
    assert logs[0].parent.stat().st_mode&0o777==0o700
    captures=[c for c in docker.calls if c[1]=='logs']
    assert len(captures)==1 and captures[0][-1]=='id-apertus'
    assert captures[0][captures[0].index('--tail')+1]=='1000'
    assert docker.calls.index(captures[0])<next(i for i,c in enumerate(docker.calls) if c[1]=='rm')
    assert 'QA stdout failure' not in json.dumps(summary)+json.dumps(run.load())
    assert key not in json.dumps(docker.calls)+json.dumps(run.load())


@pytest.mark.parametrize('changed',['owner','id'])
def test_diagnostics_never_read_unowned_or_replacement_container(case,changed):
    run,docker,config=case;run.prepare(**config);run.start()
    docker.containers[lifecycle.CONTAINER][changed]='someone-else'
    with pytest.raises(lifecycle.LifecycleError):run.stop()
    assert not any(c[1]=='logs' for c in docker.calls)
    assert not (run.directory/'diagnostics').exists()


def test_diagnostics_bound_bytes_tail_timeout_and_redact_key_fragment_at_cutoff(case):
    run,docker,config=case;run.prepare(**config);run.start()
    key=lifecycle.read_key(config['auth_env']).encode()
    limit=256*1024
    docker.log_content=b'x'*(limit-20)+key+b'z'*(limit*3)
    run.stop()
    content=next((run.directory/'diagnostics').glob('*.log')).read_bytes()
    assert len(content)<=limit and key not in content and key[:20] not in content
    assert docker.log_processes[0].offset==limit and docker.log_processes[0].killed
    assert all(size<=65536 for size in docker.log_reads)
    assert all(timeout<=5 for timeout in docker.log_waits)


@pytest.mark.parametrize('failure',['spawn','read','timeout','missing_key','changed_key','storage'])
def test_diagnostic_capture_failure_cannot_block_safe_restoration(case,failure):
    run,docker,config=case;run.prepare(**config);run.start()
    if failure=='spawn':docker.log_failure=True
    elif failure=='read':docker.log_read_failure=True
    elif failure=='timeout':docker.log_timeout=True
    elif failure=='missing_key':config['auth_env'].unlink()
    elif failure=='changed_key':config['auth_env'].write_text('VLLM_API_KEY='+'z'*48+'\n')
    else:(run.directory/'diagnostics').write_text('not a directory')
    run.stop()
    assert run.load()['phase']=='stopped'
    assert lifecycle.CONTAINER not in docker.containers
    assert all(v['running'] for v in docker.containers.values())
    captures=[c for c in docker.calls if c[1]=='logs']
    event=next(e for e in run.load()['events'] if e['type']=='diagnostic_capture')
    if failure in ('missing_key','changed_key','storage'):
        assert not captures and event['status']=='unavailable'
    else:
        assert len(captures)==1
        if failure=='timeout':
            assert event['timed_out'] is True and docker.log_processes[0].killed
        else:assert event['status']=='unavailable'


def test_startup_failure_saves_owned_container_diagnostics_before_automatic_restoration(case):
    run,docker,config=case;run.prepare(**config)
    docker.log_content=b'controlled QA kernel startup failure\n'
    def failed_start(key,base_url):raise lifecycle.LifecycleError('Controlled startup failure')
    run.probe=failed_start
    with pytest.raises(lifecycle.LifecycleError,match='Controlled startup'):run.start()
    log=next((run.directory/'diagnostics').glob('*.log'))
    assert log.read_bytes()==docker.log_content
    assert run.load()['phase']=='stopped'
    assert lifecycle.CONTAINER not in docker.containers
    assert all(v['running'] for v in docker.containers.values())
    assert [c[-1] for c in docker.calls if c[1]=='logs']==['id-apertus']
