import { useCallback, useEffect, useRef, useState } from 'react';
import { checkHealth, cleanSequence, scoreSequence } from '../api/client';
import { ScreenError, type ScoreResponse, type ScreenErrorKind } from '../types';
import { tokenEpoch } from '../auth/token';

export type ScreenStatus = 'idle' | 'loading' | 'success' | 'error';

interface ScreenState {
  status: ScreenStatus;
  data: ScoreResponse | null;
  /** The cleaned sequence that produced `data`. */
  sequence: string;
  error: string | null;
  errorKind: ScreenErrorKind | null;
  isMock: boolean;
}

const INITIAL: ScreenState = {
  status: 'idle',
  data: null,
  sequence: '',
  error: null,
  errorKind: null,
  isMock: false,
};

/**
 * Owns one screening run. Late responses from a superseded request are
 * discarded, so clicking Identify twice during a demo can't show the earlier
 * result on top of the later one.
 *
 * Also polls /health once on mount, so "the model isn't loaded" is visible
 * before anyone pastes a sequence and waits for a 503.
 */
export function useScreen() {
  const [state, setState] = useState<ScreenState>(INITIAL);
  const [modelTrained, setModelTrained] = useState<boolean | null>(null);
  const runId = useRef(0);

  useEffect(() => {
    let cancelled = false;
    void checkHealth().then((health) => {
      if (!cancelled && health) setModelTrained(health.model_trained);
    });
    return () => {
      cancelled = true;
      runId.current += 1;
    };
  }, []);

  const run = useCallback(async (raw: string) => {
    const id = ++runId.current;
    const epoch = tokenEpoch();
    setState((prev) => ({ ...prev, status: 'loading', error: null, errorKind: null }));

    try {
      const { data, isMock } = await scoreSequence({ sequence: raw });
      if (id !== runId.current || epoch !== tokenEpoch()) return;
      setState({
        status: 'success',
        data,
        sequence: cleanSequence(raw),
        error: null,
        errorKind: null,
        isMock,
      });
    } catch (error) {
      if (id !== runId.current || epoch !== tokenEpoch()) return;
      const isKnown = error instanceof ScreenError;
      setState((prev) => ({
        ...prev,
        status: 'error',
        error: isKnown ? error.message : 'Something went wrong running the screen.',
        errorKind: isKnown ? error.kind : 'server',
      }));
    }
  }, []);

  const reset = useCallback(() => {
    runId.current += 1;
    setState(INITIAL);
  }, []);

  return { ...state, modelTrained, run, reset };
}
