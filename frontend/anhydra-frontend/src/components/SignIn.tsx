import { HydraMark } from './HydraMark';

export interface SignInProvider {
  id: string;
  label: string;
  onClick: () => void;
  /** The primary option gets the filled button. */
  primary?: boolean;
}

interface SignInProps {
  /** Message from Auth0 after a refused or failed login. */
  error?: string | null;
  /** True while the SDK is restoring a session or handling the redirect back. */
  busy?: boolean;
  providers: SignInProvider[];
  /** Offered only when a database connection is configured. */
  onSignUp?: () => void;
}

/**
 * The sign-in page.
 *
 * It only chooses where to send people — Auth0's hosted page collects every
 * credential, and this app never sees a password.
 *
 * Note on copy: this page does not promise any particular admission rule.
 * Whether an account may use AnHydra is decided by the backend, and signing in
 * successfully with a provider does not by itself grant access; a rejected
 * account gets an explicit access-denied screen after sign-in. Do not add
 * claims here (".edu only", "verified emails only") unless the backend
 * actually enforces them.
 */
export function SignIn({ error, busy = false, providers, onSignUp }: SignInProps) {
  return (
    <main className="signin">
      <section className="signin__card card" aria-labelledby="signin-title">
        <div className="signin__brand">
          <HydraMark />
          <div>
            <h1 id="signin-title" className="masthead__title">
              AnHydra
            </h1>
            <p className="masthead__subtitle">Screening proteins that survive drying out</p>
          </div>
        </div>

        <p className="signin__lede">Sign in to screen sequences.</p>

        {error && (
          <p className="banner banner--error" role="alert">
            <span className="banner__text">
              <strong>Couldn’t sign you in.</strong> {error}
            </span>
          </p>
        )}

        {busy ? (
          <p className="signin__busy" aria-live="polite">
            Checking your session…
          </p>
        ) : (
          <div className="signin__actions">
            {providers.map((provider) => (
              <button
                key={provider.id}
                type="button"
                className={`btn signin__btn ${provider.primary ? 'btn--primary' : 'btn--quiet'}`}
                onClick={provider.onClick}
              >
                {provider.label}
              </button>
            ))}

            {onSignUp && (
              <button type="button" className="btn btn--chip signin__link" onClick={onSignUp}>
                New here? Create an account
              </button>
            )}
          </div>
        )}

        <p className="signin__fine">
          Sign-in is handled by Auth0. AnHydra never sees your password, and
          access to the screener is granted by the AnHydra server after you
          sign in.
        </p>
      </section>
    </main>
  );
}
