import {
  ScreenError,
  type HealthResponse,
  type ScoreRequest,
  type ScoreResponse,
} from '../types';
import { TokenError, authorizationHeaders, tokenEpoch } from '../auth/token';
import { API_BASE } from './config';
import { mockScore } from './mock';

/**
 * Backend origin. Empty string = same origin, which is what you want once the
 * built frontend is served from the same host as the API. Set VITE_API_BASE
 * only if the UI is hosted somewhere other than the FastAPI/Caddy box.
 */

/**
 * Fixtures are OPT-IN ONLY, for working on the UI with no backend running.
 *
 * There is deliberately no automatic fallback to fixtures on failure. The
 * backend's own design rule is that it returns 503 rather than inventing a
 * number, because a fabricated score would undercut the whole project — a UI
 * that quietly swapped in sample data on error would reintroduce exactly the
 * problem the 503 exists to prevent. Errors surface as errors.
 */
const USE_MOCK = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK === 'true';

const VALID_RESIDUES = /^[ACDEFGHIKLMNPQRSTVWY]+$/;
const MIN_LENGTH = 20; // matches MIN_LENGTH in app/main.py
const MAX_LENGTH = 1022; // ESM-2 token budget, matching app/main.py
const TIMEOUT_MS = 120_000; // matches the backend deployment smoke check

/**
 * Access tokens come from src/auth/token.ts, the same path /me uses, so there
 * is one lifecycle to reason about. Failures there are lifecycle facts rather
 * than HTTP results, and map onto the screen-error kinds here.
 */
async function authHeaders(): Promise<Record<string, string>> {
  try {
    return await authorizationHeaders();
  } catch (error) {
    if (error instanceof TokenError) {
      if (error.reason === 'expired') {
        throw new ScreenError(
          'Your session has expired. Sign in again to keep screening.',
          'auth_expired',
        );
      }
      // not_ready / identity_changed: a render-order race, not the user's fault.
      throw new ScreenError('Still signing you in — try that again in a moment.', 'auth_pending');
    }
    throw new ScreenError('Could not prepare an authenticated request.', 'auth_expired');
  }
}

/**
 * Strip FASTA headers and keep only the 20 standard residues.
 * Mirrors clean_sequence() in features.py so the count shown in the UI is the
 * same count the backend will validate against.
 */
export function cleanSequence(raw: string): string {
  const body = raw
    .split('\n')
    .filter((line) => !line.trim().startsWith('>'))
    .join('');
  return body
    .toUpperCase()
    .split('')
    .filter((ch) => VALID_RESIDUES.test(ch))
    .join('');
}

/** Returns an error message, or null when the sequence is worth sending. */
export function validateSequence(raw: string): string | null {
  const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const headers = lines.flatMap((line, index) => line.startsWith('>') ? [index] : []);
  if (headers.length > 1 || (headers.length === 1 && headers[0] !== 0))
    return 'Submit one sequence or one FASTA record at a time.';
  const body = lines.filter((line) => !line.startsWith('>')).join('').replace(/\s/g, '').toUpperCase();
  if (body && !VALID_RESIDUES.test(body))
    return 'Use only the 20 standard amino-acid letters.';
  const clean = cleanSequence(raw);
  if (clean.length === 0) return 'Paste a sequence first.';
  if (clean.length < MIN_LENGTH)
    return `Need at least ${MIN_LENGTH} amino acids (got ${clean.length} valid residues).`;
  if (clean.length > MAX_LENGTH)
    return `Sequence is ${clean.length} residues; the limit is ${MAX_LENGTH}.`;
  return null;
}

export interface ScoreResult {
  data: ScoreResponse;
  /** True only when VITE_USE_MOCK=true. Never true for a real response. */
  isMock: boolean;
}

/** POST /score */
export async function scoreSequence(request: ScoreRequest): Promise<ScoreResult> {
  const problem = validateSequence(request.sequence);
  if (problem) throw new ScreenError(problem, 'validation');

  if (USE_MOCK) {
    await delay(450);
    return { data: mockScore(cleanSequence(request.sequence)), isMock: true };
  }

  const epoch = tokenEpoch();
  const auth = await authHeaders();

  let response: Response;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    response = await fetch(`${API_BASE}/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...auth },
      // The backend accepts raw or FASTA and cleans it itself; send what the
      // user typed so its own parse is the one that counts.
      body: JSON.stringify({ sequence: request.sequence }),
      signal: controller.signal,
    }).finally(() => clearTimeout(timer));
  } catch (error) {
    throw new ScreenError(
      error instanceof Error && error.name === 'AbortError'
        ? 'The backend took too long to answer. Scoring on CPU can be slow — try again.'
        : 'Could not reach the screening backend.',
      'network',
    );
  }

  if (response.ok) {
    const data = (await response.json()) as ScoreResponse;
    if (epoch !== tokenEpoch()) throw new ScreenError('Your session changed. Try again.', 'auth_pending');
    return { data, isMock: false };
  }

  const detail = await extractDetail(response);

  if (response.status === 503) {
    throw new ScreenError(
      detail ?? 'A service needed for screening is temporarily unavailable.',
      'unavailable',
    );
  }
  if (response.status === 401) {
    throw new ScreenError(
      detail ?? 'Your session has expired. Sign in again to keep screening.',
      'auth_expired',
    );
  }
  if (response.status === 403) {
    throw new ScreenError(
      detail ?? 'This account is not allowed to screen sequences.',
      'auth_denied',
    );
  }
  if (response.status === 400 || response.status === 422) {
    throw new ScreenError(detail ?? 'The backend rejected that sequence.', 'validation');
  }
  throw new ScreenError(detail ?? `Backend returned ${response.status}.`, 'server');
}

/**
 * GET /health — {status, model_trained}. Used to warn up front when the
 * server is up but cannot score, instead of letting the user discover it by
 * pasting a sequence and waiting.
 */
export async function checkHealth(): Promise<HealthResponse | null> {
  if (USE_MOCK) return { status: 'ok', model_trained: true };
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) return null;
    return (await response.json()) as HealthResponse;
  } catch {
    return null;
  }
}

/** FastAPI puts validation errors in `detail`, as a string or a list. */
async function extractDetail(response: Response): Promise<string | null> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') return body.detail;
    if (Array.isArray(body?.detail)) {
      const first = body.detail[0];
      if (typeof first?.msg === 'string') return first.msg;
    }
  } catch {
    /* no JSON body */
  }
  return null;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
