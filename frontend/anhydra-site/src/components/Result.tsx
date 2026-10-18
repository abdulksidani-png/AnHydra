import { useEffect, useMemo, useState } from "react";
import {
  FEATURE_EXPLAIN,
  FEATURE_INFO,
  FEATURE_ORDER,
  LEGEND,
  MOTIF_INFO,
  RESIDUE_CLASS,
  featureLabel,
  scanMotifs,
  type ScoreResult,
} from "@/lib/protein";

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    try {
      const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
      setReduced(mq.matches);
      const on = () => setReduced(mq.matches);
      mq.addEventListener("change", on);
      return () => mq.removeEventListener("change", on);
    } catch {
      return;
    }
  }, []);
  return reduced;
}

function useCountUp(target: number, reduced: boolean, ms = 1000): number {
  const [v, setV] = useState(reduced ? target : 0);
  useEffect(() => {
    if (reduced) {
      setV(target);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / ms);
      setV(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, reduced, ms]);
  return v;
}

const R = 88;
const C = 2 * Math.PI * R;

export function Dial({ score, protective, reduced }: { score: number; protective: boolean; reduced: boolean }) {
  const s = Math.min(1, Math.max(0, score));
  const [go, setGo] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setGo(true));
    return () => cancelAnimationFrame(id);
  }, []);
  const shown = useCountUp(s, reduced);
  const offset = go || reduced ? C * (1 - s) : C;
  return (
    <div className="dial">
      <svg viewBox="0 0 220 236" role="img" aria-label={`Score ${s.toFixed(2)} out of 1. The decision line is at 0.50.`}>
        <g transform="translate(110 110)">
          <circle r={R} className="dial-track" />
          <circle
            r={R}
            className={protective ? "dial-arc dial-up" : "dial-arc dial-down"}
            strokeDasharray={C}
            strokeDashoffset={offset}
            transform="rotate(-90)"
          />
          <line x1="0" y1={R - 14} x2="0" y2={R + 14} className="dial-line" />
          <text x="0" y={R + 30} textAnchor="middle" className="dial-tick">
            0.50 line
          </text>
          <text x="0" y="12" textAnchor="middle" className="dial-num">
            {shown.toFixed(2)}
          </text>
          <text x="0" y="40" textAnchor="middle" className="dial-sub">
            family score
          </text>
        </g>
      </svg>
    </div>
  );
}

function formatValue(name: string, v: number): string {
  if (!Number.isFinite(v)) return "missing";
  if (name === "length") return String(Math.round(v));
  return v.toFixed(2);
}

