from functools import lru_cache
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.inference import load_model, predict_grid, predict_single


app = FastAPI(title="NBA Shot Make Predictor API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ShotRequest(BaseModel):
    LOC_X: float
    LOC_Y: float
    SHOT_DISTANCE: Optional[float] = None
    YEAR: int = 2024
    SHOT_TYPE: str = "3PT Field Goal"
    ACTION_TYPE: str = "Jump Shot"


class GridRequest(BaseModel):
    x_min: float = -30.0
    x_max: float = 30.0
    y_min: float = -10.0
    y_max: float = 80.0
    x_steps: int = 50
    y_steps: int = 50
    YEAR: int = 2024
    SHOT_TYPE: str = "3PT Field Goal"
    ACTION_TYPE: str = "Jump Shot"


class PlayerCompareRequest(BaseModel):
    player1: str
    player2: str
    years: Optional[List[int]] = None


@lru_cache(maxsize=1)
def _warm_model():
    return load_model()


@lru_cache(maxsize=1)
def _load_shots_data():
    """Load the cleaned shots data for player queries - optimized for memory."""
    from src.data_loader import load_clean, CLEAN_CSV_PATH, _ensure_clean_csv_exists
    
    # Only load columns we actually need
    NEEDED_COLUMNS = [
        "PLAYER_NAME", "TEAM_NAME", "LOC_X", "LOC_Y", 
        "SHOT_MADE_FLAG", "SHOT_DISTANCE", "SHOT_TYPE", "ACTION_TYPE", "YEAR"
    ]
    
    try:
        _ensure_clean_csv_exists()
        # Load only needed columns with optimized dtypes
        df = pd.read_csv(
            CLEAN_CSV_PATH,
            usecols=NEEDED_COLUMNS,
            dtype={
                "PLAYER_NAME": "category",
                "TEAM_NAME": "category",
                "SHOT_TYPE": "category",
                "ACTION_TYPE": "category",
                "LOC_X": "float32",
                "LOC_Y": "float32",
                "SHOT_DISTANCE": "float32",
                "SHOT_MADE_FLAG": "int8",
                "YEAR": "int16",
            }
        )
        print(f"Loaded {len(df):,} shots, memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
        return df
    except FileNotFoundError:
        print("Warning: No clean data file found. Player queries will be empty.")
        return pd.DataFrame()


def _get_player_stats(df: pd.DataFrame, player_name: str, years: Optional[List[int]] = None) -> dict:
    """Calculate statistics for a player."""
    player_df = df[df["PLAYER_NAME"] == player_name]
    if years:
        player_df = player_df[player_df["YEAR"].isin(years)]
    
    if player_df.empty:
        return None
    
    total_shots = len(player_df)
    made_shots = player_df["SHOT_MADE_FLAG"].sum()
    fg_pct = made_shots / total_shots if total_shots > 0 else 0
    
    # Shot type breakdown
    shot_types = player_df.groupby("SHOT_TYPE").agg({
        "SHOT_MADE_FLAG": ["count", "sum", "mean"]
    }).reset_index()
    shot_types.columns = ["shot_type", "attempts", "made", "fg_pct"]
    
    # Season breakdown
    seasons = player_df.groupby("YEAR").agg({
        "SHOT_MADE_FLAG": ["count", "sum", "mean"]
    }).reset_index()
    seasons.columns = ["year", "attempts", "made", "fg_pct"]
    
    # Distance breakdown (zones)
    player_df = player_df.copy()
    player_df["zone"] = pd.cut(
        player_df["SHOT_DISTANCE"],
        bins=[0, 5, 10, 15, 22, 35],
        labels=["Paint (0-5ft)", "Short (5-10ft)", "Mid (10-15ft)", "Long 2 (15-22ft)", "3PT (22+ft)"]
    )
    zones = player_df.groupby("zone", observed=True).agg({
        "SHOT_MADE_FLAG": ["count", "sum", "mean"]
    }).reset_index()
    zones.columns = ["zone", "attempts", "made", "fg_pct"]
    
    # Action type breakdown (top 10)
    actions = player_df.groupby("ACTION_TYPE").agg({
        "SHOT_MADE_FLAG": ["count", "sum", "mean"]
    }).reset_index()
    actions.columns = ["action_type", "attempts", "made", "fg_pct"]
    actions = actions.nlargest(10, "attempts")
    
    return {
        "player_name": player_name,
        "total_shots": int(total_shots),
        "made_shots": int(made_shots),
        "fg_pct": round(fg_pct, 3),
        "avg_distance": round(player_df["SHOT_DISTANCE"].mean(), 1),
        "shot_types": shot_types.to_dict(orient="records"),
        "seasons": seasons.to_dict(orient="records"),
        "zones": zones.to_dict(orient="records"),
        "actions": actions.to_dict(orient="records"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/players")
def get_players(
    search: str = Query(default="", description="Search filter for player names"),
    min_shots: int = Query(default=100, description="Minimum shots to include player"),
    limit: int = Query(default=50, description="Maximum players to return")
):
    """Get list of players with optional search filter."""
    df = _load_shots_data()
    if df.empty:
        return {"players": []}
    
    # Aggregate shot counts
    player_stats = df.groupby("PLAYER_NAME").agg({
        "SHOT_MADE_FLAG": ["count", "mean"]
    }).reset_index()
    player_stats.columns = ["name", "total_shots", "fg_pct"]
    
    # Filter by minimum shots
    player_stats = player_stats[player_stats["total_shots"] >= min_shots]
    
    # Search filter
    if search:
        player_stats = player_stats[
            player_stats["name"].str.lower().str.contains(search.lower())
        ]
    
    # Sort by total shots and limit
    player_stats = player_stats.nlargest(limit, "total_shots")
    
    players = [
        {
            "name": row["name"],
            "total_shots": int(row["total_shots"]),
            "fg_pct": round(row["fg_pct"], 3)
        }
        for _, row in player_stats.iterrows()
    ]
    
    return {"players": players}


@app.get("/api/years")
def get_years():
    """Get list of available years."""
    df = _load_shots_data()
    if df.empty:
        return {"years": []}
    years = sorted(df["YEAR"].unique().tolist())
    return {"years": years}


@app.get("/api/player/{player_name}")
def get_player(player_name: str, years: Optional[str] = None):
    """Get detailed stats for a specific player."""
    df = _load_shots_data()
    if df.empty:
        return {"error": "No data available"}
    
    years_list = None
    if years:
        years_list = [int(y) for y in years.split(",")]
    
    stats = _get_player_stats(df, player_name, years_list)
    if stats is None:
        return {"error": f"Player '{player_name}' not found"}
    
    return stats


@app.get("/api/player/{player_name}/shots")
def get_player_shots(
    player_name: str,
    years: Optional[str] = None,
    limit: int = Query(default=5000, description="Max shots to return")
):
    """Get shot location data for visualization."""
    df = _load_shots_data()
    if df.empty:
        return {"shots": []}
    
    player_df = df[df["PLAYER_NAME"] == player_name]
    if years:
        years_list = [int(y) for y in years.split(",")]
        player_df = player_df[player_df["YEAR"].isin(years_list)]
    
    # Sample if too many shots
    if len(player_df) > limit:
        player_df = player_df.sample(n=limit, random_state=42)
    
    shots = player_df[["LOC_X", "LOC_Y", "SHOT_MADE_FLAG", "SHOT_DISTANCE", "SHOT_TYPE", "ACTION_TYPE", "YEAR"]].to_dict(orient="records")
    
    return {"shots": shots, "total": len(shots)}


@app.post("/api/compare")
def compare_players(req: PlayerCompareRequest):
    """Compare two players' stats."""
    df = _load_shots_data()
    if df.empty:
        return {"error": "No data available"}
    
    stats1 = _get_player_stats(df, req.player1, req.years)
    stats2 = _get_player_stats(df, req.player2, req.years)
    
    if stats1 is None:
        return {"error": f"Player '{req.player1}' not found"}
    if stats2 is None:
        return {"error": f"Player '{req.player2}' not found"}
    
    return {
        "player1": stats1,
        "player2": stats2
    }


@app.post("/api/predict_shot")
def api_predict_shot(req: ShotRequest):
    _warm_model()
    prob = predict_single(req.dict())
    return {"probability_make": prob}


@app.post("/api/predict_grid")
def api_predict_grid(req: GridRequest):
    _warm_model()
    xs = np.linspace(req.x_min, req.x_max, req.x_steps)
    ys = np.linspace(req.y_min, req.y_max, req.y_steps)
    grid_df, probs = predict_grid(
        xs,
        ys,
        year=req.YEAR,
        shot_type=req.SHOT_TYPE,
        action_type=req.ACTION_TYPE,
    )
    return {
        "grid": grid_df.to_dict(orient="records"),
        "probabilities": probs.tolist(),
        "shape": {"x": req.x_steps, "y": req.y_steps},
    }
