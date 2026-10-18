// Run: node --test deploy/auth0/actions.test.cjs
// Simulates Auth0 events against the two Actions, without a tenant.
const test = require('node:test');
const assert = require('node:assert/strict');
const postLogin = require('./post-login.js');
const preRegistration = require('./pre-user-registration.js');

const NS = 'https://anhydra.work/claims/';
const API = { identifier: 'https://anhydra.work/api' };
const SECRETS = { ALLOWED_EDU_EMAILS: 'Vitor@UFL.edu, gayathri@ufl.edu\nbenjamin@ufl.edu' };
const GOOGLE = { name: 'google-oauth2', strategy: 'google-oauth2' };
const DB = { name: 'Username-Password-Authentication', strategy: 'auth0' };

async function login({ connection, email, verified = true, secrets = SECRETS, resource_server = API }) {
  const result = { denied: null, access: {}, id: {} };
  const api = {
    access: { deny: (reason) => { result.denied = reason; } },
    accessToken: { setCustomClaim: (k, v) => { result.access[k] = v; } },
    idToken: { setCustomClaim: (k, v) => { result.id[k] = v; } },
  };
  await postLogin.onExecutePostLogin(
    { connection, user: { email, email_verified: verified }, secrets, resource_server }, api);
  return result;
}

test('Google login gets google admission on the API access token only', async () => {
  const r = await login({ connection: GOOGLE, email: 'anyone@gmail.com' });
  assert.equal(r.denied, null);
  assert.deepEqual(r.access, { [NS + 'token_kind']: 'user_access', [NS + 'admission']: 'google' });
  assert.deepEqual(r.id, {}, 'claims must never go into ID tokens');
});

test('approved, verified .edu email gets verified_edu (case and spacing ignored)', async () => {
  const r = await login({ connection: DB, email: ' vitor@ufl.EDU ' });
  assert.equal(r.denied, null);
  assert.equal(r.access[NS + 'admission'], 'verified_edu');
});

for (const [why, args, message] of [
  ['unlisted .edu', { connection: DB, email: 'stranger@ufl.edu' }, /approved list/],
  ['unverified .edu', { connection: DB, email: 'gayathri@ufl.edu', verified: false }, /Verify your email/],
  ['non-.edu email', { connection: DB, email: 'vitor@gmail.com' }, /approved .edu/],
  ['lookalike domain', { connection: DB, email: 'x@ufl.edu.evil.com' }, /approved .edu/],
  ['empty approved list', { connection: DB, email: 'vitor@ufl.edu', secrets: {} }, /approved list/],
  ['some other connection', { connection: { name: 'windowslive', strategy: 'windowslive' }, email: 'a@ufl.edu' }, /not enabled/],
  ['google name but wrong strategy', { connection: { name: 'google-oauth2', strategy: 'auth0' }, email: 'a@gmail.com' }, /approved .edu/],
]) {
  test(`refused: ${why}`, async () => {
    const r = await login(args);
    assert.match(r.denied, message);
    assert.deepEqual(r.access, {});
  });
}

test('a login for some other API gets no AnHydra claims', async () => {
  const r = await login({ connection: GOOGLE, email: 'a@gmail.com', resource_server: { identifier: 'https://other/api' } });
  assert.equal(r.denied, null);
  assert.deepEqual(r.access, {});
  const none = await login({ connection: GOOGLE, email: 'a@gmail.com', resource_server: null });
  assert.deepEqual(none.access, {});
});

test('API_AUDIENCE secret overrides the default audience', async () => {
  const r = await login({ connection: GOOGLE, email: 'a@gmail.com', secrets: { API_AUDIENCE: 'https://x/api' },
                          resource_server: { identifier: 'https://x/api' } });
  assert.equal(r.access[NS + 'admission'], 'google');
});

test('sign-up only for approved .edu addresses', async () => {
  for (const [email, ok] of [['benjamin@ufl.edu', true], ['BENJAMIN@ufl.edu', true],
                             ['stranger@ufl.edu', false], ['vitor@gmail.com', false], ['', false]]) {
    let denied = null;
    await preRegistration.onExecutePreUserRegistration(
      { user: { email }, secrets: SECRETS }, { access: { deny: (code, msg) => { denied = [code, msg]; } } });
    assert.equal(denied === null, ok, email);
  }
});

// Emits the claims for the Python end-to-end check (tests that the backend accepts them).
test('emit claims for backend check', async () => {
  if (!process.env.EMIT_CLAIMS) return;
  const google = await login({ connection: GOOGLE, email: 'a@gmail.com' });
  const edu = await login({ connection: DB, email: 'vitor@ufl.edu' });
  require('node:fs').writeFileSync(process.env.EMIT_CLAIMS, JSON.stringify([google.access, edu.access]));
});