export function ResidueMap({ seq, reduced }: { seq: string; reduced: boolean }) {
  const motifs = useMemo(() => scanMotifs(seq), [seq]);
  const [ignited, setIgnited] = useState(reduced);
  const n = seq.length;
  const step = Math.min(14, 1400 / Math.max(n, 1));
  useEffect(() => {
    if (reduced) {
      setIgnited(true);
      return;
    }
    setIgnited(false);
    const id = window.setTimeout(() => setIgnited(true), n * step + 400);
    return () => window.clearTimeout(id);
  }, [seq, reduced, n, step]);

  const marks = useMemo(() => {
    const m: string[] = new Array(n).fill("");
    for (const mo of motifs) {
      for (let i = mo.start; i < mo.end && i < n; i++) m[i] += ` m-${mo.kind}`;
    }
    return m;
  }, [motifs, n]);

  const chunks: number[] = [];
  for (let i = 0; i < n; i += 10) chunks.push(i);

  return (
    <div className="resmap-wrap">
      <div className="block-head">
        <h3>Residue map</h3>
        <p className="muted">One cell per residue, coloured by chemistry. {n} residues.</p>
      </div>
      <div className="resmap" role="img" aria-label={`Residue map of ${n} residues. ${motifs.length} motif matches found.`}>
        {chunks.map((start) => (
          <span className="chunk" key={start}>
            {seq
              .slice(start, start + 10)
              .split("")
              .map((ch, j) => {
                const i = start + j;
                const cls = RESIDUE_CLASS[ch];
                return (
                  <span
                    key={i}
                    className={`res${ignited ? marks[i] : ""}`}
                    style={{ ["--c" as string]: cls?.color ?? "var(--silt)", animationDelay: `${Math.round(i * step)}ms` }}
                  >
                    {ch}
                  </span>
                );
              })}
          </span>
        ))}
      </div>
      <ul className="legend" aria-label="Residue colour key">
        {LEGEND.map((l) => (
          <li key={l.key}>
            <span className="swatch" style={{ background: l.color }} aria-hidden="true" />
            {l.letters.split("").join(" ")}
            <span className="legend-name"> {l.name.split(" (")[0]}</span>
          </li>
        ))}
      </ul>
      <div className="motifs">
        <h3>Motifs found in this sequence</h3>
        {motifs.length === 0 ? (
          <p className="muted">
            No dehydrin K-segment or Gly/Ser repeat found. That is not evidence against the call: the model reads more
            than these two patterns.
          </p>
        ) : (
          <ul>
            {motifs.map((m, i) => (
              <li key={`${m.kind}-${m.start}-${i}`} className={`motif motif-${m.kind}`}>
                <span className="motif-key" aria-hidden="true" />
                <div>
                  <p className="motif-name">
                    {MOTIF_INFO[m.kind].name}
                    <span className="mono muted"> · residues {m.start + 1}–{m.end}</span>
                  </p>
                  <p className="mono motif-seq">{seq.slice(m.start, m.end)}</p>
                  <p className="muted">{MOTIF_INFO[m.kind].note}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
        <p className="kseg-note">
          The K-segment matters: a CNN we trained from scratch, with no motif database, rediscovered it on its own. It
          is the published motif that defines the dehydrin family.
        </p>
      </div>
    </div>
  );
}

function whyLine(features: [string, number][]): string {
  if (features.length === 0) return "";
  const parts = features.map(([n, v]) => `${featureLabel(n)} (${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2)})`);
  const up = features.filter(([, v]) => v >= 0);
  const down = features.filter(([, v]) => v < 0);
  let s = "The three strongest contributions were " + parts.join(", ") + ". ";
  if (up.length) s += "Pushing toward the protective call: " + up.map(([n]) => featureLabel(n).toLowerCase()).join(", ") + ". ";
  if (down.length) s += "Pushing against it: " + down.map(([n]) => featureLabel(n).toLowerCase()).join(", ") + ". ";
  return s.trim();
}

export function Answer({ result, seq, reduced }: { result: ScoreResult; seq: string; reduced: boolean }) {
  const protective = result.label === "protective";
  return (
    <section className="answer" aria-labelledby="answer-title">
      <h2 id="answer-title" className="sr-only">
        Result
      </h2>
      {result.demo ? (
        <p className="demo-flag" role="note">
          <strong>Demo result.</strong> The score, contributions, neighbours and explanation below are sample values
          written for this demo. They are not output from the model.
        </p>
      ) : null}
      <div className="answer-top">
        <Dial score={result.score} protective={protective} reduced={reduced} />
        <div className="answer-text">
          <p className={`pill ${protective ? "pill-up" : "pill-down"}`}>
            <span aria-hidden="true">{protective ? "▲" : "▼"}</span>
            {protective ? "protective family" : "other disordered protein"}
          </p>
          <p className="verdict">
            {protective
              ? "This sequence looks like it belongs to the desiccation-protective families."
              : "This sequence does not look like it belongs to the desiccation-protective families."}
          </p>
          <p className="honest">
            The score is family membership, used for triage. It does not say how much protection a protein gives.
          </p>
          {result.explanation ? (
            <blockquote className="readout">
              <p>{result.explanation}</p>
              <footer>
                {result.demo
                  ? "Sample explanation written for the demo, not generated by Gemini."
                  : "Written by Google Gemini from the score, label and contributions. A summary, not the model's reasoning."}
              </footer>
            </blockquote>
          ) : null}
          {result.top_features?.length ? (
            <div className="why">
              <h3>Why this score</h3>
              <p>{whyLine(result.top_features)}</p>
              <p className="muted small">Signed contributions: plus argues for protective, minus argues against.</p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function Drivers({ features, values }: { features: [string, number][]; values?: Record<string, number> }) {
  const max = Math.max(0.0001, ...features.map(([, v]) => Math.abs(v)));
  return (
    <div>
      <h3>What drove the call</h3>
      <p className="muted small">Signed contributions. Plus argues for protective, minus argues against.</p>
      <ul className="drivers">
        {features.map(([name, v]) => {
          const pos = v >= 0;
          const w = (Math.abs(v) / max) * 50;
          return (
            <li key={name}>
              <div className="drv-head">
                <span>{featureLabel(name)}</span>
                <span className={`mono ${pos ? "for" : "against"}`}>
                  {pos ? "+" : "−"}
                  {Math.abs(v).toFixed(2)} · {pos ? "for" : "against"}
                </span>
              </div>
              {FEATURE_EXPLAIN[name] ? (
                <p className="drv-why">
                  <span className="muted">{FEATURE_EXPLAIN[name].what}</span>{" "}
                  {values && typeof values[name] === "number" ? (
                    <span className="mono muted">This sequence: {formatValue(name, values[name])}. </span>
                  ) : null}
                  {pos ? FEATURE_EXPLAIN[name].for : FEATURE_EXPLAIN[name].against}
                </p>
              ) : null}
              <div className="bipolar" aria-hidden="true">
                <span className="mid" />
                <span className={pos ? "fill fill-for" : "fill fill-against"} style={pos ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function Specimen({ length, seq }: { length: number | undefined; seq: string }) {
  const counts = LEGEND.map((l) => ({
    ...l,
    n: seq.split("").filter((c) => l.letters.includes(c)).length,
  }));
  const total = Math.max(1, seq.length);
  return (
    <div>
      <h3>Specimen length</h3>
      <p className="big mono">
        {length !== undefined && Number.isFinite(length) ? Math.round(length) : seq.length}
        <span className="muted small"> residues</span>
      </p>
      <p className="muted small">Accepted range 20 to 1022 residues.</p>
      <div className="comp" role="img" aria-label="Composition by residue chemistry">
        {counts.map((c) => (
          <span key={c.key} style={{ width: `${(c.n / total) * 100}%`, background: c.color }} title={`${c.name}: ${c.n}`} />
        ))}
      </div>
      <p className="muted small">Composition by chemistry, counted from your sequence.</p>
    </div>
  );
}

export function FeatureBars({ features }: { features: Record<string, number> }) {
  return (
    <div>
      <h3>All nine features</h3>
      <p className="muted small">Each bar sits within the feature's natural range.</p>
      <ul className="features">
        {FEATURE_ORDER.map((name) => {
          const info = FEATURE_INFO[name];
          const v = features?.[name];
          const ok = typeof v === "number" && Number.isFinite(v);
          const frac = ok ? Math.min(1, Math.max(0, (v - info.min) / (info.max - info.min))) : 0;
          return (
            <li key={name}>
              <div className="drv-head">
                <span>
                  {info.label}
                  <span className="muted small"> · {info.hint}</span>
                </span>
                <span className="mono">{ok ? formatValue(name, v) : "missing"}</span>
              </div>
              <div className="meter" aria-hidden="true">
                {info.diverging ? <span className="mid" /> : null}
                {ok ? (
                  info.diverging ? (
                    <span className="fill fill-neutral" style={{ left: `${Math.min(frac, 0.5) * 100}%`, width: `${Math.abs(frac - 0.5) * 100}%` }} />
                  ) : (
                    <span className="fill fill-neutral" style={{ left: 0, width: `${frac * 100}%` }} />
                  )
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function DemoGauge({ target, reduced }: { target: number; reduced: boolean }) {
  const v = useCountUp(target, reduced, 3200);
  return (
    <div className="gauge" role="img" aria-label="Simulated closeness meter">
      <div className="gauge-head">
        <span className="mono">closeness to the protective families</span>
        <span className="mono gauge-num">{Math.round(v * 100)}%</span>
      </div>
      <div className="gauge-track">
        <span className="gauge-fill" style={{ width: `${v * 100}%` }} />
        <span className="gauge-scan" />
        <span className="gauge-mark" />
      </div>
      <p className="mono small muted">Simulated run, sample values. The 50% mark is the decision line.</p>
    </div>
  );
}

export function Skeleton({ phase, demoScore, reduced = false }: { phase: string; demoScore?: number; reduced?: boolean }) {
  return (
    <section className="waiting" aria-busy="true" aria-label="Waiting for the result">
      <p className="wait-line" role="status" aria-live="polite">
        <span className="wait-dot" aria-hidden="true" />
        {phase}
      </p>
      {demoScore !== undefined ? <DemoGauge target={demoScore} reduced={reduced} /> : null}
      <div className="answer sk">
        <div className="answer-top">
          <div className="dial">
            <div className="sk-block sk-ring" />
          </div>
          <div className="answer-text">
            <div className="sk-block" style={{ width: "9rem", height: "2rem" }} />
            <div className="sk-block" style={{ width: "100%", height: "1.4rem" }} />
            <div className="sk-block" style={{ width: "70%", height: "1rem" }} />
            <div className="sk-block" style={{ width: "100%", height: "5.5rem" }} />
          </div>
        </div>
        <div className="sk-block" style={{ width: "100%", height: "8rem" }} />
      </div>
      <div className="evidence-rule">
        <span>the evidence behind it</span>
      </div>
      <div className="support-grid">
        {[11, 14, 12, 9].map((h, i) => (
          <div className="card sk" key={i}>
            <div className="sk-block" style={{ width: "50%", height: "1.1rem" }} />
            <div className="sk-block" style={{ width: "100%", height: `${h}rem` }} />
          </div>
        ))}
      </div>
    </section>
  );
}
