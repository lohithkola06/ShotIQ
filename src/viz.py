# src/viz.py

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from matplotlib import patches
from typing import Iterable, Optional, Tuple


def set_modern_style() -> None:
    """
    Apply a dark, modern style for all matplotlib/seaborn plots.
    Call once at the start of a notebook or app.
    """
    plt.style.use("dark_background")
    plt.rcParams.update(
        {
            "figure.facecolor": "#0b0c10",
            "axes.facecolor": "#0b0c10",
            "axes.edgecolor": "#c5c6c7",
            "axes.labelcolor": "#e6e6e6",
            "text.color": "#e6e6e6",
            "xtick.color": "#bfc2c7",
            "ytick.color": "#bfc2c7",
            "font.size": 11.5,
            "axes.titleweight": "bold",
            "axes.titlepad": 12,
        }
    )
    sns.set_palette("viridis")


def _maybe_sample(df: pd.DataFrame, max_rows: Optional[int]) -> pd.DataFrame:
    """
    Limit the number of plotted points to keep visuals responsive.
    """
    if max_rows is not None and len(df) > max_rows:
        return df.sample(max_rows, random_state=0)
    return df


VALID_UNITS = {"stats", "feet", "feet_long"}


def _infer_units(df: pd.DataFrame) -> str:
    """
    Infer coordinate units:
    - "stats" for NBA Stats style (~-250..250, y up to ~422)
    - "feet_long" for feet-range data that stretches beyond half-court (y up to ~120)
    - "feet" for normal half-court feet (-25..25, y up to ~50)
    """
    max_abs = float(
        max(
            df["LOC_X"].abs().max(),
            df["LOC_Y"].abs().max(),
        )
    )
    if max_abs > 150:
        return "stats"
    if max_abs > 60:
        return "feet_long"
    return "feet"


