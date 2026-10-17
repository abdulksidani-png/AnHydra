import { TokenError, authorizationHeaders, tokenEpoch } from './token';
import { API_BASE } from '../api/config';

/**
 * The application account, from `GET /me`.
 *
 * `id` is AnHydra's own UUID for the person, not the Auth0 subject. Names and
 * emails are nullable — Auth0 does not guarantee either, and a social provider
 * may withhold both — so every consumer must handle null rather than printing
 * `undefined`. `email_verified` describes the stored contact address; it says
 * nothing about whether the account may use the app, which only the backend
 * decides.
 */
export interface AccountProfile {
  id: string;
  display_name: string | null;
  email: string | null;
  email_verified: boolean;
  created_at: string;
}

export type AccountFailureKind =
  /** 401 — no credential, or it expired. Offer re-login, do not loop. */
  | 'expired'
  /** 403 — authenticated but this account is not admitted. */
  | 'denied'
  /** 503 — a service the backend needs is down. Retryable; never a login loop. */
  | 'unavailable'
  /** Network, 5xx, or a malformed response. Retryable. */
  | 'failed';

export class AccountError extends Error {
  constructor(
    public readonly kind: AccountFailureKind,
    message: string,
  ) {
    super(message);
    this.name = 'AccountError';
  }
}

const TIMEOUT_MS = 15_000;

/**
 * Resolve the application account for the current token.
 *
 * Returns the profile plus the token epoch it was fetched under, so the caller
 * can discard a response whose identity has since changed.
 */
export async function fetchAccount(): Promise<{ profile: AccountProfile; epoch: number }> {
  const epoch = tokenEpoch();

  let headers: Record<string, string>;
  try {
    headers = await authorizationHeaders();
  } catch (error) {
    if (error instanceof TokenError) {
      // not_ready and identity_changed are lifecycle races, not user errors;
      // the caller retries once the provider settles.
      throw new AccountError(
        error.reason === 'expired' ? 'expired' : 'failed',
        error.reason === 'expired'
          ? 'Your session has expired.'
          : 'Still signing you in.',
      );
    }
    throw new AccountError('failed', 'Could not prepare the request.');
  }

  let response: Response;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    response = await fetch(`${API_BASE}/me`, {
      headers,
      signal: controller.signal,
    }).finally(() => clearTimeout(timer));
  } catch {
    throw new AccountError('failed', 'Could not reach the server.');
  }

  if (response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw new AccountError('failed', 'The server sent a response we could not read.');
    }
    if (epoch !== tokenEpoch()) throw new AccountError('failed', 'Your session changed. Try again.');
    return { profile: normalize(body), epoch };
  }

  const detail = await safeDetail(response);

  switch (response.status) {
    case 401:
      throw new AccountError('expired', detail ?? 'Your session has expired.');
    case 403:
      throw new AccountError('denied', detail ?? 'This account does not have access.');
    case 503:
      throw new AccountError(
        'unavailable',
        detail ?? 'A service AnHydra needs is temporarily unavailable.',
      );
    default:
      throw new AccountError('failed', detail ?? `The server returned ${response.status}.`);
  }
}

/** Coerce the payload into the documented shape without trusting it blindly. */
function normalize(body: unknown): AccountProfile {
  const raw = (body ?? {}) as Record<string, unknown>;
  const id = typeof raw.id === 'string' ? raw.id : '';
  if (!id) throw new AccountError('failed', 'The server did not return an account id.');

  return {
    id,
    display_name: typeof raw.display_name === 'string' ? raw.display_name : null,
    email: typeof raw.email === 'string' ? raw.email : null,
    email_verified: raw.email_verified === true,
    created_at: typeof raw.created_at === 'string' ? raw.created_at : '',
  };
}

/** FastAPI's `{ "detail": "..." }`. Never surface internal exception text. */
async function safeDetail(response: Response): Promise<string | null> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string' && body.detail.length <= 300) return body.detail;
  } catch {
    /* no JSON body */
  }
  return null;
}

/** What to show for a person, given nullable fields. */
export function accountLabel(profile: AccountProfile): string {
  return profile.display_name || profile.email || 'Signed in';
}
