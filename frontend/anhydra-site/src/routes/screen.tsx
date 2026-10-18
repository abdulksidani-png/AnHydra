import { useEffect, useMemo, useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import settings from "@/config/settings.json";
import { Tour, useTour } from "@/components/Tour";
import { Answer, Drivers, ResidueMap, FeatureBars, Skeleton, Specimen, useReducedMotion } from "@/components/Result";
import { Ensemble } from "@/components/Ensemble";
import { EmbeddingMap, NearestOnly, StructurePanel } from "@/components/Evidence";
import {
  ScoreError,
  cleanSequence,
  loadExamples,
  requestHealth,
  requestScore,
  type Example,
  type Health,
  type ScoreResult,
} from "@/lib/protein";

export const Route = createFileRoute("/screen")({
  head: () => settings.routes["/screen"],
  component: ScreenPage,
});

type Fail = { status: number; message: string };

function ScreenPage() {
  const reduced = useReducedMotion();
  const tour = useTour();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [shownSeq, setShownSeq] = useState("");
  const [fail, setFail] = useState<Fail | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [checked, setChecked] = useState(false);
  const [examples, setExamples] = useState<Example[]>([]);
  const [runId, setRunId] = useState(0);
  const area = useRef<HTMLTextAreaElement | null>(null);
  const resultRef = useRef<HTMLDivElement | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    let live = true;
    requestHealth().then((h) => {
      if (!live) return;
      setHealth(h);
      setChecked(true);
    });
    loadExamples().then((list) => {
      if (live) setExamples(list);
    });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!busy) return;
    const t0 = Date.now();
    setElapsed(0);
    const id = window.setInterval(() => setElapsed(Date.now() - t0), 500);
    return () => window.clearInterval(id);
  }, [busy]);

  const cleaned = useMemo(() => cleanSequence(text), [text]);

  const submit = async () => {
    if (busy) return;
    const seq = cleaned;
    if (!seq) {
      setFail({ status: 400, message: "Paste an amino-acid sequence first." });
      area.current?.focus();
      return;
    }
    abort.current?.abort();
    const ac = new AbortController();
    abort.current = ac;
    setBusy(true);
    setFail(null);
    setResult(null);
    try {
      const r = await requestScore(text.trim(), ac.signal);
      setShownSeq(seq);
      setResult(r);
      setRunId((n) => n + 1);
      window.setTimeout(() => resultRef.current?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" }), 50);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      const err = e instanceof ScoreError ? e : new ScoreError(0, "Something went wrong while screening.");
      setFail({ status: err.status, message: err.message });
      if (err.status === 400) area.current?.focus();
    } finally {
      setBusy(false);
    }
  };

  const phase =
    elapsed >= 8000
      ? "First request after a restart — loading the model into memory…"
      : elapsed >= 2000
        ? "Embedding with ESM-2…"
        : "Sending the sequence…";

  const invalid = fail?.status === 400;
  const features = result?.top_features ?? [];
  const neighbours = result?.neighbours?.filter((n) => n && typeof n.accession === "string" && Number.isFinite(n.cosine)) ?? [];

  return (
    <div className="page screen-page">
      <a href="#screen" className="skip">
        Skip to the screening form
      </a>
      {checked && health && !health.model_trained ? (
        <div className="banner" role="alert">
          The model is not trained on this server, so screening will fail with a 503. No score will be shown.
        </div>
      ) : null}
      <main>
        <section id="screen" className="screen first" aria-labelledby="screen-title">
          <div className="screen-head">
            <h2 id="screen-title">Screen a sequence</h2>
            <button type="button" className="ghost-btn" onClick={tour.replay}>
              Show me how
            </button>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
            noValidate
          >
            <label htmlFor="seq" className="field-label">
              Amino-acid sequence, raw or one FASTA record
            </label>
            <textarea
              id="seq"
              ref={area}
              value={text}
              onChange={(e) => setText(e.target.value)}
              spellCheck={false}
              autoComplete="off"
              autoCapitalize="characters"
              rows={6}
              placeholder="MAEEY…"
              aria-invalid={invalid || undefined}
              aria-describedby={invalid ? "seq-error seq-count" : "seq-count"}
            />
            <div className="form-row">
              <p id="seq-count" className="mono count">
                {cleaned.length} residues <span className="muted">· 20 to 1022 accepted</span>
              </p>
              <button type="submit" className="screen-btn" disabled={busy}>
                {busy ? "Screening…" : "Screen"}
              </button>
            </div>
            <div className="chips" role="group" aria-label="Example sequences">
              <span className="muted small">
                {examples.length ? "Examples from the training data:" : "No examples on this server; paste a sequence."}
              </span>
              {examples.map((ex) => (
                <button
                  type="button"
                  key={ex.id}
                  className="chip"
                  title={`${ex.name} (UniProt ${ex.accession})`}
                  onClick={() => {
                    setText(ex.seq);
                    setFail(null);
                    area.current?.focus();
                  }}
                >
                  {ex.label} · {ex.accession}
                </button>
              ))}
            </div>
            <div id="seq-error" className="error-slot" aria-live="assertive">
              {fail ? (
                <div className={`error-box err-${fail.status}`}>
                  {fail.status === 401 ? <p className="err-title">Sign in required</p> : null}
                  {fail.status === 503 ? <p className="err-title">The model is not available</p> : null}
                  {fail.status === 0 ? <p className="err-title">Network problem</p> : null}
                  <p>{fail.message}</p>
                  {fail.status === 0 || fail.status >= 500 ? (
                    <button type="button" className="ghost-btn" onClick={submit}>
                      Try again
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>
          </form>
        </section>

        <div ref={resultRef} className="result-zone">
          {busy ? <Skeleton phase={phase} /> : null}
          {!busy && result ? (
            <div key={runId}>
              <Answer result={result} seq={shownSeq} reduced={reduced} />
              <div className="evidence-rule">
                <span>the evidence behind it</span>
              </div>
              <div className="support-grid">
                {features.length > 0 ? (
                  <div className="card fade wide" style={{ animationDelay: "0ms" }}>
                    <Drivers features={features} values={result.features} />
                  </div>
                ) : null}
                <div className="card fade wide" style={{ animationDelay: "70ms" }}>
                  {neighbours.length > 0 ? <EmbeddingMap neighbours={neighbours} /> : <NearestOnly accession={result.nearest_homolog} />}
                </div>
                <div className="card fade wide" style={{ animationDelay: "140ms" }}>
                  <StructurePanel accession={result.nearest_homolog} />
                </div>
                <div className="card fade wide" style={{ animationDelay: "175ms" }}>
                  <Ensemble seq={shownSeq} />
                </div>
                <div className="card fade" style={{ animationDelay: "210ms" }}>
                  <Specimen length={result.features?.length} seq={shownSeq} />
                </div>
                <div className="card fade wide" style={{ animationDelay: "280ms" }}>
                  <FeatureBars features={result.features ?? {}} />
                </div>
                <div className="card fade wide" style={{ animationDelay: "350ms" }}>
                  <ResidueMap seq={shownSeq} reduced={reduced} />
                </div>
              </div>
            </div>
          ) : null}
        </div>

      </main>
      <Tour step={tour.step} setStep={tour.setStep} finish={tour.finish} />
    </div>
  );
}
