const fs = require('fs');
const path = require('path');

function integer(value, name, min = 0, max = Number.MAX_SAFE_INTEGER) {
  const n = Number(value);
  if (!Number.isSafeInteger(n) || n < min || n > max) throw new Error(`Invalid ${name}`);
  return n;
}
function string(value, name) {
  if (typeof value !== 'string' || !value.length) throw new Error(`Missing ${name}`);
  return JSON.stringify(value);
}
function generatePgcatConfig(input) {
  const general = input.general;
  if (!general || !Array.isArray(input.DBS) || !input.DBS.length) throw new Error('general and nonempty DBS are required');
  const lines = [
    '[general]', 'host = "0.0.0.0"', 'autoreload = 15000',
    `port = ${integer(general.PGCAT_PORT, 'port', 1, 65535)}`,
    `enable_prometheus_exporter = ${general.ENABLE_PROMETHEUS === true}`,
    `prometheus_exporter_port = ${integer(general.PROMETHEUS_EXPORTER_PORT, 'metrics port', 1, 65535)}`,
    'connect_timeout = 5000', 'healthcheck_timeout = 1000', 'healthcheck_delay = 30000',
    'shutdown_timeout = 60000', 'log_client_connections = false', 'log_client_disconnections = false',
    `admin_username = ${string(general.PGCAT_SUPERUSER_USERNAME, 'admin username')}`,
    `admin_password = ${string(general.PGCAT_SUPERUSER_PASSWORD, 'admin password')}`,
  ];
  const names = new Set();
  for (const db of input.DBS) {
    if (names.has(db.NAME)) throw new Error('Duplicate pool name');
    names.add(db.NAME);
    const pool = `pools.${string(db.NAME, 'database name')}`;
    const mode = db.POOL_MODE || 'session';
    if (!['session', 'transaction'].includes(mode)) throw new Error('Unsupported pool mode');
    if (!db.users?.length || !db.shards?.length) throw new Error('Pool users and shards are required');
    lines.push('', `[${pool}]`, `pool_mode = ${JSON.stringify(mode)}`, 'default_role = "any"',
      'query_parser_enabled = true', 'query_parser_read_write_splitting = true',
      `primary_reads_enabled = ${db.PRIMARY_READ === true}`,
      `sharding_function = ${string(db.SHARDING_FUNCTION || 'pg_bigint_hash', 'sharding function')}`);
    db.users.forEach((user, i) => lines.push('', `[${pool}.users.${i}]`,
      `username = ${string(user.USER_NAME, 'username')}`, `password = ${string(user.PASSWORD, 'password')}`,
      `pool_size = ${integer(user.POOL_SIZE, 'pool size', 1)}`,
      `statement_timeout = ${integer(user.STATEMENT_TIMEOUT || 0, 'statement timeout')}`));
    db.shards.forEach((shard, i) => {
      const servers = [`[${string(shard.MASTER_HOST, 'primary host')}, ${integer(shard.MASTER_PORT, 'primary port', 1, 65535)}, "primary"]`];
      if (shard.INCLUDE_REPLICA !== false) servers.push(`[${string(shard.REPLICA_HOST, 'replica host')}, ${integer(shard.REPLICA_PORT, 'replica port', 1, 65535)}, "replica"]`);
      lines.push('', `[${pool}.shards.${i}]`, `servers = [${servers.join(', ')}]`, `database = ${string(db.NAME, 'database name')}`);
    });
  }
  return lines.join('\n') + '\n';
}

async function main() {
  const yaml = require('js-yaml');
  const chokidar = require('chokidar');
  const {log, closeLogger} = require('./logger');
  const source = process.env.PGCAT_CONFIG_SOURCE || '/config/pgcat.yaml';
  const dest = process.env.PGCAT_CONFIG_DEST || '/etc/pgcat/pgcat.toml';
  async function apply() {
    const config = generatePgcatConfig(yaml.load(await fs.promises.readFile(source, 'utf8')));
    const temporary = `${dest}.${process.pid}.tmp`;
    try {
      await fs.promises.writeFile(temporary, config, {mode: 0o600});
      await fs.promises.rename(temporary, dest);
    } finally {
      await fs.promises.rm(temporary, {force: true});
    }
    log('info', 'PgCat configuration updated');
  }
  await apply(); // Missing/invalid initial configuration must fail the init container.
  if (process.argv.includes('--once')) return;
  let pending = Promise.resolve();
  let stopping = false;
  // Kubernetes replaces the projected directory's symlinks on Secret updates.
  const watcher = chokidar.watch(path.dirname(source), {ignoreInitial: true});
  watcher.on('all', () => {
    if (stopping) return;
    pending = pending.then(apply).catch(err => log('error', 'Configuration update failed; retaining last valid configuration', {error: "configuration operation failed"}));
  });
  async function shutdown() {
    if (stopping) return;
    stopping = true;
    // Explicit handlers also work when Node is container PID 1. Finish the
    // atomic configuration write and close handles instead of waiting for KILL.
    const deadline = setTimeout(() => process.exit(1), 5000);
    try {
      await watcher.close();
      await pending;
      await closeLogger();
      clearTimeout(deadline);
      process.exit(0);
    } catch (_) {
      clearTimeout(deadline);
      process.exit(1);
    }
  }
  process.once('SIGTERM', shutdown);
  process.once('SIGINT', shutdown);
  watcher.on('error', err => { log('error', 'Configuration watch failed', {error: "configuration operation failed"}); process.exit(1); });
}
if (require.main === module) main().catch(err => { console.error("PgCat configuration initialization failed"); process.exitCode = 1; });
module.exports = {generatePgcatConfig};
