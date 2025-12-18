import glob
import os
import re
from typing import Iterable, List, Optional, Sequence

import pandas as pd


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DEFAULT_YEARS: List[int] = [2020, 2021, 2022, 2023, 2024]
YEAR_PATTERN = re.compile(r"NBA_(\d{4})_Shots\.csv$", re.IGNORECASE)


def year_to_path(year: int, data_dir: str = DATA_DIR) -> str:
    """
    Map a year like 2004 to 'data/NBA_2004_Shots.csv'
    """
    filename = f"NBA_{int(year)}_Shots.csv"
    return os.path.join(data_dir, filename)


def list_available_years(data_dir: str = DATA_DIR) -> List[int]:
    """
    Scan the data directory for files that look like NBA_YYYY_Shots.csv.
    """
    years = []
    for path in glob.glob(os.path.join(data_dir, "NBA_*_Shots.csv")):
        match = YEAR_PATTERN.search(os.path.basename(path))
        if match:
            years.append(int(match.group(1)))
    return sorted(set(years))


def _resolve_years(years: Optional[Sequence[int] | str], data_dir: str) -> List[int]:
    """
    Normalize the `years` argument to a validated list of ints.
    """
    if years is None:
        years_list: List[int] = DEFAULT_YEARS
    elif isinstance(years, str) and years.lower() in {"all", "available"}:
        years_list = list_available_years(data_dir)
    else:
        years_list = sorted({int(y) for y in years})

    if not years_list:
        raise ValueError("No seasons requested. Provide `years` or store data files.")

    missing_paths = [
        year_to_path(y, data_dir=data_dir)
        for y in years_list
        if not os.path.exists(year_to_path(y, data_dir=data_dir))
    ]
    if missing_paths:
        raise FileNotFoundError(
            "Missing data files for seasons: "
            + ", ".join(os.path.basename(p) for p in missing_paths)
        )
    return years_list


def load_raw_shots(
    years: Optional[Sequence[int] | str] = None,
    n_rows: Optional[int] = None,
    data_dir: str = DATA_DIR,
) -> pd.DataFrame:
    """
    Load and concatenate one or more yearly shot files.

    years:
        - None -> uses DEFAULT_YEARS
        - "all"/"available" -> load every NBA_YYYY_Shots.csv in data_dir
        - iterable of years -> load those seasons
    n_rows:
        If set, read only first n_rows *per file* (for quick testing).
    """
    years_to_load = _resolve_years(years, data_dir=data_dir)

    dfs = []
    for y in years_to_load:
        path = year_to_path(y, data_dir=data_dir)
        print(f"Loading {path} ...")
        df_y = pd.read_csv(path, nrows=n_rows)
        df_y["YEAR"] = y  # ensure year present for downstream filtering
        dfs.append(df_y)

    df = pd.concat(dfs, ignore_index=True)
    return df


def _pick_column(cols: Iterable[str], candidates: Sequence[str]) -> Optional[str]:
    """
    Return the first column from `candidates` that exists in `cols`.
    """
    col_set = set(cols)
    for cand in candidates:
        if cand in col_set:
            return cand
    return None


