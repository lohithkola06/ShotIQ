import { useState, useEffect } from "react";
import { PlayerSearch } from "./PlayerSearch";
import { Player, predictShot } from "../api";

// Close-range actions (only available within CLOSE_RANGE_DISTANCE)
const CLOSE_RANGE_ACTIONS = [
  "Layup Shot",
  "Dunk Shot",
  "Driving Layup Shot",
  "Tip Shot",
  "Finger Roll",
] as const;

// Mid-range 2PT actions (available outside close range but inside 3pt line)
const MID_RANGE_ACTIONS = [
  "Jump Shot",
  "Hook Shot",
  "Fadeaway",
  "Floating Jump Shot",
  "Pullup Jump Shot",
] as const;

// 3PT actions
const THREE_PT_ACTIONS = [
  "Jump Shot",
  "Fadeaway",
  "Pullup Jump Shot",
  "Step Back Jump Shot",
  "Running Jump Shot",
] as const;

// Court dimensions
const COURT = {
  width: 50,
  rimY: 1,
  threePointRadius: 23.75,
  closeRangeDistance: 8, // Within 8 feet = close range (layups, dunks, etc.)
};

export function PredictPanel() {
  const [position, setPosition] = useState({ x: 0, y: 15 });
  const [action, setAction] = useState<string>("Jump Shot");
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [probability, setProbability] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [shotAnim, setShotAnim] = useState<{ id: number; result: "make" | "miss" } | null>(null);

  // Calculate distance and shot type
  const distance = Math.sqrt(position.x ** 2 + (position.y - COURT.rimY) ** 2);
  
  // 3-point detection: corners are 22ft from sideline (straight line), arc is 23.75ft radius
  // Corner 3s: when |x| >= 22 AND distance > 22 (the corner line distance)
  // Arc 3s: when distance > 23.75
  const cornerThreeDistance = 22;
  const arcMeetY = COURT.rimY + Math.sqrt(COURT.threePointRadius ** 2 - cornerThreeDistance ** 2);
  const isCornerThree = Math.abs(position.x) >= cornerThreeDistance && position.y < arcMeetY;
  const isArcThree = distance > COURT.threePointRadius;
  const isThreePointer = isCornerThree || isArcThree;
  
  const isCloseRange = distance <= COURT.closeRangeDistance;
  const shotType = isThreePointer ? "3PT Field Goal" : "2PT Field Goal";
  
  // Get available actions based on distance
  const availableActions = isThreePointer 
    ? THREE_PT_ACTIONS 
    : isCloseRange 
      ? [...CLOSE_RANGE_ACTIONS, ...MID_RANGE_ACTIONS]
      : MID_RANGE_ACTIONS;

  // Reset action if it's not available for current zone
  useEffect(() => {
    if (!availableActions.includes(action as any)) {
      setAction("Jump Shot");
    }
  }, [isThreePointer, isCloseRange, action, availableActions]);

  // Clear probability when position changes
  useEffect(() => {
    setProbability(null);
  }, [position.x, position.y]);

  const handleCourtClick = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 500 - 250;
    const y = ((e.clientY - rect.top) / rect.height) * 470 - 50;
    
    // Convert to feet and clamp
    const xFeet = Math.max(-25, Math.min(25, x / 10));
    // clamp y to [0, 42] to prevent below-baseline selections
    const yFeet = Math.max(0, Math.min(42, y / 10));
    
    setPosition({ x: xFeet, y: yFeet });
  };

  const handlePredict = async () => {
    setLoading(true);
    try {
      const result = await predictShot({
        LOC_X: position.x,
        LOC_Y: position.y,
        YEAR: 2024,
        SHOT_TYPE: shotType,
        ACTION_TYPE: action,
        player_name: selectedPlayer?.name || undefined,
      });
      setProbability(result.probability_make);
      const made = Math.random() < result.probability_make;
      setShotAnim({ id: Date.now(), result: made ? "make" : "miss" });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getProbColor = (p: number) => {
    if (p < 0.3) return "#ff3366";
    if (p < 0.45) return "#ff9500";
    if (p < 0.55) return "#eab308";
    return "#00ff88";
  };

  const S = 10;
  
  // NBA court geometry relative to rim at y=1
  // Rim is 5.25 ft from baseline in real NBA court
  const rimSvgY = COURT.rimY * S; // = 10
  const baselineY = -4 * S; // Baseline behind rim (rim is ~5ft from baseline, but we offset for visual)
  const paintLength = 19; // 19 ft from baseline
  const paintEndY = baselineY + paintLength * S; // Free throw line position
  const ftCircleRadius = 6 * S; // 6 ft radius
  const restrictedRadius = 4 * S; // 4 ft radius
  
  return (
    <div className="predict-panel fade-in">
      <div className="predict-hero">
        <div className="predict-hero__content">
          <div className="predict-hero__eyebrow">Live model • 2024 season tuned</div>
          <h2>Predict the make odds from any spot</h2>
          <p>
            Drop the marker on the court, pick the move, and optionally bias the model toward a specific player.
            Designed for quick what-if scenarios and heat check debates.
          </p>
          <div className="predict-hero__pills">
            <span className="predict-pill">Distance: {distance.toFixed(1)} ft</span>
            <span className="predict-pill">{isThreePointer ? "Perimeter arc aware" : "Paint & midrange aware"}</span>
            <span className="predict-pill">{availableActions.length} action options</span>
          </div>
        </div>
        <div className="predict-hero__glass">
          <div className="predict-hero__stat">
            <span>Current profile</span>
            <div className="predict-hero__stat-value">
              {selectedPlayer ? selectedPlayer.name : "Global model"}
            </div>
            <p className="predict-hero__stat-note">
              {selectedPlayer
                ? "Personalized to this player's historical tendencies."
                : "Blends league-wide shot data for a neutral baseline."}
            </p>
          </div>
          <div className="predict-hero__stat">
            <span>Shot label</span>
            <div className={`predict-shot-chip ${isThreePointer ? "three" : "two"}`}>
              {isThreePointer ? "3PT field goal" : "2PT field goal"}
            </div>
            <p className="predict-hero__stat-note">Auto-detected from location.</p>
          </div>
        </div>
      </div>

      <div className="predict-player-panel">
        <div className="predict-player-header">
          <div>
            <div className="predict-player-kicker">Player personalization</div>
            <h3>Search & lock a player</h3>
            <p className="predict-player-subtitle">
              Find anyone in the database to nudge probabilities toward their shot profile. Leave blank for neutral.
            </p>
          </div>
          <div className="predict-player-chip">
            <span className="predict-player-chip__label">Active</span>
            <span className="predict-player-chip__name">
              {selectedPlayer ? selectedPlayer.name : "Global model"}
            </span>
            {selectedPlayer && (
              <button
                className="predict-player-chip__clear"
                onClick={() => setSelectedPlayer(null)}
                type="button"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        <div className="predict-player-search">
          <PlayerSearch
            onSelect={(player) => setSelectedPlayer(player)}
            selectedPlayer={selectedPlayer ?? undefined}
            placeholder="Type a name: e.g. Stephen Curry, Nikola Jokic, LeBron James"
          />
        </div>

        <div className="predict-player-hint">
          Selecting a player reweights the model with their historical shot profile; clearing falls back to the global model.
        </div>
      </div>

      <div className="predict-layout">
        {/* Interactive Court */}
        <div className="predict-court-section">
          <div className="predict-court-header">
            <h3>Click to select shot location</h3>
            <span className={`predict-shot-badge ${isThreePointer ? "three" : "two"}`}>
              {isThreePointer ? "3PT" : "2PT"} • {distance.toFixed(1)} ft
            </span>
          </div>
          
          <div className="predict-court-container">
            {shotAnim && (
              <div className="predict-anim-layer" key={shotAnim.id}>
                <div className={`predict-ball predict-ball--${shotAnim.result}`}>
                  <div className="predict-ball__texture" />
                </div>
                <div className={`predict-hoop predict-hoop--${shotAnim.result}`}>
                  <div className="predict-hoop__rim" />
                  <div className="predict-hoop__net" />
                </div>
              </div>
            )}
            <svg
              viewBox="-250 -50 500 470"
              className="predict-court-svg"
              onClick={handleCourtClick}
            >
              {/* Court surface */}
              <rect x={-250} y={-50} width={500} height={470} fill="#1e293b" />
              
              {/* Court lines */}
              <g stroke="#475569" strokeWidth={2} fill="none">
                {/* Baseline */}
                <line x1={-250} y1={baselineY} x2={250} y2={baselineY} />
                
                {/* Sidelines */}
                <line x1={-250} y1={baselineY} x2={-250} y2={420} />
                <line x1={250} y1={baselineY} x2={250} y2={420} />
                
                {/* Paint - 16ft wide, 19ft from baseline */}
                <rect x={-80} y={baselineY} width={160} height={paintLength * S} />
                <rect x={-60} y={baselineY} width={120} height={paintLength * S} />
                
                {/* Free throw circle - at end of paint */}
                <path d={`M ${-ftCircleRadius} ${paintEndY} A ${ftCircleRadius} ${ftCircleRadius} 0 0 0 ${ftCircleRadius} ${paintEndY}`} />
                <path d={`M ${-ftCircleRadius} ${paintEndY} A ${ftCircleRadius} ${ftCircleRadius} 0 0 1 ${ftCircleRadius} ${paintEndY}`} strokeDasharray="8,8" />
                
                {/* Restricted area - 4ft radius from rim */}
                <path d={`M ${-restrictedRadius} ${rimSvgY} A ${restrictedRadius} ${restrictedRadius} 0 0 0 ${restrictedRadius} ${rimSvgY}`} />
                
                {/* 3-point line */}
                <path d={`M ${-cornerThreeDistance * S} ${baselineY} L ${-cornerThreeDistance * S} ${arcMeetY * S}`} />
                <path d={`M ${cornerThreeDistance * S} ${baselineY} L ${cornerThreeDistance * S} ${arcMeetY * S}`} />
                <path d={`M ${-cornerThreeDistance * S} ${arcMeetY * S} A ${COURT.threePointRadius * S} ${COURT.threePointRadius * S} 0 0 0 ${cornerThreeDistance * S} ${arcMeetY * S}`} />
              </g>
              
              {/* Backboard */}
              <rect x={-30} y={rimSvgY - 18} width={60} height={5} fill="#64748b" rx={2} />
              
              {/* Rim */}
              <circle 
                cx={0} 
                cy={rimSvgY} 
                r={10} 
                fill="#ff6b2c" 
                fillOpacity={0.6}
                stroke="#ff6b2c"
                strokeWidth={3}
              />
              
              {/* Shot marker */}
              <g transform={`translate(${position.x * S}, ${position.y * S})`}>
                <circle r={20} fill="url(#shotGlow)" />
                <circle 
                  r={12} 
                  fill={isThreePointer ? "#00d4ff" : "#ff6b2c"}
                  stroke="#fff"
                  strokeWidth={3}
                  style={{ filter: "drop-shadow(0 0 8px rgba(255,255,255,0.5))" }}
                />
                <line x1={-18} y1={0} x2={18} y2={0} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
                <line x1={0} y1={-18} x2={0} y2={18} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
              </g>
              
              <defs>
                <radialGradient id="shotGlow">
                  <stop offset="0%" stopColor={isThreePointer ? "#00d4ff" : "#ff6b2c"} stopOpacity="0.4" />
                  <stop offset="100%" stopColor={isThreePointer ? "#00d4ff" : "#ff6b2c"} stopOpacity="0" />
                </radialGradient>
              </defs>
            </svg>
          </div>

          {/* Coordinate Controls */}
          <div className="predict-coord-controls">
            <div className="predict-coord-group">
              <div className="predict-coord-header">
                <label>X Position</label>
                <input
                  type="number"
                  value={position.x.toFixed(1)}
                  onChange={(e) => setPosition({ ...position, x: parseFloat(e.target.value) || 0 })}
                  step="0.5"
                  min="-25"
                  max="25"
                  className="predict-coord-input"
                  title="X position coordinate input field"
                />
              </div>
              <input
                type="range"
                value={position.x}
                onChange={(e) => setPosition({ ...position, x: parseFloat(e.target.value) })}
                min="-25"
                max="25"
                step="0.5"
                className="predict-slider"
                title="X position range slider"
              />
              <div className="predict-slider-labels">
                <span>Left (-25)</span>
                <span>Center</span>
                <span>Right (25)</span>
              </div>
            </div>

            <div className="predict-coord-group">
              <div className="predict-coord-header">
                <label>Y Position</label>
                <input
                  type="number"
                  value={position.y.toFixed(1)}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    const yVal = Number.isFinite(val) ? Math.max(0, Math.min(42, val)) : 0;
                    setPosition({ ...position, y: yVal });
                  }}
                  step="0.5"
                  min="0"
                  max="42"
                  className="predict-coord-input"
                  title="Y position coordinate input field"
                />
              </div>
              <input
                type="range"
                value={position.y}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  const yVal = Number.isFinite(val) ? Math.max(0, Math.min(42, val)) : 0;
                  setPosition({ ...position, y: yVal });
                }}
                min="0"
                max="42"
                step="0.5"
                className="predict-slider"
                title="Y position range slider"
              />
              <div className="predict-slider-labels">
                <span>Baseline</span>
                <span>Rim (1)</span>
                <span>Half Court</span>
              </div>
            </div>
          </div>
        </div>

        {/* Controls & Result */}
        <div className="predict-controls-section">
          <div className="predict-profile-callout">
            <div>
              <p className="predict-profile-label">Profile</p>
              <h4>{selectedPlayer ? selectedPlayer.name : "Global model"}</h4>
              <p className="predict-profile-note">
                {selectedPlayer
                  ? "Using this player's historical tendencies for personalization."
                  : "Neutral shot profile across all tracked players."}
              </p>
            </div>
            <div className="predict-profile-chip">
              {isThreePointer ? "Perimeter focus" : isCloseRange ? "Paint pressure" : "Midrange touch"}
            </div>
          </div>

          <div className="predict-control-group">
            <label>Shot Type <span className="predict-auto-tag">Auto</span></label>
            <div className="predict-shot-type-display">
              <div className={`predict-shot-type-indicator ${isThreePointer ? "three" : "two"}`}>
                {isThreePointer ? "3-Point" : "2-Point"} Field Goal
              </div>
              <span className="predict-shot-type-note">
                Based on {distance.toFixed(1)} ft from rim
              </span>
            </div>
          </div>

          <div className="predict-control-group">
            <label>
              Action Type
              {isCloseRange && <span className="predict-zone-tag close">Close Range</span>}
              {!isCloseRange && !isThreePointer && <span className="predict-zone-tag mid">Mid Range</span>}
            </label>
            <div className="predict-action-grid">
              {availableActions.map((a) => (
                <button
                  key={a}
                  className={`predict-action-btn ${action === a ? "active" : ""}`}
                  onClick={() => setAction(a)}
                >
                  {a.replace(" Shot", "")}
                </button>
              ))}
            </div>
            {isThreePointer && (
              <p className="predict-action-note">
                * Dunks & layups not available beyond 3-point line
              </p>
            )}
            {!isCloseRange && !isThreePointer && (
              <p className="predict-action-note">
                * Dunks, layups & tips require close range (&lt;{COURT.closeRangeDistance}ft)
              </p>
            )}
          </div>

          <button 
            className="predict-submit-btn"
            onClick={handlePredict}
            disabled={loading}
          >
            {loading ? (
              <span className="predict-loading">
                <span className="predict-spinner" />
                Calculating...
              </span>
            ) : (
              "Calculate Probability"
            )}
          </button>

          {probability !== null && (
            <div className="predict-result">
              <div className="predict-result-header">Make Probability</div>
              <div 
                className="predict-result-value"
                style={{ color: getProbColor(probability) }}
              >
                {(probability * 100).toFixed(1)}%
              </div>
              <div className="predict-result-bar">
                <div 
                  className="predict-result-fill"
                  style={{ 
                    width: `${probability * 100}%`,
                    background: getProbColor(probability)
                  }}
                />
              </div>
              <div className="predict-result-context">
                {probability < 0.35 && "Difficult shot — low percentage"}
                {probability >= 0.35 && probability < 0.45 && "Below average — contested range"}
                {probability >= 0.45 && probability < 0.55 && "Average — decent look"}
                {probability >= 0.55 && "Good shot — high percentage"}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
