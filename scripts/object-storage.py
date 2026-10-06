#!/usr/bin/env python3
"""Create a WAL-G config Secret from existing Secrets and provider-neutral S3 settings."""
import argparse
import base64
import json
import re
import sys
from urllib.parse import urlsplit
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'smoke-test'))
from run import run, walg_environment


def storage_config(endpoint,bucket,region,path_style,allow_http=False):
    url=urlsplit(endpoint)
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Endpoint must be HTTP(S) without embedded credentials/query')
    if url.scheme!='https' and not allow_http:raise ValueError('TLS is required unless --allow-http-development is explicit')
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket):raise ValueError('Invalid bucket')
    if not region or any(ord(c)<32 for c in region):raise ValueError('Invalid region')
    return dict(AWS_ENDPOINT=endpoint,WALG_S3_PREFIX='s3://'+bucket,AWS_REGION=region,AWS_S3_FORCE_PATH_STYLE=str(path_style).lower(),WALG_COMPRESSION_METHOD='brotli')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('namespace','credential-secret','postgres-secret','output-secret','endpoint','bucket'):p.add_argument('--'+name,required=True)
    p.add_argument('--region',default='us-east-1');p.add_argument('--path-style',action=argparse.BooleanOptionalAction,default=True)
    p.add_argument('--allow-http-development',action='store_true');p.add_argument('--apply',action='store_true')
    a=p.parse_args();config=storage_config(a.endpoint,a.bucket,a.region,a.path_style,a.allow_http_development)
    if a.output_secret in (a.credential_secret,a.postgres_secret):raise ValueError('Output must not overwrite input Secrets')
    kube=['kubectl','-n',a.namespace]
    def read(name):return {k:base64.b64decode(v).decode() for k,v in json.loads(run(kube+['get','secret',name,'-o','json']))['data'].items()}
    credentials=read(a.credential_secret);pg=read(a.postgres_secret)
    config.update(AWS_ACCESS_KEY_ID=credentials['access-key'],AWS_SECRET_ACCESS_KEY=credentials['secret-key'],PGHOST='localhost',PGPORT='5432',PGDATABASE='postgres',PGUSER=pg['superuser-username'],PGPASSWORD=pg['superuser-password'])
    obj=dict(apiVersion='v1',kind='Secret',metadata=dict(name=a.output_secret,namespace=a.namespace),stringData={'.walg.env':walg_environment(config)})
    if a.apply:run(kube+['apply','-f','-'],json.dumps(obj))
    print('WAL-G Secret '+('applied' if a.apply else 'validated; dry run')+'; credential values omitted')

if __name__=='__main__':
    try:main()
    except Exception as exc:raise SystemExit('Configuration stopped: '+type(exc).__name__)
