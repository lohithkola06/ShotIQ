"""
NBA Shot Predictor API - Using Supabase for data storage.
"""
import os
from functools import lru_cache
from time import monotonic
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


# Cached clients
@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Get Supabase client (cached)."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@lru_cache(maxsize=1)
def _warm_model():
    return load_model()

# Simple in-process cache for expensive reads (fallback when Redis unavailable)
# Structure: { key: (expires_at, data) }
_cache: Dict[str, Tuple[float, Any]] = {}


@lru_cache(maxsize=1)
def get_redis() -> Optional["Redis"]:
    """Return Redis client if configured and library present."""
    if not REDIS_URL or Redis is None:
        return None
    try:
        client = Redis.from_url(REDIS_URL, decode_responses=True)
        # quick ping to validate
        client.ping()
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
        query = supabase.table("shots").select(
            "loc_x, loc_y, shot_made_flag, shot_distance, shot_type, action_type, year"
        ).eq("player_name", player_name)
        
        if years:
            years_list = [int(y) for y in years.split(",")]
            query = query.in_("year", years_list)
        
        # Supabase REST limit defaults can be low; use range to request full span
        capped_limit = min(limit, 50000)
        query = query.range(0, capped_limit - 1)
        result = query.execute()
        
        # Convert to uppercase keys for frontend compatibility
        shots = []
        for row in result.data or []:
            shots.append({
                "LOC_X": row["loc_x"],
                "LOC_Y": row["loc_y"],
                "SHOT_MADE_FLAG": row["shot_made_flag"],
                "SHOT_DISTANCE": row["shot_distance"],
                "SHOT_TYPE": row["shot_type"],
                "ACTION_TYPE": row["action_type"],
                "YEAR": row["year"],
            })
        
        payload = {"shots": shots, "total": len(shots)}
        cache_set(cache_key, payload, ttl_seconds=180)  # shorter TTL for larger payload
        return payload
    except Exception as e:
        print(f"Error fetching shots: {e}")
        return {"shots": [], "total": 0}


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
