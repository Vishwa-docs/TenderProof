"""Create private local operator access without seeding business records."""
from pathlib import Path
import json
import secrets
from dotenv import dotenv_values, set_key

root=Path(__file__).resolve().parents[1]
env=root/'.env';env.touch(exist_ok=True);env.chmod(0o600)
values=dotenv_values(env)
runtime=root/'.runtime';runtime.mkdir(exist_ok=True)
if not values.get('POSTGRES_PASSWORD') or values['POSTGRES_PASSWORD']=='local-demo-only':
    set_key(env,'POSTGRES_PASSWORD',secrets.token_urlsafe(32))
if not values.get('TENDERPROOF_PRINCIPALS_JSON') or values['TENDERPROOF_PRINCIPALS_JSON']=='{}':
    token=secrets.token_urlsafe(32)
    principals={token:{'actor':'local-operator','role':'engineer','projects':['default']}}
    set_key(env,'TENDERPROOF_PRINCIPALS_JSON',json.dumps(principals,separators=(',',':')))
    access=runtime/'operator_token';access.write_text(token+'\n');access.chmod(0o600)
set_key(env,'APP_MODE','live')
print('Private local access configured. Operator token: .runtime/operator_token (never commit or publish).')
