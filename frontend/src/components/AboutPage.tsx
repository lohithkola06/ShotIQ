import { useEffect, useState } from "react";

type AboutPageProps = {
  onAnalyze: () => void;
  onPredict: () => void;
};

const ACTION_LABELS = ["Jump Shot", "Layup", "3PT", "Post", "Floater"];

export function AboutPage({ onAnalyze, onPredict }: AboutPageProps) {
  const [barValues, setBarValues] = useState<number[]>(() =>
    ACTION_LABELS.map(() => Math.floor(Math.random() * 60) + 30)
  );

  useEffect(() => {
    const id = setInterval(() => {
      setBarValues(ACTION_LABELS.map(() => Math.floor(Math.random() * 60) + 30));
    }, 1500);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="about-page fade-in">
      <section className="about-hero">
        <div className="about-hero__text">
          <div className="about-kicker">Data + ML + Hoops</div>
          <h1>NBA Shot Analysis & Prediction, reimagined.</h1>
          <p>
            ShotIQ ingests 3.6 million NBA shots from 18 seasons to forecast make probabilities,
            map shooting zones, and compare legends across eras. Built for analysts, fans,
            and hoopers who want to see the game through data.
          </p>
          {/* Buttons moved into hero card below */}
          <div className="about-metrics">
            <div className="about-metric">
              <div className="about-metric__value">3.6M</div>
              <div className="about-metric__label">Shots</div>
            </div>
            <div className="about-metric">
              <div className="about-metric__value">18</div>
              <div className="about-metric__label">Seasons</div>
            </div>
            <div className="about-metric">
              <div className="about-metric__value">2004–2024</div>
              <div className="about-metric__label">Coverage</div>
            </div>
            <div className="about-metric">
              <div className="about-metric__value">XGBoost</div>
              <div className="about-metric__label">ML Engine</div>
            </div>
          </div>
        </div>
        <div className="about-hero__card">
          <div className="about-hero__stat">
            <strong>Predict • Compare • Visualize</strong>
          </div>
          <div className="about-hero__bars">
            {ACTION_LABELS.map((label, idx) => (
              <div className="about-hero__bar" key={label}>
                <div className="about-hero__bar-label">{label}</div>
                <div className="about-hero__bar-track">
                  <div
                    className={`about-hero__bar-fill about-hero__bar-fill--${idx % 3}`}
                    style={{ width: `${barValues[idx]}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="about-hero__note">
            Powered by Supabase, FastAPI, and an XGBoost model trained on Kaggle NBA shot data.
          </p>
          <div className="about-hero__inline-cta">
            <button className="btn btn--primary" onClick={onAnalyze}>
              Analyze players
            </button>
            <button className="btn btn--secondary" onClick={onPredict}>
              Predict a shot
            </button>
          </div>
        </div>
      </section>

      <section className="about-grid">
        <div className="about-card">
          <div className="about-card__eyebrow">Dataset</div>
          <h3>NBA shot logs from Kaggle</h3>
          <p>
            We use Kaggle’s consolidated NBA shot logs (2004–2019, 2023–2024), cleaned and unified
            into a single Supabase table. Each shot includes location, distance, shot/action type,
            year, and result—fueling both analytics and ML inference.
          </p>
          <ul className="about-list">
            <li>3.6 million shots</li>
            <li>~2,000 unique players</li>
            <li>Locations, shot types, actions, makes/misses</li>
          </ul>
        </div>
        <div className="about-card">
          <div className="about-card__eyebrow">Prediction</div>
          <h3>Shot make probability</h3>
          <p>
            Click anywhere on the court, set shot/action type, and get an instant ML-powered make
            probability. The model uses spatial features plus context (year, shot type, action) to
            estimate outcomes.
          </p>
          <ul className="about-list">
            <li>XGBoost classifier on tabular shot features</li>
            <li>Handles 2PT/3PT, action types, distance</li>
            <li>Interactive court with live animations</li>
          </ul>
        </div>
        <div className="about-card">
          <div className="about-card__eyebrow">Player analysis</div>
          <h3>Deep dives & comparisons</h3>
          <p>
            Browse any player’s career, filter by seasons, see shot charts, zone splits, actions, and
            shot types. Compare two players head-to-head across overlapping seasons to find edges.
          </p>
          <ul className="about-list">
            <li>Career and season filters</li>
            <li>Zone, action, and shot-type breakdowns</li>
            <li>Head-to-head comparisons</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
