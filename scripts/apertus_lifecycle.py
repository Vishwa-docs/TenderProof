#!/usr/bin/env python3
"""Explicit, recoverable local GPU serving lifecycle. No downloads or SSH calls."""
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path,PurePosixPath
import re
import secrets
import selectors
import signal
import stat
import subprocess
import tempfile
import time
from urllib.error import HTTPError,URLError
from urllib.request import Request,build_opener,ProxyHandler
from uuid import uuid4

REPOSITORY='swiss-ai/Apertus-v1.5-8B'
REVISION='ef4bbc54d6fe658bc782280ff9f3b53a10a9758f'
IMAGE='ghcr.io/swiss-ai/vllm_apertus_1.5_release@sha256:d85533f251c8272218ae2e519510836376e5a335b44f2204f193018e37753bc6'
MANIFEST_SHA256='b467d83827cfad858f7edc524c47e4db74811d9e8f4cfedbc14c656e312b9a7b'
ALLOWED_WORKLOADS={'llama-qwen35','visionx-triton-face-local'}
CONTAINER='tenderproof-apertus'
OWNER_LABEL='org.tenderproof.lifecycle'
LOG_MAX_BYTES=256*1024
LOG_TIMEOUT_SECONDS=5
CONTAINER_FORMAT='{"id":{{json .Id}},"name":{{json .Name}},"running":{{json .State.Running}},"owner":{{json (index .Config.Labels "'+OWNER_LABEL+'")}}}'
NETWORK_FORMAT='{"id":{{json .Id}},"internal":{{json .Internal}},"owner":{{json (index .Labels "'+OWNER_LABEL+'")}}}'
# Loopback authentication must never be forwarded through an inherited HTTP proxy.
urlopen=build_opener(ProxyHandler({})).open

class LifecycleError(Exception):pass

def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(8*1024*1024):digest.update(block)
    return digest.hexdigest()

def private_directory(path):
    path=Path(path)
    if path.is_symlink():raise LifecycleError('Private directory cannot be a symlink.')
    path.mkdir(parents=True,exist_ok=True,mode=0o700)
    info=path.stat()
    if info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:
        raise LifecycleError('Private state/cache directory must be owned by this user with mode0700.')
    return path.resolve()

def read_key(path):
    path=Path(path)
    if path.is_symlink():raise LifecycleError('Authentication file cannot be a symlink.')
    info=path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
        raise LifecycleError('Authentication file must be user-owned with mode0600.')
    if info.st_size>1024:raise LifecycleError('Authentication file must contain only VLLM_API_KEY.')
    match=re.fullmatch(r'VLLM_API_KEY=([A-Za-z0-9._~-]{32,256})\n?',path.read_text())
    if not match:raise LifecycleError('Authentication file must contain only a bounded VLLM_API_KEY, with no HF credentials.')
    return match.group(1)

def ensure_key(path):
    """Create only when absent; never replace an existing key or print its value."""
    path=Path(path)
    if path.is_symlink():raise LifecycleError('Authentication file cannot be a symlink.')
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        try:descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        except FileExistsError:pass
        else:
            with os.fdopen(descriptor,'w') as stream:
                stream.write('VLLM_API_KEY='+secrets.token_urlsafe(48)+'\n');stream.flush();os.fsync(stream.fileno())
    return read_key(path)

