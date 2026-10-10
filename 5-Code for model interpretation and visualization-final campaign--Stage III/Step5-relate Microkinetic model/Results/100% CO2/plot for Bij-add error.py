import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import Rectangle
from matplotlib.colors import TwoSlopeNorm, ListedColormap, Normalize

# ============================================================
# 1) 输入/输出
# ============================================================
in_path = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\2D_equation-results-with-std.csv"

delta_mean_col = "Delta_ij_mean"
delta_std_col  = "Delta_ij_std"

# 输出文件（你可按需改名）
out_table  = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\2D_equation-results-with-std_noCO2_with_log.csv"
out_mean_matrix = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\Delta_2D_log_mean_matrix.csv"
out_std_matrix  = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\Delta_2D_log_std_matrix.csv"

out_mean_png = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\Delta_2D_log_mean_heatmap_with_std_annot.png"
out_mean_svg = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\Delta_2D_log_mean_heatmap_with_std_annot.svg"

# 可选：std 单独画一张热图（更直观）
PLOT_STD_HEATMAP = True
out_std_png = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\Delta_2D_log_std_heatmap.png"
out_std_svg = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\Delta_2D_log_std_heatmap.svg"

# ============================================================
# 2) 参数设置
# ============================================================
REMOVE_FEATURE = "CO2"

desired_order = [
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

# 标注：上行 mean，下行 ±std
ANNOT_MEAN_FONTSIZE = 13
ANNOT_STD_FONTSIZE  = 10

# 颜色：mean 用发散 pastel；std 用顺序色带（可改）
BASE_CMAP = "RdBu_r"
PASTEL_BLEND = 0.45
ABS_QUANTILE = 95

FIXED_CBAR_RANGE = (-8.0, 8.0)  # 强制 colorbar 范围

STD_CMAP = "Greys"
STD_QUANTILE = 95  # std 色条上限用分位数裁剪，防止极端值压缩

# std 显示方式：
# - True : 把 std 从 Δ 空间传播到 log 空间后再标注/画图
# - False: 标注/画图用原始 Δ 的 std（更“物理量”）
STD_IN_LOGSPACE = True

# ============================================================
# 3) signed log10(1+|Δ|)
# ============================================================
def signed_log10_1p(x):
    x = np.asarray(x, dtype=float)
    return np.sign(x) * np.log10(1.0 + np.abs(x))

def make_pastel_cmap(base_cmap=BASE_CMAP, blend=PASTEL_BLEND, n=256):
    base = mpl.colormaps[base_cmap]
    colors = base(np.linspace(0, 1, n))
    colors[:, :3] = colors[:, :3] * (1.0 - blend) + 1.0 * blend
    return ListedColormap(colors)

def logspace_std_from_delta(mean_delta, std_delta):
    """
    y = sign(x)*log10(1+|x|)
    dy/dx = 1/(ln(10)*(1+|x|))  （x!=0处成立，x=0附近也可用该极限形式）
    sigma_y ≈ sigma_x * dy/dx
    """
    mean_delta = np.asarray(mean_delta, dtype=float)
    std_delta  = np.asarray(std_delta, dtype=float)
    return std_delta / (np.log(10.0) * (1.0 + np.abs(mean_delta)))

# ============================================================
# 4) 读表 + 去掉 CO2 相关 pair + 计算 mean log 与 std（可选 log-space）
# ============================================================
df = pd.read_csv(in_path)
for c in ["i", "j", delta_mean_col, delta_std_col]:
    if c not in df.columns:
        raise KeyError(f"Missing column '{c}' in {in_path}. Found: {list(df.columns)}")

df = df[(df["i"] != REMOVE_FEATURE) & (df["j"] != REMOVE_FEATURE)].copy()

# mean 的 signed-log
df["Delta_log_mean"] = signed_log10_1p(df[delta_mean_col].astype(float).values)

# std：两种选择
if STD_IN_LOGSPACE:
    df["Delta_log_std"] = logspace_std_from_delta(
        df[delta_mean_col].astype(float).values,
        df[delta_std_col].astype(float).values
    )
else:
    df["Delta_log_std"] = df[delta_std_col].astype(float).values  # 实际上这是 raw-std，只是沿用列名方便后续矩阵

df.to_csv(out_table, index=False)

# ============================================================
# 5) 组装矩阵（对称填充）并按指定顺序重排
# ============================================================
features = sorted(set(df["i"]).union(set(df["j"])))
order = [x for x in desired_order if x in features] + [x for x in features if x not in desired_order]
idx = {f: k for k, f in enumerate(order)}
n = len(order)

mean_mat = np.full((n, n), np.nan, dtype=float)
std_mat  = np.full((n, n), np.nan, dtype=float)

for _, r in df.iterrows():
    ii, jj = idx[r["i"]], idx[r["j"]]
    vm = float(r["Delta_log_mean"])
    vs = float(r["Delta_log_std"])
    mean_mat[ii, jj] = vm
    mean_mat[jj, ii] = vm
    std_mat[ii, jj]  = vs
    std_mat[jj, ii]  = vs

pd.DataFrame(mean_mat, index=order, columns=order).to_csv(out_mean_matrix, index=True)
pd.DataFrame(std_mat,  index=order, columns=order).to_csv(out_std_matrix,  index=True)

# ============================================================
# 6) 画下三角热点图（mean 颜色 + mean±std 标注）
# ============================================================
mask = np.triu(np.ones_like(mean_mat, dtype=bool), k=1)
mean_data = np.ma.array(mean_mat, mask=mask | ~np.isfinite(mean_mat))

finite_mean = mean_mat[np.isfinite(mean_mat)]
if finite_mean.size == 0:
    raise ValueError("No finite values to plot after filtering.")

vmin_fix, vmax_fix = FIXED_CBAR_RANGE
norm = TwoSlopeNorm(vmin=vmin_fix, vcenter=0.0, vmax=vmax_fix)

plt.rcParams["font.family"] = "DejaVu Sans"  # 本地可换 Arial
fig, ax = plt.subplots(figsize=FIGSIZE)

im = ax.imshow(
    mean_data,
    cmap=make_pastel_cmap(),
    norm=norm,
    origin="upper",
    interpolation="none",
    aspect="equal"
)

ax.set_xticks(np.arange(n))
ax.set_yticks(np.arange(n))
ax.set_xticklabels(order, rotation=TICK_ROT, ha="right", fontsize=AXIS_FONTSIZE)
ax.set_yticklabels(order, fontsize=AXIS_FONTSIZE)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["bottom"].set_visible(True)
ax.spines["left"].set_visible(True)
ax.tick_params(length=0)

# 标注：mean（上）±std（下）+ 边框
for i in range(n):
    for j in range(n):
        if j <= i and np.isfinite(mean_mat[i, j]):
            m = mean_mat[i, j]
            s = std_mat[i, j] if np.isfinite(std_mat[i, j]) else np.nan

            # mean（上行）
            ax.text(j, i - 0.12, f"{m:.2f}", ha="center", va="center", fontsize=ANNOT_MEAN_FONTSIZE)

            # std（下行）
            if np.isfinite(s):
                ax.text(j, i + 0.22, f"±{s:.2f}", ha="center", va="center", fontsize=ANNOT_STD_FONTSIZE)

            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                   edgecolor="black", linewidth=1))

cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label(r"$\mathrm{sign}(\Delta)\,\log_{10}(1+|\Delta|)$", fontsize=AXIS_FONTSIZE)
cbar.ax.tick_params(labelsize=AXIS_FONTSIZE)

ax.set_xlim(-0.5, n - 0.5)
ax.set_ylim(n - 0.5, -0.5)
plt.tight_layout()

plt.savefig(out_mean_png, dpi=600, bbox_inches="tight")
plt.savefig(out_mean_svg, format="svg", dpi=600, bbox_inches="tight")
plt.show()

# ============================================================
# 7) 可选：std 单独画一张热图（下三角）
# ============================================================
if PLOT_STD_HEATMAP:
    std_data = np.ma.array(std_mat, mask=mask | ~np.isfinite(std_mat))
    finite_std = std_mat[np.isfinite(std_mat)]
    if finite_std.size == 0:
        raise ValueError("No finite std values to plot after filtering.")

    vmax_s = float(np.nanpercentile(finite_std, STD_QUANTILE))
    vmax_s = max(vmax_s, 1e-12)
    norm_s = Normalize(vmin=0.0, vmax=vmax_s)

    fig2, ax2 = plt.subplots(figsize=FIGSIZE)
    im2 = ax2.imshow(
        std_data,
        cmap=STD_CMAP,
        norm=norm_s,
        origin="upper",
        interpolation="none",
        aspect="equal"
    )

    ax2.set_xticks(np.arange(n))
    ax2.set_yticks(np.arange(n))
    ax2.set_xticklabels(order, rotation=TICK_ROT, ha="right", fontsize=AXIS_FONTSIZE)
    ax2.set_yticklabels(order, fontsize=AXIS_FONTSIZE)

    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["bottom"].set_visible(True)
    ax2.spines["left"].set_visible(True)
    ax2.tick_params(length=0)

    for i in range(n):
        for j in range(n):
            if j <= i and np.isfinite(std_mat[i, j]):
                ax2.text(j, i, f"{std_mat[i, j]:.2f}", ha="center", va="center", fontsize=ANNOT_MEAN_FONTSIZE)
                ax2.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                        edgecolor="black", linewidth=1))

    cbar2 = fig2.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    if STD_IN_LOGSPACE:
        cbar2.set_label(r"$\sigma\left(\mathrm{sign}(\Delta)\log_{10}(1+|\Delta|)\right)$", fontsize=AXIS_FONTSIZE)
    else:
        cbar2.set_label(r"$\sigma(\Delta)$", fontsize=AXIS_FONTSIZE)
    cbar2.ax.tick_params(labelsize=AXIS_FONTSIZE)

    ax2.set_xlim(-0.5, n - 0.5)
    ax2.set_ylim(n - 0.5, -0.5)
    plt.tight_layout()

    plt.savefig(out_std_png, dpi=600, bbox_inches="tight")
    plt.savefig(out_std_svg, format="svg", dpi=600, bbox_inches="tight")
    plt.show()

print("Saved:")
print("table:", out_table)
print("mean matrix:", out_mean_matrix)
print("std matrix:", out_std_matrix)
print("mean png:", out_mean_png)
print("mean svg:", out_mean_svg)
if PLOT_STD_HEATMAP:
    print("std png:", out_std_png)
    print("std svg:", out_std_svg)
