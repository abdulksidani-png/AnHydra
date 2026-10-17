interface ScaleBarProps {
  /** 0–1. */
  score: number;
  /** 0–1, where the call flips. */
  threshold: number;
}

/**
 * The specimen-card scale: a measured rule with the score filled in from the
 * left and a tick at the operating threshold, so the number is always read
 * against the line that decides the call.
 */
export function ScaleBar({ score, threshold }: ScaleBarProps) {
  const pct = clamp01(score) * 100;
  const thresholdPct = clamp01(threshold) * 100;
  const isLow = score < threshold;

  return (
    <div>
      <p className="scale__caption">PROTECTION SCORE</p>
      <div
        className="scale__track"
        role="meter"
        aria-valuenow={Number(score.toFixed(2))}
        aria-valuemin={0}
        aria-valuemax={1}
        aria-label={`Protection score ${score.toFixed(2)} out of 1, threshold ${threshold.toFixed(2)}`}
      >
        <div
          className={`scale__fill${isLow ? ' scale__fill--low' : ''}`}
          style={{ width: `${pct}%` }}
        />
        <div className="scale__threshold" style={{ left: `${thresholdPct}%` }} />
      </div>
      <div className="scale__ticks">
        <span>0.00</span>
        <span>{threshold.toFixed(2)}</span>
        <span>1.00</span>
      </div>
    </div>
  );
}

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n));
}