def verify_files(manifest_path,model_dir):
    manifest_path=Path(manifest_path);model_dir=Path(model_dir).resolve()
    if sha256(manifest_path)!=MANIFEST_SHA256:raise LifecycleError('Trusted pinned manifest hash does not match.')
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('repo')!=REPOSITORY or manifest.get('revision')!=REVISION:
        raise LifecycleError('Manifest does not identify the pinned official model.')
    files=manifest.get('files');seen=set();total=0
    if not isinstance(files,list) or not files:raise LifecycleError('Manifest has no files.')
    for item in files:
        name=item.get('path');expected=item.get('sha256');size=item.get('bytes')
        if not isinstance(name,str) or not name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or name in seen:
            raise LifecycleError('Unsafe or duplicate manifest path.')
        if not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected) or type(size) is not int or size<0:
            raise LifecycleError('Every manifest file must have its pinned size and SHA256.')
        path=model_dir/name;seen.add(name)
        if not path.resolve().is_relative_to(model_dir) or any(p.is_symlink() for p in [path,*path.parents] if p!=model_dir and p.is_relative_to(model_dir)):
            raise LifecycleError('Model file paths cannot escape the model directory or use symlinks.')
        if not path.is_file() or path.stat().st_size!=size or sha256(path)!=expected:
            raise LifecycleError('Model file integrity verification failed: '+name)
        total+=size
    return {'manifest_sha256':MANIFEST_SHA256,'repository':REPOSITORY,'revision':REVISION,
            'file_count':len(files),'bytes':total,'verified_at':datetime.now(timezone.utc).isoformat()}

