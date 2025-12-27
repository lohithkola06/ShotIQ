import { useState, useCallback } from "react";
import { Shot } from "../api";

interface ShotChartProps {
  shots: Shot[];
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

export function ShotChart({ shots }: ShotChartProps) {
  const [tooltip, setTooltip] = useState<{
    shot: Shot;
    x: number;
    y: number;
  } | null>(null);

  const handleMouseEnter = useCallback(
    (shot: Shot, event: React.MouseEvent) => {
      setTooltip({
        shot,
        x: event.clientX + 12,
        y: event.clientY + 12,
      });
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  // Scale: 1 foot = 10 SVG units
  const S = 10;
  
  // Court height we want to show (up to ~42 feet from baseline)
  const courtViewHeight = 42;
  
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
        {/* Court surface */}
        <rect
          x={viewBoxX}
          y={viewBoxY}
          width={viewBoxW}
          height={viewBoxH}
          fill="#1a1a22"
        />

        {/* === COURT LINES === */}
        <g stroke="#3a3a50" strokeWidth={2} fill="none">
          
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
          fill="#555"
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

        {/* === SHOT DOTS === */}
        {shots.map((shot, idx) => (
          <circle
            key={idx}
            className="shot-dot"
            cx={shot.LOC_X * S}
            cy={shot.LOC_Y * S}
            r={4}
            fill={shot.SHOT_MADE_FLAG === 1 ? "#00ff88" : "#ff3366"}
            fillOpacity={0.7}
            stroke={shot.SHOT_MADE_FLAG === 1 ? "#00ff88" : "#ff3366"}
            strokeWidth={1}
            strokeOpacity={0.4}
            onMouseEnter={(e) => handleMouseEnter(shot, e)}
            onMouseLeave={handleMouseLeave}
          />
        ))}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div className="tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
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

      {/* Legend */}
      <div className="legend">
        <div className="legend-item">
          <div className="legend-dot legend-dot--made" />
          <span>Made</span>
        </div>
        <div className="legend-item">
          <div className="legend-dot legend-dot--missed" />
          <span>Missed</span>
        </div>
      </div>
    </div>
  );
}
