"""
NBA Shot Predictor API - Using Supabase for data storage.
"""
import os
import json
import threading
from functools import lru_cache
from time import monotonic, time
from typing import Any, Dict, List, Optional, Tuple
from math import sqrt

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

from src.inference import load_model, predict_single

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pabegzmewqavkqndmclg.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBhYmVnem1ld3FhdmtxbmRtY2xnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NjA3NTUsImV4cCI6MjA4MjQzNjc1NX0.uzlx6XpH5JkJIuO0uWfqeAD6woa1gI9fNlVrk0AyXU4")
CACHE_FILE = os.path.join("data", "player_stats_cache.json")

app = FastAPI(title="NBA Shot Predictor API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ShotRequest(BaseModel):
    LOC_X: float
    LOC_Y: float
    SHOT_DISTANCE: Optional[float] = None
    YEAR: int = 2024
    SHOT_TYPE: str = "3PT Field Goal"
    ACTION_TYPE: str = "Jump Shot"


class PlayerCompareRequest(BaseModel):
    player1: str
    player2: str
    years: Optional[List[int]] = None

class ShotsPageRequest(BaseModel):
    player_name: str
    years: Optional[List[int]] = None
    page: int = 1
    page_size: int = 2000

class ShotsBinsRequest(BaseModel):
    player_name: str
    years: Optional[List[int]] = None
    x_bins: int = 25
    y_bins: int = 20

# Cached clients
@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Get Supabase client (cached)."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@lru_cache(maxsize=1)
def _warm_model():
    return load_model()

# Warm critical resources on startup so first request is fast
@app.on_event("startup")
async def _startup_warm():
    try:
        _warm_model()
    except Exception as e:
        print(f"Model warmup failed: {e}")
    # Opportunistic player roster prefetch (keep it light to avoid Supabase timeouts)
    try:
        _load_players_cache(min_shot_count=50, limit=500)
    except Exception as e:
        print(f"Player prefetch at startup failed: {e}")
    threading.Thread(target=_warm_stats_cache, daemon=True).start()

# Simple in-process cache for expensive reads (fallback when Redis unavailable)
# Structure: { key: (expires_at, data) }
_cache: Dict[str, Tuple[float, Any]] = {}
_players_cache: Dict[str, Any] = {"data": None, "fetched_at": 0}
_stats_cache: Dict[str, Any] = {}
_stats_cache_lock = threading.Lock()


def get_redis() -> None:
    """Redis disabled: always return None (use in-process cache)."""
    return None


def cache_get(key: str) -> Any:
    item = _cache.get(key)
    if not item:
        return None
    expires_at, data = item
    if monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return data


def cache_set(key: str, data: Any, ttl_seconds: int) -> None:
    _cache[key] = (monotonic() + ttl_seconds, data)


def _load_players_cache(min_shot_count: int = 50, limit: int = 500) -> None:
    """Prefetch players once to serve fast, local filtering."""
    supabase = get_supabase()
    try:
        result = supabase.rpc(
            "get_players_with_stats",
            {
                "search_term": "",
                "min_shot_count": min_shot_count,
                "result_limit": limit,
            },
        ).execute()
        if result.data:
            _players_cache["data"] = result.data
            _players_cache["fetched_at"] = time()
    except Exception as e:
        print(f"Prefetch players cache failed: {e}")


def _compute_stats_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute player stats from a list of shot rows (Python fallback)."""
    if not rows:
        return {}

    total_shots = len(rows)
    made_shots = sum(1 for r in rows if r.get("shot_made_flag"))
    distances = []
    shot_types: Dict[str, Dict[str, Any]] = {}
    seasons: Dict[int, Dict[str, Any]] = {}
    zones: Dict[str, Dict[str, Any]] = {}
    actions: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        dist = r.get("shot_distance")
        if dist is None and r.get("loc_x") is not None and r.get("loc_y") is not None:
            dist = sqrt(r["loc_x"] ** 2 + r["loc_y"] ** 2)
        if dist is not None:
            distances.append(dist)

        stype = r.get("shot_type") or "Unknown"
        shot_types.setdefault(stype, {"attempts": 0, "made": 0})
        shot_types[stype]["attempts"] += 1
        shot_types[stype]["made"] += 1 if r.get("shot_made_flag") else 0

        year = r.get("year")
        if year is not None:
            seasons.setdefault(year, {"attempts": 0, "made": 0})
            seasons[year]["attempts"] += 1
            seasons[year]["made"] += 1 if r.get("shot_made_flag") else 0

        action = r.get("action_type") or "Other"
        actions.setdefault(action, {"attempts": 0, "made": 0})
        actions[action]["attempts"] += 1
        actions[action]["made"] += 1 if r.get("shot_made_flag") else 0

        # distance-based zones
        z_label = "3PT (22+ft)"
        if dist is not None:
            if dist <= 5:
                z_label = "Paint (0-5ft)"
            elif dist <= 10:
                z_label = "Short (5-10ft)"
            elif dist <= 15:
                z_label = "Mid (10-15ft)"
            elif dist <= 22:
                z_label = "Long 2 (15-22ft)"
        zones.setdefault(z_label, {"attempts": 0, "made": 0})
        zones[z_label]["attempts"] += 1
        zones[z_label]["made"] += 1 if r.get("shot_made_flag") else 0

    def to_list(d: Dict[Any, Any], sort_key=None, limit=None):
        items = []
        for k, v in d.items():
            attempts = v.get("attempts", 0)
            made = v.get("made", 0)
            fg = made / attempts if attempts else 0
            items.append({**({"year": k} if isinstance(k, int) else {"label": k}), "attempts": attempts, "made": made, "fg_pct": round(fg, 3)})
        if sort_key:
            items.sort(key=sort_key, reverse=True)
        if limit:
            items = items[:limit]
        return items

    avg_distance = sum(distances) / len(distances) if distances else None

    return {
        "player_name": rows[0].get("player_name"),
        "total_shots": total_shots,
        "made_shots": made_shots,
        "fg_pct": round(made_shots / total_shots, 3) if total_shots else 0,
        "avg_distance": round(avg_distance, 1) if avg_distance is not None else None,
        "shot_types": to_list(shot_types, sort_key=lambda x: x["attempts"]),
        "seasons": to_list(seasons, sort_key=lambda x: x["year"]),
        "zones": to_list(zones, sort_key=lambda x: x["attempts"]),
        "actions": to_list(actions, sort_key=lambda x: x["attempts"], limit=10),
    }


def _warm_stats_cache() -> None:
    """Fetch all player stats once and save to disk + memory for fast reads."""
    os.makedirs("data", exist_ok=True)
    supabase = get_supabase()
    try:
        # Get list of all players with minimal filter
        roster = supabase.rpc(
            "get_players_with_stats",
            {
                "search_term": "",
                "min_shot_count": 1,
                "result_limit": 2000,  # avoid long scans/timeouts
            },
        ).execute()
        players = [p["name"] for p in roster.data or [] if p.get("name")]
    except Exception as e:
        print(f"Stats cache warmup failed to load roster: {e}")
        return

    cache_out: Dict[str, Any] = {}
    for name in players:
        try:
            result = supabase.rpc(
                "get_player_stats",
                {
                    "p_player_name": name,
                    "p_years": None,
                },
            ).execute()
            if result.data:
                cache_out[name] = result.data
        except Exception as e:
            print(f"Stats cache warmup failed for {name}: {e}")

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_out, f)
    except Exception as e:
        print(f"Failed to write stats cache file: {e}")

    with _stats_cache_lock:
        _stats_cache.clear()
        _stats_cache.update(cache_out)


# Health check
@app.get("/")
def health():
    return {"status": "ok", "message": "NBA Shot Predictor API"}


# Prediction endpoints
@app.post("/api/predict_shot")
def predict_shot(req: ShotRequest):
    """Predict probability of making a shot."""
    _warm_model()
    
    shot_dict = {
        "LOC_X": req.LOC_X,
        "LOC_Y": req.LOC_Y,
        "SHOT_DISTANCE": req.SHOT_DISTANCE or ((req.LOC_X**2 + req.LOC_Y**2) ** 0.5),
        "YEAR": req.YEAR,
        "SHOT_TYPE": req.SHOT_TYPE,
        "ACTION_TYPE": req.ACTION_TYPE,
    }
    
    prob = predict_single(shot_dict)
    return {"probability_make": round(float(prob), 3)}


# Player endpoints
@app.get("/api/players")
def get_players(
    search: str = Query("", description="Search term for player name"),
    min_shots: int = Query(100, description="Minimum number of shots"),
    limit: int = Query(100, description="Maximum results"),
):
    """Get list of players with shot statistics."""
    supabase = get_supabase()
    cache_key = f"players|{search}|{min_shots}|{limit}"
    
    cached = cache_get(cache_key)
    if cached is not None:
        return {"players": cached}

    # Try in-memory cached roster first to avoid timeouts on frequent searches
    now = time()
    if not _players_cache["data"] or now - _players_cache["fetched_at"] > 600:
        _load_players_cache(min_shot_count=10, limit=6000)
    if _players_cache["data"]:
        filtered = [
            p for p in _players_cache["data"]
            if p.get("total_shots", 0) >= min_shots
            and (search.strip() == "" or search.lower() in p.get("name", "").lower())
        ]
        filtered = sorted(filtered, key=lambda p: p.get("total_shots", 0), reverse=True)[:limit]
        cache_set(cache_key, filtered, ttl_seconds=120)
        return {"players": filtered}
    
    try:
        result = supabase.rpc(
            "get_players_with_stats",
            {
                "search_term": search,
                "min_shot_count": min_shots,
                "result_limit": limit,
            },
        ).execute()
        players = result.data or []
        cache_set(cache_key, players, ttl_seconds=300)  # 5 minutes
        return {"players": players}
    except Exception as e:
        print(f"Error fetching players: {e}")
        # Fallback: lightweight client-side aggregation on a capped sample
        try:
            sample_limit = 5000
            query = (
                supabase.table("shots")
                .select("player_name, shot_made_flag")
                .limit(sample_limit)
            )
            if search:
                query = query.ilike("player_name", f"%{search}%")
            sample = query.execute()
            rows = sample.data or []
            # Aggregate locally
            counts: dict[str, dict[str, float]] = {}
            for row in rows:
                name = row["player_name"]
                if name not in counts:
                    counts[name] = {"attempts": 0, "made": 0}
                counts[name]["attempts"] += 1
                counts[name]["made"] += float(row["shot_made_flag"] or 0)
            players = []
            for name, agg in counts.items():
                if agg["attempts"] >= min_shots:
                    fg = agg["made"] / agg["attempts"] if agg["attempts"] else 0
                    players.append(
                        {
                            "name": name,
                            "total_shots": int(agg["attempts"]),
                            "fg_pct": round(fg, 3),
                        }
                    )
            players = sorted(players, key=lambda p: p["total_shots"], reverse=True)[:limit]
            return {"players": players}
        except Exception as e2:
            print(f"Fallback player fetch failed: {e2}")
            return {"players": []}


@app.get("/api/years")
def get_years():
    """Get all available years in the dataset."""
    supabase = get_supabase()
    cache_key = "years"

    cached = cache_get(cache_key)
    if cached is not None:
        return {"years": cached}
    
    try:
        result = supabase.rpc("get_available_years").execute()
        years = [r["year"] for r in result.data] if result.data else []
        cache_set(cache_key, years, ttl_seconds=3600)  # 1 hour
        return {"years": sorted(years)}
    except Exception as e:
        print(f"Error fetching years: {e}")
        return {"years": []}


@app.get("/api/player/{player_name}")
def get_player(
    player_name: str,
    years: Optional[str] = Query(None, description="Comma-separated years"),
):
    """Get detailed statistics for a player."""
    supabase = get_supabase()
    
    years_list = [int(y) for y in years.split(",")] if years else None
    cache_key = f"player|{player_name}|{','.join(map(str, years_list)) if years_list else 'all'}"

    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    # Use precomputed all-years cache if no year filter
    if years_list is None:
        with _stats_cache_lock:
            cached_stats = _stats_cache.get(player_name)
        if not cached_stats and os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cached_stats = data.get(player_name)
                if cached_stats:
                    with _stats_cache_lock:
                        _stats_cache.update(data)
            except Exception as e:
                print(f"Failed to read stats cache file: {e}")
        if cached_stats:
            cache_set(cache_key, cached_stats, ttl_seconds=600)
            return cached_stats
    
    try:
        result = supabase.rpc("get_player_stats", {
            "p_player_name": player_name,
            "p_years": years_list
        }).execute()
        
        if result.data:
            cache_set(cache_key, result.data, ttl_seconds=300)
            return result.data
        else:
            raise HTTPException(status_code=404, detail=f"Player '{player_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching player stats via RPC, falling back: {e}")
        # Fallback: page through shots and aggregate locally (capped)
        try:
            page_size = 2000
            capped_limit = 60000
            collected = []
            offset = 0
            while len(collected) < capped_limit:
                q = supabase.table("shots").select(
                    "player_name, loc_x, loc_y, shot_made_flag, shot_distance, shot_type, action_type, year"
                ).eq("player_name", player_name)
                if years_list:
                    q = q.in_("year", years_list)
                q = q.range(offset, offset + page_size - 1)
                res = q.execute()
                rows = res.data or []
                collected.extend(rows)
                if len(rows) < page_size:
                    break
                offset += page_size
            stats = _compute_stats_from_rows(collected)
            if not stats:
                raise HTTPException(status_code=404, detail=f"Player '{player_name}' not found")
            cache_set(cache_key, stats, ttl_seconds=300)
            return stats
        except HTTPException:
            raise
        except Exception as e2:
            print(f"Fallback stats aggregation failed: {e2}")
            raise HTTPException(status_code=500, detail="Unable to load player stats right now")


@app.get("/api/player/{player_name}/shots")
def get_player_shots(
    player_name: str,
    years: Optional[str] = Query(None, description="Comma-separated years"),
    limit: int = Query(50000, description="Maximum shots to return"),
):
    """Get shot data for a player."""
    supabase = get_supabase()
    
    cache_key = f"shots|{player_name}|{years or 'all'}|{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        page_size = 1000
        capped_limit = min(limit, 50000)
        collected = []
        offset = 0

        years_list = [int(y) for y in years.split(",")] if years else None

        while len(collected) < capped_limit:
            q = supabase.table("shots").select(
                "loc_x, loc_y, shot_made_flag, shot_distance, shot_type, action_type, year"
            ).eq("player_name", player_name)

            if years_list:
                q = q.in_("year", years_list)

            q = q.order("year", desc=False).order("id", desc=False) if "id" in ["id"] else q.order("year", desc=False)
            q = q.range(offset, offset + page_size - 1)
            result = q.execute()

            rows = result.data or []
            for row in rows:
                collected.append({
                    "LOC_X": row["loc_x"],
                    "LOC_Y": row["loc_y"],
                    "SHOT_MADE_FLAG": row["shot_made_flag"],
                    "SHOT_DISTANCE": row["shot_distance"],
                    "SHOT_TYPE": row["shot_type"],
                    "ACTION_TYPE": row["action_type"],
                    "YEAR": row["year"],
                })
                if len(collected) >= capped_limit:
                    break

            if len(rows) < page_size:
                break
            offset += page_size
        
        payload = {"shots": collected, "total": len(collected)}
        cache_set(cache_key, payload, ttl_seconds=600)  # keep longer to reduce repeat hits
        return payload
    except Exception as e:
        print(f"Error fetching shots: {e}")
        return {"shots": [], "total": 0}


@app.post("/api/player/shots/page")
def get_player_shots_page(req: ShotsPageRequest):
    """Paged shots for a player to reduce payload size."""
    supabase = get_supabase()
    page = max(1, req.page)
    page_size = max(100, min(req.page_size, 5000))
    offset = (page - 1) * page_size
    
    years_list = req.years
    cache_key = f"shots_page|{req.player_name}|{','.join(map(str, years_list)) if years_list else 'all'}|{page}|{page_size}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        q = supabase.table("shots").select(
            "loc_x, loc_y, shot_made_flag, shot_distance, shot_type, action_type, year"
        ).eq("player_name", req.player_name)
        if years_list:
            q = q.in_("year", years_list)
        q = q.order("year", desc=False).range(offset, offset + page_size - 1)
        result = q.execute()
        rows = result.data or []
        shots = [{
            "LOC_X": row["loc_x"],
            "LOC_Y": row["loc_y"],
            "SHOT_MADE_FLAG": row["shot_made_flag"],
            "SHOT_DISTANCE": row["shot_distance"],
            "SHOT_TYPE": row["shot_type"],
            "ACTION_TYPE": row["action_type"],
            "YEAR": row["year"],
        } for row in rows]
        payload = {"shots": shots, "page": page, "page_size": page_size, "count": len(shots)}
        cache_set(cache_key, payload, ttl_seconds=600)
        return payload
    except Exception as e:
        print(f"Error fetching paged shots: {e}")
        return {"shots": [], "page": page, "page_size": page_size, "count": 0}


@app.post("/api/player/shots/bins")
def get_player_shots_binned(req: ShotsBinsRequest):
    """Return binned shot counts/makes to speed up heatmaps."""
    supabase = get_supabase()
    years_list = req.years
    cache_key = f"shots_bins|{req.player_name}|{','.join(map(str, years_list)) if years_list else 'all'}|{req.x_bins}|{req.y_bins}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        q = supabase.table("shots").select(
            "loc_x, loc_y, shot_made_flag"
        ).eq("player_name", req.player_name)
        if years_list:
            q = q.in_("year", years_list)
        q = q.limit(60000)
        result = q.execute()
        rows = result.data or []
        if not rows:
            return {"bins": []}
        
        xs = [r["loc_x"] for r in rows]
        ys = [r["loc_y"] for r in rows]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        x_step = (max_x - min_x) / max(req.x_bins, 1)
        y_step = (max_y - min_y) / max(req.y_bins, 1)
        bins: dict[tuple[int,int], dict[str,int]] = {}
        for r in rows:
            bx = int((r["loc_x"] - min_x) / x_step) if x_step else 0
            by = int((r["loc_y"] - min_y) / y_step) if y_step else 0
            key = (bx, by)
            if key not in bins:
                bins[key] = {"attempts": 0, "made": 0}
            bins[key]["attempts"] += 1
            bins[key]["made"] += int(r["shot_made_flag"] or 0)
        out = []
        for (bx, by), agg in bins.items():
            out.append({
                "x_bin": bx,
                "y_bin": by,
                "attempts": agg["attempts"],
                "made": agg["made"],
                "fg_pct": agg["made"] / agg["attempts"] if agg["attempts"] else 0,
            })
        payload = {
            "bins": out,
            "x_bins": req.x_bins,
            "y_bins": req.y_bins,
            "x_range": [min_x, max_x],
            "y_range": [min_y, max_y],
        }
        cache_set(cache_key, payload, ttl_seconds=900)
        return payload
    except Exception as e:
        print(f"Error fetching binned shots: {e}")
        return {"bins": []}


@app.post("/api/compare")
def compare_players(req: PlayerCompareRequest):
    """Compare two players' statistics."""
    supabase = get_supabase()
    
    cache_key = f"compare|{req.player1}|{req.player2}|{','.join(map(str, req.years)) if req.years else 'all'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        # Get stats for both players
        result1 = supabase.rpc("get_player_stats", {
            "p_player_name": req.player1,
            "p_years": req.years
        }).execute()
        
        result2 = supabase.rpc("get_player_stats", {
            "p_player_name": req.player2,
            "p_years": req.years
        }).execute()
        
        if not result1.data:
            raise HTTPException(status_code=404, detail=f"Player '{req.player1}' not found")
        if not result2.data:
            raise HTTPException(status_code=404, detail=f"Player '{req.player2}' not found")
        
        payload = {
            "player1": result1.data,
            "player2": result2.data,
        }
        cache_set(cache_key, payload, ttl_seconds=300)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error comparing players: {e}")
        raise HTTPException(status_code=500, detail=str(e))
