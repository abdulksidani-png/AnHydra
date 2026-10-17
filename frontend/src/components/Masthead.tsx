import { HydraMark } from './HydraMark';

interface MastheadProps {
  runNumber: number;
  screenedAt: Date;
}

export function Masthead({ runNumber, screenedAt }: MastheadProps) {
  return (
    <header className="masthead">
      <HydraMark />
      <div className="masthead__titles">
        <h1 className="masthead__title">AnHydra</h1>
        <p className="masthead__subtitle">
          Screening proteins that survive drying out
        </p>
      </div>
      <dl className="masthead__meta">
        <dt>Run</dt>
        <dd>{runNumber}</dd>
        <dt>Date</dt>
        <dd>
          <time dateTime={screenedAt.toISOString()}>
            {screenedAt.toISOString().slice(0, 10)}
          </time>
        </dd>
      </dl>
    </header>
  );
}
