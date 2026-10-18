import { API_BASE } from "../lib/protein.ts";
import { TokenError, authorizationHeaders, tokenEpoch } from "./token.ts";

// The application account from GET /me. Auth0 says who someone is; /me says whether AnHydra will
// admit them, so screening waits for it. Names and emails are nullable.
export type AccountProfile = {
  id: string;
  display_name: string | null;
  email: string | null;
  email_verified: boolean;
  created_at: string;
};

// expired: 401, offer one explicit sign-in. denied: 403. unavailable: 503, retry and never a
// login loop. failed: network, other status, or a malformed answer; retry.
export type AccountFailure = "expired" | "denied" | "unavailable" | "failed";

export class AccountError extends Error {
  kind: AccountFailure;
  constructor(kind: AccountFailure, message: string) {
    super(message);
    this.kind = kind;
  }
}

export async function fetchAccount(): Promise<{ profile: AccountProfile; epoch: number }> {
  const epoch = tokenEpoch();
  let headers: Record<string, string>;
  try {
    headers = await authorizationHeaders();
  } catch (e) {
    const expired = e instanceof TokenError && e.reason === "expired";
    throw new AccountError(expired ? "expired" : "failed", expired ? "Your session has expired." : "Still signing you in.");
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/me`, { headers, signal: AbortSignal.timeout(15_000) });
  } catch {
    throw new AccountError("failed", "Could not reach the server.");
  }
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (res.ok) {
    const raw = (body ?? {}) as Record<string, unknown>;
    if (typeof raw.id !== "string" || !raw.id) throw new AccountError("failed", "The server did not return an account.");
    if (epoch !== tokenEpoch()) throw new AccountError("failed", "Your session changed. Try again.");
    return {
      epoch,
      profile: {
        id: raw.id,
        display_name: typeof raw.display_name === "string" ? raw.display_name : null,
        email: typeof raw.email === "string" ? raw.email : null,
        email_verified: raw.email_verified === true,
        created_at: typeof raw.created_at === "string" ? raw.created_at : "",
      },
    };
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  const message = typeof detail === "string" && detail.length <= 300 ? detail : null;
  if (res.status === 401) throw new AccountError("expired", message ?? "Your session has expired.");
  if (res.status === 403) throw new AccountError("denied", message ?? "This account does not have access.");
  if (res.status === 503) throw new AccountError("unavailable", message ?? "A service AnHydra needs is temporarily unavailable.");
  throw new AccountError("failed", message ?? `The server answered with status ${res.status}.`);
}
