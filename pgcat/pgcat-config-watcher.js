const fs = require('fs');
const fsp = fs.promises;
const chokidar = require('chokidar');
const yaml = require('js-yaml');
const {log} = require('./logger');

const CONFIG_PATH = process.env.PGCAT_CONFIG_SOURCE || '/config/pgcat.yaml';
const OUTPUT_PATH = process.env.PGCAT_CONFIG_DEST || '/etc/pgcat/pgcat.toml';

const DEFAULT_CONFIG = `
general:
  PGCAT_PORT: '5432'
  PGCAT_SUPERUSER_USERNAME: postgres
  PGCAT_SUPERUSER_PASSWORD: mmm
  ENABLE_PROMETHEUS: false
  PROMETHEUS_EXPORTER_PORT: 9930
DBS:
  - NAME: postgres
    POOL_MODE: session
    PRIMARY_READ: false
    SHARDING_FUNCTION: pg_bigint_hash
    users:
      - USER_NAME: postgres
        PASSWORD: mmm
        POOL_SIZE: 9
        STATEMENT_TIMEOUT: 0
    shards:
      - MASTER_HOST: patronidemo-master
        MASTER_PORT: '5432'
        REPLICA_HOST: patronidemo-replica
        REPLICA_PORT: '5432'
`;

//stop 0.1: convert json config to pgcat config format
function generatePgcatConfig(input) {
  const general = input.general;
  const dbs = input.DBS;

  let config = `[general]
host = "0.0.0.0"
autoreload = 15000
port = ${general.PGCAT_PORT}
enable_prometheus_exporter = ${general.ENABLE_PROMETHEUS ?? false}
prometheus_exporter_port = ${general.PROMETHEUS_EXPORTER_PORT ?? 9930}
connect_timeout = 5000
healthcheck_timeout = 1000
healthcheck_delay = 30000
shutdown_timeout = 60000
log_client_connections = false
log_client_disconnections = false
admin_username = "${general.PGCAT_SUPERUSER_USERNAME}"
admin_password = "${general.PGCAT_SUPERUSER_PASSWORD}"
`;

  dbs.forEach((db) => {
    config += `
[pools.${db.NAME}]
pool_mode = "${db.POOL_MODE ?? "session"}"
default_role = "any"
query_parser_enabled = true
query_parser_read_write_splitting = true
primary_reads_enabled = ${db.PRIMARY_READ ?? false}
sharding_function = "${db.SHARDING_FUNCTION ?? "pg_bigint_hash"}"
`;

    db.users.forEach((user, index) => {
      config += `
[pools.${db.NAME}.users.${index}]
username = "${user.USER_NAME}"
password = "${user.PASSWORD}"
pool_size = ${user.POOL_SIZE}
statement_timeout = ${user.STATEMENT_TIMEOUT || 0}
`;
    });

    db.shards.forEach((shard, index) => {
      config += `
[pools.${db.NAME}.shards.${index}]
servers = [
  [ "${shard.MASTER_HOST}", ${shard.MASTER_PORT}, "primary" ],
  [ "${shard.REPLICA_HOST}", ${shard.REPLICA_PORT}, "replica" ],
]
database = "${db.NAME}"
`;
    });
  });

  return config.trim();
}

// Step 1: Create default config if missing
function ensureConfigExists() {
  if (!fs.existsSync(CONFIG_PATH)) {
    log('error', `Config not found. Creating default at ${CONFIG_PATH}`);
    fs.writeFileSync(CONFIG_PATH, DEFAULT_CONFIG, 'utf8');
  }
}

// Step 2: Read config and generate output
async function applyConfig() {
  try {
    const yamlText = await fsp.readFile (CONFIG_PATH, 'utf8');
    const config = yaml.load(yamlText);
    log('info', 'Config loaded.');
    log('debug' , 'json confile loaded is : ' , {config})
    const pgCatConfig = generatePgcatConfig(config)
    await fsp.writeFile(OUTPUT_PATH, pgCatConfig , 'utf8');
    log('info', 'Updated output', { outputPath: OUTPUT_PATH });
    log('debug' , 'pgcat config loaded' , {pgCatConfig})
  } catch (err) {
    log('error', 'Error reading or applying config', { error: err.message });
  }
}

// Step 3: Watch for changes
function watchConfig() {
  chokidar.watch(CONFIG_PATH).on('change', () => {
    log('warn', 'Config changed — reapplying...');
    applyConfig();
  });
}

// Run all steps
ensureConfigExists();
applyConfig().then(()=>{
  watchConfig();
})

  