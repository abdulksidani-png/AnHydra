/** Recorded historical results from docs/results/results_table.csv. */

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
  protocol: 'Five-fold cross-validation split by CD-HIT clusters at 40% identity. More remote relatives can remain across folds.',
  lastUpdated: '2026-10-17 · recorded experiment, before release fixes',
  rows: [
    { task: 'vs ordered globular (sanity)', model: 'Composition baseline', rocAuc: 0.9215341581, prAuc: 0.9066046999, tier: 'sanity' },
    { task: 'vs ordered globular (sanity)', model: 'Biophysical features', rocAuc: 0.8930475874, prAuc: 0.8732615273, tier: 'sanity' },
    { task: 'vs ordered globular (sanity)', model: 'ESM-2 + head', rocAuc: 0.9975374394, prAuc: 0.9970886997, tier: 'sanity' },
    { task: 'vs matched disordered proteins', model: 'Composition baseline', rocAuc: 0.8973678209, prAuc: 0.8976658049, tier: 'real' },
    { task: 'vs matched disordered proteins', model: 'Biophysical features', rocAuc: 0.7795334854, prAuc: 0.8041229635, tier: 'real' },
    { task: 'vs matched disordered proteins', model: 'ESM-2 + head', rocAuc: 0.9897496372, prAuc: 0.9901075189, tier: 'real' },
  ],
  caveat: 'Recorded OOF artifacts contain 529 positives and 520 negatives. The data is plant-dominated with no CAHS examples; species bias and related-family leakage remain possible. These historical measurements have not been rerun with the release validation changes. The score is not calibrated protection efficacy.',
};
