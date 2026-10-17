import type { ScreenErrorKind } from '../types';

interface ErrorBannerProps {
  message: string;
  kind: ScreenErrorKind;
  onRetry?: () => void;
}

/**
 * Errors are shown as errors. In particular a 503 (model not loaded) is never
 * dressed up or replaced with sample data: the backend returns it precisely so
 * that nobody sees a fabricated score, and the UI honours that.
 */
export function ErrorBanner({ message, kind, onRetry }: ErrorBannerProps) {
  const heading =
    kind === 'model_untrained'
      ? 'The server cannot score yet.'
      : kind === 'network'
        ? 'Could not reach the backend.'
        : kind === 'validation'
          ? 'That sequence needs a change.'
          : 'The backend errored.';

  return (
    <div className="banner banner--error" role="alert">
      <span className="banner__text">
        <strong>{heading}</strong> {message}
        {kind === 'model_untrained' && (
          <span className="banner__hint">
            {' '}
            No score is shown rather than a made-up one.
          </span>
        )}
      </span>
      {onRetry && kind !== 'validation' && (
        <button type="button" className="btn btn--chip" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function MockBanner() {
  return (
    <p className="banner banner--mock" role="status">
      <span className="banner__text">
        <strong>Fixture mode.</strong> <code>VITE_USE_MOCK=true</code>, so this
        card shows sample data and no request was sent. Unset it to screen for
        real.
      </span>
    </p>
  );
}

export function UntrainedWarning() {
  return (
    <p className="banner banner--mock" role="status">
      <span className="banner__text">
        <strong>Heads up.</strong> The backend is reachable but reports{' '}
        <code>model_trained: false</code>, so screening will return a 503 until{' '}
        <code>data/models.joblib</code> is on the server.
      </span>
    </p>
  );
}

export function EmptyState() {
  return (
    <section className="card empty">
      <h2 className="empty__title">Nothing screened yet</h2>
      <p className="empty__body">
        Paste an amino-acid sequence above and AnHydra will score it for
        CAHS-like, desiccation-protective family character — then show you
        which sequence features drove that score.
      </p>
    </section>
  );
}

export function LoadingState() {
  return (
    <section className="card" aria-busy="true" aria-live="polite">
      <p className="card__label">Scoring…</p>
      <span className="sr-only">Screening the sequence.</span>
      <div className="skeleton skeleton--title" />
      <div className="skeleton skeleton--line" style={{ width: '38%' }} />
      <div className="skeleton skeleton--bar" />
      <div className="skeleton skeleton--line" style={{ width: '72%' }} />
      <div className="skeleton skeleton--line" style={{ width: '64%' }} />
      <p className="card__lede" style={{ margin: '14px 0 0' }}>
        Embedding with ESM-2 on CPU — a long sequence can take a few seconds.
      </p>
    </section>
  );
}
