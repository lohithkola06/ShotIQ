from functools import lru_cache
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from src.inference import load_model, predict_grid, predict_single


app = FastAPI(title="NBA Shot Make Predictor API")


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


@lru_cache(maxsize=1)
def _warm_model():
    return load_model()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/predict_shot")
def api_predict_shot(req: ShotRequest):
    _warm_model()
    prob = predict_single(req.dict())
    return {"probability_make": prob}


@app.post("/api/predict_grid")
def api_predict_grid(req: GridRequest):
    _warm_model()
    import numpy as np

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

