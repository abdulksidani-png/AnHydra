/**
 * The contract between this UI and the AnHydra backend.
 *
 * This mirrors `ScoreResponse` in app/main.py exactly — field names are the
 * backend's snake_case, deliberately left untranslated so the two files can
 * be diffed by eye. Nothing here is invented: if a value isn't in the API
 * response, the UI doesn't show it.
 *
 * Endpoint: POST /score  { "sequence": "..." }
 */

/** The family call. `predict()` returns POSITIVE above 0.5, else "other_idp". */
export type FamilyLabel = 'protective' | 'other_idp';

/** The nine interpretable features from features.py `Features.as_dict()`. */
export interface FeatureValues {
  length: number;
  fraction_charged: number;
  net_charge_per_residue: number;
  mean_hydropathy: number;
  glycine: number;
  serine: number;
  histidine: number;
  gly_ser_his: number;
  low_complexity: number;
}

/** [feature_name, signed contribution] — standardized value x logistic coefficient. */
export type FeatureContribution = [string, number];

export interface ScoreRequest {
  sequence: string;
}

export interface ScoreResponse {
  /** 0–1. Always P(protective) — never the negative class. */
  score: number;
  label: FamilyLabel;
  /** sequence_id of the nearest known protective sequence, or null. */
  nearest_homolog: string | null;
  /** Top 3 drivers by absolute contribution. Sign matters. */
  top_features: FeatureContribution[];
  features: FeatureValues;
  /** Gemini readout, or the offline template fallback. One block of prose. */
  explanation: string;
}

/** GET /health */
export interface HealthResponse {
  status: string;
  model_trained: boolean;
  /** True when the server requires an Auth0 sign-in for /score. */
  auth_required?: boolean;
}

export type ScreenErrorKind =
  /** Failed our own check before sending, or the backend returned 400/422. */
  | 'validation'
  /** 503 — models.joblib is missing on the server. */
  | 'model_untrained'
  /** Couldn't reach the backend at all. */
  | 'network'
  /** 5xx other than 503. */
  | 'server'
  /** Signed in, but the token provider is not installed yet. Transient. */
  | 'auth_pending'
  /** 401 — no credential or it expired. Offer re-login; never loop. */
  | 'auth_expired'
  /** 403 — authenticated, but this account is not admitted. */
  | 'auth_denied';

export class ScreenError extends Error {
  constructor(
    message: string,
    public readonly kind: ScreenErrorKind,
  ) {
    super(message);
    this.name = 'ScreenError';
  }
}
