import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================
# 0) 全局设置
# =========================
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.linewidth'] = 1.5

LABEL_FS = 16
TICK_FS = 14
LEGEND_FS = 14

# =========================
# 1) 物理常数 & CO2 映射
# =========================
R = 8.314
T = 298.15

# 0–1 atm ↔ 0–0.23 M（你的设定）
CO2_MAX_M = 0.23

# 关键开关：Ai 的线性构造 Ai = k*C + b 中，C 用哪个单位？
# - True  : 用溶解浓度(M)  -> C = 0.23 * atm
# - False : 用分压/比例(atm) -> C = atm
USE_M_FOR_Ai = True

# 绘图横轴用 M（更符合你提问）
PLOT_X_IN_M = True

# y 轴是否用 sign*log10(|y|)
USE_SIGNED_LOG10 = True
LOG10_EPS = 1e-12

def signed_log10(x, eps=LOG10_EPS):
    x = np.asarray(x, dtype=float)
    return np.sign(x) * np.log10(np.abs(x) + eps)

# =========================
# 2) kobs(C_atm) 朗格米尔模型（注意：输入必须是 atm）
# =========================
# 用你之前拟合得到的参数（拟合时 C 用 atm，所以这里 K 的单位是 1/atm）
KOBS_KMAX = 5.24e4
KOBS_K    = 9.80

# ✅ 新增：当 C_atm=0 时 kobs 取 1000
KOBS_K0   = 1000.0

def kobs_langmuir_atm(C_atm, kmax=KOBS_KMAX, K=KOBS_K, k0=KOBS_K0):
    """Langmuir-type kobs with baseline; C_atm 必须是 0–1 atm（或同量纲比例）。"""
    C_atm = np.asarray(C_atm, dtype=float)
    return k0 + kmax * (K * C_atm) / (1.0 + K * C_atm)

# =========================
# 3) 读取汇总表（含 mean_Ci_*, std_Ci_*）
# =========================
csv_path = "modified_table_scaled.csv"
df = pd.read_csv(csv_path, index_col=0)

mean_cols = sorted(
    [c for c in df.columns if c.startswith('mean_Ci_')],
    key=lambda x: float(x.split('_')[-1])
)
std_cols = ['std_' + c.split('mean_')[1] for c in mean_cols]

# 从列名提取 0–1 atm（或比例轴）
C_atm = np.array([float(c.split('_')[-1]) for c in mean_cols], dtype=float)
C_M   = C_atm * CO2_MAX_M

# Ai 的 x 轴（用于 Ai = k*C + b）
C_for_Ai = C_M if USE_M_FOR_Ai else C_atm

# 画图 x 轴
x_plot = C_M if PLOT_X_IN_M else C_atm

# =========================
# 4) 特征列表（与你原脚本保持一致）
# =========================
inter_feats = [
    'Phenol*CO2',
    'TFE*CO2',
    '1,1,1,3,3,3-Hexafluoro-2-methyl-2-propanol*CO2',
    'TBAPF6*CO2',
    'CsPF6*CO2',
    'TMAPF6*CO2',
    'Perylene*CO2',
    'CO2*CO2'
]
base_feats = [f.split('*')[0] for f in inter_feats]

# =========================
# 5) 主计算 & 作图
# =========================
fig, ax = plt.subplots(figsize=(10, 6))

