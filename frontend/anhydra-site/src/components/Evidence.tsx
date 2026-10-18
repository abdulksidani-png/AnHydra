import { useEffect, useRef, useState } from "react";
import { isSample, loadAlphaFold, plddtColor, uniprotUrl, type AlphaFoldState, type CaPoint, type Neighbour } from "@/lib/protein";
import { OrbitControls, fitCanvas, persp, rotate, useOrbit } from "@/components/Orbit";
import { useReducedMotion } from "@/components/Result";

const FAMILY_COLORS = ["#9aa9c4", "#c4a98a", "#8fb3a3", "#b79aa8", "#a6a98b", "#8f9fb3", "#c2937f"];

function niceStep(x: number): number {
  const p = Math.pow(10, Math.floor(Math.log10(x)));
  const f = x / p;
  const n = f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10;
  return n * p;
}

export function NearestOnly({ accession }: { accession: string | null }) {
  return (
    <div>
      <h3>Nearest sequence</h3>
      {accession ? (
        <>
          <p className="big mono">
            <a href={uniprotUrl(accession)} target="_blank" rel="noreferrer">
              {accession}
            </a>
          </p>
          <p className="muted small">
            The closest known protective sequence in ESM-2 embedding space (cosine neighbour). This is representation
            proximity, not a sequence alignment: no percent identity or E-value is computed.
          </p>
          <p className="muted small">The server did not return similarity values, so no distance map can be drawn.</p>
        </>
      ) : (
        <p className="muted">The server did not name a nearest sequence for this input.</p>
      )}
    </div>
  );
}

type Node3 = { x: number; y: number; z: number; color: string };

