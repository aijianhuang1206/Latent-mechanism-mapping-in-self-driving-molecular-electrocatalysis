"""计算原始 E″ 的 100% CO2 - 5% CO2 差值，并沿用原脚本的热图格式。

将本脚本放在同时包含以下两个文件夹的目录中，然后直接运行：
    Bxixj 5% CO2
    Bxixj 100% CO2

auto 模式优先读取各文件夹中的 2D_equation-results-with-std.csv。
如果两组原始表不齐全，则从两组 Delta_2D_log_mean_matrix.csv 和
Delta_2D_log_std_matrix.csv 还原原始量；绝不直接相减 log 矩阵。
还原方式对应前面绘图脚本的 sign(x)*log10(1+abs(x)) 及一阶误差传播。

只有两组均值和 STD 时无法恢复组间协方差；默认按独立条件传播 STD。
若有同一 fold 下的两组原始结果，逐 fold 相减后求 STD 更准确。
所有输出均保存在本脚本所在目录，不覆盖两组输入文件。
依赖：numpy、pandas、matplotlib；Arial 需在运行电脑上安装。
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap, Normalize, TwoSlopeNorm
from matplotlib.patches import Rectangle


# ====================== 输入、输出及统计设置 ======================
ROOT_DIR = Path(__file__).resolve().parent
LOW_DIR = ROOT_DIR / "Bxixj 5% CO2"
HIGH_DIR = ROOT_DIR / "Bxixj 100% CO2"
OUTPUT_DIR = ROOT_DIR
PREFIX = "Epp_difference_100_minus_5"

# auto：两组原始表都存在时优先使用；否则使用下面的两个 log 矩阵。
# 可设为 raw 或 log_matrices，强制使用某种输入。
INPUT_MODE = "auto"
RAW_NAME = "2D_equation-results-with-std.csv"
LOG_MEAN_NAME = "Delta_2D_log_mean_matrix.csv"
LOG_STD_NAME = "Delta_2D_log_std_matrix.csv"

# 对应此前绘图脚本的 STD_IN_LOGSPACE=True。
# 仅在读取 log 矩阵时使用；若原脚本设为 False，此处也需改为 False。
INPUT_STD_IN_LOGSPACE = True

# 两条件间的相关系数，未知时默认按独立条件近似（rho=0）。
# 不能从两张均值/STD 汇总表推断此系数。
CORRELATION = 0.0
REMOVE_FEATURE = "CO2"

# ====================== 沿用原来的绘图格式 ======================
DESIRED_ORDER = [
    "TFE",
    "1,1,1,3,3,3-Hexafluoro-2-methyl-2-propanol",
    "Phenol",
    "TBAPF6",
    "TMAPF6",
    "CsPF6",
    "Perylene",
]
FIGSIZE = (11, 9)
AXIS_FONTSIZE = 14
TICK_ROT = 45
ANNOT_MEAN_FONTSIZE = 13
ANNOT_STD_FONTSIZE = 13
BASE_CMAP = "RdBu_r"
PASTEL_BLEND = 0.45
FIXED_CBAR_RANGE = (-8.0, 8.0)
STD_CMAP = "Greys"
STD_QUANTILE = 95
PLOT_STD_HEATMAP = True
SHOW_FIGURES = True
SAVE_DPI = 600


def signed_log10_1p(values):
    values = np.asarray(values, dtype=float)
    return np.sign(values) * np.log1p(np.abs(values)) / np.log(10.0)


def inverse_signed_log10_1p(values):
    values = np.asarray(values, dtype=float)
    with np.errstate(over="raise", invalid="raise"):
        return np.sign(values) * np.expm1(np.abs(values) * np.log(10.0))


def logspace_std(mean, std):
    return np.asarray(std) / (np.log(10.0) * (1.0 + np.abs(mean)))


def pack_pairs(rows, source):
    """以无序特征对为键对齐数据，拒绝冲突的对称/重复记录。"""
    pairs = {}
    for i, j, mean, std in rows:
        if pd.isna(i) or pd.isna(j) or not str(i).strip() or not str(j).strip():
            raise ValueError(f"Empty feature name in {source}")
        i, j = str(i).strip(), str(j).strip()
        if REMOVE_FEATURE in (i, j):
            continue
        mean, std = float(mean), float(std)
        if not np.isfinite(mean):
            raise ValueError(f"Non-finite mean for ({i}, {j}) in {source}")
        if np.isinf(std) or (np.isfinite(std) and std < 0):
            raise ValueError(f"Invalid STD for ({i}, {j}) in {source}")
        key = tuple(sorted((i, j)))
        if key in pairs and not np.allclose(
            pairs[key], (mean, std), rtol=1e-9, atol=1e-12, equal_nan=True
        ):
            raise ValueError(f"Conflicting duplicate pair {key} in {source}")
        pairs[key] = (mean, std)
    if not pairs:
        raise ValueError(f"No usable feature pairs in {source}")
    return pairs


def load_raw(folder):
    path = folder / RAW_NAME
    df = pd.read_csv(path, encoding="utf-8-sig")
    required = ["i", "j", "Delta_ij_mean", "Delta_ij_std"]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns {sorted(missing)} in {path}")
    rows = df[required].itertuples(index=False, name=None)
    return pack_pairs(rows, path)


def read_matrix(path):
    df = pd.read_csv(path, index_col=0, encoding="utf-8-sig")
    df.index = df.index.map(lambda x: str(x).strip())
    df.columns = df.columns.map(lambda x: str(x).strip())
    if not df.index.is_unique or not df.columns.is_unique:
        raise ValueError(f"Duplicate feature labels in {path}")
    if set(df.index) != set(df.columns):
        raise ValueError(f"Row/column feature sets differ in {path}")
    return df.apply(pd.to_numeric, errors="raise")


def load_log_matrices(folder):
    mean_path, std_path = folder / LOG_MEAN_NAME, folder / LOG_STD_NAME
    means, stds = read_matrix(mean_path), read_matrix(std_path)
    if set(means.index) != set(stds.index):
        raise ValueError(f"Mean/STD feature sets differ in {folder}")
    stds = stds.reindex(index=means.index, columns=means.columns)
    # 均值矩阵中上三角缺失时，允许从下三角读取；原脚本输出对称矩阵。
    rows = []
    for i in means.index:
        for j in means.columns:
            y = means.loc[i, j]
            if pd.isna(y):
                continue
            if not np.isfinite(y):
                raise ValueError(f"Non-finite log mean for ({i}, {j}) in {mean_path}")
            raw_mean = float(inverse_signed_log10_1p(y))
            std = stds.loc[i, j]
            if pd.isna(std):
                std = stds.loc[j, i]
            raw_std = (
                float(std) * np.log(10.0) * (1.0 + abs(raw_mean))
                if INPUT_STD_IN_LOGSPACE else float(std)
            )
            rows.append((i, j, raw_mean, raw_std))
    return pack_pairs(rows, folder)


def load_inputs():
    if INPUT_MODE not in {"auto", "raw", "log_matrices"}:
        raise ValueError("INPUT_MODE must be auto, raw or log_matrices")
    for folder in (LOW_DIR, HIGH_DIR):
        if not folder.is_dir():
            raise FileNotFoundError(
                f"Input folder not found: {folder}\n"
                "Place this script beside 'Bxixj 5% CO2' and 'Bxixj 100% CO2'."
            )
    both_raw = all((folder / RAW_NAME).is_file() for folder in (LOW_DIR, HIGH_DIR))
    use_raw = INPUT_MODE == "raw" or (INPUT_MODE == "auto" and both_raw)
    loader = load_raw if use_raw else load_log_matrices
    source = "raw Epp tables" if use_raw else "inverse-transformed signed-log matrices"
    low, high = loader(LOW_DIR), loader(HIGH_DIR)
    if set(low) != set(high):
        raise ValueError(
            "Feature pairs do not match across conditions.\n"
            f"Only in 5%: {sorted(set(low) - set(high))}\n"
            f"Only in 100%: {sorted(set(high) - set(low))}"
        )
    return low, high, source


def calculate_difference(low, high):
    if not np.isfinite(CORRELATION) or not -1.0 <= CORRELATION <= 1.0:
        raise ValueError("CORRELATION must be a finite number between -1 and 1")
    if set(low) != set(high) or not low:
        raise ValueError("The two conditions must have the same nonempty pair set")
    rows = []
    for i, j in sorted(high):
        mean_high, std_high = high[(i, j)]
        mean_low, std_low = low[(i, j)]
        # 先对原始 E″ 做差，方向固定为 100% - 5%。
        difference = mean_high - mean_low
        if np.isfinite(std_high) and np.isfinite(std_low):
            if CORRELATION == 0:
                difference_std = np.hypot(std_high, std_low)
            else:
                # 等价于 s100²+s5²-2*rho*s100*s5，避免 rho=1 时相消误差。
                variance = (std_high - std_low) ** 2 + (
                    2.0 * (1.0 - CORRELATION) * std_high * std_low
                )
                difference_std = np.sqrt(variance)
        else:
            difference_std = np.nan
        if not np.isfinite(difference) or np.isinf(difference_std):
            raise ValueError(f"Difference overflow for ({i}, {j})")
        rows.append({
            "i": i, "j": j,
            "Epp_100_mean": mean_high, "Epp_100_std": std_high,
            "Epp_5_mean": mean_low, "Epp_5_std": std_low,
            "Difference_mean_100_minus_5": difference,
            "Difference_std": difference_std,
            "Difference_log_mean": float(signed_log10_1p(difference)),
            "Difference_log_std": float(logspace_std(difference, difference_std)),
            "Assumed_correlation": CORRELATION,
        })
    return pd.DataFrame(rows)


def build_matrices(results):
    features = set(results["i"]) | set(results["j"])
    order = [x for x in DESIRED_ORDER if x in features]
    order += sorted(features - set(order))
    columns = {
        "raw_mean": "Difference_mean_100_minus_5",
        "raw_std": "Difference_std",
        "log_mean": "Difference_log_mean",
        "log_std": "Difference_log_std",
    }
    matrices = {}
    for name, column in columns.items():
        mat = pd.DataFrame(np.nan, index=order, columns=order)
        for _, row in results.iterrows():
            mat.loc[row["i"], row["j"]] = row[column]
            mat.loc[row["j"], row["i"]] = row[column]
        matrices[name] = mat
    return matrices


def set_arial():
    plt.rcParams.update({
        "font.family": "Arial",
        "font.sans-serif": ["Arial"],
        "mathtext.fontset": "custom",
        "mathtext.rm": "Arial",
        "mathtext.it": "Arial:italic",
        "mathtext.bf": "Arial:bold",
        "mathtext.sf": "Arial",
        "mathtext.tt": "Arial",
        "mathtext.cal": "Arial",
    })


def make_pastel_cmap():
    colors = mpl.colormaps[BASE_CMAP](np.linspace(0, 1, 256))
    colors[:, :3] = colors[:, :3] * (1.0 - PASTEL_BLEND) + PASTEL_BLEND
    return ListedColormap(colors)


def plot_heatmap(matrix, std_matrix=None):
    is_mean = std_matrix is not None
    values = matrix.to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    if not finite.size:
        return None
    n = len(matrix)
    mask = np.triu(np.ones_like(values, dtype=bool), k=1) | ~np.isfinite(values)
    if is_mean:
        vmin, vmax = FIXED_CBAR_RANGE
        norm, cmap = TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax), make_pastel_cmap()
        suffix = "log_mean_heatmap_with_std_annot"
        label = r"$\mathrm{sign}(d)\,\log_{10}(1+|d|)$"
        std_values = std_matrix.to_numpy(dtype=float)
    else:
        vmax = max(float(np.nanpercentile(finite, STD_QUANTILE)), 1e-12)
        norm, cmap = Normalize(vmin=0.0, vmax=vmax), STD_CMAP
        suffix = "log_std_heatmap"
        label = r"$\sigma\left(\mathrm{sign}(d)\log_{10}(1+|d|)\right)$"
    fig, ax = plt.subplots(figsize=FIGSIZE)
    im = ax.imshow(np.ma.array(values, mask=mask), cmap=cmap, norm=norm,
                   origin="upper", interpolation="none", aspect="equal")
    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(matrix.columns, rotation=TICK_ROT, ha="right", fontsize=AXIS_FONTSIZE)
    ax.set_yticklabels(matrix.index, fontsize=AXIS_FONTSIZE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Difference: 100% CO2 - 5% CO2", fontsize=AXIS_FONTSIZE, pad=12)
    for i in range(n):
        for j in range(i + 1):
            if not np.isfinite(values[i, j]):
                continue
            ax.text(j, i - 0.12 if is_mean else i, f"{values[i, j]:.2f}",
                    ha="center", va="center", fontsize=ANNOT_MEAN_FONTSIZE)
            if is_mean and np.isfinite(std_values[i, j]):
                ax.text(j, i + 0.22, f"±{std_values[i, j]:.2f}",
                        ha="center", va="center", fontsize=ANNOT_STD_FONTSIZE)
            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                   edgecolor="black", linewidth=1))
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(label, fontsize=AXIS_FONTSIZE)
    cbar.ax.tick_params(labelsize=AXIS_FONTSIZE)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(n - 0.5, -0.5)
    fig.tight_layout()
    for extension in ("png", "svg"):
        path = OUTPUT_DIR / f"{PREFIX}_{suffix}.{extension}"
        fig.savefig(path, dpi=SAVE_DPI, bbox_inches="tight")
        print(f"Saved: {path}")
    return fig


def main():
    low, high, source = load_inputs()
    print(f"Input source: {source}")
    print("Difference = raw Epp(100% CO2) - raw Epp(5% CO2)")
    print(f"STD assumption: cross-condition correlation rho = {CORRELATION:g}")
    print("Color/mean annotation = sign(d)*log10(1+abs(d)); STD uses first-order propagation.")
    results = calculate_difference(low, high)
    results["Input_source"] = source
    matrices = build_matrices(results)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = OUTPUT_DIR / f"{PREFIX}_results.csv"
    results.to_csv(table_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {table_path}")
    for name, matrix in matrices.items():
        path = OUTPUT_DIR / f"{PREFIX}_{name}_matrix.csv"
        matrix.to_csv(path, encoding="utf-8-sig")
        print(f"Saved: {path}")
    set_arial()
    figures = [plot_heatmap(matrices["log_mean"], matrices["log_std"])]
    if PLOT_STD_HEATMAP:
        figures.append(plot_heatmap(matrices["log_std"]))
    if SHOW_FIGURES:
        plt.show()
    for fig in figures:
        if fig is not None:
            plt.close(fig)
    print(f"Completed: {len(results)} feature pairs. Outputs: {OUTPUT_DIR}")
    return results


if __name__ == "__main__":
    main()
