import { HydraMark } from './HydraMark';

interface SignInProps {
  /** Message from Auth0 after a refused login (e.g. a non-.edu email). */
  error?: string | null;
  /** True while the SDK is restoring a session or handling the redirect back. */
  busy?: boolean;
  onGoogle: () => void;
  onEmail: () => void;
  onSignUp: () => void;
}

/**
 * The sign-in page. It only chooses where to send people — Auth0's hosted
 * page collects the password, and the access rule (.edu email, or Google) is
 * enforced by Auth0 and again by the backend on every /score request.
 */
export function SignIn({ error, busy = false, onGoogle, onEmail, onSignUp }: SignInProps) {
  return (
    <main className="signin">
      <section className="signin__card card" aria-labelledby="signin-title">
        <div className="signin__brand">
          <HydraMark />
          <div>
            <h1 id="signin-title" className="masthead__title">AnHydra</h1>
            <p className="masthead__subtitle">Screening proteins that survive drying out</p>
          </div>
        </div>

        <p className="signin__lede">
          Sign in to screen sequences. Use a Google account, or an email address
          ending in <strong>.edu</strong>.
        </p>

        {error && (
          <p className="banner banner--error" role="alert">
            <span className="banner__text">
              <strong>Couldn’t sign you in.</strong> {error}
            </span>
          </p>
        )}

        {busy ? (
          <p className="signin__busy" aria-live="polite">Checking your session…</p>
        ) : (
          <div className="signin__actions">
            <button type="button" className="btn btn--primary signin__btn" onClick={onGoogle}>
              Continue with Google
            </button>

            <p className="signin__divider" aria-hidden="true">
              <span>or with a .edu email</span>
            </p>

            <button type="button" className="btn btn--quiet signin__btn" onClick={onEmail}>
              Sign in with email
            </button>
            <button type="button" className="btn btn--chip signin__link" onClick={onSignUp}>
              New here? Create an account
            </button>
          </div>
        )}

        <p className="signin__fine">
          Email accounts must use a .edu address and be verified from the link
          we send. Sign-in is handled by Auth0; AnHydra never sees your password.
        </p>
      </section>
    </main>
  );
}
