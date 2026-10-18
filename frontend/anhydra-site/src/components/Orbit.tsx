import { useEffect, useRef, useState, type MutableRefObject, type RefObject } from "react";

export type View = { yaw: number; pitch: number; zoom: number; spin: boolean; dragging: boolean; lock: boolean };

export const newView = (): View => ({ yaw: 0.6, pitch: 0.35, zoom: 1, spin: true, dragging: false, lock: false });

export function rotate(v: View, x: number, y: number, z: number): [number, number, number] {
  const cy = Math.cos(v.yaw);
  const sy = Math.sin(v.yaw);
  const cp = Math.cos(v.pitch);
  const sp = Math.sin(v.pitch);
  const x1 = x * cy + z * sy;
  const z1 = -x * sy + z * cy;
  return [x1, y * cp - z1 * sp, y * sp + z1 * cp];
}

export function persp(z: number, flat = 0): number {
  return 1 / (1 - z * 0.28 * (1 - flat));
}

export function fitCanvas(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { w, h, S: (Math.min(w, h) / 2) * 0.86 };
}

export function useOrbit(canvasRef: RefObject<HTMLCanvasElement | null>, onChange: () => void): MutableRefObject<View> {
  const view = useRef<View>(newView());
  const cb = useRef(onChange);
  cb.current = onChange;

  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    let lx = 0;
    let ly = 0;
    const down = (e: PointerEvent) => {
      if (view.current.lock) return;
      view.current.dragging = true;
      lx = e.clientX;
      ly = e.clientY;
      el.setPointerCapture(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (!view.current.dragging) return;
      view.current.yaw += (e.clientX - lx) * 0.01;
      view.current.pitch = Math.max(-1.4, Math.min(1.4, view.current.pitch + (e.clientY - ly) * 0.01));
      lx = e.clientX;
      ly = e.clientY;
      cb.current();
    };
    const up = () => {
      view.current.dragging = false;
    };
    const key = (e: KeyboardEvent) => {
      const v = view.current;
      if (v.lock && (e.key.startsWith("Arrow") || e.key === "0")) return;
      let used = true;
      if (e.key === "ArrowLeft") v.yaw -= 0.15;
      else if (e.key === "ArrowRight") v.yaw += 0.15;
      else if (e.key === "ArrowUp") v.pitch = Math.max(-1.4, v.pitch - 0.15);
      else if (e.key === "ArrowDown") v.pitch = Math.min(1.4, v.pitch + 0.15);
      else if (e.key === "+" || e.key === "=") v.zoom = Math.min(3, v.zoom * 1.15);
      else if (e.key === "-") v.zoom = Math.max(0.5, v.zoom / 1.15);
      else if (e.key === "0") Object.assign(v, newView(), { lock: v.lock });
      else used = false;
      if (used) {
        e.preventDefault();
        cb.current();
      }
    };
    el.addEventListener("pointerdown", down);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerup", up);
    el.addEventListener("pointercancel", up);
    el.addEventListener("keydown", key);
    return () => {
      el.removeEventListener("pointerdown", down);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerup", up);
      el.removeEventListener("pointercancel", up);
      el.removeEventListener("keydown", key);
    };
  }, [canvasRef]);

  return view;
}

export function OrbitControls({
  view,
  onChange,
  reduced,
}: {
  view: MutableRefObject<View>;
  onChange: () => void;
  reduced: boolean;
}) {
  const [spin, setSpin] = useState(view.current.spin);
  return (
    <div className="orbit-controls" role="group" aria-label="3D view controls">
      <button
        type="button"
        className="ghost-btn"
        onClick={() => {
          view.current.zoom = Math.min(3, view.current.zoom * 1.25);
          onChange();
        }}
      >
        Zoom in
      </button>
      <button
        type="button"
        className="ghost-btn"
        onClick={() => {
          view.current.zoom = Math.max(0.5, view.current.zoom / 1.25);
          onChange();
        }}
      >
        Zoom out
      </button>
      <button
        type="button"
        className="ghost-btn"
        onClick={() => {
          const s = view.current.spin;
          Object.assign(view.current, newView(), { lock: view.current.lock });
          view.current.spin = s;
          onChange();
        }}
      >
        Reset
      </button>
      {!reduced ? (
        <button
          type="button"
          className="ghost-btn"
          aria-pressed={!spin}
          onClick={() => {
            view.current.spin = !view.current.spin;
            setSpin(view.current.spin);
          }}
        >
          {spin ? "Pause rotation" : "Resume rotation"}
        </button>
      ) : null}
      <span className="muted small orbit-hint">Drag to rotate. Arrow keys, + and − also work when focused.</span>
    </div>
  );
}
