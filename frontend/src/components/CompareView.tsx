import { useState, useEffect, useMemo } from "react";
import { Player, PlayerStats, comparePlayers, getPlayer } from "../api";
import { PlayerSearch } from "./PlayerSearch";
import { BarChart } from "./BarChart";

export function CompareView() {
  const [player1, setPlayer1] = useState<Player | null>(null);
  const [player2, setPlayer2] = useState<Player | null>(null);
  const [player1Years, setPlayer1Years] = useState<number[]>([]);
  const [player2Years, setPlayer2Years] = useState<number[]>([]);
  const [stats1, setStats1] = useState<PlayerStats | null>(null);
  const [stats2, setStats2] = useState<PlayerStats | null>(null);
  const [selectedYears, setSelectedYears] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingYears, setLoadingYears] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawerCollapsed, setDrawerCollapsed] = useState(false);

  // Common years between both players
  const commonYears = useMemo(() => {
    if (player1Years.length === 0 || player2Years.length === 0) return [];
    const set1 = new Set(player1Years);
    return player2Years.filter((year) => set1.has(year)).sort((a, b) => a - b);
  }, [player1Years, player2Years]);

  // Load player 1's available years
  useEffect(() => {
    if (!player1) {
      setPlayer1Years([]);
      return;
    }
    setLoadingYears(true);
    getPlayer(player1.name)
      .then((data) => {
        setPlayer1Years(data.seasons.map((s) => s.year).sort((a, b) => a - b));
      })
      .catch(console.error)
      .finally(() => setLoadingYears(false));
  }, [player1]);

  // Load player 2's available years
  useEffect(() => {
    if (!player2) {
      setPlayer2Years([]);
      return;
    }
    setLoadingYears(true);
    getPlayer(player2.name)
      .then((data) => {
        setPlayer2Years(data.seasons.map((s) => s.year).sort((a, b) => a - b));
      })
      .catch(console.error)
      .finally(() => setLoadingYears(false));
  }, [player2]);

  // Clear selected years that are no longer common when players change
  useEffect(() => {
    if (commonYears.length > 0) {
      setSelectedYears((prev) => prev.filter((y) => commonYears.includes(y)));
    } else {
      setSelectedYears([]);
    }
  }, [commonYears]);

  // Load comparison when both players selected
  useEffect(() => {
    if (!player1 || !player2) {
      setStats1(null);
      setStats2(null);
      return;
    }

    async function loadComparison() {
      setLoading(true);
      setError(null);
      try {
        const yearsParam = selectedYears.length > 0 ? selectedYears : undefined;
        const result = await comparePlayers(player1!.name, player2!.name, yearsParam);
        setStats1(result.player1);
        setStats2(result.player2);
        setDrawerCollapsed(true);
      } catch (err) {
        console.error("Comparison failed:", err);
        setError("Unable to load comparison right now. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    loadComparison();
  }, [player1, player2, selectedYears]);

  const toggleYear = (year: number) => {
    setSelectedYears((prev) =>
      prev.includes(year) ? prev.filter((y) => y !== year) : [...prev, year]
    );
  };

  const renderCompareRow = (
    label: string,
    val1: number | string,
    val2: number | string,
    isPercentage = false
  ) => {
    const v1 = typeof val1 === "number" ? val1 : parseFloat(val1) || 0;
    const v2 = typeof val2 === "number" ? val2 : parseFloat(val2) || 0;
    const winner = v1 > v2 ? 1 : v2 > v1 ? 2 : 0;

    const format = (v: number | string) => {
      if (typeof v === "string") return v;
      return isPercentage ? `${(v * 100).toFixed(1)}%` : v.toLocaleString();
    };

    return (
      <div className="compare-row" key={label}>
        <div
          className={`compare-value compare-value--left ${
            winner === 1 ? "compare-value--winner" : ""
          }`}
        >
          {format(val1)}
        </div>
        <div className="compare-label">{label}</div>
        <div
          className={`compare-value compare-value--right ${
            winner === 2 ? "compare-value--winner" : ""
          }`}
        >
          {format(val2)}
        </div>
      </div>
    );
  };

  return (
    <div className="fade-in">
      {/* Player selectors */}
      {!drawerCollapsed && (
        <div className="compare-selectors">
          <div className="card compare-selector-card compare-selector-card--left">
            <div className="card__header">
              <h2 className="card__title compare-title--left">
                {player1?.name || "Player 1"}
              </h2>
            </div>
            <PlayerSearch
              onSelect={setPlayer1}
              selectedPlayer={player1}
              placeholder="Search first player..."
            />
          </div>

          <div className="compare-vs-badge">VS</div>

          <div className="card compare-selector-card compare-selector-card--right">
            <div className="card__header">
              <h2 className="card__title compare-title--right">
                {player2?.name || "Player 2"}
              </h2>
            </div>
            <PlayerSearch
              onSelect={setPlayer2}
              selectedPlayer={player2}
              placeholder="Search second player..."
            />
          </div>
        </div>
      )}

      {drawerCollapsed && (
        <div className="compare-reopen">
          <button className="btn btn--secondary" onClick={() => setDrawerCollapsed(false)}>
            Change players / years
          </button>
        </div>
      )}

      {/* Year filters - only show common years */}
      {player1 && player2 && commonYears.length > 0 && (
        <div className="compare-years-section">
          <div className="compare-years-label">Common Seasons</div>
          <div className="year-filters">
            {commonYears.map((year) => (
              <button
                key={year}
                className={`year-pill ${selectedYears.includes(year) ? "year-pill--active" : ""}`}
                onClick={() => toggleYear(year)}
              >
                {year}
              </button>
            ))}
            {selectedYears.length > 0 && (
              <button className="year-pill year-pill--clear" onClick={() => setSelectedYears([])}>
                Clear
              </button>
            )}
          </div>
        </div>
      )}

      {player1 && player2 && commonYears.length === 0 && !loadingYears && (player1Years.length > 0 || stats1?.seasons?.length) && (player2Years.length > 0 || stats2?.seasons?.length) && (
        <div className="compare-no-common-years">
          These players have no overlapping seasons in the dataset.
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {/* Loading state */}
      {loading && (
        <div className="loading">
          <div className="spinner" />
        </div>
      )}

      {/* Comparison results */}
      {stats1 && stats2 && !loading && (
        <div className="card fade-in">
          <div className="compare-header">
            <div className="compare-player compare-player--orange compare-player--left">
              {stats1.player_name}
            </div>
            <div className="compare-vs">STAT</div>
            <div className="compare-player compare-player--blue compare-player--right">
              {stats2.player_name}
            </div>
          </div>

          {renderCompareRow("Total Shots", stats1.total_shots, stats2.total_shots)}
          {renderCompareRow("Made Shots", stats1.made_shots, stats2.made_shots)}
          {renderCompareRow("FG%", stats1.fg_pct, stats2.fg_pct, true)}
          {renderCompareRow("Avg Distance", `${stats1.avg_distance} ft`, `${stats2.avg_distance} ft`)}

          <div className="compare-charts-section">
            <div className="compare-chart compare-chart--left">
              <h3 className="compare-chart-title compare-chart-title--left">
                {stats1.player_name} - Zone FG%
              </h3>
              <BarChart
                data={stats1.zones.map((z) => ({
                  label: z.zone,
                  value: z.fg_pct,
                  maxValue: 1,
                }))}
              />
            </div>
            <div className="compare-chart compare-chart--right">
              <h3 className="compare-chart-title compare-chart-title--right">
                {stats2.player_name} - Zone FG%
              </h3>
              <BarChart
                data={stats2.zones.map((z) => ({
                  label: z.zone,
                  value: z.fg_pct,
                  maxValue: 1,
                }))}
                variant="blue"
                alignRight
              />
            </div>
          </div>

          <div className="compare-charts-section">
            <div className="compare-chart compare-chart--left">
              <h3 className="compare-chart-title compare-chart-title--left">
                Shot Types
              </h3>
              <BarChart
                data={stats1.shot_types.map((st) => ({
                  label: st.shot_type,
                  value: st.fg_pct,
                  maxValue: 1,
                }))}
              />
            </div>
            <div className="compare-chart compare-chart--right">
              <h3 className="compare-chart-title compare-chart-title--right">
                Shot Types
              </h3>
              <BarChart
                data={stats2.shot_types.map((st) => ({
                  label: st.shot_type,
                  value: st.fg_pct,
                  maxValue: 1,
                }))}
                variant="blue"
                alignRight
              />
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {(!player1 || !player2) && !loading && (
        <div className="empty-state">
          <div className="empty-state__icon">⚔️</div>
          <div className="empty-state__title">Select two players to compare</div>
          <p>Choose players from the panels above</p>
        </div>
      )}
    </div>
  );
}
