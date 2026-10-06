'use strict';
// Readiness checks a real query through this pod's PgCat listener.
const fs = require('fs');
const yaml = require('js-yaml');
const {spawnSync} = require('child_process');
function check(config, execute = spawnSync) {
  const db = config.DBS[0];
  const user = db.users[0];
  const result = execute('psql', ['-X', '-w', '-h', '127.0.0.1', '-p',
    String(config.general.PGCAT_PORT), '-U', user.USER_NAME, '-d', db.NAME,
    '-Atqc', 'SELECT 1'], {
    env: {...process.env, PGPASSWORD: String(user.PASSWORD), PGCONNECT_TIMEOUT: '3',
      PGOPTIONS: '-c statement_timeout=3000'}, timeout: 6000, encoding: 'utf8',
  });
  return result.status === 0 && result.stdout.trim() === '1';
}
if (require.main === module) {
  try {
    const config = yaml.load(fs.readFileSync(process.env.PGCAT_CONFIG_SOURCE || '/config/pgcat.yaml', 'utf8'));
    process.exitCode = check(config) ? 0 : 1;
  } catch (_) { process.exitCode = 1; }
  // Never log client diagnostics or config: they can include credentials.
}
module.exports = {check};
