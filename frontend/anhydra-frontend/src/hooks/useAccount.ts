import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AccountError,
  fetchAccount,
  type AccountFailureKind,
  type AccountProfile,
} from '../auth/account';
import { tokenEpoch } from '../auth/token';

export type AccountStatus = 'idle' | 'loading' | 'ready' | 'error';

interface AccountState {
  identity: string | null;
  epoch: number | null;
  status: AccountStatus;
  profile: AccountProfile | null;
  errorKind: AccountFailureKind | null;
  error: string | null;
}

const IDLE: AccountState = { identity: null, epoch: null, status: 'idle', profile: null, errorKind: null, error: null };

/**
 * Resolves the application account after Auth0 has authenticated someone.
 *
 * `identity` is the Auth0 subject. Changing it — including to null on
 * sign-out — clears the profile immediately and invalidates any request still
 * in flight, so a late response for the previous person can never populate the
 * new session.
 *
 * `providerEpoch` gates requests on the installed provider and restarts
 * resolution when it changes, including for the same subject.
 */
export function useAccount(identity: string | null, providerEpoch: number | null) {
  const [state, setState] = useState<AccountState>(IDLE);
  const runId = useRef(0);
  const activeIdentity = useRef<string | null>(null);

  const load = useCallback(async (who: string | null) => {
    const id = ++runId.current;
    const epochAtStart = tokenEpoch();
    setState({ ...IDLE, identity: who, epoch: epochAtStart, status: 'loading' });

    try {
      const { profile, epoch } = await fetchAccount();
      // Three guards: a newer run started, the identity changed, or the token
      // provider was swapped underneath us.
      if (id !== runId.current || activeIdentity.current !== who || epoch !== tokenEpoch()) return;
      setState({ identity: who, epoch, status: 'ready', profile, errorKind: null, error: null });
    } catch (error) {
      if (id !== runId.current || activeIdentity.current !== who || epochAtStart !== tokenEpoch()) return;
      const known = error instanceof AccountError;
      setState({
        identity: who,
        epoch: epochAtStart,
        status: 'error',
        profile: null,
        errorKind: known ? error.kind : 'failed',
        error: known ? error.message : 'Could not load your account.',
      });
    }
  }, []);

  useEffect(() => {
    activeIdentity.current = identity;
    // Any identity change invalidates in-flight work and wipes user state.
    runId.current += 1;

    if (!identity || providerEpoch === null) {
      setState(IDLE);
    } else {
      void load(identity);
    }
    return () => { runId.current += 1; activeIdentity.current = null; };
  }, [identity, providerEpoch, load]);

  const retry = useCallback(() => {
    if (identity && providerEpoch !== null && providerEpoch === tokenEpoch()) void load(identity);
  }, [identity, providerEpoch, load]);

  // Hide a previous account during render, before effect cleanup gets a turn.
  const current = identity && state.identity === identity && state.epoch === providerEpoch
    && providerEpoch === tokenEpoch();
  return { ...(current ? state : IDLE), retry };
}
