#!/bin/bash
set -e

rm -rf /var/lib/postgresql/newdata
until PGPASSWORD=$REPLICATION_PASS pg_basebackup -h $MASTER_HOST --port=$MASTER_PORT -D /var/lib/postgresql/newdata -U replicator -Fp -Xs -P; do
  echo 'Waiting for primary to connect...'
  sleep 1s
done

chmod 0700 /var/lib/postgresql/newdata
echo 'Backup done, starting replica...'
touch /var/lib/postgresql/newdata/standby.signal
exec postgres -D /var/lib/postgresql/newdata -c config_file=/etc/postgresql/postgresql.conf  -c cluster_name=$1
