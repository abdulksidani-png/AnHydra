/**
 * The single place access tokens are acquired.
 *
 * Both /score and /me go through `authorizationHeaders()`, so there is one
 * token path to reason about rather than two that can drift apart.
 *
 * Two lifecycle problems this module exists to solve:
 *
 * 1. A request must not race ahead of the provider. Between Auth0 reporting
 *    `isAuthenticated` and App installing the provider there is a render or
 *    two; a request sent in that window would go out unauthenticated and come
 *    back 401. When auth is required and no provider is installed, we fail
 *    with `not_ready` instead of sending the request.
 *
 * 2. A response must not outlive its identity. Every install/clear bumps an
 *    epoch; a token acquired under an old epoch is refused, so a slow /me for
 *    a signed-out user cannot populate the next session.
 *
 * Tokens are never logged, stored, or returned to callers — only the finished
 * Authorization header leaves this module.
 */

export type TokenFailure =
  /** Auth is required but the provider has not been installed yet. */
  | 'not_ready'
  /** The signed-in identity changed while we were acquiring a token. */
  | 'identity_changed'
  /** Auth0 could not produce a token — usually an expired session. */
  | 'expired';

export class TokenError extends Error {
  constructor(public readonly reason: TokenFailure) {
    super(reason);
    this.name = 'TokenError';
  }
}

type TokenProvider = () => Promise<string | undefined>;

let provider: TokenProvider | null = null;
let identity: string | null = null;
let epoch = 0;

/** True when the app is running in a mode that requires a signed-in user. */
let authRequired = false;

export function setAuthRequired(required: boolean): void {
  authRequired = required;
}

/**
 * Install the provider for `who` (the Auth0 subject). Returns the new epoch,
 * which callers can compare against `tokenEpoch()` to detect a change.
 */
export function setAccessTokenProvider(next: TokenProvider, who: string): number {
  provider = next;
  identity = who;
  epoch += 1;
  return epoch;
}

/** Remove the provider — on sign-out, identity change, or unmount. */
export function clearAccessTokenProvider(): void {
  provider = null;
  identity = null;
  epoch += 1;
}

export function tokenEpoch(): number {
  return epoch;
}

export function currentIdentity(): string | null {
  return identity;
}

/**
 * The Authorization header for an API call, or `{}` when the app is running
 * without sign-in (the explicit dev-only anonymous mode).
 */
export async function authorizationHeaders(): Promise<Record<string, string>> {
  if (!authRequired) return {};

  if (!provider) throw new TokenError('not_ready');

  const mine = epoch;
  let token: string | undefined;
  try {
    token = await provider();
  } catch {
    throw new TokenError('expired');
  }

  // The provider may have been replaced while we awaited it.
  if (mine !== epoch) throw new TokenError('identity_changed');
  if (!token) throw new TokenError('expired');

  return { Authorization: `Bearer ${token}` };
}
