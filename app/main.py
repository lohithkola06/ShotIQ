"""
NBA Shot Predictor API - Using Supabase for data storage.
"""
import os
from functools import lru_cache
from typing import List, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

from src.inference import load_model, predict_single

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pabegzmewqavkqndmclg.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBhYmVnem1ld3FhdmtxbmRtY2xnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NjA3NTUsImV4cCI6MjA4MjQzNjc1NX0.uzlx6XpH5JkJIuO0uWfqeAD6woa1gI9fNlVrk0AyXU4")

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
    
    try:
        result = supabase.rpc("get_players_with_stats", {
            "search_term": search,
            "min_shot_count": min_shots,
            "result_limit": limit
        }).execute()
        
        return {"players": result.data or []}
    except Exception as e:
        print(f"Error fetching players: {e}")
        return {"players": []}


@app.get("/api/years")
def get_years():
    """Get all available years in the dataset."""
    supabase = get_supabase()
    
    try:
        result = supabase.rpc("get_available_years").execute()
        years = [r["year"] for r in result.data] if result.data else []
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
    
    try:
        result = supabase.rpc("get_player_stats", {
            "p_player_name": player_name,
            "p_years": years_list
        }).execute()
        
        if result.data:
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
    limit: int = Query(2500, description="Maximum shots to return"),
):
    """Get shot data for a player."""
    supabase = get_supabase()
    
    try:
        query = supabase.table("shots").select(
            "loc_x, loc_y, shot_made_flag, shot_distance, shot_type, action_type, year"
        ).eq("player_name", player_name)
        
        if years:
            years_list = [int(y) for y in years.split(",")]
            query = query.in_("year", years_list)
        
        query = query.limit(limit)
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
        
        return {"shots": shots, "total": len(shots)}
    except Exception as e:
        print(f"Error fetching shots: {e}")
        return {"shots": [], "total": 0}


@app.post("/api/compare")
def compare_players(req: PlayerCompareRequest):
    """Compare two players' statistics."""
    supabase = get_supabase()
    
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
        
        return {
            "player1": result1.data,
            "player2": result2.data,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error comparing players: {e}")
        raise HTTPException(status_code=500, detail=str(e))
