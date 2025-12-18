import { useMemo, useState } from "react";
import { predictGrid, predictShot, GridRequest, ShotRequest } from "./api";
import { Court } from "./components/Court";
import { HeatmapPreview } from "./components/HeatmapPreview";

const defaultShot: ShotRequest = {
  LOC_X: 0,
  LOC_Y: 10,
  YEAR: 2024,
  SHOT_TYPE: "3PT Field Goal",
  ACTION_TYPE: "Jump Shot",
};

const defaultGrid: GridRequest = {
  x_min: -30,
  x_max: 30,
  y_min: -10,
  y_max: 80,
  x_steps: 50,
  y_steps: 50,
  YEAR: 2024,
  SHOT_TYPE: "3PT Field Goal",
  ACTION_TYPE: "Jump Shot",
};

function numberInput(label: string, value: number, onChange: (n: number) => void) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </label>
  );
}

function textInput(label: string, value: string, onChange: (s: string) => void) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

export default function App() {
  const [shot, setShot] = useState<ShotRequest>(defaultShot);
  const [gridReq, setGridReq] = useState<GridRequest>(defaultGrid);
  const [prob, setProb] = useState<number | null>(null);
  const [gridData, setGridData] = useState<number[]>([]);
  const [gridMeta, setGridMeta] = useState<{ xs: number; ys: number }>({ xs: 0, ys: 0 });
  const [loadingShot, setLoadingShot] = useState(false);
  const [loadingGrid, setLoadingGrid] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePredictShot = async () => {
    setError(null);
    setLoadingShot(true);
    try {
      const res = await predictShot(shot);
      setProb(res.probability_make);
    } catch (e: any) {
      setError(e.message || "Shot prediction failed");
    } finally {
      setLoadingShot(false);
    }
  };

  const handlePredictGrid = async () => {
    setError(null);
    setLoadingGrid(true);
    try {
      const res = await predictGrid(gridReq);
      setGridData(res.probabilities);
      setGridMeta({ xs: gridReq.x_steps ?? 0, ys: gridReq.y_steps ?? 0 });
    } catch (e: any) {
      setError(e.message || "Grid prediction failed");
    } finally {
      setLoadingGrid(false);
    }
  };

  const heatmapMatrix = useMemo(() => {
    if (!gridMeta.xs || !gridMeta.ys) return [];
    const out: number[][] = [];
    for (let i = 0; i < gridMeta.ys; i++) {
      const row = gridData.slice(i * gridMeta.xs, (i + 1) * gridMeta.xs);
      out.push(row);
    }
    return out;
  }, [gridData, gridMeta]);

  return (
    <div className="app">
      <header>
        <h1>NBA Shot Make Predictor</h1>
        <p>Model-driven shot probabilities and expected FG% heatmaps.</p>
      </header>

      {error && <div className="error">{error}</div>}

      <div className="panels">
        <section className="panel">
          <h2>Shot Inputs</h2>
          <div className="grid-2">
            {numberInput("LOC_X", shot.LOC_X, (n) => setShot({ ...shot, LOC_X: n }))}
            {numberInput("LOC_Y", shot.LOC_Y, (n) => setShot({ ...shot, LOC_Y: n }))}
            {numberInput("YEAR", shot.YEAR ?? 2024, (n) => setShot({ ...shot, YEAR: n }))}
            {numberInput(
              "SHOT_DISTANCE",
              shot.SHOT_DISTANCE ?? Math.sqrt(shot.LOC_X ** 2 + shot.LOC_Y ** 2),
              (n) => setShot({ ...shot, SHOT_DISTANCE: n })
            )}
            {textInput("SHOT_TYPE", shot.SHOT_TYPE || "", (s) => setShot({ ...shot, SHOT_TYPE: s }))}
            {textInput("ACTION_TYPE", shot.ACTION_TYPE || "", (s) =>
              setShot({ ...shot, ACTION_TYPE: s })
            )}
          </div>
          <button onClick={handlePredictShot} disabled={loadingShot}>
            {loadingShot ? "Predicting..." : "Predict Shot Make"}
          </button>
          {prob !== null && (
            <div className="result">
              Probability of Make: <strong>{(prob * 100).toFixed(1)}%</strong>
            </div>
          )}
        </section>

        <section className="panel">
          <h2>Expected FG% Heatmap</h2>
          <div className="grid-3">
            {numberInput("x_min", gridReq.x_min ?? -30, (n) => setGridReq({ ...gridReq, x_min: n }))}
            {numberInput("x_max", gridReq.x_max ?? 30, (n) => setGridReq({ ...gridReq, x_max: n }))}
            {numberInput("x_steps", gridReq.x_steps ?? 50, (n) => setGridReq({ ...gridReq, x_steps: n }))}
            {numberInput("y_min", gridReq.y_min ?? -10, (n) => setGridReq({ ...gridReq, y_min: n }))}
            {numberInput("y_max", gridReq.y_max ?? 80, (n) => setGridReq({ ...gridReq, y_max: n }))}
            {numberInput("y_steps", gridReq.y_steps ?? 50, (n) => setGridReq({ ...gridReq, y_steps: n }))}
            {textInput("SHOT_TYPE", gridReq.SHOT_TYPE || "", (s) => setGridReq({ ...gridReq, SHOT_TYPE: s }))}
            {textInput("ACTION_TYPE", gridReq.ACTION_TYPE || "", (s) =>
              setGridReq({ ...gridReq, ACTION_TYPE: s })
            )}
            {numberInput("YEAR", gridReq.YEAR ?? 2024, (n) => setGridReq({ ...gridReq, YEAR: n }))}
          </div>
          <button onClick={handlePredictGrid} disabled={loadingGrid}>
            {loadingGrid ? "Generating..." : "Generate Heatmap"}
          </button>
          <HeatmapPreview matrix={heatmapMatrix} />
        </section>
      </div>

      <section className="panel">
        <h2>Court (Reference)</h2>
        <Court />
      </section>
    </div>
  );
}

