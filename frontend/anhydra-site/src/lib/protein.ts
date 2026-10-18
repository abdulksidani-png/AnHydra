import { TokenError, authorizationHeaders } from "../auth/token.ts";

export type Neighbour = { accession: string; cosine: number; family?: string | null };

export type ScoreResult = {
  score: number;
  label: "protective" | "other_idp" | string;
  nearest_homolog: string | null;
  top_features: [string, number][];
  features: Record<string, number>;
  explanation?: string;
  neighbours?: Neighbour[];
};

export type Health = { status: string; model_trained: boolean };

export const API_BASE = "";

export const RESIDUE_CLASS: Record<string, { key: string; name: string; color: string }> = {};
const groups: [string, string, string, string][] = [
  ["DE", "acidic", "Acidic (D, E)", "var(--res-acidic)"],
  ["KRH", "basic", "Basic (K, R, H)", "var(--res-basic)"],
  ["STNQCY", "polar", "Polar (S, T, N, Q, C, Y)", "var(--res-polar)"],
  ["AVLIMFW", "hydro", "Hydrophobic (A, V, L, I, M, F, W)", "var(--res-hydro)"],
  ["GP", "flex", "Flexible (G, P)", "var(--res-flex)"],
];
for (const [letters, key, name, color] of groups) {
  for (const ch of letters) RESIDUE_CLASS[ch] = { key, name, color };
}
export const LEGEND = groups.map(([letters, key, name, color]) => ({ letters, key, name, color }));

export function cleanSequence(raw: string): string {
  const lines = raw.split(/\r?\n/).filter((l) => !l.trim().startsWith(">"));
  return lines.join("").replace(/\s+/g, "").toUpperCase();
}

export type Motif = { kind: "kseg" | "kcore" | "gs"; start: number; end: number };

export const MOTIF_INFO: Record<Motif["kind"], { name: string; note: string }> = {
  kseg: {
    name: "Dehydrin K-segment (full)",
    note: "The published motif that defines the dehydrin family.",
  },
  kcore: {
    name: "K-segment core",
    note: "The conserved core of the K-segment.",
  },
  gs: {
    name: "Gly/Ser repeat",
    note: "CAHS-style glycine and serine rich stretch.",
  },
};

export function scanMotifs(seq: string): Motif[] {
  const defs: [Motif["kind"], RegExp][] = [
    ["kseg", /[A-Z]K[A-Z]G[A-Z]{2}[DE]KIK[DE]K[A-Z]PG/g],
    ["kcore", /K[IL]K[DE]K[A-Z]PG/g],
    ["gs", /(?:[GS]{2,}[A-Z]{0,2}){4,}/g],
  ];
  const out: Motif[] = [];
  for (const [kind, re] of defs) {
    for (const m of seq.matchAll(re)) {
      if (m.index === undefined || m[0].length === 0) continue;
      out.push({ kind, start: m.index, end: m.index + m[0].length });
    }
  }
  return out.sort((a, b) => a.start - b.start);
}

export const FEATURE_INFO: Record<
  string,
  { label: string; hint: string; min: number; max: number; diverging?: boolean }
> = {
  length: { label: "Length", hint: "residues", min: 20, max: 1022 },
  fraction_charged: { label: "Fraction charged", hint: "share of D, E, K, R", min: 0, max: 1 },
  net_charge_per_residue: {
    label: "Net charge per residue",
    hint: "negative to positive",
    min: -1,
    max: 1,
    diverging: true,
  },
  mean_hydropathy: {
    label: "Mean hydropathy",
    hint: "Kyte-Doolittle, hydrophilic to hydrophobic",
    min: -4.5,
    max: 4.5,
    diverging: true,
  },
  glycine: { label: "Glycine", hint: "fraction of residues", min: 0, max: 1 },
  serine: { label: "Serine", hint: "fraction of residues", min: 0, max: 1 },
  histidine: { label: "Histidine", hint: "fraction of residues", min: 0, max: 1 },
  gly_ser_his: { label: "Gly + Ser + His", hint: "combined fraction", min: 0, max: 1 },
  low_complexity: { label: "Low complexity", hint: "fraction of residues", min: 0, max: 1 },
};

