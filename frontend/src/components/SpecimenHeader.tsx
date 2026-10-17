import type { FeatureValues } from '../types';

interface SpecimenHeaderProps {
  features: FeatureValues;
  /** What the user pasted, already cleaned. */
  sequence: string;
}

/**
 * What was screened. Only facts the response carries: the cleaned length the
 * backend actually scored, and the residues themselves. No molecular weight —
 * the API doesn't return one, and estimating it from length would be a number
 * the UI made up.
 */
export function SpecimenHeader({ features, sequence }: SpecimenHeaderProps) {
  const preview =
    sequence.length > 180 ? `${sequence.slice(0, 180)}…` : sequence;

  return (
    <section className="card card--tight" aria-labelledby="specimen-heading">
      <p className="card__label" id="specimen-heading">
        Sequence
      </p>
      <dl className="record">
        <div className="record__row">
          <dt className="record__key">Scored length</dt>
          <dd className="record__value">{features.length} aa</dd>
        </div>
      </dl>
      {preview && (
        <p className="specimen__seq" title="the cleaned sequence that was scored">
          {preview}
        </p>
      )}
    </section>
  );
}
