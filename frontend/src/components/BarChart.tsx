interface BarChartData {
  label: string;
  value: number;
  maxValue?: number;
}

interface BarChartProps {
  data: BarChartData[];
  title?: string;
  variant?: "orange" | "blue";
  formatValue?: (value: number) => string;
  alignRight?: boolean;
}

export function BarChart({
  data,
  title,
  variant = "orange",
  formatValue = (v) => `${(v * 100).toFixed(1)}%`,
  alignRight = false,
}: BarChartProps) {
  const maxVal = Math.max(...data.map((d) => d.maxValue ?? d.value), 0.01);

  return (
    <div className={`chart ${alignRight ? "chart--right" : ""}`}>
      {title && <div className="chart__title">{title}</div>}
      <div className="bar-chart">
        {data.map((item, idx) => (
          <div key={idx} className={`bar-row ${alignRight ? "bar-row--right" : ""}`}>
            {!alignRight && (
              <span className="bar-label" title={item.label}>
                {item.label}
              </span>
            )}
            <div className={`bar-track ${alignRight ? "bar-track--right" : ""}`}>
              <div
                className={`bar-fill bar-fill--${variant} ${alignRight ? "bar-fill--right" : ""}`}
                style={{ width: `${(item.value / maxVal) * 100}%` }}
              />
              <span className={`bar-value ${alignRight ? "bar-value--right" : ""}`}>
                {formatValue(item.value)}
              </span>
            </div>
            {alignRight && (
              <span className="bar-label bar-label--right" title={item.label}>
                {item.label}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
