import math
import os
from functools import lru_cache
from typing import Iterable, Optional, Sequence

import joblib
import numpy as np
import pandas as pd


DEFAULT_MODEL_PATH = os.path.join("models", "shot_model_xgb.pkl")


def _ensure_dataframe(data: pd.DataFrame | dict | Sequence[dict]) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, dict):
        return pd.DataFrame([data])
    return pd.DataFrame(list(data))


def _compute_distance(df: pd.DataFrame) -> pd.Series:
    return np.sqrt(df["LOC_X"] ** 2 + df["LOC_Y"] ** 2)


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Required columns
    required_numeric = ["LOC_X", "LOC_Y", "YEAR"]
    required_categorical = ["SHOT_TYPE", "ACTION_TYPE"]

    # Fill defaults if missing
    for col in required_numeric:
        if col not in df:
            if col == "YEAR":
                df[col] = 2024
            else:
                raise ValueError(f"Missing required numeric column: {col}")

    for col in required_categorical:
        if col not in df:
            if col == "SHOT_TYPE":
                df[col] = "2PT Field Goal"
            elif col == "ACTION_TYPE":
                df[col] = "Jump Shot"

    # Shot distance
    if "SHOT_DISTANCE" not in df:
        df["SHOT_DISTANCE"] = _compute_distance(df)
    else:
        df["SHOT_DISTANCE"] = pd.to_numeric(df["SHOT_DISTANCE"], errors="coerce")
        # If NaN after coercion, recompute
        mask = df["SHOT_DISTANCE"].isna()
        if mask.any():
            df.loc[mask, "SHOT_DISTANCE"] = _compute_distance(df[mask])

    # Cast types
    df["LOC_X"] = pd.to_numeric(df["LOC_X"], errors="coerce")
    df["LOC_Y"] = pd.to_numeric(df["LOC_Y"], errors="coerce")
    df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce").astype(int)
    df["SHOT_TYPE"] = df["SHOT_TYPE"].astype(str)
    df["ACTION_TYPE"] = df["ACTION_TYPE"].astype(str)

    return df[
        ["LOC_X", "LOC_Y", "SHOT_DISTANCE", "YEAR", "SHOT_TYPE", "ACTION_TYPE"]
    ]


@lru_cache(maxsize=2)
def load_model(model_path: str = DEFAULT_MODEL_PATH):
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model file not found at {model_path}. Train and save the model first."
        )
    return joblib.load(model_path)


def predict_proba(
    data: pd.DataFrame | dict | Sequence[dict],
    model_path: str = DEFAULT_MODEL_PATH,
) -> np.ndarray:
    """
    Predict shot-make probabilities for one or many shots.
    data: DataFrame or mapping(s) with keys LOC_X, LOC_Y, SHOT_TYPE, ACTION_TYPE, YEAR (optional SHOT_DISTANCE)
    Returns: numpy array of probabilities (P(make))
    """
    df = _ensure_dataframe(data)
    df = _prepare_features(df)
    model = load_model(model_path)
    probs = model.predict_proba(df)[:, 1]
    return probs


def predict_single(
    shot: dict,
    model_path: str = DEFAULT_MODEL_PATH,
) -> float:
    return float(predict_proba(shot, model_path=model_path)[0])


def predict_grid(
    xs: Iterable[float],
    ys: Iterable[float],
    year: int = 2024,
    shot_type: str = "3PT Field Goal",
    action_type: str = "Jump Shot",
    model_path: str = DEFAULT_MODEL_PATH,
) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Predict make probabilities on a grid of x/y points.
    Returns (grid_df, probs) where probs aligns with grid_df rows.
    """
    grid = []
    for x in xs:
        for y in ys:
            grid.append(
                {
                    "LOC_X": x,
                    "LOC_Y": y,
                    "SHOT_DISTANCE": math.sqrt(x * x + y * y),
                    "YEAR": year,
                    "SHOT_TYPE": shot_type,
                    "ACTION_TYPE": action_type,
                }
            )
    grid_df = pd.DataFrame(grid)
    probs = predict_proba(grid_df, model_path=model_path)
    return grid_df, probs

