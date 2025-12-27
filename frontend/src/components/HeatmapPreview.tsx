interface HeatmapPreviewProps {
  matrix: number[][];
}

const COLORS = [
  "#0d0d12",
  "#1a1a40",
  "#1e3a8a",
  "#0891b2",
  "#22c55e",
  "#eab308",
  "#f97316",
  "#ef4444",
  "#dc2626",
];

function interpolateColor(value: number): string {
  if (!Number.isFinite(value)) return COLORS[0];
  
  const v = Math.max(0, Math.min(1, value));
  const idx = Math.floor(v * (COLORS.length - 1));
  const t = v * (COLORS.length - 1) - idx;
  
  const c1 = COLORS[idx];
  const c2 = COLORS[Math.min(COLORS.length - 1, idx + 1)];
  
  const parseHex = (hex: string) =>
    [1, 3, 5].map((i) => parseInt(hex.substring(i, i + 2), 16));
  
  const [r1, g1, b1] = parseHex(c1);
  const [r2, g2, b2] = parseHex(c2);
  
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  
  return `rgb(${r},${g},${b})`;
}

export function HeatmapPreview({ matrix }: HeatmapPreviewProps) {
  if (!matrix.length) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">🎯</div>
        <div className="empty-state__title">Generate a heatmap</div>
        <p>Visualize FG% probabilities across the court</p>
      </div>
    );
  }

  const rows = matrix.length;
  const cols = matrix[0]?.length || 0;
  const cellSize = 6;

  return (
    <div className="heatmap-container">
      <div
        className="heatmap-grid"
        style={{
          width: cols * cellSize,
          height: rows * cellSize,
          gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
        }}
      >
        {matrix.flat().map((val, i) => (
          <div
            key={i}
            style={{
              width: cellSize,
              height: cellSize,
              background: interpolateColor(val),
            }}
            title={`${(val * 100).toFixed(1)}%`}
          />
        ))}
      </div>
      
      <div className="heatmap-legend">
        <span className="heatmap-legend__label">0%</span>
        <div
          className="heatmap-legend__bar"
          style={{
            background: `linear-gradient(to right, ${COLORS.join(", ")})`,
          }}
        />
        <span className="heatmap-legend__label">100%</span>
      </div>
    </div>
  );
}