export const FEATURE_ORDER = [
  "length",
  "fraction_charged",
  "net_charge_per_residue",
  "mean_hydropathy",
  "glycine",
  "serine",
  "histidine",
  "gly_ser_his",
  "low_complexity",
];

export function featureLabel(name: string): string {
  return FEATURE_INFO[name]?.label ?? name.replace(/_/g, " ");
}

export const FEATURE_EXPLAIN: Record<string, { what: string; for: string; against: string }> = {
  length: {
    what: "Number of residues in the chain.",
    for: "Protective families tend to sit in a characteristic length range, and this sequence falls in it.",
    against: "This length is atypical for the protective families the model was trained on.",
  },
  fraction_charged: {
    what: "Share of residues that carry a charge (D, E, K, R).",
    for: "A high charged share is common in disordered, water-loving proteins like the protective families, which stay flexible when drying.",
    against: "Few charged residues is more typical of folded or membrane proteins than of the protective families.",
  },
  net_charge_per_residue: {
    what: "Overall charge divided by length, from strongly negative to strongly positive.",
    for: "The overall charge balance resembles the protective families.",
    against: "The overall charge balance looks unlike the protective families.",
  },
  mean_hydropathy: {
    what: "Average water-avoidance of the residues. Low values mean the chain is water-loving.",
    for: "A water-loving chain stays unfolded and hydrated, which fits the protective families.",
    against: "A more water-avoiding chain tends to collapse into a fold, which argues against a protective-family call.",
  },
  glycine: {
    what: "Share of glycine, the smallest and most flexible residue.",
    for: "Glycine-rich chains stay flexible, a hallmark of the protective families.",
    against: "Little glycine suggests a stiffer chain than the protective families usually have.",
  },
  serine: {
    what: "Share of serine, a small polar residue.",
    for: "Serine-rich stretches are common in disordered protective proteins.",
    against: "Little serine is less typical of the protective families.",
  },
  histidine: {
    what: "Share of histidine, which can bind metals and buffer pH.",
    for: "Histidine content is in the range seen in dehydrin-type proteins.",
    against: "Histidine content is outside the range typical of the protective families.",
  },
  gly_ser_his: {
    what: "Combined share of glycine, serine and histidine.",
    for: "These three residues together are over-represented in protective families such as dehydrins and CAHS proteins.",
    against: "These three residues are scarce here, unlike in the protective families.",
  },
  low_complexity: {
    what: "Share of the chain made of repetitive stretches built from only a few residue types.",
    for: "Repetitive, low-complexity stretches are a signature of the disordered protective proteins.",
    against: "The sequence is varied rather than repetitive, which is more typical of folded proteins.",
  },
};

export function isSample(accession: string): boolean {
  return accession.startsWith("DEMO-");
}

export function uniprotUrl(accession: string): string {
  return `https://www.uniprot.org/uniprotkb/${encodeURIComponent(accession)}`;
}

export type Example = { id: string; label: string; accession: string; name: string; seq: string };

// examples.json is written at deploy time by scripts/pick_examples.py from the training data, so the
// buttons always show real proteins. Without it (local dev, previews) the page simply has none.
export async function loadExamples(): Promise<Example[]> {
  try {
    const res = await fetch(`${API_BASE}/examples.json`);
    if (!res.ok) return [];
    const list: unknown = await res.json();
    if (!Array.isArray(list)) return [];
    return list.filter(
      (e): e is Example =>
        !!e &&
        typeof e === "object" &&
        ["id", "label", "accession", "name", "seq"].every((k) => typeof (e as Record<string, unknown>)[k] === "string") &&
        /^[A-Z]+$/.test((e as Example).seq),
    );
  } catch {
    return [];
  }
}

export class ScoreError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function detailText(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const d = (body as { detail?: unknown }).detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    const parts = d
      .map((x) => (x && typeof x === "object" && "msg" in x ? String((x as { msg: unknown }).msg) : null))
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  return null;
}

