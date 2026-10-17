import type { FeatureValues } from './types';

/**
 * Display metadata for the nine features in features.py.
 *
 * `plotMax` only controls how long a bar is drawn — it is a legibility
 * choice, not a claim about the feature's range. `bipolar` features are drawn
 * from the centre because their sign is meaningful (net charge can go either
 * way; hydropathy below zero means hydrophilic).
 *
 * If the model owner adds a feature (predicted disorder is the TODO in
 * features.py), add it here and it appears in the UI automatically.
 */
export interface FeatureMeta {
  label: string;
  /** How to render the number. */
  format: (value: number) => string;
  /** Bar scale. */
  plotMax: number;
  bipolar?: boolean;
  /** One short clause on how to read it. */
  blurb: string;
}

export const FEATURE_META: Record<keyof FeatureValues, FeatureMeta> = {
  length: {
    label: 'Length',
    format: (v) => `${Math.round(v)} aa`,
    plotMax: 800,
    blurb: 'residues after cleaning',
  },
  fraction_charged: {
    label: 'Fraction charged residues',
    format: fixed2,
    plotMax: 0.6,
    blurb: 'FCR — D, E, K and R as a share of the sequence',
  },
  net_charge_per_residue: {
    label: 'Net charge per residue',
    format: signed2,
    plotMax: 0.4,
    bipolar: true,
    blurb: 'NCPR — positive means more K/R than D/E',
  },
  mean_hydropathy: {
    label: 'Mean hydropathy',
    format: signed2,
    plotMax: 2.5,
    bipolar: true,
    blurb: 'Kyte-Doolittle; below zero is hydrophilic, typical of IDPs',
  },
  glycine: {
    label: 'Glycine fraction',
    format: fixed2,
    plotMax: 0.3,
    blurb: 'enriched in CAHS-family proteins',
  },
  serine: {
    label: 'Serine fraction',
    format: fixed2,
    plotMax: 0.3,
    blurb: 'enriched in CAHS-family proteins',
  },
  histidine: {
    label: 'Histidine fraction',
    format: fixed2,
    plotMax: 0.15,
    blurb: 'a minor but characteristic signal',
  },
  gly_ser_his: {
    label: 'Gly + Ser + His fraction',
    format: fixed2,
    plotMax: 0.6,
    blurb: 'the combined enrichment the model leans on',
  },
  low_complexity: {
    label: 'Low-complexity fraction',
    format: fixed2,
    plotMax: 1,
    blurb: 'share of 20-residue windows below 2.2 bits of entropy',
  },
};

/** The order features are shown in. Grouped: size, charge, composition, repeats. */
export const FEATURE_ORDER: Array<keyof FeatureValues> = [
  'length',
  'fraction_charged',
  'net_charge_per_residue',
  'mean_hydropathy',
  'glycine',
  'serine',
  'histidine',
  'gly_ser_his',
  'low_complexity',
];

/** Fall back to a readable label for a feature the UI doesn't know yet. */
export function labelFor(name: string): string {
  const known = FEATURE_META[name as keyof FeatureValues];
  if (known) return known.label;
  return name.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
}

export function formatFeature(name: string, value: number): string {
  const known = FEATURE_META[name as keyof FeatureValues];
  return known ? known.format(value) : fixed2(value);
}

/** Bar geometry: a left-origin fill, or a centre-origin fill for bipolar features. */
export interface BarGeometry {
  /** Percentage width of the fill. */
  width: number;
  /** Percentage offset of the fill's left edge. */
  left: number;
  /** True when the value sits on the negative side of a bipolar scale. */
  negative: boolean;
}

export function barFor(name: string, value: number): BarGeometry {
  const meta = FEATURE_META[name as keyof FeatureValues];
  const plotMax = meta?.plotMax ?? 1;
  const bipolar = meta?.bipolar ?? false;

  if (!bipolar) {
    const width = clamp(Math.abs(value) / plotMax, 0, 1) * 100;
    return { width, left: 0, negative: value < 0 };
  }

  const half = clamp(Math.abs(value) / plotMax, 0, 1) * 50;
  return {
    width: half,
    left: value < 0 ? 50 - half : 50,
    negative: value < 0,
  };
}

/** Contribution bars share one scale so their lengths are comparable. */
export function contributionBar(value: number, maxAbs: number): BarGeometry {
  const half = clamp(Math.abs(value) / (maxAbs || 1), 0, 1) * 50;
  return {
    width: half,
    left: value < 0 ? 50 - half : 50,
    negative: value < 0,
  };
}

function fixed2(value: number): string {
  return value.toFixed(2);
}

function signed2(value: number): string {
  return `${value >= 0 ? '+' : '-'}${Math.abs(value).toFixed(2)}`;
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}
