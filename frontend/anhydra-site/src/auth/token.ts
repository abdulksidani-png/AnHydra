// The one place access tokens are acquired: /me and /score both go through authorizationHeaders().
//
// A request must not race ahead of the provider: with sign-in required and no provider installed
// yet, it fails with "not_ready" instead of going out unauthenticated. And a response must not
// outlive its identity: every install or clear bumps an epoch, and a token acquired under an old
// epoch is refused, so a slow request for one person cannot fill in the next person's session.
// Tokens never leave this module except inside the finished Authorization header.

export type TokenFailure = "not_ready" | "identity_changed" | "expired";

export class TokenError extends Error {
  reason: TokenFailure;
  constructor(reason: TokenFailure) {
    super(reason);
    this.reason = reason;
  }
}

type TokenProvider = () => Promise<string | undefined>;

let provider: TokenProvider | null = null;
let epoch = 0;
let required = false;

export function setAuthRequired(value: boolean): void {
  required = value;
}

export function setAccessTokenProvider(next: TokenProvider): number {
  provider = next;
  return ++epoch;
}

export function clearAccessTokenProvider(): void {
  provider = null;
  epoch += 1;
}

export function tokenEpoch(): number {
  return epoch;
}

export async function authorizationHeaders(): Promise<Record<string, string>> {
  if (!required) return {};
  if (!provider) throw new TokenError("not_ready");
  const mine = epoch;
  let token: string | undefined;
  try {
    token = await provider();
  } catch {
    throw new TokenError("expired");
  }
  if (mine !== epoch) throw new TokenError("identity_changed");
  if (!token) throw new TokenError("expired");
  return { Authorization: `Bearer ${token}` };
}
