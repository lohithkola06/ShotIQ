import { useEffect, useState } from "react";
import { Player, getPlayer, getPlayerShots, getPlayers, getYears } from "./api";
import { PlayerSearch } from "./components/PlayerSearch";
import { PlayerStats } from "./components/PlayerStats";
import { PredictPanel } from "./components/PredictPanel";
import { CompareView } from "./components/CompareView";
import { AboutPage } from "./components/AboutPage";

type Tab = "about" | "players" | "predict" | "compare";

const NAV_ITEMS: { id: Tab; label: string; icon: string }[] = [
  { id: "players", label: "Players", icon: "🏀" },
  { id: "predict", label: "Predict", icon: "🎯" },
  { id: "compare", label: "Compare", icon: "⚔️" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("about");
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [preloading, setPreloading] = useState(true);

  // Warm up data caches on first load
  useEffect(() => {
    (async () => {
      try {
        const [{ players }, _years] = await Promise.all([
          getPlayers("", 50),
          getYears(),
        ]);
        // Prefetch first popular player stats/shots to make initial click instant
        if (players && players.length > 0) {
          const top = players[0];
          await Promise.all([
            getPlayer(top.name),
            getPlayerShots(top.name, undefined, 15000),
          ]);
        }
      } catch (err) {
        console.error("Preload failed", err);
      } finally {
        // brief delay for UX polish
        setTimeout(() => setPreloading(false), 400);
      }
    })();
  }, []);

  // Background prefetch for top players to keep cache warm
  useEffect(() => {
    let cancelled = false;
    async function prefetchLoop() {
      try {
        const { players } = await getPlayers("", 100);
        const top = players.slice(0, 8);
        for (const p of top) {
          if (cancelled) break;
          await Promise.all([
            getPlayer(p.name),
            getPlayerShots(p.name, undefined, 20000),
          ]);
        }
      } catch (err) {
        console.error("Background prefetch failed", err);
      } finally {
        if (!cancelled) {
          setTimeout(prefetchLoop, 10 * 60 * 1000); // refresh every 10 minutes
        }
      }
    }
    prefetchLoop();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-container">
      {preloading && (
        <div className="preload-overlay">
          <div className="preload-glow" />
          <div className="preload-card">
            <div className="preload-logo">🏀</div>
            <div className="preload-title">ShotIQ</div>
            <div className="preload-subtitle">Warming up data & model...</div>
            <div className="preload-progress">
              <div className="preload-progress__bar" />
            </div>
          </div>
        </div>
      )}
      {/* Header */}
      <header className="site-header">
        <div className="site-header__shell">
          <div
            className="site-header__brand site-header__brand--clickable"
            onClick={() => setActiveTab("about")}
            role="button"
            aria-label="Go to About"
          >
            <div className="site-header__logo-badge">
              <span className="site-header__logo">🏀</span>
            </div>
            <div className="site-header__title">ShotIQ</div>
          </div>

          <nav className="site-header__nav">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                className={`site-header__nav-btn ${activeTab === item.id ? "active" : ""}`}
                onClick={() => setActiveTab(item.id)}
              >
                <span className="site-header__nav-icon">{item.icon}</span>
                <span className="site-header__nav-label">{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="site-header__meta">
            <div className="site-header__tagline">NBA Shot Analysis & Prediction</div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {activeTab === "about" && (
          <AboutPage onAnalyze={() => setActiveTab("players")} onPredict={() => setActiveTab("predict")} />
        )}

        {activeTab === "players" && (
          <div className="grid grid--sidebar fade-in">
            <div className="card">
              <div className="card__header">
                <h2 className="card__title">Select Player</h2>
              </div>
              <PlayerSearch
                onSelect={setSelectedPlayer}
                selectedPlayer={selectedPlayer}
              />
            </div>

            <div className="card">
              {selectedPlayer ? (
                <>
                  <div className="card__header">
                    <h2
                      className="card__title"
                      style={{
                        fontSize: "1.4rem",
                        background: "linear-gradient(135deg, var(--neon-orange), #ffaa00)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                        backgroundClip: "text",
                      }}
                    >
                      {selectedPlayer.name}
                    </h2>
                  </div>
                  <PlayerStats playerName={selectedPlayer.name} />
                </>
              ) : (
                <div className="empty-state">
                  <div className="empty-state__icon">🏀</div>
                  <div className="empty-state__title">Select a player</div>
                  <p>Choose a player from the list to view their shot analysis</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "predict" && <PredictPanel />}

        {activeTab === "compare" && <CompareView />}
      </main>

      {/* Footer */}
      <footer className="site-footer">
        <div className="site-footer__content">
          <div className="site-footer__brand">
            <span className="site-footer__logo">🏀</span>
            <span className="site-footer__title">ShotIQ</span>
            <span className="site-footer__tagline">NBA Shot Analysis Platform</span>
          </div>
          
          <div className="site-footer__info">
            <div className="site-footer__stat">
              <span className="site-footer__stat-value">3.6M+</span>
              <span className="site-footer__stat-label">Shots Analyzed</span>
            </div>
            <div className="site-footer__stat">
              <span className="site-footer__stat-value">18</span>
              <span className="site-footer__stat-label">Seasons</span>
            </div>
            <div className="site-footer__stat">
              <span className="site-footer__stat-value">XGBoost</span>
              <span className="site-footer__stat-label">ML Model</span>
            </div>
          </div>

          <div className="site-footer__credits">
            <p>Powered by machine learning • Data from 2004–2019, 2023–2024 NBA seasons</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
