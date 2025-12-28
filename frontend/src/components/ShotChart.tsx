import { useState, useCallback } from "react";
import { Shot, ShotBinsResponse } from "../api";

interface ShotChartProps {
  shots?: Shot[];
  bins?: ShotBinsResponse | null;
}

// NBA Court dimensions in feet (official measurements)
const COURT = {
  width: 50,
  halfLength: 47,
  rimFromBaseline: 5.25,
  rimRadius: 0.75,
  backboardFromBaseline: 4,
  paintWidth: 16,
  paintLength: 19,
  ftCircleRadius: 6,
  restrictedRadius: 4,
  threePointRadius: 23.75,
  threePointSideDistance: 22,
};

type TooltipState =
  | { kind: "shot"; shot: Shot; x: number; y: number }
  | { kind: "bin"; bin: { attempts: number; made: number; fg_pct: number }; x: number; y: number };

export function ShotChart({ shots = [], bins }: ShotChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const handleMouseEnter = useCallback(
    (shot: Shot, event: React.MouseEvent<SVGCircleElement, MouseEvent>, idx: number) => {
      const svgRect = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
      if (svgRect) {
        setTooltip({
          kind: "shot",
          shot,
          x: event.clientX - svgRect.left + 12,
          y: event.clientY - svgRect.top + 12,
        });
      }
      setHoveredIdx(idx);
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
    setHoveredIdx(null);
  }, []);

  const handleBinEnter = useCallback(
    (
      bin: { attempts: number; made: number; fg_pct: number },
      event: React.MouseEvent<SVGRectElement, MouseEvent>
    ) => {
      const svgRect = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
      if (svgRect) {
        setTooltip({
          kind: "bin",
          bin,
          x: event.clientX - svgRect.left + 12,
          y: event.clientY - svgRect.top + 12,
        });
      }
    },
    []
  );

  // Scale: 1 foot = 10 SVG units
  const S = 10;
  
  // Court height we want to show (up to half court)
  const courtViewHeight = 47;
  
  // Viewbox dimensions
  const viewBoxX = (-COURT.width / 2) * S;
  const viewBoxY = 0;
  const viewBoxW = COURT.width * S;
  const viewBoxH = courtViewHeight * S;

  // Helper to flip Y coordinate (hoop at top means we invert Y)
  // Data has y=0 at baseline, increasing away from hoop
  // We want y=0 at top (near hoop) in SVG
  const flipY = (y: number) => y * S;
  
  // Rim position (will be near top since rimFromBaseline is small)
  const rimY = COURT.rimFromBaseline * S;
  
  // Calculate where 3pt arc meets the corner lines
  const cornerX = 22;
  const arcMeetY = COURT.rimFromBaseline + Math.sqrt(
    COURT.threePointRadius ** 2 - cornerX ** 2
  );

  return (
    <div className="court-wrapper">
      <svg
        className="court-svg"
        viewBox={`${viewBoxX} ${viewBoxY} ${viewBoxW} ${viewBoxH}`}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="courtGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#11131c" />
            <stop offset="100%" stopColor="#0c1017" />
          </linearGradient>
          <radialGradient id="rimGlow" cx="50%" cy="0%" r="60%">
            <stop offset="0%" stopColor="rgba(255,107,44,0.45)" />
            <stop offset="100%" stopColor="rgba(255,107,44,0)" />
          </radialGradient>
          <filter id="shotShadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="2" floodColor="rgba(0,0,0,0.5)" />
          </filter>
        </defs>

        {/* Court surface */}
        <rect
          x={viewBoxX}
          y={viewBoxY}
          width={viewBoxW}
          height={viewBoxH}
          fill="url(#courtGradient)"
        />
        <rect
          x={viewBoxX}
          y={viewBoxY}
          width={viewBoxW}
          height={viewBoxH}
          fill="url(#rimGlow)"
        />

        {/* === COURT LINES === */}
        <g stroke="#2f3545" strokeWidth={2} fill="none">
          
          {/* Baseline at y=0 (top of court view) */}
          <line 
            x1={(-COURT.width / 2) * S} 
            y1={0} 
            x2={(COURT.width / 2) * S} 
            y2={0} 
          />
          
          {/* Sidelines */}
          <line 
            x1={(-COURT.width / 2) * S} 
            y1={0} 
            x2={(-COURT.width / 2) * S} 
            y2={courtViewHeight * S} 
          />
          <line 
            x1={(COURT.width / 2) * S} 
            y1={0} 
            x2={(COURT.width / 2) * S} 
            y2={courtViewHeight * S} 
          />

          {/* Paint/Key - outer rectangle */}
          <rect 
            x={(-COURT.paintWidth / 2) * S} 
            y={0} 
            width={COURT.paintWidth * S} 
            height={COURT.paintLength * S} 
          />
          
          {/* Paint/Key - inner lane */}
          <rect 
            x={-6 * S} 
            y={0} 
            width={12 * S} 
            height={COURT.paintLength * S} 
          />

          {/* Free throw circle (bottom half - solid) */}
          <path 
            d={`M ${-COURT.ftCircleRadius * S} ${COURT.paintLength * S} 
                A ${COURT.ftCircleRadius * S} ${COURT.ftCircleRadius * S} 0 0 0 
                  ${COURT.ftCircleRadius * S} ${COURT.paintLength * S}`} 
          />
          
          {/* Free throw circle (top half - dashed, inside paint) */}
          <path 
            d={`M ${-COURT.ftCircleRadius * S} ${COURT.paintLength * S} 
                A ${COURT.ftCircleRadius * S} ${COURT.ftCircleRadius * S} 0 0 1 
                  ${COURT.ftCircleRadius * S} ${COURT.paintLength * S}`}
            strokeDasharray="10,10"
          />

          {/* Restricted area arc */}
          <path 
            d={`M ${-COURT.restrictedRadius * S} ${rimY} 
                A ${COURT.restrictedRadius * S} ${COURT.restrictedRadius * S} 0 0 0 
                  ${COURT.restrictedRadius * S} ${rimY}`} 
          />

          {/* 3-point line - left corner */}
          <line 
            x1={-cornerX * S} 
            y1={0} 
            x2={-cornerX * S} 
            y2={arcMeetY * S} 
          />
          
          {/* 3-point line - right corner */}
          <line 
            x1={cornerX * S} 
            y1={0} 
            x2={cornerX * S} 
            y2={arcMeetY * S} 
          />
          
          {/* 3-point arc */}
          <path 
            d={`M ${-cornerX * S} ${arcMeetY * S} 
                A ${COURT.threePointRadius * S} ${COURT.threePointRadius * S} 0 0 0 
                  ${cornerX * S} ${arcMeetY * S}`} 
          />
        </g>

        {/* === BACKBOARD & RIM === */}
        {/* Backboard */}
        <rect 
          x={-3 * S} 
          y={COURT.backboardFromBaseline * S - 3} 
          width={6 * S} 
          height={5} 
          fill="#6b7280"
          rx={1}
        />
        
        {/* Rim */}
        <circle
          cx={0}
          cy={rimY}
          r={COURT.rimRadius * S + 2}
          fill="rgba(255, 107, 44, 0.4)"
          stroke="#ff6b2c"
          strokeWidth={3}
        />

        {/* === SHOTS (BINS or DOTS) === */}
        {bins && bins.bins.length > 0 ? (
          (() => {
            const xStep = (bins.x_range[1] - bins.x_range[0]) / bins.x_bins;
            const yStep = (bins.y_range[1] - bins.y_range[0]) / bins.y_bins;
            const maxAttempts = Math.max(...bins.bins.map((b) => b.attempts));
            const fgToColor = (fg: number) => {
              const clamped = Math.max(0, Math.min(1, fg));
              const r = Math.round(255 * (1 - clamped));
              const g = Math.round(255 * clamped);
              return `rgba(${r},${g},120,0.8)`;
            };
            return bins.bins.map((b, idx) => {
              const x = (bins.x_range[0] + b.x_bin * xStep) * S;
              const y = (bins.y_range[0] + b.y_bin * yStep) * S;
              const width = xStep * S;
              const height = yStep * S;
              const scale = 0.4 + 0.6 * (b.attempts / maxAttempts || 0);
              return (
                <rect
                  key={idx}
                  x={x}
                  y={y}
                  width={width}
                  height={height}
                  fill={fgToColor(b.fg_pct)}
                  fillOpacity={0.85 * scale}
                  stroke="rgba(255,255,255,0.04)"
                  strokeWidth={1}
                  onMouseEnter={(e) => handleBinEnter(b, e)}
                  onMouseLeave={handleMouseLeave}
                />
              );
            });
          })()
        ) : (
          shots.map((shot, idx) => {
            const isMade = shot.SHOT_MADE_FLAG === 1;
            return (
              <circle
                key={idx}
                className={`shot-dot ${isMade ? "shot-dot--made" : "shot-dot--missed"} ${
                  hoveredIdx === idx ? "shot-dot--active" : ""
                }`}
                cx={shot.LOC_X * S}
                cy={shot.LOC_Y * S}
                r={4.4}
                onMouseEnter={(e) => handleMouseEnter(shot, e, idx)}
                onMouseLeave={handleMouseLeave}
                filter="url(#shotShadow)"
              />
            );
          })
        )}
      </svg>

      {/* Tooltip */}
      {tooltip && tooltip.kind === "shot" && (
        <div className="tooltip tooltip--inset" style={{ left: tooltip.x, top: tooltip.y }}>
          <div className="tooltip__title">
            {tooltip.shot.SHOT_MADE_FLAG === 1 ? "✓ Made" : "✗ Missed"}
          </div>
          <div className="tooltip__row">
            <span>Type</span>
            <span>{tooltip.shot.SHOT_TYPE}</span>
          </div>
          <div className="tooltip__row">
            <span>Action</span>
            <span>{tooltip.shot.ACTION_TYPE.replace(" Shot", "")}</span>
          </div>
          <div className="tooltip__row">
            <span>Distance</span>
            <span>{tooltip.shot.SHOT_DISTANCE.toFixed(1)} ft</span>
          </div>
        </div>
      )}

      {tooltip && tooltip.kind === "bin" && (
        <div className="tooltip tooltip--inset" style={{ left: tooltip.x, top: tooltip.y }}>
          <div className="tooltip__title">Zone Summary</div>
          <div className="tooltip__row">
            <span>Attempts</span>
            <span>{tooltip.bin.attempts}</span>
          </div>
          <div className="tooltip__row">
            <span>FG%</span>
            <span>{(tooltip.bin.fg_pct * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="legend">
        {bins && bins.bins.length > 0 ? (
          <>
            <div className="legend-item">
              <div className="legend-dot legend-dot--missed" />
              <span>Lower FG%</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot legend-dot--made" />
              <span>Higher FG%</span>
            </div>
          </>
        ) : (
          <>
            <div className="legend-item">
              <div className="legend-dot legend-dot--made" />
              <span>Made</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot legend-dot--missed" />
              <span>Missed</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot legend-dot--active" />
              <span>Hover</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
