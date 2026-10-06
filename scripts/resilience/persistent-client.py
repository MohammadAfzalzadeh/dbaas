"""Runs inside an independent lab pod. Emits outcomes, never connection credentials."""
import json
import os
import sys
import time
from datetime import datetime, timezone
import psycopg2

identity=sys.argv[1];host=sys.argv[2];duration=float(sys.argv[3]);interval=float(sys.argv[4])
start=time.monotonic();connection=None;number=0;connections=0
while time.monotonic()-start<duration and not os.path.exists('/tmp/stop-'+identity):
    at=time.monotonic();key=identity+'-'+str(number);number+=1
    item=dict(timestamp=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(at-start,6),id=key)
    try:
        if connection is None:
            connection=psycopg2.connect(host=host,dbname='postgres',user='postgres',password=os.environ['PGPASSWORD'],connect_timeout=3,
                options='-c statement_timeout=3000',keepalives=1,keepalives_idle=3,keepalives_interval=1,keepalives_count=2,tcp_user_timeout=5000)
            connections+=1
        with connection.cursor() as cursor:cursor.execute('INSERT INTO resilience_ledger(id) VALUES (%s)',(key,))
        connection.commit();item['success']=True
    except Exception as error:
        item.update(success=False,error=type(error).__name__)
        if connection:
            try:connection.close()
            except Exception:pass
        connection=None
    item.update(latency_seconds=round(time.monotonic()-at,6),connections=connections)
    print(json.dumps(item),flush=True)
    time.sleep(interval)
if connection:connection.close()