export async function requestScore(sequence: string, signal?: AbortSignal): Promise<ScoreResult> {
  let auth: Record<string, string>;
  try {
    auth = await authorizationHeaders();
  } catch (e) {
    if (e instanceof TokenError && e.reason !== "expired") throw new ScoreError(0, "Still signing you in. Try again in a moment.");
    throw new ScoreError(401, "Your session has expired. Log in again to screen sequences.");
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth },
      body: JSON.stringify({ sequence }),
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ScoreError(0, "The screening service could not be reached.");
  }
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const detail = detailText(body);
    if (res.status === 401) throw new ScoreError(401, detail ?? "Log in to screen sequences.");
    throw new ScoreError(res.status, detail ?? `The server answered with status ${res.status}.`);
  }
  const r = body as ScoreResult | null;
  if (!r || typeof r.score !== "number" || !Number.isFinite(r.score)) {
    throw new ScoreError(502, "The server's answer did not contain a score.");
  }
  const raw: unknown = r.neighbours;
  return { ...r, neighbours: Array.isArray(raw) ? raw.map(toNeighbour).filter((n): n is Neighbour => n !== null) : undefined };
}

// The backend sends each neighbour as [accession, cosine, family]; the components read named fields.
function toNeighbour(n: unknown): Neighbour | null {
  if (Array.isArray(n)) {
    const [accession, cosine, family] = n;
    if (typeof accession !== "string" || typeof cosine !== "number") return null;
    return { accession, cosine, family: typeof family === "string" ? family : null };
  }
  return n && typeof n === "object" ? (n as Neighbour) : null;
}

export async function requestHealth(): Promise<Health | null> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) return null;
    const j = (await res.json()) as Health;
    if (typeof j?.model_trained !== "boolean") return null;
    return j;
  } catch {
    return null;
  }
}

export type CaPoint = { x: number; y: number; z: number; plddt: number };

export type AlphaFoldState =
  | { kind: "loading" }
  | { kind: "none" }
  | { kind: "error"; message: string }
  | { kind: "ready"; points: CaPoint[]; entry: string };

export async function loadAlphaFold(accession: string, signal: AbortSignal): Promise<AlphaFoldState> {
  let res: Response;
  try {
    res = await fetch(`https://alphafold.ebi.ac.uk/api/prediction/${encodeURIComponent(accession)}`, { signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    return { kind: "error", message: "AlphaFold DB could not be reached." };
  }
  if (res.status === 404) return { kind: "none" };
  if (!res.ok) return { kind: "error", message: `AlphaFold DB answered with status ${res.status}.` };
  let list: unknown;
  try {
    list = await res.json();
  } catch {
    return { kind: "error", message: "AlphaFold DB sent an unreadable answer." };
  }
  const first = Array.isArray(list) ? (list[0] as { pdbUrl?: string; entryId?: string } | undefined) : undefined;
  if (!first?.pdbUrl) return { kind: "none" };
  try {
    const pdbRes = await fetch(first.pdbUrl, { signal });
    if (!pdbRes.ok) return { kind: "error", message: "The structure file could not be downloaded." };
    const text = await pdbRes.text();
    const points: CaPoint[] = [];
    for (const line of text.split("\n")) {
      if (!line.startsWith("ATOM") || line.slice(12, 16).trim() !== "CA") continue;
      const x = parseFloat(line.slice(30, 38));
      const y = parseFloat(line.slice(38, 46));
      const z = parseFloat(line.slice(46, 54));
      const plddt = parseFloat(line.slice(60, 66));
      if ([x, y, z, plddt].every(Number.isFinite)) points.push({ x, y, z, plddt });
    }
    if (points.length < 2) return { kind: "none" };
    return { kind: "ready", points, entry: first.entryId ?? accession };
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    return { kind: "error", message: "The structure file could not be downloaded." };
  }
}

export function plddtColor(v: number): string {
  if (v > 90) return "#2f6fe0";
  if (v > 70) return "#65cbf3";
  if (v > 50) return "#ffdb13";
  return "#ff7d45";
}
