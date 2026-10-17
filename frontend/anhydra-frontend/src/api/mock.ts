import type { ScoreResponse } from '../types';

/**
 * Fixtures for working on the UI with no backend running
 * (VITE_USE_MOCK=true). They are never substituted for a failed real
 * request — see the note in client.ts.
 *
 * Shapes match ScoreResponse in app/main.py. The numbers are illustrative.
 */

const PROTECTIVE: ScoreResponse = {
  score: 0.84,
  label: 'protective',
  nearest_homolog: 'P0DOW4',
  top_features: [
    ['low_complexity', 0.91],
    ['gly_ser_his', 0.44],
    ['mean_hydropathy', -0.38],
  ],
  features: {
    length: 227,
    fraction_charged: 0.41,
    net_charge_per_residue: 0.06,
    mean_hydropathy: -0.92,
    glycine: 0.16,
    serine: 0.12,
    histidine: 0.05,
    gly_ser_his: 0.33,
    low_complexity: 0.34,
  },
  explanation:
    'This sequence scores 0.84 for desiccation-protective family character (call: protective), driven mainly by its low-complexity repeat blocks, combined Gly/Ser/His enrichment, and strongly hydrophilic composition. On that basis it is worth prioritizing for wet-lab testing. Note: this is a family/triage signal, not a measured protection efficacy.',
};

const NOT_PROTECTIVE: ScoreResponse = {
  score: 0.07,
  label: 'other_idp',
  nearest_homolog: 'P0DOW4',
  top_features: [
    ['mean_hydropathy', -0.72],
    ['low_complexity', -0.51],
    ['gly_ser_his', -0.29],
  ],
  features: {
    length: 609,
    fraction_charged: 0.26,
    net_charge_per_residue: -0.02,
    mean_hydropathy: 0.31,
    glycine: 0.04,
    serine: 0.05,
    histidine: 0.03,
    gly_ser_his: 0.12,
    low_complexity: 0.04,
  },
  explanation:
    'This sequence scores 0.07 for desiccation-protective family character (call: other_idp), driven mainly by its hydrophobic core, absence of low-complexity repeats, and lack of Gly/Ser/His enrichment. On that basis it is unlikely to be protective. Note: this is a family/triage signal, not a measured protection efficacy.',
};

/** Example sequences offered in the input panel. */
export const EXAMPLES: ReadonlyArray<{
  id: string;
  label: string;
  blurb: string;
  sequence: string;
}> = [
  {
    id: 'cahs-like',
    label: 'CAHS-like toy',
    blurb: 'Gly/Ser-rich',
    // The demo sequence from features.py, repeated to clear MIN_LENGTH comfortably.
    sequence:
      'MSGSGSGKEKEKDKDKGSGSGSHGHGSGSEKEKDKDKGSGSGSGHKGHGSGSEKEKDKDKGSGSGSHGHGSGSEKEKDKDKGSGSGSGHKGHGSGS',
  },
  {
    id: 'albumin',
    label: 'Serum albumin',
    blurb: 'negative control',
    sequence:
      'MKWVTFISLLFLFSSAYSRGVFRRDAHKSEVAHRFKDLGEENFKALVLIAFAQYLQQCPFEDHVKLVNEVTEFAKTCVADESAENCDKSLHTLFGDKLCTVATLRETYGEMADCCAKQEPERNECFLQHKDDNPNLPRLVRPEVDVMCTAFHDNEETFLKKYLYEIARRHPYFYAPELLFFAKRYKAAFTECCQAADKAACLLPKLDELRDEGKASSAKQRLKCASLQKFGERAFKAWAVARLSQRFPKAEFAEVSKLVTDLTKVHTECCHGDLLECADDRADLAKYICENQDSISSKLKECCEKPLLEKSHCIAEVENDEMPADLPSLAADFVESKDVCKNYAEAKDVFLGMFLYEYARRHPDYSVVLLLRLAKTYETTLEKCCAAADPHECYAKVFDEFKPLVEEPQNLIKQNCELFEQLGEYKFQNALLVRYTKKVPQVSTPTLVEVSRNLGKVGSKCCKHPEAKRMPCAEDYLSVVLNQLCVLHEKTPVSDRVTKCCTESLVNRRPCFSALEVDETYVPKEFNAETFTFHADICTLSEKERQIKKQTALVELVKHKPKATKEQLKAVMDDFAAFVEKCCKADDKETCFAEEGKKLVAASQAALGL',
  },
];

/** Crude switch so the two example buttons produce different fixtures. */
export function mockScore(sequence: string): ScoreResponse {
  const glySer =
    sequence.split('').filter((c) => c === 'G' || c === 'S').length /
    Math.max(sequence.length, 1);
  const base = glySer > 0.2 ? PROTECTIVE : NOT_PROTECTIVE;
  return {
    ...base,
    features: { ...base.features, length: sequence.length || base.features.length },
  };
}
