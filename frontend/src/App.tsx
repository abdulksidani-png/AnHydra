import { useCallback, useEffect, useState } from 'react';
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
import { SignIn } from './components/SignIn';
import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  MockBanner,
  UntrainedWarning,
} from './components/States';
import { useScreen } from './hooks/useScreen';
import { setAccessTokenProvider } from './api/client';
import { auth0Config, authEnabled } from './auth/config';

export default function App() {
  return authEnabled ? <AuthGate /> : <Screener />;
}

/** Shows the sign-in page until Auth0 says who this is, then the screener. */
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

  useEffect(() => {
    setAccessTokenProvider(isAuthenticated ? () => getAccessTokenSilently() : null);
    return () => setAccessTokenProvider(null);
  }, [isAuthenticated, getAccessTokenSilently]);

  const signIn = useCallback(
    (connection: string, signup = false) =>
      void loginWithRedirect({
        authorizationParams: {
          connection,
          ...(signup ? { screen_hint: 'signup' } : {}),
        },
      }),
    [loginWithRedirect],
  );

  if (isLoading || !isAuthenticated) {
    return (
      <SignIn
        busy={isLoading}
        error={error?.message}
        onGoogle={() => signIn(auth0Config.googleConnection)}
        onEmail={() => signIn(auth0Config.dbConnection)}
        onSignUp={() => signIn(auth0Config.dbConnection, true)}
      />
    );
  }

  const account: Account = {
    label: user?.email ?? user?.name ?? 'Signed in',
    onSignOut: () => void logout({ logoutParams: { returnTo: window.location.origin } }),
  };
  return <Screener account={account} />;
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
            <DiagnosticCharacters
              features={data.features}
              topFeatures={data.top_features}
            />
            <Reliability />
            <Limitations />

            <footer className="footer">
              <span>
                AnHydra scores family character, not protective strength.
              </span>
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
