CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '123456';
SELECT pg_create_physical_replication_slot('replication_slot');
-- CREATE USER barman PASSWORD 'b123';
-- CREATE USER barman_streamer PASSWORD 'bs123';

--Barman configs
-- GRANT EXECUTE ON FUNCTION pg_start_backup(text, boolean, boolean) TO barman; 
-- GRANT EXECUTE ON FUNCTION pg_stop_backup() TO barman;
-- GRANT EXECUTE ON FUNCTION pg_stop_backup(boolean, boolean) TO barman;
-- GRANT EXECUTE ON FUNCTION pg_switch_wal() TO barman;
-- GRANT EXECUTE ON FUNCTION pg_create_restore_point(text) TO barman;

-- GRANT pg_read_all_settings TO barman
-- GRANT pg_read_all_stats TO barman
-- GRANT connect on database postgres TO barman
-- SELECT pg_create_physical_replication_slot('barman_slot');