def _mirror_full_to_half_court(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mirror only when data clearly spans full court (y well above half-court range).
    """
    df_out = df.copy()
    max_y = df_out["LOC_Y"].max()
    if max_y > 150:  # likely stats-style full court
        df_out["LOC_Y"] = df_out["LOC_Y"].where(df_out["LOC_Y"] <= 0, df_out["LOC_Y"] * 0 - df_out["LOC_Y"])
    return df_out


def _prep_for_court(
    df: pd.DataFrame,
    units_preference: Optional[str] = None,
) -> Tuple[pd.DataFrame, str]:
    """
    Prepare dataframe for plotting on a half court:
    - Optionally mirror full-court y to half court
    - Infer units for correct court scaling
    """
    df_half = _mirror_full_to_half_court(df)

    max_abs = float(
        max(
            df_half["LOC_X"].abs().max(),
            df_half["LOC_Y"].abs().max(),
        )
    )
    if max_abs < 30:
        # Tiny ranges (e.g., 2020–2022): scale to feet and anchor rim to 0
        df_half = df_half.copy()
        rim_y = float(df_half["LOC_Y"].quantile(0.02))
        x_max = float(df_half["LOC_X"].abs().max()) or 1.0
        y_span = float((df_half["LOC_Y"] - rim_y).max()) or 1.0
        x_scale = 25.0 / x_max
        y_scale = 47.0 / y_span
        df_half["LOC_X"] = df_half["LOC_X"] * x_scale
        df_half["LOC_Y"] = (df_half["LOC_Y"] - rim_y) * y_scale
        units = "feet"
    else:
        units = (
            units_preference
            if units_preference in VALID_UNITS
            else _infer_units(df_half)
        )
        if units in {"feet", "feet_long"}:
            df_half = df_half.copy()
            rim_y = float(df_half["LOC_Y"].quantile(0.02))
            df_half["LOC_Y"] = df_half["LOC_Y"] - rim_y
        # stats: leave as-is

    return df_half, units


def _court_extents(units: str) -> Tuple[float, float, float, float]:
    if units == "stats":
        return (-250, 250, -47.5, 422.5)
    if units == "feet_long":
        return (-30, 30, -10, 80)
    return (-30, 30, -10, 55)


def _set_limits_with_padding(ax: plt.Axes, df: pd.DataFrame, units: str, pad_frac: float = 0.05) -> None:
    xmin, xmax, ymin, ymax = _court_extents(units)
    data_xmin, data_xmax = df["LOC_X"].min(), df["LOC_X"].max()
    data_ymin, data_ymax = df["LOC_Y"].min(), df["LOC_Y"].max()

    dx = max(1e-3, data_xmax - data_xmin)
    dy = max(1e-3, data_ymax - data_ymin)
    px = dx * pad_frac
    py = dy * pad_frac

    ax.set_xlim(max(xmin, data_xmin - px), min(xmax, data_xmax + px))
    ax.set_ylim(max(ymin, data_ymin - py), min(ymax, data_ymax + py))


def plot_shot_chart(
    df: pd.DataFrame,
    title: str = "Shot Chart",
    max_shots: Optional[int] = 4000,
    ax: Optional[plt.Axes] = None,
    show: bool = True,
) -> plt.Axes:
    """
    Simple scatter-based shot chart for a subset of shots.
    df must have columns: LOC_X, LOC_Y, SHOT_MADE_FLAG.
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")

    df_plot = _maybe_sample(df, max_shots)
    made = df_plot[df_plot["SHOT_MADE_FLAG"] == 1]
    missed = df_plot[df_plot["SHOT_MADE_FLAG"] == 0]

    created_ax = False
    if ax is None:
        created_ax = True
        _, ax = plt.subplots(figsize=(6, 5))

    ax.scatter(
        missed["LOC_X"],
        missed["LOC_Y"],
        s=6,
        alpha=0.25,
        label="Miss",
        color="#d62728",
    )
    ax.scatter(
        made["LOC_X"],
        made["LOC_Y"],
        s=6,
        alpha=0.25,
        label="Make",
        color="#2ca02c",
    )

    ax.set_title(title)
    ax.set_xlabel("LOC_X")
    ax.set_ylabel("LOC_Y")
    ax.legend()
    ax.set_aspect("equal", "box")
    if created_ax and show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_shot_kde(
    df: pd.DataFrame,
    title: str = "Shot Density Heatmap",
    thresh: float = 0.05,
    ax: Optional[plt.Axes] = None,
    show: bool = True,
) -> plt.Axes:
    """
    KDE-based heatmap of shot locations (ignores make/miss).
    df must have LOC_X, LOC_Y.
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")

    created_ax = False
    if ax is None:
        created_ax = True
        _, ax = plt.subplots(figsize=(6, 5))

    sns.kdeplot(
        x=df["LOC_X"],
        y=df["LOC_Y"],
        fill=True,
        thresh=thresh,
        levels=50,
        ax=ax,
        cmap="mako",
    )
    ax.set_title(title)
    ax.set_xlabel("LOC_X")
    ax.set_ylabel("LOC_Y")
    ax.set_aspect("equal", "box")
    if created_ax and show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_make_rate_heatmap(
    df: pd.DataFrame,
    bins: int = 30,
    title: str = "Make Rate Heatmap",
    ax: Optional[plt.Axes] = None,
    show: bool = True,
) -> plt.Axes:
    """
    Grid-based FG% heatmap:
    - Bin LOC_X / LOC_Y into a grid
    - Compute FG% in each cell
    df must have LOC_X, LOC_Y, SHOT_MADE_FLAG.
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")

    x = df["LOC_X"].values
    y = df["LOC_Y"].values
    made = df["SHOT_MADE_FLAG"].values

    x_bins = bins
    y_bins = bins

    counts, x_edges, y_edges = np.histogram2d(x, y, bins=[x_bins, y_bins])
    made_counts, _, _ = np.histogram2d(
        x, y, bins=[x_bins, y_bins], weights=made
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        make_rate = np.where(counts > 0, made_counts / counts, np.nan)

    created_ax = False
    if ax is None:
        created_ax = True
        _, ax = plt.subplots(figsize=(6, 5))

    im = ax.imshow(
        make_rate.T,
        origin="lower",
        extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
        aspect="equal",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
    )
    plt.colorbar(im, ax=ax, label="FG%")
    ax.set_title(title)
    ax.set_xlabel("LOC_X")
    ax.set_ylabel("LOC_Y")
    if created_ax and show:
        plt.tight_layout()
        plt.show()
    return ax


def draw_nba_half_court(
    ax: Optional[plt.Axes] = None,
    line_color: str = "#c5c6c7",
    lw: int = 2,
    units: str = "stats",
) -> plt.Axes:
    """
    Draw an NBA half court (NBA Stats coordinate system).
    x: -250..250, y: -47.5..422.5 (offensive half) in "stats" units.
    For "feet" units, scales to x: -25..25, y: -5..47.
    """
    if ax is None:
        ax = plt.gca()

    if units not in {"stats", "feet", "feet_long"}:
        units = "stats"

    scale = 1.0 if units == "stats" else 0.1  # stats units are roughly 10x feet

    hoop = patches.Circle((0, 0), radius=7.5 * scale, linewidth=lw, color=line_color, fill=False)
    backboard = patches.Rectangle((-30 * scale, -7.5 * scale), 60 * scale, -1 * scale, linewidth=lw, color=line_color)
    outer_box = patches.Rectangle((-80 * scale, -47.5 * scale), 160 * scale, 190 * scale, linewidth=lw, color=line_color, fill=False)
    inner_box = patches.Rectangle((-60 * scale, -47.5 * scale), 120 * scale, 190 * scale, linewidth=lw, color=line_color, fill=False)
    free_throw_circle = patches.Arc((0, 142.5 * scale), 120 * scale, 120 * scale, theta1=0, theta2=180, linewidth=lw, color=line_color)
    restricted = patches.Arc((0, 0), 80 * scale, 80 * scale, theta1=0, theta2=180, linewidth=lw, color=line_color)
    three_line_side_left = patches.Rectangle((-220 * scale, -47.5 * scale), 0, 140 * scale, linewidth=lw, color=line_color)
    three_line_side_right = patches.Rectangle((220 * scale, -47.5 * scale), 0, 140 * scale, linewidth=lw, color=line_color)
    three_arc = patches.Arc((0, 0), 475 * scale, 475 * scale, theta1=22, theta2=158, linewidth=lw, color=line_color)
    center_circle = patches.Arc((0, 422.5 * scale), 120 * scale, 120 * scale, theta1=180, theta2=360, linewidth=lw, color=line_color)

    for elem in [
        hoop,
        backboard,
        outer_box,
        inner_box,
        free_throw_circle,
        restricted,
        three_line_side_left,
        three_line_side_right,
        three_arc,
        center_circle,
    ]:
        ax.add_patch(elem)

    xmin, xmax, ymin, ymax = _court_extents(units)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", "box")
    ax.axis("off")
    return ax


def plot_player_views(
    df: pd.DataFrame,
    player_name: str,
    years: Optional[Iterable[int]] = None,
    bins: int = 32,
    max_shots: Optional[int] = 5000,
) -> None:
    """
    Convenience wrapper to render scatter, KDE, and FG% heatmap for one player.
    Pass `years` to restrict seasons; otherwise uses all seasons in df.
    """
    sub = df[df["PLAYER_NAME"] == player_name]
    if years is not None:
        years_set = {int(y) for y in years}
        sub = sub[sub["YEAR"].isin(years_set)]

    if sub.empty:
        raise ValueError(f"No shots found for {player_name} with current filters.")

    sub = _maybe_sample(sub, max_shots)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    plot_shot_chart(
        sub,
        title=f"{player_name} Shot Chart",
        max_shots=max_shots,
        ax=axes[0],
        show=False,
    )
    plot_shot_kde(
        sub,
        title=f"{player_name} Shot Density",
        ax=axes[1],
        show=False,
    )
    plot_make_rate_heatmap(
        sub,
        bins=bins,
        title=f"{player_name} FG% Heatmap",
        ax=axes[2],
        show=False,
    )
    plt.tight_layout()
    plt.show()


# -----------------------------
# Modern, dark-themed visuals
# -----------------------------


def plot_shot_chart_modern(
    df: pd.DataFrame,
    title: str = "Shot Chart (Modern)",
    units: str = "auto",
    max_points: Optional[int] = 8000,
) -> None:
    """
    Modern scatter shot chart on dark theme.
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")

    df_plot, units_resolved = _prep_for_court(
        df,
        units_preference=None if units == "auto" else units,
    )
    df_plot = _maybe_sample(df_plot, max_points)
    made = df_plot[df_plot["SHOT_MADE_FLAG"] == 1]
    missed = df_plot[df_plot["SHOT_MADE_FLAG"] == 0]

    fig, ax = plt.subplots(figsize=(7, 6))
    draw_nba_half_court(ax, units=units_resolved)

    miss_color = "#3a5fcd"
    make_color = "#12d8c4"
    ax.scatter(
        missed["LOC_X"],
        missed["LOC_Y"],
        s=8,
        alpha=0.25,
        color=miss_color,
        edgecolors="none",
        label="Miss",
    )
    ax.scatter(
        made["LOC_X"],
        made["LOC_Y"],
        s=9,
        alpha=0.5,
        color=make_color,
        edgecolors="none",
        label="Make",
    )

    ax.set_title(title)
    ax.legend(frameon=False, loc="upper right")
    _set_limits_with_padding(ax, df_plot, units_resolved, pad_frac=0.08)
    plt.tight_layout()
    plt.show()


def plot_hexbin_frequency(
    df: pd.DataFrame,
    gridsize: int = 30,
    title: str = "Shot Frequency (Hexbin)",
    units: str = "auto",
    max_points: Optional[int] = None,
) -> None:
    """
    Hexbin plot showing shot frequency.
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")

    df_plot, units_resolved = _prep_for_court(
        df,
        units_preference=None if units == "auto" else units,
    )
    if max_points is not None:
        df_plot = _maybe_sample(df_plot, max_points)

    fig, ax = plt.subplots(figsize=(7, 6))
    draw_nba_half_court(ax, units=units_resolved)

    hb = ax.hexbin(
        df_plot["LOC_X"],
        df_plot["LOC_Y"],
        gridsize=gridsize,
        cmap="viridis",
        mincnt=1,
        linewidths=0,
        alpha=0.9,
    )
    cbar = fig.colorbar(hb, ax=ax)
    cbar.set_label("Shot Attempts")
    ax.set_title(title)
    _set_limits_with_padding(ax, df_plot, units_resolved, pad_frac=0.08)
    plt.tight_layout()
    plt.show()


def plot_hexbin_fg_pct(
    df: pd.DataFrame,
    gridsize: int = 30,
    title: str = "FG% by Location (Hexbin)",
    units: str = "auto",
) -> None:
    """
    Hexbin map of FG% per location.
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")

    df_plot, units_resolved = _prep_for_court(
        df,
        units_preference=None if units == "auto" else units,
    )

    x = df_plot["LOC_X"].values
    y = df_plot["LOC_Y"].values
    made = df_plot["SHOT_MADE_FLAG"].values

    counts, x_edges, y_edges = np.histogram2d(x, y, bins=gridsize)
    made_counts, _, _ = np.histogram2d(x, y, bins=gridsize, weights=made)

    with np.errstate(divide="ignore", invalid="ignore"):
        fg_pct = np.where(counts > 0, made_counts / counts, np.nan)

    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])
    Xc, Yc = np.meshgrid(x_centers, y_centers)

    fig, ax = plt.subplots(figsize=(7, 6))
    draw_nba_half_court(ax, units=units_resolved)

    sc = ax.scatter(
        Xc.ravel(),
        Yc.ravel(),
        c=fg_pct.T.ravel(),
        cmap="plasma",
        s=180,
        marker="h",
        edgecolors="none",
    )
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("FG%")
    ax.set_title(title)
    plt.tight_layout()
    plt.show()


def plot_kde_heatmap_modern(
    df: pd.DataFrame,
    title: str = "Shot Density (KDE)",
    thresh: float = 0.1,
    levels: int = 60,
    units: str = "auto",
    cmap: str = "magma",
) -> None:
    """
    Smooth KDE heatmap on dark court background.
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")

    df_plot, units_resolved = _prep_for_court(
        df,
        units_preference=None if units == "auto" else units,
    )

    fig, ax = plt.subplots(figsize=(7, 6))
    draw_nba_half_court(ax, units=units_resolved)

    sns.kdeplot(
        x=df_plot["LOC_X"],
        y=df_plot["LOC_Y"],
        fill=True,
        cmap=cmap,
        thresh=thresh,
        levels=levels,
        alpha=0.85,
        ax=ax,
    )
    ax.set_title(title)
    _set_limits_with_padding(ax, df_plot, units_resolved, pad_frac=0.08)
    plt.tight_layout()
    plt.show()


def plot_fg_prob_heatmap_modern(
    df: pd.DataFrame,
    bins: int = 40,
    title: str = "FG% Heatmap",
    min_attempts: int = 1,
    units: str = "auto",
    cmap: str = "plasma_r",
) -> None:
    """
    FG% heatmap on a grid with dark court background.
    - Yellow/red = higher make probability
    - Blue/purple = low make probability
    - Cells with fewer than `min_attempts` are hidden (NaN)
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")

    df_plot, units_resolved = _prep_for_court(
        df,
        units_preference=None if units == "auto" else units,
    )

    x = df_plot["LOC_X"].values
    y = df_plot["LOC_Y"].values
    made = df_plot["SHOT_MADE_FLAG"].values

    counts, x_edges, y_edges = np.histogram2d(x, y, bins=bins)
    made_counts, _, _ = np.histogram2d(x, y, bins=bins, weights=made)

    with np.errstate(divide="ignore", invalid="ignore"):
        fg = np.where(counts >= min_attempts, made_counts / counts, np.nan)

    fig, ax = plt.subplots(figsize=(7, 6))
    draw_nba_half_court(ax, units=units_resolved)

    im = ax.imshow(
        fg.T,
        origin="lower",
        extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
        aspect="equal",
        cmap=cmap,  # purple/blue low -> yellow high
        vmin=0,
        vmax=1,
        alpha=0.9,
    )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("FG%")
    ax.set_title(title)
    _set_limits_with_padding(ax, df_plot, units_resolved, pad_frac=0.08)
    plt.tight_layout()
    plt.show()


def plot_fg_prob_kde_modern(
    df: pd.DataFrame,
    bins: int = 80,
    sigma: float = 1.2,
    title: str = "FG% Heatmap (Smoothed)",
    min_attempts: float = 0.5,
    units: str = "auto",
    cmap: str = "plasma_r",
) -> None:
    """
    Smoothed FG% surface:
    - Build a fine grid of attempts/makes
    - Apply Gaussian smoothing
    - Display FG% with purple/blue low -> yellow high
    """
    if df.empty:
        raise ValueError("No shots to plot (empty dataframe).")
    try:
        from scipy.ndimage import gaussian_filter
    except Exception as exc:  # pragma: no cover - scipy may be missing
        raise ImportError("scipy is required for KDE FG% heatmap") from exc

    df_plot, units_resolved = _prep_for_court(
        df,
        units_preference=None if units == "auto" else units,
    )

    x = df_plot["LOC_X"].values
    y = df_plot["LOC_Y"].values
    made = df_plot["SHOT_MADE_FLAG"].values

    counts, x_edges, y_edges = np.histogram2d(x, y, bins=bins)
    made_counts, _, _ = np.histogram2d(x, y, bins=bins, weights=made)

    counts_s = gaussian_filter(counts, sigma=sigma, mode="constant")
    makes_s = gaussian_filter(made_counts, sigma=sigma, mode="constant")

    with np.errstate(divide="ignore", invalid="ignore"):
        fg = np.where(counts_s >= min_attempts, makes_s / counts_s, np.nan)

    fig, ax = plt.subplots(figsize=(7, 6))
    draw_nba_half_court(ax, units=units_resolved)

    im = ax.imshow(
        fg.T,
        origin="lower",
        extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
        aspect="equal",
        cmap=cmap,
        vmin=0,
        vmax=1,
        alpha=0.9,
    )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("FG% (smoothed)")
    ax.set_title(title)
    _set_limits_with_padding(ax, df_plot, units_resolved, pad_frac=0.08)
    plt.tight_layout()
    plt.show()