def clean_shots(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the Kaggle-style NBA shots dataset into
    a consistent schema across seasons while preserving every source column.

    The returned frame guarantees the canonical columns
    (TEAM_NAME, PLAYER_NAME, LOC_X, LOC_Y, SHOT_MADE_FLAG, SHOT_DISTANCE,
    SHOT_TYPE, ACTION_TYPE, YEAR) appear first, followed by all other
    original fields so downstream tasks can access the full data types.
    """
    df = df.copy()
    df.columns = [c.strip().upper() for c in df.columns]

    col_team = _pick_column(df.columns, ["TEAM_NAME", "TEAM"])
    col_player = _pick_column(df.columns, ["PLAYER_NAME", "PLAYER"])
    col_loc_x = _pick_column(df.columns, ["LOC_X", "X_LOC", "SHOT_X"])
    col_loc_y = _pick_column(df.columns, ["LOC_Y", "Y_LOC", "SHOT_Y"])
    col_result = _pick_column(
        df.columns, ["SHOT_MADE_FLAG", "SHOT_RESULT", "SHOT_OUTCOME", "EVENT_TYPE"]
    )
    col_distance = _pick_column(df.columns, ["SHOT_DISTANCE", "SHOT_DIST", "DISTANCE"])
    col_shot_type = _pick_column(df.columns, ["SHOT_TYPE", "SHOT_CATEGORY"])
    col_action_type = _pick_column(df.columns, ["ACTION_TYPE", "ACTION_CATEGORY"])
    col_year = _pick_column(df.columns, ["YEAR", "SEASON"])

    required = [col_team, col_player, col_loc_x, col_loc_y, col_result, col_year]
    if any(c is None for c in required):
        raise ValueError(
            "Missing required columns; found "
            f"{df.columns.tolist()}. Check dataset headers."
        )

    # numeric conversions
    for coord_col in [col_loc_x, col_loc_y]:
        df[coord_col] = pd.to_numeric(df[coord_col], errors="coerce")
    if col_distance:
        df[col_distance] = pd.to_numeric(df[col_distance], errors="coerce")

    # drop rows with missing coordinates or result
    df = df.dropna(subset=[col_loc_x, col_loc_y, col_result])

    # Normalize coordinate scale:
    # Some seasons come in ~1/10th scale (x up to ~2.5, y up to ~11).
    # If detected, scale up by 10 to match the standard feet-like range.
    max_abs = float(max(df[col_loc_x].abs().max(), df[col_loc_y].abs().max()))
    if max_abs < 30:
        df[col_loc_x] = df[col_loc_x] * 10
        df[col_loc_y] = df[col_loc_y] * 10

    # normalize made/miss to 1/0
    if df[col_result].dtype.kind in {"i", "u", "b"}:
        df[col_result] = df[col_result].astype(int).clip(0, 1)
    else:
        result_map = {
            "made": 1,
            "make": 1,
            "made shot": 1,
            "made_shot": 1,
            "miss": 0,
            "missed": 0,
            "missed shot": 0,
            "missed_shot": 0,
        }
        df[col_result] = (
            df[col_result]
            .astype(str)
            .str.lower()
            .str.strip()
            .map(result_map)
        )
    df = df.dropna(subset=[col_result])
    df[col_result] = df[col_result].astype(int)

    rename_map = {
        col_team: "TEAM_NAME",
        col_player: "PLAYER_NAME",
        col_loc_x: "LOC_X",
        col_loc_y: "LOC_Y",
        col_result: "SHOT_MADE_FLAG",
        col_year: "YEAR",
    }
    if col_distance:
        rename_map[col_distance] = "SHOT_DISTANCE"
    if col_shot_type:
        rename_map[col_shot_type] = "SHOT_TYPE"
    if col_action_type:
        rename_map[col_action_type] = "ACTION_TYPE"

    df = df.rename(columns=rename_map)

    # ensure canonical shot distance exists even if original column missing
    if "SHOT_DISTANCE" not in df.columns:
        df["SHOT_DISTANCE"] = (df["LOC_X"] ** 2 + df["LOC_Y"] ** 2) ** 0.5

    # fill optional text columns
    if "SHOT_TYPE" not in df.columns:
        df["SHOT_TYPE"] = "Unknown"
    df["ACTION_TYPE"] = df.get("ACTION_TYPE", "Unknown").fillna("Unknown")

    # clean up types
    df["TEAM_NAME"] = df["TEAM_NAME"].astype(str).str.strip()
    df["PLAYER_NAME"] = df["PLAYER_NAME"].astype(str).str.strip()
    df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce").astype(int)

    canonical_order = [
        "TEAM_NAME",
        "PLAYER_NAME",
        "LOC_X",
        "LOC_Y",
        "SHOT_MADE_FLAG",
        "SHOT_DISTANCE",
        "SHOT_TYPE",
        "ACTION_TYPE",
        "YEAR",
    ]
    canonical_order = [c for c in canonical_order if c in df.columns]
    extra_cols = [c for c in df.columns if c not in canonical_order]

    ordered_cols = canonical_order + extra_cols
    return df[ordered_cols].reset_index(drop=True)


def save_clean(df: pd.DataFrame, path: str = os.path.join(DATA_DIR, "nba_shots_clean.csv")) -> None:
    df.to_csv(path, index=False)


def load_clean(path: str = os.path.join(DATA_DIR, "nba_shots_clean.csv")) -> pd.DataFrame:
    return pd.read_csv(path)


def get_player_shots(
    df: pd.DataFrame,
    player_name: str,
    year: Optional[int] = None,
    years: Optional[Iterable[int]] = None,
    team: Optional[str] = None,
) -> pd.DataFrame:
    """
    Filter cleaned dataset for a specific player (and optional season[s]/team).
    """
    sub = df[df["PLAYER_NAME"] == player_name]
    if years is not None:
        years_set = {int(y) for y in years}
        sub = sub[sub["YEAR"].isin(years_set)]
    if year is not None:
        sub = sub[sub["YEAR"] == year]
    if team is not None:
        sub = sub[sub["TEAM_NAME"] == team]
    return sub.reset_index(drop=True)
