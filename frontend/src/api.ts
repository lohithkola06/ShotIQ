export type ShotRequest = {
  LOC_X: number;
  LOC_Y: number;
  SHOT_DISTANCE?: number;
  YEAR?: number;
  SHOT_TYPE?: string;
  ACTION_TYPE?: string;
  player_name?: string;
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

export type ShotBin = {
  x_bin: number;
  y_bin: number;
  attempts: number;
  made: number;
  fg_pct: number;
};

export type ShotBinsResponse = {
  bins: ShotBin[];
  x_bins: number;
  y_bins: number;
  x_range: [number, number];
  y_range: [number, number];
};
const API_BASE = "/api";

// Simple in-memory caches to reduce repeat network calls
const cache = {
  players: new Map<string, Promise<{ players: Player[] }>>(),
  years: null as Promise<{ years: number[] }> | null,
  playerStats: new Map<string, Promise<PlayerStats>>(),
  playerShots: new Map<string, Promise<{ shots: Shot[]; total: number }>>(),
  compare: new Map<string, Promise<{ player1: PlayerStats; player2: PlayerStats }>>(),
};

function memoize<T>(store: Map<string, Promise<T>>, key: string, fn: () => Promise<T>) {
  if (store.has(key)) return store.get(key)!;
  const promise = fn().catch((err) => {
    store.delete(key);
    throw err;
  });
  store.set(key, promise);
  return promise;
}

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
    limit: "50",
  });
  const key = `${search}|${minShots}`;
  return memoize(cache.players, key, async () => {
    const res = await fetch(`${API_BASE}/players?${params}`);
    if (!res.ok) throw new Error(`getPlayers failed: ${res.status}`);
    return res.json() as Promise<{ players: Player[] }>;
  });
}

export async function getYears() {
  if (cache.years) return cache.years;
  cache.years = (async () => {
    const res = await fetch(`${API_BASE}/years`);
    if (!res.ok) throw new Error(`getYears failed: ${res.status}`);
    return res.json() as Promise<{ years: number[] }>;
  })().catch((err) => {
    cache.years = null;
    throw err;
  });
  return cache.years;
}

export async function getPlayer(playerName: string, years?: number[]) {
  const params = years ? `?years=${years.join(",")}` : "";
  const key = `${playerName}|${years?.join(",") || "all"}`;
  return memoize(cache.playerStats, key, async () => {
    const res = await fetch(`${API_BASE}/player/${encodeURIComponent(playerName)}${params}`);
    if (!res.ok) throw new Error(`getPlayer failed: ${res.status}`);
    return res.json() as Promise<PlayerStats>;
  });
}

export async function getPlayerShots(playerName: string, years?: number[], limit: number = 3000) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (years) params.set("years", years.join(","));
  const key = `${playerName}|${years?.join(",") || "all"}|${limit}`;
  return memoize(cache.playerShots, key, async () => {
    const res = await fetch(`${API_BASE}/player/${encodeURIComponent(playerName)}/shots?${params}`);
    if (!res.ok) throw new Error(`getPlayerShots failed: ${res.status}`);
    return res.json() as Promise<{ shots: Shot[]; total: number }>;
  });
}

export async function comparePlayers(player1: string, player2: string, years?: number[]) {
  const key = `${player1}|${player2}|${years?.join(",") || "all"}`;
  return memoize(cache.compare, key, async () => {
    const res = await fetch(`${API_BASE}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player1, player2, years }),
    });
    if (!res.ok) throw new Error(`comparePlayers failed: ${res.status}`);
    return res.json() as Promise<{ player1: PlayerStats; player2: PlayerStats }>;
  });
}
