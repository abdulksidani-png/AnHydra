import { contributionBar, labelFor } from '../features';
import type { FeatureContribution } from '../types';

interface DriversProps {
  topFeatures: FeatureContribution[];
}

/**
 * The top three drivers, with their signs intact.
 *
 * A contribution is the standardized feature value times its logistic
 * coefficient, so it is signed: to the right pushes toward "protective", to
 * the left pushes away. Showing only magnitudes would turn a feature arguing
 * against the call into one that looks like it supported it.
 */
export function Drivers({ topFeatures }: DriversProps) {
  if (topFeatures.length === 0) return null;

  const maxAbs = Math.max(...topFeatures.map(([, value]) => Math.abs(value)));

  return (
    <section className="card" aria-labelledby="drivers-heading">
      <p className="card__label" id="drivers-heading">
        What drove this call
      </p>
      <p className="card__lede">
        Contribution of each feature in the interpretable model: standardized
        value times its coefficient. Right of centre argues for protective
        character, left against.
      </p>

      {topFeatures.map(([name, value]) => {
        const bar = contributionBar(value, maxAbs);
        return (
          <div className="driver" key={name}>
            <div className="driver__head">
              <span className="driver__name">{labelFor(name)}</span>
              <span className="driver__value">
                {value >= 0 ? '+' : '−'}
                {Math.abs(value).toFixed(3)}
              </span>
            </div>
            <div
              className="driver__track"
              role="img"
              aria-label={`${labelFor(name)} contributes ${value.toFixed(3)}, ${
                value >= 0 ? 'toward' : 'against'
              } a protective call`}
            >
              <span className="driver__axis" aria-hidden="true" />
              <span
                className={`driver__fill${bar.negative ? ' driver__fill--against' : ''}`}
                style={{ left: `${bar.left}%`, width: `${bar.width}%` }}
              />
            </div>
          </div>
        );
      })}

      <div className="driver__legend" aria-hidden="true">
        <span>← against</span>
        <span>for →</span>
      </div>
    </section>
  );
}
