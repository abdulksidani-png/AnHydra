import type { Health } from "@/lib/protein";

export function Tardigrade({ animated = false, className }: { animated?: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 250 130" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <g className={animated ? "tardi-legs" : undefined}>
        <path d="M66 92 L60 110 M60 110 l-5 3 M60 110 l1 5 M60 110 l5 3" />
        <path d="M102 97 L99 112 M99 112 l-5 3 M99 112 l1 5 M99 112 l5 3" />
        <path d="M142 98 L142 113 M142 113 l-5 3 M142 113 l0 5 M142 113 l5 3" />
        <path d="M178 93 L183 109 M183 109 l-5 3 M183 109 l1 5 M183 109 l5 3" />
      </g>
      <g className={animated ? "tardi-body" : undefined}>
        <path d="M40 62 C40 32 90 22 140 24 C180 26 200 40 202 58 C204 80 176 96 140 96 C90 98 40 92 40 62Z" />
        <path d="M200 48 C218 50 226 58 224 66 C222 74 212 78 200 76" />
        <path d="M76 28 C70 50 72 72 78 94 M108 24 C103 48 104 74 108 97 M140 24 C136 50 137 74 140 96 M172 28 C168 50 169 72 172 94" opacity="0.55" />
        <circle cx="212" cy="58" r="1.8" fill="currentColor" stroke="none" />
        <path d="M222 66 l5 1" />
      </g>
    </svg>
  );
}

export function Masthead({ health, checked }: { health: Health | null; checked: boolean }) {
  let status = "checking model status";
  let tone = "idle";
  if (checked && health?.model_trained) {
    status = "model loaded";
    tone = "live";
  } else if (checked && health && !health.model_trained) {
    status = "model not trained";
    tone = "warn";
  } else if (checked) {
    status = "status unavailable";
    tone = "warn";
  }
  return (
    <div className="masthead">
      <dl className="stamp">
        <div>
          <dt>Model</dt>
          <dd>ESM-2, frozen</dd>
        </div>
        <div>
          <dt>Unseen-family AUC</dt>
          <dd className="glow-text">0.818</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd className={`status status-${tone}`} role="status">
            <span className="dot" aria-hidden="true" />
            {status}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function Hero() {
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-copy">
        <h1 id="hero-title">A tardigrade can lose nearly all of its water, stop, and come back</h1>
        <p>
          A few protein families do that work. CAHS proteins in tardigrades, LEA proteins and dehydrins in plants turn
          the inside of a cell into glass instead of letting it crystallise. Finding more of them matters for shipping
          vaccines without refrigeration.
        </p>
      </div>
      <figure className="hero-fig">
        <div className="hero-stage">
          <svg viewBox="0 0 250 130" className="hero-drops" aria-hidden="true">
            <g fill="currentColor" stroke="none">
              <circle className="drop d1" cx="70" cy="60" r="3" />
              <circle className="drop d2" cx="120" cy="50" r="2.5" />
              <circle className="drop d3" cx="160" cy="62" r="3" />
              <circle className="drop d4" cx="100" cy="70" r="2" />
              <circle className="drop d5" cx="190" cy="52" r="2.5" />
            </g>
          </svg>
          <Tardigrade animated className="hero-tardi" />
        </div>
        <figcaption className="hero-caps">
          <span className="cap c1">hydrated · active</span>
          <span className="cap c2">water leaving</span>
          <span className="cap c3">a tun · metabolism stopped</span>
          <span className="cap c4">rehydrated</span>
        </figcaption>
      </figure>
    </section>
  );
}