class Docker:
    def call(self,args,timeout=180):
        try:result=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=timeout)
        except (OSError,subprocess.TimeoutExpired) as exc:raise LifecycleError('Docker operation unavailable or timed out: '+args[0]) from exc
        if result.returncode:
            # Docker diagnostics can contain command/environment details. Never echo them.
            raise LifecycleError('Docker operation failed: '+args[0]+' (exit '+str(result.returncode)+').')
        return result.stdout.strip()
    def _inspect(self,kind,identity,format):
        try:return json.loads(self.call([kind,'inspect','--format',format,identity]))
        except LifecycleError as failure:
            # Exit1 also means daemon/permission failures. Only a successful full
            # listing can prove absence; uncertainty must block GPU restoration.
            name_field='.Names' if kind=='container' else '.Name'
            listing_format='{"id":{{json .ID}},"name":{{json '+name_field+'}}}'
            args=[kind,'ls',*(['--all'] if kind=='container' else []),'--no-trunc','--format',listing_format]
            listing=self.call(args)
            rows=[json.loads(line) for line in listing.splitlines() if line.strip()]
            if any(identity in (row['id'],row['name']) for row in rows):raise failure
            return None
    def container(self,identity):
        return self._inspect('container',identity,CONTAINER_FORMAT)
    def network(self,name):
        return self._inspect('network',name,NETWORK_FORMAT)
    def verify_image(self):
        values=json.loads(self.call(['image','inspect','--format','{{json .RepoDigests}}',IMAGE]))
        if IMAGE not in values:raise LifecycleError('The pinned official image is not locally verified.')
    def container_address(self,container_id,network):
        """Private IPv4 of the owned container on its task network, or None until assigned.

        Docker ignores --publish on an --internal network, so the host reaches the
        server only through this bridge address. Anything else is never probed."""
        try:value=json.loads(self.call(['container','inspect','--format','{{json (index .NetworkSettings.Networks "'+network+'").IPAddress}}',container_id]))
        except (LifecycleError,ValueError):return None
        try:address=ipaddress.ip_address(value)
        except ValueError:return None
        return f'http://{address}:8000/v1' if address.version==4 and address.is_private else None
    def recent_logs(self,container_id):
        """Bound both pipe memory and time; terminate only the diagnostic CLI."""
        process=subprocess.Popen(['docker','logs','--tail','1000','--timestamps',container_id],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        output=bytearray();timed_out=False
        try:
            deadline=time.monotonic()+LOG_TIMEOUT_SECONDS
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                while len(output)<LOG_MAX_BYTES:
                    remaining=deadline-time.monotonic()
                    if remaining<=0 or not selector.select(remaining):
                        timed_out=True;break
                    chunk=process.stdout.read1(min(65536,LOG_MAX_BYTES-len(output)))
                    if not chunk:break
                    output.extend(chunk)
        finally:
            try:
                if process.poll() is None:process.kill()
                process.wait(timeout=1)
            except (OSError,subprocess.TimeoutExpired):pass
            process.stdout.close()
        return bytes(output),{'truncated':len(output)==LOG_MAX_BYTES,'timed_out':timed_out,
                              'exit_code':process.returncode}

def probe_model(key,base_url):
    """Return readiness, and reject an endpoint that accepts unauthenticated access."""
    url=base_url.rstrip('/')+'/models'
    try:
        with urlopen(Request(url,headers={'Authorization':'Bearer '+key}),timeout=5) as response:
            data=json.loads(response.read(1024*1024))
        if not any(row.get('id')==REPOSITORY for row in data.get('data',[])):return False
        try:
            with urlopen(Request(url),timeout=5):pass
        except HTTPError as exc:
            if exc.code==401:return True
            raise LifecycleError('Unauthenticated model access did not return401.') from None
        raise LifecycleError('Endpoint accepts unauthenticated model access.')
    except (URLError,TimeoutError,ValueError):return False

class Lifecycle:
    def __init__(self,state_dir,probe=probe_model,sleep=time.sleep):
        self.directory=private_directory(state_dir)
        self.path=self.directory/'state.json';self.docker=Docker();self.probe=probe;self.sleep=sleep
    @contextmanager
    def locked(self):
        descriptor=os.open(self.directory/'lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as exc:raise LifecycleError('Another lifecycle operation holds the state lock.') from exc
            yield
        finally:os.close(descriptor)
    def load(self):
        if self.path.is_symlink():raise LifecycleError('State cannot be a symlink.')
        if not self.path.exists():raise LifecycleError('Run prepare first.')
        return json.loads(self.path.read_text())
    def save(self,state):
        fd,name=tempfile.mkstemp(prefix='.state-',dir=self.directory)
        try:
            with os.fdopen(fd,'w') as stream:
                json.dump(state,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(name,self.path)
            directory_fd=os.open(self.directory,os.O_DIRECTORY)
            try:os.fsync(directory_fd)
            finally:os.close(directory_fd)
        finally:
            if os.path.exists(name):os.unlink(name)
    def record(self,state,kind,**details):
        state['events'].append({'at':datetime.now(timezone.utc).isoformat(),'type':kind,**details});self.save(state)
    def prepare(self,manifest,model_dir,auth_env,stop_workloads=(),max_context=32768,cpu_offload=0,gpu_memory_utilization=0.9):
        with self.locked():
            if not set(stop_workloads).issubset(ALLOWED_WORKLOADS):raise LifecycleError('Only explicitly authorized workload names may be stopped.')
            if type(max_context) is not int or not 4096<=max_context<=32768:raise LifecycleError('Context must be4096–32768 tokens.')
            if isinstance(cpu_offload,bool) or not math.isfinite(cpu_offload) or not 0<=cpu_offload<=16:raise LifecycleError('CPU offload must be0–16GiB.')
            if isinstance(gpu_memory_utilization,bool) or not isinstance(gpu_memory_utilization,(int,float)) \
                    or not math.isfinite(gpu_memory_utilization) or not 0.5<=gpu_memory_utilization<=0.95:
                raise LifecycleError('GPU memory utilization must be between 0.5 and 0.95.')
            verification=verify_files(manifest,model_dir)
            model_dir=Path(model_dir).resolve();original_auth_path=Path(auth_env);auth_env=original_auth_path.resolve()
            if any(c in str(path) for path in (model_dir,self.directory) for c in ',\r\n'):
                raise LifecycleError('Docker mount paths cannot contain commas or line breaks.')
            if auth_env.is_relative_to(model_dir) or self.directory.is_relative_to(model_dir):raise LifecycleError('Secrets and writable state must be outside the read-only model directory.')
            previous=self.load() if self.path.exists() else None
            if previous and previous['phase'] not in ('prepared','stopped'):raise LifecycleError('Stop and restore the existing lifecycle before preparing again.')
            ensure_key(original_auth_path)
            private_directory(self.directory/'cache')
            owner=str(uuid4())
            state={'phase':'prepared','owner':owner,'container_id':None,'network':'tenderproof-apertus-'+owner[:12],
                'manifest':str(Path(manifest).resolve()),'model_dir':str(model_dir),'auth_env':str(auth_env),
                'image':IMAGE,'verification':verification,'stop_workloads':sorted(set(stop_workloads)),
                'max_context':max_context,'cpu_offload':cpu_offload,'gpu_memory_utilization':gpu_memory_utilization,'workloads':[],
                'events':previous['events'] if previous else [],'running_before':[]}
            self.record(state,'prepared',verification=verification,stop_workloads=state['stop_workloads'])
            return self.summary(state)
    def summary(self,state):
        return {'phase':state['phase'],'image':IMAGE,'revision':REVISION,'container_id':state['container_id'],
            'endpoint':state.get('endpoint'),'verification':state['verification'],
            'max_context':state['max_context'],'cpu_offload_gib':state['cpu_offload'],
            'gpu_memory_utilization':state.get('gpu_memory_utilization',0.9),
            'memory_fit':'candidate_not_verified' if state['phase']!='running' else 'startup_succeeded_not_a_full_request_memory_test',
            'workloads':state['workloads']}
    def start(self,startup_timeout=900):
        if not 30<=startup_timeout<=1800:raise LifecycleError('Startup timeout must be30–1800 seconds.')
        with self.locked():
            state=self.load()
            if state['phase']=='running':return self._status(state)
            if state['phase'] not in ('prepared','stopped'):raise LifecycleError('Run stop to finish recovery before starting again.')
            state['verification']=verify_files(state['manifest'],state['model_dir'])
            key=read_key(state['auth_env']);self.docker.verify_image()
            state['auth_key_sha256']=hashlib.sha256(key.encode()).hexdigest()
            if self.docker.container(CONTAINER):raise LifecycleError('The serving container name is already in use; no owned launch can proceed.')
            state['running_before']=self.docker.call(['ps','--format','{{.Names}}']).splitlines()
            state['workloads']=[]
            for name in state['stop_workloads']:
                item=self.docker.container(name)
                if item is None:raise LifecycleError('Authorized workload does not exist: '+name)
                state['workloads'].append({'name':name,'id':item['id'],'was_running':item['running'],
                    'stop_requested':False,'stopped':False,'restored':False})
            state['phase']='starting';self.record(state,'starting',running_before=state['running_before'])
            try:
                if self.docker.network(state['network']):raise LifecycleError('Task network name already exists.')
                self.docker.call(['network','create','--internal','--label',OWNER_LABEL+'='+state['owner'],state['network']])
                network=self.docker.network(state['network'])
                if not network or not network['internal'] or network['owner']!=state['owner']:raise LifecycleError('Task network isolation was not confirmed.')
                for item in state['workloads']:
                    if not item['was_running']:continue
                    item['stop_requested']=True;self.record(state,'workload_stop_requested',name=item['name'],container_id=item['id'])
                    self.docker.call(['stop','--time','30',item['id']])
                    current=self.docker.container(item['id'])
                    if not current or current['running']:raise LifecycleError('Authorized workload did not stop cleanly.')
                    item['stopped']=True;self.record(state,'workload_stopped',name=item['name'],container_id=item['id'])
                command=['run','--detach','--name',CONTAINER,'--pull','never','--label',OWNER_LABEL+'='+state['owner'],
                    '--gpus','all','--network',state['network'],
                    '--env-file',state['auth_env'],'--user',f'{os.getuid()}:{os.getgid()}',
                    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
                    '--tmpfs','/tmp:rw,nosuid,nodev,size=4g','--shm-size','4g',
                    '--mount','type=bind,src='+state['model_dir']+',dst=/models/apertus,readonly',
                    '--mount','type=bind,src='+str(self.directory/'cache')+',dst=/cache',
                    '--entrypoint','/opt/venv/bin/vllm']
                for value in ('HF_HUB_OFFLINE=1','TRANSFORMERS_OFFLINE=1','HF_DATASETS_OFFLINE=1','DO_NOT_TRACK=1',
                              'HF_HUB_DISABLE_TELEMETRY=1','VLLM_NO_USAGE_STATS=1','HOME=/cache','USER=tenderproof','LOGNAME=tenderproof','XDG_CACHE_HOME=/cache',
                              'HF_HOME=/cache/huggingface','VLLM_CACHE_ROOT=/cache/vllm',
                              'TORCHINDUCTOR_CACHE_DIR=/cache/torchinductor','TRITON_CACHE_DIR=/cache/triton'):
                    command+=['--env',value]
                command+=[IMAGE,'serve','/models/apertus','--served-model-name',REPOSITORY,'--host','0.0.0.0','--port','8000',
                    '--chat-template-content-format','string','--max-model-len',str(state['max_context']),
                    '--max-num-seqs','1','--max-num-batched-tokens','2048','--gpu-memory-utilization',str(state.get('gpu_memory_utilization',0.9)),
                    '--enforce-eager','--cpu-offload-gb',str(state['cpu_offload']),'--language-model-only','--skip-mm-profiling',
                    '--no-enable-log-requests','--no-enable-log-outputs']
                state['container_id']=self.docker.call(command);self.record(state,'server_launched',container_id=state['container_id'])
                deadline=time.monotonic()+startup_timeout
                while time.monotonic()<deadline:
                    current=self.docker.container(state['container_id'])
                    if not current or not current['running']:raise LifecycleError('Serving container exited before readiness.')
                    base_url=self.docker.container_address(state['container_id'],state['network'])
                    if base_url and self.probe(key,base_url):
                        state['endpoint']=base_url
                        state['phase']='running';self.record(state,'authenticated_text_server_ready');return self.summary(state)
                    self.sleep(2)
                raise LifecycleError('Serving readiness deadline expired; no model-quality result is claimed.')
            except BaseException:
                self.record(state,'start_failed')
                self._stop(state)
                raise
    def _capture_diagnostics(self,state,container_id):
        """Best effort, private and redacted; called only after ownership checks."""
        details={'container_id':container_id,'status':'unavailable'}
        try:
            key=read_key(state['auth_env']).encode()
            # An old or replaced key cannot safely redact the actual launch key.
            if hashlib.sha256(key).hexdigest()!=state.get('auth_key_sha256'):
                raise LifecycleError('Launch authentication fingerprint is unavailable or changed.')
            directory=private_directory(self.directory/'diagnostics')
            output,metadata=self.docker.recent_logs(container_id)
            output=output.replace(key,b'[REDACTED]')
            # The byte/time bound may split a secret at the end of the pipe.
            for length in range(len(key)-1,0,-1):
                if output.endswith(key[:length]):
                    output=output[:-length]+b'[REDACTED]';break
            output=output[:LOG_MAX_BYTES]
            filename=str(uuid4())+'.log'
            fd=os.open(directory/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as stream:
                stream.write(output);stream.flush();os.fsync(stream.fileno())
            details.update(status='captured',file=filename,bytes=len(output),**metadata)
        except (Exception,KeyboardInterrupt):
            # Do not copy exception messages, log text or keys into public/state output.
            pass
        try:self.record(state,'diagnostic_capture',**details)
        except (Exception,KeyboardInterrupt):pass
    def _stop(self,state):
        state['phase']='restore_pending';self.save(state)
        serving=self.docker.container(CONTAINER)
        if serving:
            if serving['owner']!=state['owner'] or state['container_id'] not in (None,serving['id']):
                raise LifecycleError('Serving name belongs to another container; refusing to stop it or restore competing workloads.')
            self._capture_diagnostics(state,serving['id'])
            self.docker.call(['rm','--force',serving['id']]);self.record(state,'server_removed',container_id=serving['id'])
        state['container_id']=None;state['endpoint']=None;self.save(state)
        errors=[]
        for item in state['workloads']:
            if not item['was_running'] or not item['stop_requested'] or item['restored']:continue
            try:
                current=self.docker.container(item['id'])
                if not current:raise LifecycleError('Original workload container no longer exists; replacement names are never restored.')
                if not current['running']:self.docker.call(['start',item['id']])
                current=self.docker.container(item['id'])
                if not current or not current['running']:raise LifecycleError('Original workload did not restart.')
                item['restored']=True;self.record(state,'workload_restored',name=item['name'],container_id=item['id'])
            except LifecycleError:errors.append(item['name'])
        network=self.docker.network(state['network'])
        if network:
            if network['owner']!=state['owner']:raise LifecycleError('Network ownership changed; refusing to remove it.')
            self.docker.call(['network','rm',state['network']])
        if errors:
            self.record(state,'restore_incomplete',workloads=errors)
            raise LifecycleError('Restoration incomplete; retry stop after resolving Docker/container availability: '+', '.join(errors))
        state['phase']='stopped';self.record(state,'stopped');return self.summary(state)
    def stop(self):
        with self.locked():
            state=self.load()
            if state['phase']=='stopped':return self.summary(state)
            return self._stop(state)
    def _status(self,state):
        result=self.summary(state);item=self.docker.container(CONTAINER)
        result['owned_container_running']=bool(item and item['owner']==state['owner'] and item['id']==state['container_id'] and item['running'])
        result['authenticated_model_ready']=bool(state.get('endpoint') and self.probe(read_key(state['auth_env']),state['endpoint'])) if result['owned_container_running'] else False
        return result
    def status(self):
        with self.locked():return self._status(self.load())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',type=Path,default=Path.home()/'tenderproof/runtime/apertus-lifecycle')
    modes=parser.add_subparsers(dest='mode',required=True)
    prepare=modes.add_parser('prepare')
    adjacent_manifest=Path(__file__).resolve().with_name('apertus-model-manifest.json')
    prepare.add_argument('--manifest',type=Path,default=adjacent_manifest if adjacent_manifest.exists() else Path(__file__).resolve().parents[1]/'deploy/apertus-model-manifest.json')
    prepare.add_argument('--model-dir',type=Path,required=True)
    prepare.add_argument('--auth-env',type=Path,required=True)
    prepare.add_argument('--stop-workload',dest='stop_workloads',choices=sorted(ALLOWED_WORKLOADS),action='append',default=[])
    prepare.add_argument('--max-context',type=int,default=32768)
    prepare.add_argument('--cpu-offload','--cpu-offload-gb',dest='cpu_offload',type=float,default=0)
    prepare.add_argument('--gpu-memory-utilization',type=float,default=0.9)
    start=modes.add_parser('start');start.add_argument('--startup-timeout',type=int,default=900)
    modes.add_parser('status');modes.add_parser('stop')
    args=vars(parser.parse_args());mode=args.pop('mode');state_dir=args.pop('state_dir')
    def interrupted(signum,frame):raise LifecycleError('Lifecycle interrupted; recovery will be attempted.')
    for sig in (signal.SIGTERM,signal.SIGHUP):signal.signal(sig,interrupted)
    try:print(json.dumps(getattr(Lifecycle(state_dir),mode)(**args),indent=2))
    except (LifecycleError,OSError,ValueError,KeyboardInterrupt) as exc:
        # Avoid tracebacks or exception bodies from Docker/HTTP/files containing secrets.
        print(str(exc) if isinstance(exc,LifecycleError) else 'Lifecycle failed; inspect private state and run stop to recover.',file=__import__('sys').stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
