import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Step = { target: string; title: string; body: string };

const STEPS: Step[] = [
  {
    target: "#seq",
    title: "Paste a protein sequence",
    body: "Drop in raw amino-acid letters or one FASTA record. It needs between 20 and 1022 residues.",
  },
  {
    target: ".chips",
    title: "No sequence handy?",
    body: "These example chips fill the box for you. They are illustrative sequences for trying the tool, plus a folded control that should score low.",
  },
  {
    target: "#seq-count",
    title: "Live residue count",
    body: "This counts the residues as you type, ignoring any FASTA header and spaces, so you know you are inside the accepted range.",
  },
  {
    target: ".screen-btn",
    title: "Screen it",
    body: "This sends the sequence to the model. The first run after a restart can take about 15 seconds while it loads, and the page will tell you what it is doing.",
  },
  {
    target: ".screen-btn",
    title: "Then read the answer",
    body: "You get a dial from 0 to 1 with a line at 0.50, a residue map with any motifs found, and the evidence behind the call. The score says whether a protein belongs to the protective families. It does not say how much it protects.",
  },
];

const KEY = "anhydra-tour-done";

export function useTour() {
  const [step, setStep] = useState<number | null>(null);
  useEffect(() => {
    let seen = false;
    try {
      seen = window.localStorage.getItem(KEY) === "1";
    } catch {
      seen = false;
    }
    if (!seen) {
      const id = window.setTimeout(() => setStep(0), 1600);
      return () => window.clearTimeout(id);
    }
  }, []);
  const finish = useCallback(() => {
    setStep(null);
    try {
      window.localStorage.setItem(KEY, "1");
    } catch {
      return;
    }
  }, []);
  return { step, setStep, finish, replay: () => setStep(0) };
}

type Rect = { top: number; left: number; width: number; height: number };

export function Tour({ step, setStep, finish }: { step: number | null; setStep: (n: number) => void; finish: () => void }) {
  const [rect, setRect] = useState<Rect | null>(null);
  const [vh, setVh] = useState(0);
  const card = useRef<HTMLDivElement | null>(null);

  const measure = useCallback(() => {
    if (step === null) return;
    const el = document.querySelector(STEPS[step].target);
    if (!el) return;
    const r = el.getBoundingClientRect();
    setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    setVh(window.innerHeight);
  }, [step]);

  useLayoutEffect(() => {
    if (step === null) return;
    const el = document.querySelector(STEPS[step].target);
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
    measure();
    let raf = 0;
    const t0 = performance.now();
    const follow = () => {
      measure();
      if (performance.now() - t0 < 1800) raf = requestAnimationFrame(follow);
    };
    raf = requestAnimationFrame(follow);
    return () => cancelAnimationFrame(raf);
  }, [step, measure]);

  useEffect(() => {
    if (step === null) return;
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") finish();
      if (e.key === "ArrowRight") setStep(Math.min(step + 1, STEPS.length - 1));
      if (e.key === "ArrowLeft") setStep(Math.max(step - 1, 0));
    };
    window.addEventListener("keydown", key);
    card.current?.focus();
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
      window.removeEventListener("keydown", key);
    };
  }, [step, measure, finish, setStep]);

  if (step === null || !rect) return null;
  const s = STEPS[step];
  const pad = 8;
  const below = rect.top + rect.height + 200 < vh;
  const cardTop = below ? rect.top + rect.height + pad + 14 : Math.max(12, rect.top - pad - 14 - 190);
  const cardLeft = Math.min(Math.max(12, rect.left), Math.max(12, window.innerWidth - 332));
  const last = step === STEPS.length - 1;

  // Rendered into <body>: the screen page's entry animation makes it the containing block for fixed
  // descendants, which would offset the spotlight from the elements it measures.
  return createPortal(
    <div className="tour" role="presentation">
      <div
        className="tour-spot"
        style={{ top: rect.top - pad, left: rect.left - pad, width: rect.width + pad * 2, height: rect.height + pad * 2 }}
      />
      <div
        ref={card}
        tabIndex={-1}
        role="dialog"
        aria-modal="false"
        aria-label={`Tutorial step ${step + 1} of ${STEPS.length}: ${s.title}`}
        className="tour-card"
        style={{ top: cardTop, left: cardLeft }}
        key={step}
      >
        <p className="tour-count mono">
          {step + 1} / {STEPS.length}
        </p>
        <h3>{s.title}</h3>
        <p>{s.body}</p>
        <div className="tour-actions">
          <button type="button" className="ghost-btn" onClick={finish}>
            Skip
          </button>
          <span className="tour-spacer" />
          {step > 0 ? (
            <button type="button" className="ghost-btn" onClick={() => setStep(step - 1)}>
              Back
            </button>
          ) : null}
          <button type="button" className="ghost-btn tour-next" onClick={() => (last ? finish() : setStep(step + 1))}>
            {last ? "Got it" : "Next"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
