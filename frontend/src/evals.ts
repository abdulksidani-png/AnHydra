/**
 * Held-out evaluation numbers shown on the results page.
 *
 * These are NOT returned by /score — they are a property of the model, not of
 * one sequence, so they live here and you edit them by hand from
 * docs/EVALS.md after each run.
 *
 * The numbers below are copied from docs/STATUS.md as of 2026-10-17, which
 * records them as real measurements on a negative set that was later found to
 * be confounded. They are presented with that caveat attached rather than on
 * their own, because 0.987 on the "hard" task without the caveat is the
 * overclaiming STATUS.md warns against. Replace both the table and the
 * caveat once the rebuilt negatives are re-run.
 */

export interface EvalRow {
  task: string;
  model: string;
  /** ROC-AUC. */
  rocAuc: number;
  /** PR-AUC, or null when it hasn't been recorded yet. */
  prAuc: number | null;
  /** 'sanity' rows are de-emphasised so the real task reads as the headline. */
  tier: 'sanity' | 'real';
}

export interface EvalTable {
  rows: EvalRow[];
  /** Method line: how the folds were split. */
  protocol: string;
  /**
   * The honest caveat, rendered directly under the table. Set to null to hide
   * it — but only when there is genuinely nothing to qualify.
   */
  caveat: string | null;
  /** Shown in small type so a judge knows how current the numbers are. */
  lastUpdated: string;
}

export const EVALUATION: EvalTable = {
  protocol:
    'Five-fold cross-validation, folds split by CD-HIT cluster at 40% identity so homologs cannot straddle train and test.',
  lastUpdated: '2026-10-17 · pre-rebuild',
  rows: [
    { task: 'vs ordered globular (sanity)', model: 'Composition baseline', rocAuc: 0.912, prAuc: null, tier: 'sanity' },
    { task: 'vs ordered globular (sanity)', model: 'Biophysical features', rocAuc: 0.886, prAuc: null, tier: 'sanity' },
    { task: 'vs ordered globular (sanity)', model: 'ESM-2 + head', rocAuc: 0.997, prAuc: null, tier: 'sanity' },
    { task: 'vs other disordered proteins', model: 'Composition baseline', rocAuc: 0.872, prAuc: null, tier: 'real' },
    { task: 'vs other disordered proteins', model: 'Biophysical features', rocAuc: 0.851, prAuc: null, tier: 'real' },
    { task: 'vs other disordered proteins', model: 'ESM-2 + head', rocAuc: 0.987, prAuc: null, tier: 'real' },
  ],
  caveat:
    'The 0.987 on the hard task is a real measurement, but not a trustworthy one. Shuffled-label controls sit at 0.50, so the cross-validation is sound, and length-matching does not explain it. The negative set does: most DisProt entries are folded proteins with a disordered region, not fully disordered proteins, so the "hard" task was substantially re-measuring folded vs. unfolded. The negatives are being rebuilt from UniProt and filtered on disorder coverage; these numbers will be replaced by the re-run.',
};
