type HeatmapPreviewProps = {
  matrix: number[][];
};

const colors = ["#2c2c54", "#3a5fcd", "#12d8c4", "#f2d57c", "#f58518"];

function interpColor(value: number) {
  if (Number.isNaN(value) || value === undefined) return "#0b0c10";
  const v = Math.min(1, Math.max(0, value));
  const idx = Math.floor(v * (colors.length - 1));
  const t = v * (colors.length - 1) - idx;
  const c1 = colors[idx];
  const c2 = colors[Math.min(colors.length - 1, idx + 1)];
  // simple channel lerp
  const hex = (c: string) =>
    [1, 3, 5].map((i) => parseInt(c.substring(i, i + 2), 16));
  const [r1, g1, b1] = hex(c1);
  const [r2, g2, b2] = hex(c2);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r},${g},${b})`;
}

export const HeatmapPreview = ({ matrix }: HeatmapPreviewProps) => {
  if (!matrix || matrix.length === 0) {
    return <div className="heatmap-placeholder">Heatmap will appear here</div>;
  }
  const rows = matrix.length;
  const cols = matrix[0].length || 0;
  const cellSize = 6;
  return (
    <div
      className="heatmap"
      style={{
        width: cols * cellSize,
        height: rows * cellSize,
        gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
      }}
    >
      {matrix.flat().map((v, i) => (
        <div
          key={i}
          style={{
            width: cellSize,
            height: cellSize,
            background: interpColor(v),
          }}
          title={`P(make): ${(v * 100).toFixed(1)}%`}
        />
      ))}
    </div>
  );
};

