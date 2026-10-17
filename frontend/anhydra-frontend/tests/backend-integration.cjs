// Invoked by pytest against an isolated FastAPI + PostgreSQL service.
const assert = require('node:assert/strict');
const loadModules = require('./load.cjs');

async function main() {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  const { backend, tokens } = JSON.parse(input);
  process.env.VITE_PROXY_TARGET = backend;
  const { createServer } = await import('vite');
  const vite = await createServer({ server: { host: '127.0.0.1', port: 0, strictPort: false }, logLevel: 'error' });
  try {
    await vite.listen();
    const origin = `http://127.0.0.1:${vite.httpServer.address().port}`;
    const load = loadModules({ VITE_API_BASE: origin });
    const token = load('auth/token.ts');
    const account = load('auth/account.ts');
    const client = load('api/client.ts');
    token.setAuthRequired(true);
    token.setAccessTokenProvider(async () => tokens.valid, 'integration-user');
    const first = (await account.fetchAccount()).profile;
    assert.match(first.id, /^[0-9a-f-]{36}$/);
    assert.equal(first.email, null);
    assert.equal((await account.fetchAccount()).profile.id, first.id);
    const result = await client.scoreSequence({ sequence: '>record\n' + 'A'.repeat(40) });
    assert.equal(result.isMock, false);
    assert.equal(result.data.score, 0.7);
    assert.equal(result.data.features.length, 40);
    for (const [name, kind] of [['expired', 'expired'], ['denied', 'denied'], ['disabled', 'denied']]) {
      token.setAccessTokenProvider(async () => tokens[name], name);
      await assert.rejects(account.fetchAccount(), error => error.kind === kind);
    }
    await assert.rejects(client.scoreSequence({ sequence: 'A'.repeat(40) }), error => error.kind === 'auth_denied');
    assert.equal((await client.checkHealth()).status, 'ok');
    assert.equal((await fetch(origin + '/me')).status, 401);
    console.log('Frontend -> Vite proxy -> FastAPI -> PostgreSQL integration passed.');
  } finally {
    await vite.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
