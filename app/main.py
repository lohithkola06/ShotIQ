"""
NBA Shot Predictor API - Using Supabase for data storage.
"""
import os
import json
from functools import lru_cache
from time import monotonic, time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
try:
    from redis import Redis
except ImportError:
    Redis = None  # type: ignore

from src.inference import load_model, predict_single

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pabegzmewqavkqndmclg.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBhYmVnem1ld3FhdmtxbmRtY2xnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NjA3NTUsImV4cCI6MjA4MjQzNjc1NX0.uzlx6XpH5JkJIuO0uWfqeAD6woa1gI9fNlVrk0AyXU4")
REDIS_URL = os.environ.get("REDIS_URL", "")

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
    # Opportunistic player roster prefetch (non-blocking if Redis is available)
    try:
        _load_players_cache(min_shot_count=10, limit=6000)
    except Exception as e:
        print(f"Player prefetch at startup failed: {e}")

# Simple in-process cache for expensive reads (fallback when Redis unavailable)
# Structure: { key: (expires_at, data) }
_cache: Dict[str, Tuple[float, Any]] = {}
_players_cache: Dict[str, Any] = {"data": None, "fetched_at": 0}


@lru_cache(maxsize=1)
def get_redis() -> Optional["Redis"]:
    """Return Redis client if configured and library present."""
    if not REDIS_URL or Redis is None:
        return None
    url = REDIS_URL
    # If the URL uses redis:// but the server expects TLS, allow upgrade to rediss://
    if url.startswith("redis://") and "redislabs.com" in url:
        url = url.replace("redis://", "rediss://", 1)
    try:
        client = Redis.from_url(url, decode_responses=True)
        client.ping()  # quick validation
        return client
    except Exception as e:
        print(f"Redis unavailable, falling back to in-process cache: {e}")
        return None


def cache_get(key: str) -> Any:
    redis_client = get_redis()
    if redis_client:
        try:
            val = redis_client.get(key)
            if val is not None:
                import json
                return json.loads(val)
        except Exception as e:
            print(f"Redis get failed for {key}: {e}")

    item = _cache.get(key)
    if not item:
        return None
    expires_at, data = item
    if monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return data


def cache_set(key: str, data: Any, ttl_seconds: int) -> None:
    redis_client = get_redis()
    if redis_client:
        try:
          import json
          redis_client.setex(key, ttl_seconds, json.dumps(data))
          return
        except Exception as e:
            print(f"Redis set failed for {key}: {e}")

    _cache[key] = (monotonic() + ttl_seconds, data)


def _load_players_cache(min_shot_count: int = 10, limit: int = 6000) -> None:
    """Prefetch players once to serve fast, local filtering."""
    supabase = get_supabase()
    redis_client = get_redis()
    cache_key = "players_prefetch_v1"

    # Try Redis first
    if redis_client:
        try:
            val = redis_client.get(cache_key)
            if val:
                players = json.loads(val)
                _players_cache["data"] = players
                _players_cache["fetched_at"] = time()
                return
        except Exception as e:
            print(f"Redis players prefetch read failed: {e}")

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
            if redis_client:
                try:
                    redis_client.setex(cache_key, 900, json.dumps(result.data))
                except Exception as e:
                    print(f"Redis players prefetch write failed: {e}")
    except Exception as e:
        print(f"Prefetch players cache failed: {e}")


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
        print(f"Error fetching player stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
