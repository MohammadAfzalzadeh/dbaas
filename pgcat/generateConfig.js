function generatePgcatConfig(input) {
    const general = input.general;
    const dbs = input.DBS;
  
    let config = `[general]
host = "0.0.0.0"
port = ${general.PGCAT_PORT}
enable_prometheus_exporter = true
prometheus_exporter_port = 9930
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
pool_mode = "session"
default_role = "any"
query_parser_enabled = true
query_parser_read_write_splitting = true
primary_reads_enabled = false
sharding_function = "pg_bigint_hash"
  `;
  
      db.users.forEach((user, index) => {
        config += `
[pools.${db.NAME}.users.${index}]
username = "${user.USER_NAME}"
password = "${user.PASSWORD}"
pool_size = ${user.POOL_SIZE}
statement_timeout = 0
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
  
  // Example usage
  const input = {
    "general": {
      "PGCAT_PORT": "5432",
      "PGCAT_SUPERUSER_USERNAME": "postgres",
      "PGCAT_SUPERUSER_PASSWORD": "mmm"
    },
    "DBS": [
      {
        "NAME": "postgres",
        "users": [
          {
            "USER_NAME": "postgres",
            "PASSWORD": "mmm",
            "POOL_SIZE": 9
          },
          {
            "USER_NAME": "mammad",
            "PASSWORD": "123",
            "POOL_SIZE": 15
          },
        ],
        "shards": [
          {
            "MASTER_HOST": "patronidemo-master",
            "MASTER_PORT": "5432",
            "REPLICA_HOST": "patronidemo-replica",
            "REPLICA_PORT": "5432"
          },
          {
            "MASTER_HOST": "127.0.0.1",
            "MASTER_PORT": "5432",
            "REPLICA_HOST": "127.0.0.1",
            "REPLICA_PORT": "5433"
          }
        ]
      },
      {
        "NAME": "Test GPT",
        "users": [
          {
            "USER_NAME": "postgres",
            "PASSWORD": "mmm",
            "POOL_SIZE": 9
          },
          {
            "USER_NAME": "mammad",
            "PASSWORD": "123",
            "POOL_SIZE": 15
          },
        ],
        "shards": [
          {
            "MASTER_HOST": "patronidemo-master",
            "MASTER_PORT": "5432",
            "REPLICA_HOST": "patronidemo-replica",
            "REPLICA_PORT": "5432"
          },
          {
            "MASTER_HOST": "127.0.0.1",
            "MASTER_PORT": "5432",
            "REPLICA_HOST": "127.0.0.1",
            "REPLICA_PORT": "5433"
          }
        ]
      }
    ]
  };
  
  console.log(generatePgcatConfig(input));
  