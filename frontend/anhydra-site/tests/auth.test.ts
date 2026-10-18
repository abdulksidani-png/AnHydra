import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { resolveAuthMode } from "../src/auth/config.ts";
import { AccountError, fetchAccount } from "../src/auth/account.ts";
import { TokenError, authorizationHeaders, clearAccessTokenProvider, setAccessTokenProvider, setAuthRequired } from "../src/auth/token.ts";
import { ScoreError, requestScore } from "../src/lib/protein.ts";

const AUTH0 = { VITE_AUTH0_DOMAIN: "t.example", VITE_AUTH0_CLIENT_ID: "spa", VITE_AUTH0_AUDIENCE: "api" };
const original = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = original;
  clearAccessTokenProvider();
  setAuthRequired(false);
});

test("the site runs with sign-in, explicitly without it, or not at all", () => {
  assert.equal(resolveAuthMode(AUTH0).kind, "auth0");
  assert.equal(resolveAuthMode({ VITE_PUBLIC_ACCESS: "true" }).kind, "public");
  assert.deepEqual(resolveAuthMode({}), { kind: "misconfigured", missing: Object.keys(AUTH0) });
  assert.deepEqual(resolveAuthMode({ VITE_AUTH0_DOMAIN: "t.example" }).kind, "misconfigured");
  assert.equal(resolveAuthMode({ ...AUTH0, VITE_PUBLIC_ACCESS: "true" }).kind, "misconfigured");
});

test("no request goes out before the token provider is installed", async () => {
  setAuthRequired(true);
  await assert.rejects(authorizationHeaders(), (e) => e instanceof TokenError && e.reason === "not_ready");
  let sent = false;
  globalThis.fetch = async () => ((sent = true), new Response("{}"));
  await assert.rejects(requestScore("A".repeat(40)), (e) => e instanceof ScoreError && e.status === 0);
  assert.equal(sent, false);
});

test("a token acquired for a previous identity is refused", async () => {
  setAuthRequired(true);
  let release!: (token: string) => void;
  setAccessTokenProvider(() => new Promise((resolve) => (release = resolve)));
  const pending = authorizationHeaders();
  setAccessTokenProvider(async () => "second-person");
  release("first-person");
  await assert.rejects(pending, (e) => e instanceof TokenError && e.reason === "identity_changed");
});

test("/me and /score carry the same bearer token", async () => {
  setAuthRequired(true);
  setAccessTokenProvider(async () => "token-1");
  const seen: (string | null)[] = [];
  globalThis.fetch = async (_url, init) => {
    seen.push(new Headers(init?.headers).get("Authorization"));
    return new Response(JSON.stringify({ id: "u-1", display_name: null, email: null, email_verified: false, created_at: "", score: 0.5 }));
  };
  const { profile } = await fetchAccount();
  assert.equal(profile.display_name, null);
  await requestScore("A".repeat(40));
  assert.deepEqual(seen, ["Bearer token-1", "Bearer token-1"]);
});

test("/me failures map to distinct account states", async () => {
  setAuthRequired(true);
  setAccessTokenProvider(async () => "token-1");
  for (const [status, kind] of [[401, "expired"], [403, "denied"], [503, "unavailable"], [500, "failed"]] as const) {
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: "Safe message." }), { status });
    await assert.rejects(fetchAccount(), (e) => e instanceof AccountError && e.kind === kind && e.message === "Safe message.");
  }
});
