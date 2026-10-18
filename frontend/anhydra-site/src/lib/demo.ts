import { EXAMPLES, cleanSequence, scanMotifs, type Neighbour, type ScoreResult } from "@/lib/protein";

export const DEMO_MS = 3600;

const KD: Record<string, number> = {
  A: 1.8, R: -4.5, N: -3.5, D: -3.5, C: 2.5, Q: -3.5, E: -3.5, G: -0.4, H: -3.2, I: 4.5,
  L: 3.8, K: -3.9, M: 1.9, F: 2.8, P: -1.6, S: -0.8, T: -0.7, W: -0.9, Y: -1.3, V: 4.2,
};

function computeFeatures(seq: string): Record<string, number> {
  const n = seq.length;
  const count = (letters: string) => seq.split("").filter((c) => letters.includes(c)).length;
  let hyd = 0;
  for (const c of seq) hyd += KD[c] ?? 0;
  const covered = new Array(n).fill(false);
  for (let i = 0; i + 8 <= n; i++) {
    if (new Set(seq.slice(i, i + 8)).size <= 3) for (let j = i; j < i + 8; j++) covered[j] = true;
  }
  const r = (v: number) => Math.round(v * 100) / 100;
  return {
    length: n,
    fraction_charged: r(count("DEKR") / n),
    net_charge_per_residue: r((count("KR") - count("DE")) / n),
    mean_hydropathy: r(hyd / n),
    glycine: r(count("G") / n),
    serine: r(count("S") / n),
    histidine: r(count("H") / n),
    gly_ser_his: r(count("GSH") / n),
    low_complexity: r(covered.filter(Boolean).length / n),
  };
}

type Spec = {
  score: number;
  label: string;
  top: [string, number][];
  neighbours: Neighbour[];
  why: (f: Record<string, number>, motifs: string) => string;
};

const pct = (v: number) => `${Math.round(v * 100)}%`;

const SPECS: Record<string, Spec> = {
  dehydrin: {
    score: 0.96,
    label: "protective",
    top: [["low_complexity", 1.42], ["gly_ser_his", 0.88], ["mean_hydropathy", -0.51]],
    neighbours: [
      { accession: "A0A346RSN4", cosine: 0.91, family: "dehydrin" },
      { accession: "Q9XGK9", cosine: 0.88, family: "LEA" },
      { accession: "DEMO-01", cosine: 0.84, family: "dehydrin" },
      { accession: "DEMO-02", cosine: 0.79, family: "CAHS" },
      { accession: "DEMO-03", cosine: 0.74, family: "LEA" },
    ],
    why: (f, m) =>
      `This sequence scores 0.96, well above the 0.50 line, so the classifier places it with the desiccation-protective families. The biggest push came from low complexity (${pct(f.low_complexity)} of residues sit in repetitive stretches), followed by its glycine, serine and histidine content (${pct(f.gly_ser_his)}). Its mean hydropathy of ${f.mean_hydropathy} pulled slightly the other way. ${m} A high score means it resembles the family, not that it protects strongly.`,
  },
  cahs: {
    score: 0.91,
    label: "protective",
    top: [["gly_ser_his", 1.1], ["fraction_charged", 0.74], ["low_complexity", 0.35]],
    neighbours: [
      { accession: "Q9XGK9", cosine: 0.83, family: "LEA" },
      { accession: "DEMO-04", cosine: 0.81, family: "CAHS" },
      { accession: "DEMO-05", cosine: 0.77, family: "CAHS" },
      { accession: "A0A346RSN4", cosine: 0.7, family: "dehydrin" },
    ],
    why: (f, m) =>
      `This sequence scores 0.91, so it lands on the protective side. Glycine, serine and histidine make up ${pct(f.gly_ser_his)} of the chain, which was the strongest argument for the call, and a high share of charged residues (${pct(f.fraction_charged)}) added to it. Low complexity helped a little (${pct(f.low_complexity)}). ${m} This is family membership, not a measure of protection.`,
  },
  folded: {
    score: 0.07,
    label: "other_idp",
    top: [["low_complexity", -0.95], ["fraction_charged", -0.62], ["gly_ser_his", -0.4]],
    neighbours: [
      { accession: "DEMO-06", cosine: 0.52, family: "LEA" },
      { accession: "DEMO-07", cosine: 0.44, family: "dehydrin" },
      { accession: "DEMO-08", cosine: 0.38, family: "CAHS" },
    ],
    why: (f, m) =>
      `This sequence scores 0.07, far below the 0.50 line, so it does not look like the protective families. Almost none of it is repetitive (${pct(f.low_complexity)} low complexity), its charged share is modest (${pct(f.fraction_charged)}) and glycine, serine and histidine are scarce (${pct(f.gly_ser_his)}). All three argued against the call. ${m} This is the folded control, so a low score is the expected result.`,
  },
};

export function demoFor(raw: string): ScoreResult | null {
  const seq = cleanSequence(raw);
  const ex = EXAMPLES.find((e) => e.seq === seq);
  if (!ex) return null;
  const spec = SPECS[ex.id];
  if (!spec) return null;
  const f = computeFeatures(seq);
  const motifs = scanMotifs(seq);
  const m =
    motifs.length > 0
      ? `The motif scan also found ${motifs.length} match${motifs.length > 1 ? "es" : ""} in the sequence, highlighted in the residue map.`
      : "The motif scan found no K-segment or Gly/Ser repeat.";
  const first = spec.neighbours[0];
  return {
    score: spec.score,
    label: spec.label,
    nearest_homolog: first && !first.accession.startsWith("DEMO") ? first.accession : null,
    top_features: spec.top,
    features: f,
    explanation: spec.why(f, m),
    neighbours: spec.neighbours,
    demo: true,
  };
}