for inter, base in zip(inter_feats, base_feats):
    k_mean = df.loc[inter, mean_cols].values.astype(float)
    b_mean = df.loc[base,  mean_cols].values.astype(float)
    k_std  = df.loc[inter, std_cols].values.astype(float)
    b_std  = df.loc[base,  std_cols].values.astype(float)

    # ---- (a) 先算 Ai（你说 y 值就是 Ai）
    Ai_mean = k_mean * C_for_Ai + b_mean
    Ai_std  = np.sqrt((C_for_Ai * k_std)**2 + b_std**2)

    # ---- (b) 再算 kobs(C_atm) —— 注意：这里必须用 atm
    # ✅ 现在 C_atm=0 时 kobs=1000，不再为 0
    kobs_C = kobs_langmuir_atm(C_atm)

    # ---- (c) 按公式归一化
    factor = -(R * T / 2.0) / kobs_C
    Ai_norm_mean = factor * Ai_mean
    Ai_norm_std  = np.abs(factor) * Ai_std  # 暂不传播 kobs 拟合不确定度（如需可加）

    # ---- label 美化
    label = inter.replace('CO2', 'CO$_2$')
    label = label.replace('TBAPF6', 'TBAPF$_6$')
    label = label.replace('CsPF6', 'CsPF$_6$')
    label = label.replace('TMAPF6', 'TMAPF$_6$')
    label = label.replace('*CO$_2$', '')

    # ---- (d) y轴变换与误差带
    if USE_SIGNED_LOG10:
        y_plot = signed_log10(Ai_norm_mean)
        y_low  = signed_log10(Ai_norm_mean - Ai_norm_std)
        y_high = signed_log10(Ai_norm_mean + Ai_norm_std)

        ax.plot(x_plot, y_plot, linewidth=2.5, label=label)
        ax.fill_between(
            x_plot,
            np.minimum(y_low, y_high),
            np.maximum(y_low, y_high),
            alpha=0.2
        )
    else:
        # 只画正值（log10要求），并过滤 NaN/无穷
        mask = np.isfinite(Ai_norm_mean) & np.isfinite(Ai_norm_std) & (Ai_norm_mean > 0)
        if np.any(mask):
            y_plot = np.log10(Ai_norm_mean[mask])
            y_std_log = Ai_norm_std[mask] / (Ai_norm_mean[mask] * np.log(10))

            ax.plot(x_plot[mask], y_plot, linewidth=2.5, label=label)
            ax.fill_between(
                x_plot[mask],
                y_plot - y_std_log,
                y_plot + y_std_log,
                alpha=0.2
            )

# =========================
# 6) 坐标轴、图例、保存
# =========================
if PLOT_X_IN_M:
    ax.set_xlabel('Dissolved CO$_2$ (M)', fontsize=LABEL_FS, labelpad=10)
    ax.set_xlim(-0.005, CO2_MAX_M)
else:
    ax.set_xlabel('CO$_2$ (atm)', fontsize=LABEL_FS, labelpad=10)
    ax.set_xlim(0, 1.0)

if USE_SIGNED_LOG10:
    ax.set_ylabel(r'$\mathrm{sign}(A_i^{norm})\,\log_{10}(|A_i^{norm}|)$', fontsize=LABEL_FS, labelpad=10)
else:
    ax.set_ylabel(r'$\log_{10}(A_i^{norm})$', fontsize=LABEL_FS, labelpad=10)

ax.tick_params(width=1.5, length=6, labelsize=TICK_FS)
ax.grid(False)

ax.legend(
    loc="lower right",
    bbox_to_anchor=(0.98, 0.15),
    bbox_transform=ax.transAxes,
    fontsize=LEGEND_FS,
    frameon=False
)

plt.tight_layout()

suffix_ai = "AiUsesM" if USE_M_FOR_Ai else "AiUsesAtm"
suffix_x  = "xM0-0p23" if PLOT_X_IN_M else "xAtm0-1"
suffix_y  = "signedlog10" if USE_SIGNED_LOG10 else "log10pos"

out_png = f"3-AiNorm_{suffix_ai}_{suffix_x}_{suffix_y}.png"
out_svg = f"3-AiNorm_{suffix_ai}_{suffix_x}_{suffix_y}.svg"

plt.savefig(out_png, dpi=600, bbox_inches='tight')
plt.savefig(out_svg, format='svg', dpi=600, bbox_inches='tight')
plt.show()

print("Saved:", out_png)
print("Saved:", out_svg)
