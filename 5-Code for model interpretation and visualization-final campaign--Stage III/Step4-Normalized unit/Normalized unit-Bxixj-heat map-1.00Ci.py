# -*- coding: utf-8 -*-
"""
Heatmap with log10 scaling (signed log10) for contribution coefficients.

Based on your original script:
- Still reads Ci_1.00_stats_scaled.csv (mean_Ci / std_Ci)
- Builds lower-triangle matrix and plots a diverging heatmap
- Now applies signed log10 to mean for color + annotation
- Converts std into log-domain std via first-order error propagation
"""

import csv
import pathlib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import Rectangle
from matplotlib.colors import TwoSlopeNorm, ListedColormap

# —— 全局字体设置为 Arial ——
plt.rcParams["font.family"] = "Arial"

# =========================
# log10 settings
# =========================
APPLY_LOG10 = True
LOG10_EPS = 1e-12  # avoids log10(0); adjust if needed

# =========================
# colorbar / colormap settings
# =========================
# COLORBAR_MODE:
#   - "auto":     use max(|value|) (original behavior)
#   - "fixed":    use VMIN_USER/VMAX_USER (or symmetric VMAX_USER if VMIN_USER is None)
#   - "quantile": use percentile of |value| (robust to outliers)
COLORBAR_MODE = "fixed"
VMIN_USER = -8.0      # e.g., -3.0  (signed log10 domain if APPLY_LOG10=True)
VMAX_USER = 8      # e.g.,  3.0  (signed log10 domain if APPLY_LOG10=True)
ABS_QUANTILE = 95     # used when COLORBAR_MODE == "quantile"

# Pastel (macaron-like) diverging colormap
USE_PASTEL_CMAP = True
BASE_CMAP = "RdBu_r"   # other options: "coolwarm", "PuOr", "PRGn", "BrBG"
PASTEL_BLEND = 0.45     # 0~1; higher = lighter/pastel

LN10 = np.log(10.0)


def signed_log10(x: np.ndarray, eps: float = LOG10_EPS) -> np.ndarray:
    """sign(x) * log10(|x| + eps)"""
    x = np.asarray(x, dtype=float)
    return np.sign(x) * np.log10(np.abs(x) + eps)


def std_in_signed_log10_domain(mean: np.ndarray, std: np.ndarray, eps: float = LOG10_EPS) -> np.ndarray:
    """
    First-order error propagation for log10(|mean|):
      sigma_log10 ≈ sigma / ((|mean| + eps) * ln(10))
    Keep it finite with eps.
    """
    mean = np.asarray(mean, dtype=float)
    std = np.asarray(std, dtype=float)
    denom = (np.abs(mean) + eps) * LN10
    return std / denom




def make_pastel_cmap(base_cmap: str = BASE_CMAP, blend: float = PASTEL_BLEND, n: int = 256) -> ListedColormap:
    """Blend a diverging colormap with white to obtain a pastel (macaron-like) palette."""
    base = mpl.cm.get_cmap(base_cmap)
    colors = base(np.linspace(0, 1, n))
    blend = float(np.clip(blend, 0.0, 1.0))
    colors[:, :3] = colors[:, :3] * (1.0 - blend) + 1.0 * blend
    return ListedColormap(colors, name=f"{base_cmap}_pastel")
def read_ci_stats(csv_path: str):
    """
    Read a CSV with an "index" first column and numeric columns mean_Ci / std_Ci.
    Returns:
      mean_map: dict[str, float]
      std_map : dict[str, float]
    """
    mean_map = {}
    std_map = {}

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Empty or invalid CSV: {csv_path}")

        index_col = reader.fieldnames[0]
        required = {"mean_Ci", "std_Ci"}
        missing_cols = required - set(reader.fieldnames)
        if missing_cols:
            raise KeyError(f"CSV missing required columns {sorted(missing_cols)}. Found: {reader.fieldnames}")

        for row in reader:
            key = (row.get(index_col) or "").strip()
            if not key:
                continue

            try:
                mean_map[key] = float(row["mean_Ci"])
                std_map[key] = float(row["std_Ci"])
            except (TypeError, ValueError) as e:
                raise ValueError(f"Non-numeric mean_Ci/std_Ci for key='{key}': {e}") from e

    return mean_map, std_map