export function EmbeddingMap({ neighbours }: { neighbours: Neighbour[] }) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLCanvasElement | null>(null);
  const [active, setActive] = useState<number | null>(null);
  const activeRef = useRef<number | null>(null);
  const drawRef = useRef<() => void>(() => undefined);
  const settleRef = useRef<(dt: number) => void>(() => undefined);
  const hits = useRef<{ x: number; y: number; r: number; i: number }[]>([]);
  const moved = useRef(false);
  const [mode, setMode] = useState<"3d" | "2d">("3d");
  const modeRef = useRef<"3d" | "2d">("3d");
  const flat = useRef(0);
  const pitchT = useRef<number | null>(null);
  const view = useOrbit(ref, () => drawRef.current());

  const items = neighbours.filter((n) => Number.isFinite(n.cosine));
  const families = Array.from(new Set(items.map((n) => n.family || "family not given"))).sort();
  const colorOf = (f: string) => (f === "family not given" ? "#8c8f94" : FAMILY_COLORS[families.indexOf(f) % FAMILY_COLORS.length]);
  const dmax = Math.max(0.001, ...items.map((n) => Math.max(0, 1 - n.cosine)));
  const step = niceStep(dmax / 3);
  const rings: number[] = [];
  for (let d = step; d <= dmax * 1.02; d += step) rings.push(d);

  const setAct = (i: number | null) => {
    if (activeRef.current === i) return;
    activeRef.current = i;
    setActive(i);
    drawRef.current();
  };

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const n = items.length;
    const nodes: Node3[] = items.map((nb, i) => {
      const y = n > 1 ? 1 - (2 * (i + 0.5)) / n : 0.2;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const phi = i * 2.399963;
      const rad = (Math.max(0, 1 - nb.cosine) / dmax) * 0.92;
      return { x: Math.cos(phi) * r * rad, y: y * rad, z: Math.sin(phi) * r * rad, color: colorOf(nb.family || "family not given") };
    });
    const t0 = performance.now();
    let last = t0;
    let raf = 0;
    const ease = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

    const settle = (dt: number) => {
      const v = view.current;
      const two = modeRef.current === "2d";
      v.lock = two;
      const tf = two ? 1 : 0;
      const k = reduced ? 1 : 1 - Math.exp(-dt / 170);
      flat.current += (tf - flat.current) * k;
      if (Math.abs(tf - flat.current) < 0.002) flat.current = tf;
      if (!two && pitchT.current !== null) {
        v.pitch += (pitchT.current - v.pitch) * k;
        if (Math.abs(pitchT.current - v.pitch) < 0.005) {
          v.pitch = pitchT.current;
          pitchT.current = null;
        }
      }
      if (two) {
        const yt = Math.round(v.yaw / (Math.PI * 2)) * Math.PI * 2;
        v.pitch += (Math.PI / 2 - v.pitch) * k;
        v.yaw += (yt - v.yaw) * k;
        v.zoom += (1 - v.zoom) * k;
      }
    };
    settleRef.current = settle;

    const draw = (now = performance.now()) => {
      const { w, h, S } = fitCanvas(canvas, ctx);
      const v = view.current;
      const sc = S * v.zoom;
      const P = (x: number, y: number, z: number) => {
        const [a, b, c] = rotate(v, x, y, z);
        const q = persp(c, flat.current);
        return { x: w / 2 + a * sc * q, y: h / 2 + b * sc * q, z: c, q };
      };
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(180,180,180,0.18)";
      for (const [ax, ay, az] of [[1, 0, 0], [0, 1, 0], [0, 0, 1]]) {
        const a = P(-ax, -ay, -az);
        const b = P(ax, ay, az);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = "rgba(180,180,180,0.3)";
      ctx.fillStyle = "rgba(180,180,180,0.75)";
      ctx.font = "10px IBM Plex Mono, monospace";
      for (const d of rings) {
        const rr = (d / dmax) * 0.92;
        ctx.beginPath();
        for (let k = 0; k <= 72; k++) {
          const a = (k / 72) * Math.PI * 2;
          const p = P(Math.cos(a) * rr, 0, Math.sin(a) * rr);
          if (k === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
        const lp = P(rr, 0, 0);
        ctx.fillText(d.toFixed(step < 0.01 ? 3 : 2), lp.x + 4, lp.y - 4);
      }
      ctx.setLineDash([]);
      const o = P(0, 0, 0);
      const drawn = nodes.map((nd, i) => {
        const g = reduced ? 1 : ease((now - t0 - i * 70) / 1000);
        return { i, nd, p: P(nd.x * g, nd.y * g, nd.z * g) };
      });
      drawn.sort((a, b) => a.p.z - b.p.z);
      hits.current = [];
      for (const { i, nd, p } of drawn) {
        const isA = activeRef.current === i;
        ctx.strokeStyle = isA ? "rgba(239,239,239,0.8)" : "rgba(180,180,180,0.28)";
        ctx.beginPath();
        ctx.moveTo(o.x, o.y);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        const r = (isA ? 9 : 6.5) * p.q;
        ctx.globalAlpha = 0.6 + 0.4 * ((p.z + 1) / 2) * (1 - flat.current) + 0.4 * flat.current;
        ctx.fillStyle = nd.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        if (isA) {
          ctx.strokeStyle = "#efefef";
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.lineWidth = 1;
        }
        hits.current.push({ x: p.x, y: p.y, r: r + 6, i });
      }
      ctx.fillStyle = "#efefef";
      ctx.beginPath();
      ctx.arc(o.x, o.y, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "rgba(239,239,239,0.8)";
      ctx.fillText("your sequence", o.x + 12, o.y + 4);
    };
    drawRef.current = () => draw();
    if (reduced) {
      draw();
      const on = () => draw();
      window.addEventListener("resize", on);
      return () => window.removeEventListener("resize", on);
    }
    const loop = (t: number) => {
      const dt = t - last;
      last = t;
      const v = view.current;
      settle(dt);
      if (v.spin && !v.dragging && activeRef.current === null && modeRef.current === "3d") v.yaw += dt * 0.00022;
      draw(t);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [neighbours, reduced]);

  const switchMode = (m: "3d" | "2d") => {
    modeRef.current = m;
    pitchT.current = m === "3d" ? 0.35 : null;
    setMode(m);
    if (reduced) {
      settleRef.current(1000);
      drawRef.current();
    }
  };

  const act = active !== null ? items[active] : null;

  return (
    <div>
      <div className="embed-head">
        <h3>Nearest neighbours in embedding space</h3>
        <div className="seg" role="group" aria-label="View mode">
          <button type="button" aria-pressed={mode === "3d"} onClick={() => switchMode("3d")}>3D</button>
          <button type="button" aria-pressed={mode === "2d"} onClick={() => switchMode("2d")}>2D</button>
        </div>
      </div>
      <div className="embed">
        <div>
          <canvas
            ref={ref}
            className="embed3d"
            tabIndex={0}
            role="application"
            aria-label="Interactive 3D map of the nearest known protective sequences. Drag to rotate. A list of the same sequences follows."
            onPointerDown={() => {
              moved.current = false;
            }}
            onPointerMove={(e) => {
              if (view.current.dragging) {
                moved.current = true;
                return;
              }
              const r = e.currentTarget.getBoundingClientRect();
              const x = e.clientX - r.left;
              const y = e.clientY - r.top;
              let best: number | null = null;
              let bd = Infinity;
              for (const h of hits.current) {
                const d = Math.hypot(h.x - x, h.y - y);
                if (d < h.r && d < bd) {
                  bd = d;
                  best = h.i;
                }
              }
              setAct(best);
            }}
            onPointerLeave={() => setAct(null)}
            onClick={() => {
              if (moved.current || activeRef.current === null) return;
              const nb = items[activeRef.current];
              if (nb && !isSample(nb.accession)) window.open(uniprotUrl(nb.accession), "_blank", "noopener");
            }}
          />
          {mode === "3d" ? <OrbitControls view={view} onChange={() => drawRef.current()} reduced={reduced} /> : <p className="muted small">Flat view: distance from the centre is the only thing drawn.</p>}
        </div>
        <div className="embed-side">
          <p className="embed-axis mono">Radius: distance in ESM-2 embedding space (1 − cosine)</p>
          <div className="embed-read" aria-live="polite">
            {act ? (
              <>
                <p className="mono">{act.accession}</p>
                <p className="muted small">
                  cosine {act.cosine.toFixed(3)} · {act.family || "family not given"}
                </p>
                {isSample(act.accession) ? (
                  <p className="muted small">Sample point, no UniProt entry.</p>
                ) : (
                  <a href={uniprotUrl(act.accession)} target="_blank" rel="noreferrer">
                    Open in UniProt
                  </a>
                )}
              </>
            ) : (
              <p className="muted small">Hover a point for its accession, cosine and family. Click to open UniProt.</p>
            )}
          </div>
          <ul className="legend vertical" aria-label="Neighbours">
            {items.map((n, i) => {
              const fam = n.family || "family not given";
              return (
                <li key={n.accession + i}>
                  <button
                    type="button"
                    className="nb-btn"
                    onMouseEnter={() => setAct(i)}
                    onFocus={() => setAct(i)}
                    onMouseLeave={() => setAct(null)}
                    onBlur={() => setAct(null)}
                  >
                    <span className="swatch round" style={{ background: colorOf(fam) }} aria-hidden="true" />
                    {n.accession} · {fam} · {n.cosine.toFixed(2)}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
      <p className="muted small">
        This is representation proximity, not sequence alignment, and implies nothing about percent identity. The
        direction of each point carries no meaning; only its distance from the centre does.
      </p>
    </div>
  );
}

function Backbone({ points }: { points: CaPoint[] }) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const reduced = useReducedMotion();
  const drawRef = useRef<() => void>(() => undefined);
  const view = useOrbit(ref, () => drawRef.current());

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const cx = points.reduce((a, p) => a + p.x, 0) / points.length;
    const cy = points.reduce((a, p) => a + p.y, 0) / points.length;
    const cz = points.reduce((a, p) => a + p.z, 0) / points.length;
    const raw = points.map((p) => ({ x: p.x - cx, y: p.y - cy, z: p.z - cz, v: p.plddt }));
    const rad = Math.max(1, ...raw.map((p) => Math.hypot(p.x, p.y, p.z)));
    const pts = raw.map((p) => ({ x: p.x / rad, y: p.y / rad, z: p.z / rad, v: p.v }));
    let raf = 0;
    let last = performance.now();

    const draw = () => {
      const { w, h, S } = fitCanvas(canvas, ctx);
      const v = view.current;
      const sc = S * v.zoom;
      const proj = pts.map((p) => {
        const [a, b, c] = rotate(v, p.x, p.y, p.z);
        const q = persp(c);
        return { x: w / 2 + a * sc * q, y: h / 2 + b * sc * q, z: c, v: p.v, q };
      });
      const order = Array.from({ length: proj.length - 1 }, (_, i) => i).sort(
        (a, b) => proj[a].z + proj[a + 1].z - (proj[b].z + proj[b + 1].z),
      );
      ctx.lineCap = "round";
      for (const i of order) {
        const a = proj[i];
        const b = proj[i + 1];
        const d = (a.z + b.z) / 2;
        ctx.globalAlpha = 0.5 + 0.45 * ((d + 1) / 2);
        ctx.lineWidth = (2 + 1.4 * ((d + 1) / 2)) * ((a.q + b.q) / 2);
        ctx.strokeStyle = plddtColor((a.v + b.v) / 2);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    };
    drawRef.current = draw;
    if (reduced) {
      draw();
      window.addEventListener("resize", draw);
      return () => window.removeEventListener("resize", draw);
    }
    const loop = (t: number) => {
      const dt = t - last;
      last = t;
      if (view.current.spin && !view.current.dragging) view.current.yaw += dt * 0.00035;
      draw();
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [points, reduced, view]);

  return (
    <div className="backbone">
      <canvas
        ref={ref}
        className="canvas3d"
        tabIndex={0}
        role="application"
        aria-label="Interactive 3D backbone of the AlphaFold prediction, coloured by per-residue confidence. Drag to rotate."
      />
      <OrbitControls view={view} onChange={() => drawRef.current()} reduced={reduced} />
    </div>
  );
}

export function StructurePanel({ accession }: { accession: string | null }) {
  const [state, setState] = useState<AlphaFoldState>({ kind: "loading" });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!accession) return;
    const ac = new AbortController();
    setState({ kind: "loading" });
    loadAlphaFold(accession, ac.signal)
      .then((s) => setState(s))
      .catch(() => undefined);
    return () => ac.abort();
  }, [accession, tick]);

  let stats: { mean: number; low: number; high: number } | null = null;
  if (state.kind === "ready") {
    const n = state.points.length;
    stats = {
      mean: state.points.reduce((a, p) => a + p.plddt, 0) / n,
      low: (state.points.filter((p) => p.plddt < 50).length / n) * 100,
      high: (state.points.filter((p) => p.plddt > 90).length / n) * 100,
    };
  }

  return (
    <div>
      <h3>Predicted structure, coloured by confidence</h3>
      {!accession ? (
        <div className="empty">
          <p>No nearest sequence was returned, so there is no structure to fetch.</p>
        </div>
      ) : state.kind === "loading" ? (
        <div className="empty" aria-busy="true">
          <p className="muted">Asking AlphaFold DB for {accession}…</p>
        </div>
      ) : state.kind === "none" ? (
        <div className="empty">
          <p>AlphaFold DB has no prediction for {accession}.</p>
          <p className="muted small">Nothing is drawn in its place. A made-up structure would say more than we know.</p>
        </div>
      ) : state.kind === "error" ? (
        <div className="empty">
          <p>{state.message}</p>
          <button type="button" className="ghost-btn" onClick={() => setTick((t) => t + 1)}>
            Try again
          </button>
        </div>
      ) : (
        <>
          <Backbone points={state.points} />
          <ul className="legend plddt" aria-label="pLDDT colour key">
            <li><span className="swatch" style={{ background: plddtColor(95) }} aria-hidden="true" />very high, above 90</li>
            <li><span className="swatch" style={{ background: plddtColor(80) }} aria-hidden="true" />confident, 70 to 90</li>
            <li><span className="swatch" style={{ background: plddtColor(60) }} aria-hidden="true" />low, 50 to 70</li>
            <li><span className="swatch" style={{ background: plddtColor(30) }} aria-hidden="true" />very low, below 50</li>
          </ul>
          {stats ? (
            <p className="mono small stats">
              mean pLDDT {stats.mean.toFixed(1)} · {stats.low.toFixed(0)}% of residues below 50 · {stats.high.toFixed(0)}% above 90
            </p>
          ) : null}
        </>
      )}
      <p className="muted small">
        This is AlphaFold's prediction for the nearest homolog {accession ?? ""}, not for your pasted sequence. Low
        confidence here is the finding, not a failure: AlphaFold is uncertain because there is no fixed structure to
        predict. That disorder is the mechanism.
      </p>
    </div>
  );
}
