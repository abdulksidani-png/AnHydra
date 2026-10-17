const { test } = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { create, act } = require('react-test-renderer');
const loadModules = require('./load.cjs');

const profile = { id: '9cf783d6-b568-47a6-8b61-a4ff3af678ea', display_name: null,
  email: null, email_verified: false, created_at: '2026-10-17T12:00:00Z' };
const response = (body, status = 200) => ({ ok: status === 200, status, json: async () => body });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('me and score use the same bearer token and normalized API origin; health is public', async () => {
  const requests = [];
  const load = loadModules({ VITE_API_BASE: 'https://api.example/' }, async (url, options) => {
    requests.push({ url, options });
    return response(url.endsWith('/me') ? profile : { score: 0.7 });
  });
  const token = load('auth/token.ts');
  token.setAuthRequired(true);
  token.setAccessTokenProvider(async () => 'controlled-token', 'subject');
  const account = await load('auth/account.ts').fetchAccount();
  assert.equal(account.profile.email, null);
  assert.equal(load('auth/account.ts').accountLabel(account.profile), 'Signed in');
  const client = load('api/client.ts');
  const sequence = '>record\n' + 'A'.repeat(40);
  await client.scoreSequence({ sequence });
  await client.checkHealth();
  assert.deepEqual(requests.map(r => r.url), ['https://api.example/me', 'https://api.example/score', 'https://api.example/health']);
  assert.equal(requests[0].options.headers.Authorization, 'Bearer controlled-token');
  assert.equal(requests[1].options.headers.Authorization, 'Bearer controlled-token');
  assert.equal(JSON.parse(requests[1].options.body).sequence, sequence);
  assert.equal(requests[2].options, undefined);
});

test('the frontend enforces the backend sequence boundary', () => {
  const client = loadModules()('api/client.ts');
  assert.equal(client.validateSequence('A'.repeat(1022)), null);
  assert.match(client.validateSequence('A'.repeat(1023)), /limit is 1022/);
  assert.match(client.validateSequence('A'.repeat(19)), /at least 20/);
  assert.match(client.validateSequence('A'.repeat(40) + 'X'), /standard/);
  assert.match(client.validateSequence('>a\nAAAA\n>b\nAAAA'), /one sequence/);
});

test('missing token provider cannot send unauthenticated requests', async () => {
  const load = loadModules({}, () => { throw new Error('Unexpected network request'); });
  load('auth/token.ts').setAuthRequired(true);
  await assert.rejects(load('auth/account.ts').fetchAccount(), e => e.kind === 'failed');
  await assert.rejects(load('api/client.ts').scoreSequence({ sequence: 'A'.repeat(40) }), e => e.kind === 'auth_pending');
});

for (const [status, accountKind, screenKind] of [[401, 'expired', 'auth_expired'], [403, 'denied', 'auth_denied'], [503, 'unavailable', 'unavailable']]) {
  test(`${status} has the correct account and scoring state`, async () => {
    const load = loadModules({}, async () => response({ detail: 'Safe backend message' }, status));
    await assert.rejects(load('auth/account.ts').fetchAccount(), e => e.kind === accountKind);
    await assert.rejects(load('api/client.ts').scoreSequence({ sequence: 'A'.repeat(40) }), e => e.kind === screenKind);
  });
}

test('identity changes invalidate pending token acquisition and account responses', async () => {
  const pending = deferred();
  const load = loadModules({}, async () => pending.promise);
  const token = load('auth/token.ts');
  token.setAuthRequired(true);
  const acquisition = deferred();
  token.setAccessTokenProvider(() => acquisition.promise, 'old');
  const headers = token.authorizationHeaders();
  token.clearAccessTokenProvider();
  acquisition.resolve('old-token');
  await assert.rejects(headers, e => e.reason === 'identity_changed');
  token.setAccessTokenProvider(async () => 'current-token', 'current');
  const account = load('auth/account.ts').fetchAccount();
  await Promise.resolve();
  token.clearAccessTokenProvider();
  pending.resolve(response(profile));
  await assert.rejects(account, e => e.kind === 'failed');
});

test('account hook hides the previous profile on identity change and ignores late responses', async () => {
  const requests = [];
  const load = loadModules({}, () => { const p = deferred(); requests.push(p); return p.promise; });
  const token = load('auth/token.ts');
  token.setAuthRequired(true);
  const { useAccount } = load('hooks/useAccount.ts');
  const renders = [];
  function Probe({ who, epoch }) { const state = useAccount(who, epoch); renders.push({ who, ...state }); return null; }
  let root;
  let epoch = token.setAccessTokenProvider(async () => 'a', 'a');
  await act(async () => { root = create(React.createElement(Probe, { who: 'a', epoch })); });
  await act(async () => { requests[0].resolve(response(profile)); });
  assert.equal(renders.at(-1).status, 'ready');
  epoch = token.setAccessTokenProvider(async () => 'b', 'b');
  await act(async () => { root.update(React.createElement(Probe, { who: 'b', epoch })); });
  assert.ok(renders.filter(r => r.who === 'b').every(r => r.profile === null));
  // Same-subject provider replacement must restart resolution too.
  epoch = token.setAccessTokenProvider(async () => 'b-new', 'b');
  await act(async () => { root.update(React.createElement(Probe, { who: 'b', epoch })); });
  await act(async () => { requests[1].resolve(response(profile)); });
  assert.equal(renders.at(-1).profile, null);
  await act(async () => { requests[2].resolve(response({ ...profile, id: 'second-account' })); });
  assert.equal(renders.at(-1).profile.id, 'second-account');
  token.clearAccessTokenProvider();
  await act(async () => { root.update(React.createElement(Probe, { who: null, epoch: null })); });
  assert.equal(renders.at(-1).profile, null);
  await act(async () => { root.unmount(); });
});

test('anonymous mode is explicit, development-only, and refuses partial auth configuration', () => {
  const state = env => loadModules(env)('auth/config.ts').authState.kind;
  assert.equal(state({}), 'misconfigured');
  assert.equal(state({ DEV: false, VITE_AUTH0_ALLOW_ANONYMOUS: 'true' }), 'misconfigured');
  assert.equal(state({ DEV: true, VITE_AUTH0_ALLOW_ANONYMOUS: 'true' }), 'anonymous');
  assert.equal(state({ DEV: true, VITE_AUTH0_ALLOW_ANONYMOUS: 'true', VITE_AUTH0_DOMAIN: 'example.auth0.com' }), 'misconfigured');
});

test('fixture mode cannot replace a production service failure', async () => {
  const load = loadModules({ DEV: false, VITE_USE_MOCK: 'true' }, async () => response({ detail: 'Unavailable' }, 503));
  await assert.rejects(load('api/client.ts').scoreSequence({ sequence: 'A'.repeat(40) }), e => e.kind === 'unavailable');
});
