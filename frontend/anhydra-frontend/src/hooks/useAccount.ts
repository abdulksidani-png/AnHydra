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
  status: AccountStatus;
  profile: AccountProfile | null;
  errorKind: AccountFailureKind | null;
  error: string | null;
}

const IDLE: AccountState = { status: 'idle', profile: null, errorKind: null, error: null };

/**
 * Resolves the application account after Auth0 has authenticated someone.
 *
 * `identity` is the Auth0 subject. Changing it — including to null on
 * sign-out — clears the profile immediately and invalidates any request still
 * in flight, so a late response for the previous person can never populate the
 * new session.
 *
 * `enabled` gates the first fetch on the token provider actually being
 * installed, which keeps /me from racing ahead of it.
 */
export function useAccount(identity: string | null, enabled: boolean) {
  const [state, setState] = useState<AccountState>(IDLE);
  const runId = useRef(0);
  const activeIdentity = useRef<string | null>(null);

  const load = useCallback(async (who: string | null) => {
    const id = ++runId.current;
    const epochAtStart = tokenEpoch();
    setState((prev) => ({ ...prev, status: 'loading', error: null, errorKind: null }));

    try {
      const { profile, epoch } = await fetchAccount();
      // Three guards: a newer run started, the identity changed, or the token
      // provider was swapped underneath us.
      if (id !== runId.current || activeIdentity.current !== who || epoch !== epochAtStart) return;
      setState({ status: 'ready', profile, errorKind: null, error: null });
    } catch (error) {
      if (id !== runId.current || activeIdentity.current !== who) return;
      const known = error instanceof AccountError;
      setState({
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

    if (!identity || !enabled) {
      setState(IDLE);
      return;
    }

    setState({ status: 'loading', profile: null, errorKind: null, error: null });
    void load(identity);
  }, [identity, enabled, load]);

  const retry = useCallback(() => {
    if (activeIdentity.current) void load(activeIdentity.current);
  }, [load]);

  return { ...state, retry };
}
