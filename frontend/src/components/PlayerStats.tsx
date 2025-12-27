import { useState, useEffect } from "react";
import {
  getPlayer,
  getPlayerShots,
  PlayerStats as PlayerStatsType,
  Shot,
} from "../api";
import { BarChart } from "./BarChart";
import { ShotChart } from "./ShotChart";

interface PlayerStatsProps {
  playerName: string;
}

type ViewTab = "shots" | "zones" | "seasons";

export function PlayerStats({ playerName }: PlayerStatsProps) {
  const [stats, setStats] = useState<PlayerStatsType | null>(null);
  const [shots, setShots] = useState<Shot[]>([]);
  const [playerYears, setPlayerYears] = useState<number[]>([]);
  const [selectedYears, setSelectedYears] = useState<number[]>([]);
  const [activeTab, setActiveTab] = useState<ViewTab>("shots");
  const [loading, setLoading] = useState(true);

  // Reset selected years when player changes
  useEffect(() => {
    setSelectedYears([]);
  }, [playerName]);

  // Load player data when name or years change
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const yearsParam = selectedYears.length > 0 ? selectedYears : undefined;
        const [playerData, shotsData] = await Promise.all([
          getPlayer(playerName, yearsParam),
          getPlayerShots(playerName, yearsParam, 2500),
        ]);
        setStats(playerData);
        setShots(shotsData.shots);
        
        // Extract player's years from their season data (only on initial load)
        if (selectedYears.length === 0 && playerData.seasons) {
          const years = playerData.seasons.map((s) => s.year).sort((a, b) => a - b);
          setPlayerYears(years);
        }
      } catch (err) {
        console.error("Failed to load player data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [playerName, selectedYears]);

  const toggleYear = (year: number) => {
    setSelectedYears((prev) =>
      prev.includes(year) ? prev.filter((y) => y !== year) : [...prev, year]
    );
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  if (!stats) {
    return <div className="error-message">Failed to load player data</div>;
  }

  return (
    <div className="fade-in">
      {/* Year filters - only show years the player has played */}
      <div className="year-filters">
        {playerYears.map((year) => (
          <button
            key={year}
            className={`year-pill ${selectedYears.includes(year) ? "year-pill--active" : ""}`}
            onClick={() => toggleYear(year)}
          >
            {year}
          </button>
        ))}
        {selectedYears.length > 0 && (
          <button className="year-pill" onClick={() => setSelectedYears([])}>
            Clear
          </button>
        )}
      </div>

      {/* Stats overview */}
      <div className="stats-row">
        <div className="stat-card fade-in stagger-1">
          <div className="stat-card__value">{stats.total_shots.toLocaleString()}</div>
          <div className="stat-card__label">Total Shots</div>
        </div>
        <div className="stat-card fade-in stagger-2">
          <div className="stat-card__value">{stats.made_shots.toLocaleString()}</div>
          <div className="stat-card__label">Made</div>
        </div>
        <div className="stat-card fade-in stagger-3">
          <div className="stat-card__value">{(stats.fg_pct * 100).toFixed(1)}%</div>
          <div className="stat-card__label">FG%</div>
        </div>
        <div className="stat-card fade-in stagger-4">
          <div className="stat-card__value">{stats.avg_distance.toFixed(1)}</div>
          <div className="stat-card__label">Avg Dist (ft)</div>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === "shots" ? "tab--active" : ""}`}
          onClick={() => setActiveTab("shots")}
        >
          Shot Chart
        </button>
        <button
          className={`tab ${activeTab === "zones" ? "tab--active" : ""}`}
          onClick={() => setActiveTab("zones")}
        >
          Zone Analysis
        </button>
        <button
          className={`tab ${activeTab === "seasons" ? "tab--active" : ""}`}
          onClick={() => setActiveTab("seasons")}
        >
          By Season
        </button>
      </div>

      {/* Tab content */}
      {activeTab === "shots" && (
        <div className="grid grid--2 fade-in">
          <div>
            <ShotChart shots={shots} />
          </div>
          <div>
            <BarChart
              title="FG% by Shot Type"
              data={stats.shot_types.map((st) => ({
                label: st.shot_type,
                value: st.fg_pct,
                maxValue: 1,
              }))}
            />
            <div style={{ marginTop: "var(--space-4)" }}>
              <BarChart
                title="Top Actions"
                data={stats.actions.slice(0, 6).map((a) => ({
                  label: a.action_type.replace(" Shot", ""),
                  value: a.fg_pct,
                  maxValue: 1,
                }))}
                variant="blue"
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === "zones" && (
        <div className="grid grid--2 fade-in">
          <BarChart
            title="FG% by Distance"
            data={stats.zones.map((z) => ({
              label: z.zone,
              value: z.fg_pct,
              maxValue: 1,
            }))}
          />
          <BarChart
            title="Volume by Zone"
            data={stats.zones.map((z) => ({
              label: z.zone,
              value: z.attempts,
            }))}
            variant="blue"
            formatValue={(v) => v.toLocaleString()}
          />
        </div>
      )}

      {activeTab === "seasons" && (
        <div className="grid grid--2 fade-in">
          <BarChart
            title="FG% by Season"
            data={stats.seasons.map((s) => ({
              label: String(s.year),
              value: s.fg_pct,
              maxValue: 1,
            }))}
          />
          <BarChart
            title="Volume by Season"
            data={stats.seasons.map((s) => ({
              label: String(s.year),
              value: s.attempts,
            }))}
            variant="blue"
            formatValue={(v) => v.toLocaleString()}
          />
        </div>
      )}
    </div>
  );
}
