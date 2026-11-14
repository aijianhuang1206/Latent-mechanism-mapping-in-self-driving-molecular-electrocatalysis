# -*- coding: utf-8 -*-
"""
Fix for "numpy.dtype size changed ... binary incompatibility" on import pandas/seaborn:
- Remove the pandas + seaborn dependency
- Use only standard library (csv) + numpy + matplotlib

Input:
  Ci_1.00_stats.csv
    - first column: feature key (index)
    - columns: mean_Ci, std_Ci

Output:
  second_order_Ci_stats_heatmap_reordered_diag2nd.png
  second_order_Ci_stats_heatmap_reordered_diag2nd.svg
"""

import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import TwoSlopeNorm


# —— 全局字体设置为 Arial ——
plt.rcParams["font.family"] = "Arial"


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
    # —— 1. 读取 Ci_1.00_stats.csv ——
    mean_ci, std_ci = read_ci_stats("Ci_1.00_stats.csv")

    # —— 2. 定义新的双轴变量顺序并处理下标 ——
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

            # 对角线位置读取二阶项，如 Phenol*Phenol，而不是一阶项 Phenol
            if i == j:
                key = f"{vi}*{vi}"
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

    # —— 4. 绘制热图（不用 seaborn） ——
    fig, ax = plt.subplots(figsize=(10, 8))

    # 对称色标：以 0 为中心
    finite = mat_mean[np.isfinite(mat_mean)]
    vmax = float(np.max(np.abs(finite))) if finite.size else 1.0
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)

    data = np.ma.masked_invalid(mat_mean)
    im = ax.imshow(
        data,
        cmap="bwr",
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
    cbar.set_label("Bxixj", fontsize=14)
    cbar.ax.tick_params(labelsize=14)

    # annotations + bold borders only for data cells (lower triangle)
    for i in range(n):
        for j in range(n):
            if j <= i and np.isfinite(mat_mean[i, j]):
                m = mat_mean[i, j]
                s = mat_std[i, j]
                ax.text(j, i, f"{m:.1f}\n±{s:.1f}", ha="center", va="center", fontsize=12)

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
    plt.savefig("second_order_Ci_1.00.png", dpi=600, bbox_inches="tight")
    plt.savefig("second_order_Ci_1.00.svg", format="svg", dpi=600, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()
