import { HydraMark } from './HydraMark';

export interface Account {
  /** Email (or name) of the signed-in person. */
  label: string;
  onSignOut: () => void;
}

interface MastheadProps {
  runNumber: number;
  screenedAt: Date;
  /** Present only when sign-in is enabled. */
  account?: Account;
}

export function Masthead({ runNumber, screenedAt, account }: MastheadProps) {
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
        {account && (
          <>
            <dt>User</dt>
            <dd className="masthead__user">
              <span className="masthead__email" title={account.label}>
                {account.label}
              </span>
              <button type="button" className="masthead__signout" onClick={account.onSignOut}>
                Sign out
              </button>
            </dd>
          </>
        )}
      </dl>
    </header>
  );
}
