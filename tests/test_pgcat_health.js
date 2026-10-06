'use strict';
const assert = require('assert');
const {check} = require('../pgcat/pgcat-health');
const config = {general: {PGCAT_PORT: 5432}, DBS: [{NAME: 'postgres', users: [{USER_NAME: 'postgres', PASSWORD: 'synthetic-only'}]}]};
assert(check(config, (cmd, args, options) => {
  assert.equal(cmd, 'psql');
  assert(!args.includes('synthetic-only'));
  assert.equal(options.env.PGPASSWORD, 'synthetic-only');
  assert.equal(options.timeout, 6000);
  return {status: 0, stdout: '1\n'};
}));
assert(!check(config, () => ({status: 1, stdout: ''})));
assert(!check(config, () => ({status: null, error: new Error('timeout')})));
assert(!check(config, () => ({status: 0, stdout: 'wrong'})));
console.log('PASS 4 PgCat SQL readiness cases');
