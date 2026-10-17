import type { ReactNode } from 'react';
import { HydraMark } from './HydraMark';

/** Shared frame so every pre-app state looks like one family. */
function Gate({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="signin">
      <section className="signin__card card" aria-labelledby="gate-title">
        <div className="signin__brand">
          <HydraMark />
          <div>
            <h1 id="gate-title" className="masthead__title">
              AnHydra
            </h1>
            <p className="masthead__subtitle">{title}</p>
          </div>
        </div>
        {children}
      </section>
    </main>
  );
}

/**
 * A build with incomplete Auth0 settings. Deliberately a dead end: the
 * alternative — quietly serving the screener without sign-in — is the failure
 * mode this screen exists to prevent.
 */
export function ConfigurationError({
  missing,
  anonymousIgnored,
}: {
  missing: string[];
  anonymousIgnored: boolean;
}) {
  return (
    <Gate title="Not configured">
      <p className="signin__lede">
        This build is missing required sign-in settings, so it will not start.
      </p>
      <ul className="gate__list">
        {missing.map((name) => (
          <li key={name}>
            <code>{name}</code>
          </li>
        ))}
      </ul>
      {anonymousIgnored && (
        <p className="banner banner--mock" role="status">
          <span className="banner__text">
            <code>VITE_AUTH0_ALLOW_ANONYMOUS</code> is set, but it only applies
            to development builds and was ignored here.
          </span>
        </p>
      )}
      <p className="signin__fine">
        Set these at build time and rebuild. They are public settings, not
        secrets — but a client secret or Management API credential must never
        be put in a <code>VITE_</code> variable.
      </p>
    </Gate>
  );
}

/** Auth0 has authenticated someone; we are resolving their AnHydra account. */
export function AccountLoading() {
  return (
    <Gate title="Signing you in">
      <p className="signin__busy" aria-live="polite">
        Loading your account…
      </p>
    </Gate>
  );
}

/** 403 — authenticated, but the backend will not admit this account. */
export function AccessDenied({
  detail,
  onSignOut,
}: {
  detail: string;
  onSignOut: () => void;
}) {
  return (
    <Gate title="Access denied">
      <p className="signin__lede">{detail}</p>
      <p className="signin__fine">
        Signing in with a different account may work. Access is decided by the
        AnHydra backend, not by the identity provider.
      </p>
      <div className="signin__actions">
        <button type="button" className="btn btn--quiet signin__btn" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </Gate>
  );
}

/** 401 at account resolution — offer one explicit re-login, never a loop. */
export function SessionExpired({
  detail,
  onSignIn,
}: {
  detail: string;
  onSignIn: () => void;
}) {
  return (
    <Gate title="Session expired">
      <p className="signin__lede">{detail}</p>
      <div className="signin__actions">
        <button type="button" className="btn btn--primary signin__btn" onClick={onSignIn}>
          Sign in again
        </button>
      </div>
    </Gate>
  );
}

/**
 * 503 or a network failure. Retryable, and explicitly NOT a reason to bounce
 * the user back through Auth0 — that would be a redirect loop against a
 * service that is simply down.
 */
export function AccountUnavailable({
  detail,
  onRetry,
  onSignOut,
}: {
  detail: string;
  onRetry: () => void;
  onSignOut: () => void;
}) {
  return (
    <Gate title="Temporarily unavailable">
      <p className="signin__lede">{detail}</p>
      <p className="signin__fine">
        Your sign-in is fine — the server could not complete the request. Try
        again in a moment.
      </p>
      <div className="signin__actions">
        <button type="button" className="btn btn--primary signin__btn" onClick={onRetry}>
          Try again
        </button>
        <button type="button" className="btn btn--chip signin__link" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </Gate>
  );
}
