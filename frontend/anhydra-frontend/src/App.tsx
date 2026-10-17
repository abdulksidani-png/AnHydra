import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import './styles/app.css';

import { Masthead, type Account } from './components/Masthead';
import { SequenceInput } from './components/SequenceInput';
import { SpecimenHeader } from './components/SpecimenHeader';
import { Determination } from './components/Determination';
import { ClosestRecord } from './components/ClosestRecord';
import { FieldNotes } from './components/FieldNotes';
import { Drivers } from './components/Drivers';
import { DiagnosticCharacters } from './components/DiagnosticCharacters';
import { Reliability } from './components/Reliability';
import { Limitations } from './components/Limitations';
import { SignIn, type SignInProvider } from './components/SignIn';
import {
  AccessDenied,
  AccountLoading,
  AccountUnavailable,
  ConfigurationError,
  SessionExpired,
} from './components/AccountStates';
import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  MockBanner,
  UntrainedWarning,
} from './components/States';
import { useScreen } from './hooks/useScreen';
import { useAccount } from './hooks/useAccount';
import { accountLabel } from './auth/account';
import {
  clearAccessTokenProvider,
  setAccessTokenProvider,
  setAuthRequired,
} from './auth/token';
import { authState } from './auth/config';

// Done once, at module load, so no request can be sent before the client
// knows whether a token is required.
setAuthRequired(authState.kind === 'configured');

export default function App() {
  switch (authState.kind) {
    case 'misconfigured':
      return (
        <ConfigurationError
          missing={authState.missing}
          anonymousIgnored={authState.anonymousIgnored}
        />
      );
    case 'anonymous':
      // Development only — config.ts refuses this in a production build.
      return <Screener />;
    case 'configured':
      return <AuthGate />;
  }
}

/**
 * Auth0 → application account → screener.
 *
 * Two gates, deliberately separate. Auth0 says *who* someone is; `GET /me`
 * says whether AnHydra has an account for them and will admit them. Protected
 * content waits for the second, because provider success alone is not
 * admission.
 */
function AuthGate() {
  const {
    isLoading,
    isAuthenticated,
    error,
    user,
    loginWithRedirect,
    logout,
    getAccessTokenSilently,
  } = useAuth0();

  const settings = authState.kind === 'configured' ? authState.settings : null;
  const identity = isAuthenticated ? (user?.sub ?? null) : null;
  const [providerSession, setProviderSession] = useState<{ identity: string; epoch: number } | null>(null);

  // Install the token provider for this identity, and tear it down on sign-out
  // or identity change so nothing can keep using the old one.
  useEffect(() => {
    if (!identity) {
      clearAccessTokenProvider();
      setProviderSession(null);
      return;
    }
    const epoch = setAccessTokenProvider(() => getAccessTokenSilently(), identity);
    setProviderSession({ identity, epoch });
    return () => {
      clearAccessTokenProvider();
    };
  }, [identity, getAccessTokenSilently]);

  const account = useAccount(identity, providerSession?.identity === identity ? providerSession.epoch : null);

  const signIn = useCallback(
    (connection?: string, signup = false) =>
      void loginWithRedirect({
        authorizationParams: {
          ...(connection ? { connection } : {}),
          ...(signup ? { screen_hint: 'signup' } : {}),
        },
      }),
    [loginWithRedirect],
  );

  const signOut = useCallback(() => {
    clearAccessTokenProvider();
    setProviderSession(null);
    void logout({ logoutParams: { returnTo: window.location.origin } });
  }, [logout]);

  const providers = useMemo<SignInProvider[]>(() => {
    if (!settings) return [];
    const list: SignInProvider[] = [
      {
        id: 'google',
        label: 'Continue with Google',
        primary: true,
        onClick: () => signIn(settings.googleConnection),
      },
    ];
    // Only offered when the tenant actually has a Microsoft connection under
    // this name. An unconfigured button would send people to a dead end.
    if (settings.microsoftConnection) {
      list.push({
        id: 'microsoft',
        label: 'Continue with Microsoft',
        onClick: () => signIn(settings.microsoftConnection),
      });
    }
    list.push({
      id: 'email',
      label: 'Sign in with email',
      onClick: () => signIn(settings.dbConnection),
    });
    return list;
  }, [settings, signIn]);

  if (isLoading || !isAuthenticated) {
    return (
      <SignIn
        busy={isLoading}
        error={error?.message}
        providers={providers}
        onSignUp={settings ? () => signIn(settings.dbConnection, true) : undefined}
      />
    );
  }

  if (account.status === 'idle' || account.status === 'loading') return <AccountLoading />;

  if (account.status === 'error') {
    const detail = account.error ?? 'Could not load your account.';
    switch (account.errorKind) {
      case 'denied':
        return <AccessDenied detail={detail} onSignOut={signOut} />;
      case 'expired':
        // One explicit action, never an automatic redirect.
        return <SessionExpired detail={detail} onSignIn={() => signIn()} />;
      default:
        return (
          <AccountUnavailable detail={detail} onRetry={account.retry} onSignOut={signOut} />
        );
    }
  }

  const profile = account.profile;
  if (!profile) return <AccountLoading />;

  // Keying on the account id discards every piece of user-scoped state —
  // including any result on screen — when the identity changes.
  return (
    <Screener
      key={profile.id}
      account={{ label: accountLabel(profile), onSignOut: signOut }}
    />
  );
}

function Screener({ account }: { account?: Account }) {
  const [sequence, setSequence] = useState('');
  const [runNumber, setRunNumber] = useState(1);
  const {
    status,
    data,
    sequence: scoredSequence,
    error,
    errorKind,
    isMock,
    modelTrained,
    run,
  } = useScreen();

  const handleSubmit = useCallback(() => {
    setRunNumber((n) => (status === 'success' ? n + 1 : n));
    void run(sequence);
  }, [run, sequence, status]);

  return (
    <div className="shell">
      <Masthead runNumber={runNumber} screenedAt={new Date()} account={account} />

      <div className="stack" style={{ marginTop: 26 }}>
        {modelTrained === false && <UntrainedWarning />}

        <SequenceInput
          value={sequence}
          onChange={setSequence}
          onSubmit={handleSubmit}
          isLoading={status === 'loading'}
        />

        {status === 'error' && error && errorKind && (
          <ErrorBanner
            message={error}
            kind={errorKind}
            onRetry={handleSubmit}
            onSignOut={account?.onSignOut}
          />
        )}

        {status === 'idle' && <EmptyState />}
        {status === 'loading' && <LoadingState />}

        {status === 'success' && data && (
          <>
            {isMock && <MockBanner />}

            <SpecimenHeader features={data.features} sequence={scoredSequence} />

            <div className="row">
              <Determination result={data} />
              <ClosestRecord nearestHomolog={data.nearest_homolog} />
            </div>

            <FieldNotes explanation={data.explanation} />
            <Drivers topFeatures={data.top_features} />
            <DiagnosticCharacters features={data.features} topFeatures={data.top_features} />
            <Reliability />
            <Limitations />

            <footer className="footer">
              <span>AnHydra scores family character, not protective strength.</span>
              <span className="footer__mono">
                ESM-2 esm2_t12_35M_UR50D · frozen, mean-pooled
              </span>
            </footer>
          </>
        )}
      </div>
    </div>
  );
}
