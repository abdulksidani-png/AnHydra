import type { ScoreResponse } from '../types';
import { ScaleBar } from './ScaleBar';

interface DeterminationProps {
  result: ScoreResponse;
}

/** Wording for each family call. The score is always P(protective). */
const CALLS = {
  protective: {
    headline: 'Protective family character',
    family: 'resembles the CAHS / LEA / anhydrobiosis families',
  },
  other_idp: {
    headline: 'No protective signature',
    family: 'does not resemble the protective families',
  },
} as const;

export function Determination({ result }: DeterminationProps) {
  const call = CALLS[result.label] ?? CALLS.other_idp;

  return (
    <section className="card" aria-labelledby="determination-heading">
      <p className="card__label" id="determination-heading">
        Determination
      </p>
      <h2 className="determination__call">{call.headline}</h2>
      <p className="determination__family">{call.family}</p>

      <ScaleBar score={result.score} threshold={0.5} />

      <p className="determination__score">
        {result.score.toFixed(2)}
        <span className="determination__meta">
          Protection-family score, from 0 to 1. The model calls this{' '}
          <code>{result.label}</code>.
        </span>
      </p>
    </section>
  );
}
