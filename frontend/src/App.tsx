import { useCallback, useState } from 'react';
import './styles/app.css';

import { Masthead } from './components/Masthead';
import { SequenceInput } from './components/SequenceInput';
import { SpecimenHeader } from './components/SpecimenHeader';
import { Determination } from './components/Determination';
import { ClosestRecord } from './components/ClosestRecord';
import { FieldNotes } from './components/FieldNotes';
import { Drivers } from './components/Drivers';
import { DiagnosticCharacters } from './components/DiagnosticCharacters';
import { Reliability } from './components/Reliability';
import { Limitations } from './components/Limitations';
import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  MockBanner,
  UntrainedWarning,
} from './components/States';
import { useScreen } from './hooks/useScreen';

export default function App() {
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
      <Masthead runNumber={runNumber} screenedAt={new Date()} />

      <div className="stack" style={{ marginTop: 26 }}>
        {modelTrained === false && <UntrainedWarning />}

        <SequenceInput
          value={sequence}
          onChange={setSequence}
          onSubmit={handleSubmit}
          isLoading={status === 'loading'}
        />

        {status === 'error' && error && errorKind && (
          <ErrorBanner message={error} kind={errorKind} onRetry={handleSubmit} />
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
