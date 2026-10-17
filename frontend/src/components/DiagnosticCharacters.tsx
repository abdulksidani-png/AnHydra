import { FEATURE_META, FEATURE_ORDER, barFor, formatFeature } from '../features';
import type { FeatureContribution, FeatureValues } from '../types';

interface DiagnosticCharactersProps {
  features: FeatureValues;
  topFeatures: FeatureContribution[];
}

/**
 * All nine interpretable features, computed by features.py independently of
 * the language model. The three the model leaned on hardest are marked, so
 * this card and the drivers card agree without repeating the numbers.
 */
export function DiagnosticCharacters({
  features,
  topFeatures,
}: DiagnosticCharactersProps) {
  const drivers = new Set(topFeatures.map(([name]) => name));

  // Render any key the backend sent, even one this UI predates.
  const extras = Object.keys(features).filter(
    (key) => !FEATURE_ORDER.includes(key as keyof FeatureValues),
  ) as Array<keyof FeatureValues>;
  const keys = [...FEATURE_ORDER, ...extras];

  return (
    <section className="card" aria-labelledby="characters-heading">
      <p className="card__label" id="characters-heading">
        Diagnostic characters
      </p>
      <p className="card__lede">
        Measured from the sequence itself, independent of the language model.
        Teal marks one of the three features that drove the call.
      </p>

      <div className="characters">
        {keys.map((key) => {
          const value = features[key];
          if (typeof value !== 'number') return null;

          const meta = FEATURE_META[key];
          const bar = barFor(key, value);
          const isDriver = drivers.has(key);

          return (
            <div key={key}>
              <div className="character__head">
                <span className="character__name">
                  {meta?.label ?? key}
                  {isDriver && (
                    <span className="character__flag" title="drove the call">
                      ●
                    </span>
                  )}
                </span>
                <span className="character__value">{formatFeature(key, value)}</span>
              </div>
              <div
                className="character__track"
                role="img"
                aria-label={`${meta?.label ?? key}: ${formatFeature(key, value)}${
                  meta ? `, ${meta.blurb}` : ''
                }`}
              >
                {meta?.bipolar && <span className="character__axis" aria-hidden="true" />}
                <span
                  className={`character__fill${isDriver ? ' character__fill--drives' : ''}`}
                  style={{ left: `${bar.left}%`, width: `${bar.width}%` }}
                />
              </div>
              {meta && <p className="character__note">{meta.blurb}</p>}
            </div>
          );
        })}
      </div>
    </section>
  );
}
