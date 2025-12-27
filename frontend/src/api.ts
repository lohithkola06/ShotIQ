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

export type Player = {
  name: string;
  total_shots: number;
  fg_pct: number;
};

export type ShotTypeStats = {
  shot_type: string;
  attempts: number;
  made: number;
  fg_pct: number;
};

export type SeasonStats = {
  year: number;
  attempts: number;
  made: number;
  fg_pct: number;
};

export type ZoneStats = {
  zone: string;
  attempts: number;
  made: number;
  fg_pct: number;
};

export type ActionStats = {
  action_type: string;
  attempts: number;
  made: number;
  fg_pct: number;
};

export type PlayerStats = {
  player_name: string;
  total_shots: number;
  made_shots: number;
  fg_pct: number;
  avg_distance: number;
  shot_types: ShotTypeStats[];
  seasons: SeasonStats[];
  zones: ZoneStats[];
  actions: ActionStats[];
};

export type Shot = {
  LOC_X: number;
  LOC_Y: number;
  SHOT_MADE_FLAG: number;
  SHOT_DISTANCE: number;
  SHOT_TYPE: string;
  ACTION_TYPE: string;
  YEAR: number;
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

export async function getPlayers(search: string = "", minShots: number = 500) {
  const params = new URLSearchParams({
    search,
    min_shots: minShots.toString(),
    limit: "100",
  });
  const res = await fetch(`${API_BASE}/players?${params}`);
  if (!res.ok) throw new Error(`getPlayers failed: ${res.status}`);
  return res.json() as Promise<{ players: Player[] }>;
}

export async function getYears() {
  const res = await fetch(`${API_BASE}/years`);
  if (!res.ok) throw new Error(`getYears failed: ${res.status}`);
  return res.json() as Promise<{ years: number[] }>;
}

export async function getPlayer(playerName: string, years?: number[]) {
  const params = years ? `?years=${years.join(",")}` : "";
  const res = await fetch(`${API_BASE}/player/${encodeURIComponent(playerName)}${params}`);
  if (!res.ok) throw new Error(`getPlayer failed: ${res.status}`);
  return res.json() as Promise<PlayerStats>;
}

export async function getPlayerShots(playerName: string, years?: number[], limit: number = 3000) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (years) params.set("years", years.join(","));
  const res = await fetch(`${API_BASE}/player/${encodeURIComponent(playerName)}/shots?${params}`);
  if (!res.ok) throw new Error(`getPlayerShots failed: ${res.status}`);
  return res.json() as Promise<{ shots: Shot[]; total: number }>;
}

export async function comparePlayers(player1: string, player2: string, years?: number[]) {
  const res = await fetch(`${API_BASE}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player1, player2, years }),
  });
  if (!res.ok) throw new Error(`comparePlayers failed: ${res.status}`);
  return res.json() as Promise<{ player1: PlayerStats; player2: PlayerStats }>;
}
