#!/bin/bash
# sleep 100 
PGDATA=${1:-/var/lib/postgresql/data}
BACKUP_ENABLE=${2:-false}
# exec /wal-g/wal-g backup-fetch "$PGDATA" --config /wal-g-credentials/.walg.env LATEST

# Attempt to fetch latest backup
echo "Trying to fetch latest WAL-G backup..."
if $BACKUP_ENABLE ;then
    exec /wal-g/wal-g backup-fetch "$PGDATA" --config /wal-g-credentials/.walg.env LATEST;
    echo "Backup restored successfully."
else
    echo "Initializing new database..."
    initdb -D "$PGDATA"
fi

