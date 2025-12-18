export type ShotRequest = {
  LOC_X: number;
  LOC_Y: number;
  SHOT_DISTANCE?: number;
  YEAR?: number;
  SHOT_TYPE?: string;
  ACTION_TYPE?: string;
};

export type GridRequest = {
  x_min?: number;
  x_max?: number;
  y_min?: number;
  y_max?: number;
  x_steps?: number;
  y_steps?: number;
  YEAR?: number;
  SHOT_TYPE?: string;
  ACTION_TYPE?: string;
};

const API_BASE = "/api";

export async function predictShot(req: ShotRequest) {
  const res = await fetch(`${API_BASE}/predict_shot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`predict_shot failed: ${res.status}`);
  return res.json() as Promise<{ probability_make: number }>;
}

export async function predictGrid(req: GridRequest) {
  const res = await fetch(`${API_BASE}/predict_grid`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`predict_grid failed: ${res.status}`);
  return res.json() as Promise<{ grid: any[]; probabilities: number[] }>;
}

