const { test } = require('node:test');
const assert = require('node:assert/strict');

test('production build configuration rejects missing auth and development bypasses', async () => {
  const { loadConfigFromFile } = await import('vite');
  const settings = { VITE_AUTH0_DOMAIN: 'integration.invalid', VITE_AUTH0_CLIENT_ID: 'test-spa',
    VITE_AUTH0_AUDIENCE: 'test-api', VITE_AUTH0_ALLOW_ANONYMOUS: 'false', VITE_USE_MOCK: 'false' };
  const before = Object.fromEntries(Object.keys(settings).map(key => [key, process.env[key]]));
  const config = () => loadConfigFromFile({ command: 'build', mode: 'production' }, undefined, undefined, 'silent');
  try {
    Object.assign(process.env, settings);
    process.env.VITE_AUTH0_AUDIENCE = '';
    await assert.rejects(config(), /Missing production auth settings/);
    Object.assign(process.env, settings, { VITE_AUTH0_ALLOW_ANONYMOUS: 'true' });
    await assert.rejects(config(), /cannot use anonymous access/);
    Object.assign(process.env, settings, { VITE_USE_MOCK: 'true' });
    await assert.rejects(config(), /cannot use anonymous access/);
  } finally {
    for (const [key, value] of Object.entries(before)) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
});