def main():
    # —— 1. 读取 Ci_1.00_stats_scaled.csv ——
    csv_path = pathlib.Path(__file__).with_name("Ci_1.00_stats_scaled.csv")
    mean_ci, std_ci = read_ci_stats(str(csv_path))

    # —— 2. 定义变量顺序并处理下标 ——
    variables = [
        "TFE",
        "1,1,1,3,3,3-Hexafluoro-2-methyl-2-propanol",
        "Phenol",
        "TBAPF$_6$",
        "TMAPF$_6$",
        "CsPF$_6$",
        "Perylene",
    ]
    n = len(variables)

    # 简化变量名用于索引匹配（把 TBAPF$_6$ → TBAPF6）
    raw_vars = [v.replace("$_6$", "6") for v in variables]

    # —— 3. 构建下三角矩阵 ——
    mat_mean = np.full((n, n), np.nan, dtype=float)
    mat_std = np.full((n, n), np.nan, dtype=float)

    missing_keys = []

    for i, vi in enumerate(raw_vars):
        for j, vj in enumerate(raw_vars):
            if j > i:
                continue

            if i == j:
                # Some datasets store diagonal terms as "vi*vi" rather than "vi".
                k_linear = vi
                k_square = f"{vi}*{vi}"
                if k_linear in mean_ci:
                    key = k_linear
                elif k_square in mean_ci:
                    key = k_square
                else:
                    # Keep square form so missing_keys shows the expected diagonal name.
                    key = k_square
            else:
                k1 = f"{vi}*{vj}"
                k2 = f"{vj}*{vi}"
                key = k1 if k1 in mean_ci else k2

            if key not in mean_ci or key not in std_ci:
                missing_keys.append(key)
                continue

            mat_mean[i, j] = mean_ci[key]
            mat_std[i, j] = std_ci[key]

    if missing_keys:
        uniq = sorted(set(missing_keys))
        print(f"[WARN] Missing {len(uniq)} keys in CSV index. Examples: {uniq[:10]}")

    # =========================
    # 3.5 log10 transform (for plotting)
    # =========================
    if APPLY_LOG10:
        mat_plot = signed_log10(mat_mean, eps=LOG10_EPS)
        mat_std_plot = std_in_signed_log10_domain(mat_mean, mat_std, eps=LOG10_EPS)
        cbar_label = r"signed $\log_{10}(|\mathrm{Ci}|+\epsilon)$"
    else:
        mat_plot = mat_mean.copy()
        mat_std_plot = mat_std.copy()
        cbar_label = "Contribution coefficient"

    # —— 4. 绘制热图（不用 seaborn） ——
    fig, ax = plt.subplots(figsize=(10, 8))

    finite = mat_plot[np.isfinite(mat_plot)]

    if COLORBAR_MODE == "fixed":
        if VMAX_USER is None and VMIN_USER is None:
            raise ValueError("COLORBAR_MODE='fixed' requires VMAX_USER and/or VMIN_USER to be set.")
        if VMIN_USER is None:
            vmax = float(VMAX_USER)
            norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
        else:
            norm = TwoSlopeNorm(vmin=float(VMIN_USER), vcenter=0.0, vmax=float(VMAX_USER))
    elif COLORBAR_MODE == "quantile":
        vmax = float(np.nanpercentile(np.abs(finite), ABS_QUANTILE)) if finite.size else 1.0
        vmax = max(vmax, 1e-12)
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    else:  # "auto"
        vmax = float(np.max(np.abs(finite))) if finite.size else 1.0
        vmax = max(vmax, 1e-12)
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)

    cmap_to_use = make_pastel_cmap(BASE_CMAP, PASTEL_BLEND) if USE_PASTEL_CMAP else BASE_CMAP

    data = np.ma.masked_invalid(mat_plot)
    im = ax.imshow(
        data,
        cmap=cmap_to_use,
        norm=norm,
        origin="upper",
        interpolation="none",
        aspect="equal",
    )

    # ticks / labels
    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(variables, rotation=45, ha="right", fontsize=14)
    ax.set_yticklabels(variables, fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(cbar_label, fontsize=14)
    cbar.ax.tick_params(labelsize=14)

    # annotations + borders (lower triangle)
    for i in range(n):
        for j in range(n):
            if j <= i and np.isfinite(mat_plot[i, j]):
                m = mat_plot[i, j]
                s = mat_std_plot[i, j]
                ax.text(j, i, f"{m:.2f}\n±{s:.2f}", ha="center", va="center", fontsize=12)

                rect = Rectangle(
                    (j - 0.5, i - 0.5),
                    1,
                    1,
                    fill=False,
                    edgecolor="black",
                    linewidth=1,
                    clip_on=False,
                )
                ax.add_patch(rect)

    # keep full border visible
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(n - 0.5, -0.5)

    plt.tight_layout()

    # —— 5. 保存与展示 ——
    suffix = "log10" if APPLY_LOG10 else "linear"
    plt.savefig(f"4-change order-second_order_Ci_stats_heatmap_no_CO2-1.00_borders_only_{suffix}.png", dpi=600, bbox_inches="tight")
    plt.savefig(f"4-change order-second_order_Ci_stats_heatmap_no_CO2-1.00_borders_only_{suffix}.svg", format="svg", dpi=600, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()
