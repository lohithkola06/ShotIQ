import { useState } from "react";
import { Player } from "./api";
import { PlayerSearch } from "./components/PlayerSearch";
import { PlayerStats } from "./components/PlayerStats";
import { PredictPanel } from "./components/PredictPanel";
import { CompareView } from "./components/CompareView";

type Tab = "players" | "predict" | "compare";

const NAV_ITEMS: { id: Tab; label: string; icon: string }[] = [
  { id: "players", label: "Players", icon: "🏀" },
  { id: "predict", label: "Predict", icon: "🎯" },
  { id: "compare", label: "Compare", icon: "⚔️" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("players");
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="site-header">
        <div className="site-header__brand">
          <span className="site-header__logo">🏀</span>
          <span className="site-header__title">ShotIQ</span>
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
          <span className="site-header__seasons">2004–2024</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
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
