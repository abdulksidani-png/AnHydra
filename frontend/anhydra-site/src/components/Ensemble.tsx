import { useEffect, useRef } from "react";
import { LEGEND, RESIDUE_CLASS } from "@/lib/protein";
import { OrbitControls, fitCanvas, persp, rotate, useOrbit } from "@/components/Orbit";
import { useReducedMotion } from "@/components/Result";

const HEX: Record<string, string> = { acidic: "#ef7d5a", basic: "#6fb6ff", polar: "#44d3c4", hydro: "#7d93a8", flex: "#e9c46a" };

function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function Ensemble({ seq }: { seq: string }) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const reduced = useReducedMotion();
  const drawRef = useRef<() => void>(() => undefined);
  const view = useOrbit(ref, () => drawRef.current());

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const stride = Math.max(1, Math.ceil(seq.length / 260));
    const beads = seq.split("").filter((_, i) => i % stride === 0);
    let seed = 7;
    for (const c of seq) seed = (seed * 31 + c.charCodeAt(0)) >>> 0;
    const K = 6;
    const chains = Array.from({ length: K }, (_, k) => {
      const r = rng(seed + k * 977);
      const pts: [number, number, number][] = [[0, 0, 0]];
      let d: [number, number, number] = [r() - 0.5, r() - 0.5, r() - 0.5];
      for (let i = 1; i < beads.length; i++) {
        d = [d[0] * 0.55 + (r() - 0.5), d[1] * 0.55 + (r() - 0.5), d[2] * 0.55 + (r() - 0.5)];
        const l = Math.hypot(...d) || 1;
        const p = pts[i - 1];
        pts.push([p[0] + d[0] / l, p[1] + d[1] / l, p[2] + d[2] / l]);
      }
      const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length;
      const cy = pts.reduce((a, p) => a + p[1], 0) / pts.length;
      const cz = pts.reduce((a, p) => a + p[2], 0) / pts.length;
      return { pts: pts.map((p) => [p[0] - cx, p[1] - cy, p[2] - cz] as [number, number, number]), phase: r() * 6.28, speed: 0.6 + r() * 0.8 };
    });
    const rad = Math.max(1, ...chains.flatMap((c) => c.pts.map((p) => Math.hypot(p[0], p[1], p[2]))));
    let raf = 0;
    let last = performance.now();

    const draw = (t = 0) => {
      const { w, h, S } = fitCanvas(canvas, ctx);
      const v = view.current;
      const sc = S * v.zoom;
      ctx.lineCap = "round";
      type Seg = { ax: number; ay: number; bx: number; by: number; z: number; cls: string; a: number; q: number };
      const segs: Seg[] = [];
      chains.forEach((c, k) => {
        let prev: { x: number; y: number; z: number; q: number } | null = null;
        c.pts.forEach((p, i) => {
          const f = i / c.pts.length;
          const m = reduced ? 0 : 1;
          const wob = Math.sin(t * 0.0009 * c.speed + i * 0.35 + c.phase) * 0.9 * f * m;
          const wz = Math.cos(t * 0.0007 * c.speed + i * 0.3) * 0.7 * f * m;
          const [a, b, z] = rotate(v, (p[0] + wob) / rad, (p[1] + wob * 0.5) / rad, (p[2] + wz) / rad);
          const q = persp(z);
          const cur = { x: w / 2 + a * sc * q, y: h / 2 + b * sc * q, z, q };
          if (prev) {
            segs.push({
              ax: prev.x, ay: prev.y, bx: cur.x, by: cur.y,
              z: (prev.z + cur.z) / 2,
              cls: RESIDUE_CLASS[beads[i]]?.key ?? "hydro",
              a: 0.2 + 0.05 * (k % 3),
              q: (prev.q + cur.q) / 2,
            });
          }
          prev = cur;
        });
      });
      segs.sort((a, b) => a.z - b.z);
      for (const s of segs) {
        ctx.globalAlpha = s.a + 0.35 * ((s.z + 1) / 2);
        ctx.lineWidth = 1.3 * s.q;
        ctx.strokeStyle = HEX[s.cls];
        ctx.beginPath();
        ctx.moveTo(s.ax, s.ay);
        ctx.lineTo(s.bx, s.by);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    };
    drawRef.current = () => draw(performance.now());
    if (reduced) {
      draw(0);
      drawRef.current = () => draw(0);
      const on = () => draw(0);
      window.addEventListener("resize", on);
      return () => window.removeEventListener("resize", on);
    }
    const loop = (t: number) => {
      const dt = t - last;
      last = t;
      if (view.current.spin && !view.current.dragging) view.current.yaw += dt * 0.00022;
      draw(t);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [seq, reduced, view]);

  return (
    <div>
      <h3>Your sequence as a loose ensemble</h3>
      <canvas
        ref={ref}
        className="canvas3d"
        tabIndex={0}
        role="application"
        aria-label="Interactive 3D view of several faint, shifting conformations of the sequence, coloured by residue chemistry. Drag to rotate."
      />
      <OrbitControls view={view} onChange={() => drawRef.current()} reduced={reduced} />
      <ul className="legend" aria-label="Residue colour key">
        {LEGEND.map((l) => (
          <li key={l.key}>
            <span className="swatch" style={{ background: l.color }} aria-hidden="true" />
            {l.letters.split("").join(" ")}
            <span className="legend-name"> {l.name.split(" (")[0]}</span>
          </li>
        ))}
      </ul>
      <p className="muted small">
        Illustration, not a prediction. Intrinsically disordered proteins hold no single shape, so several faint random
        conformations are drawn and never settle.
      </p>
    </div>
  );
}
