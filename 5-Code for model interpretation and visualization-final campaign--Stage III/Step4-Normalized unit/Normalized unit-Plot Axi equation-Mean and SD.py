import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# —— 全局样式 & 字体 ——
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.linewidth'] = 1.5

# 字体大小设置
LABEL_FS = 16
TICK_FS = 14
LEGEND_FS = 14

# =========================
# 关键设定：把自变量 fractions 直接改为 0–0.23 M
# 物理映射：0–1 atm  ↔  0–0.23 M
# =========================
CO2_MAX_M = 0.23  # 1 atm 对应 0.23 M（你的设定）

# =========================
# y 轴：signed log10（误差带连续，不断开）
# =========================
USE_SIGNED_LOG10 = True
LOG10_EPS = 1e-12

def signed_log10(x, eps=LOG10_EPS):
    """
    与原始脚本一致的“保符号 log10”：
      Y = sign(y) * log10(|y| + eps)
    """
    x = np.asarray(x, dtype=float)
    return np.sign(x) * np.log10(np.abs(x) + eps)

# —— 1. 读取统计汇总表 ——
csv_path = 'modified_table_scaled.csv'
df = pd.read_csv(csv_path, index_col=0)

# —— 2. 提取 CO₂ 分数列并排序 ——
mean_cols = sorted(
    [c for c in df.columns if c.startswith('mean_Ci_')],
    key=lambda x: float(x.split('_')[-1])
)
std_cols = ['std_' + c.split('mean_')[1] for c in mean_cols]

# 原始“归一化/atm”自变量（0–1），仅用于从列名取坐标
fractions_atm = np.array([float(c.split('_')[-1]) for c in mean_cols])

# 现在真正用于模型与绘图的自变量：0–0.23 M
fractions = fractions_atm * CO2_MAX_M  # 单位：M

# —— 3. 定义交互特征及一阶特征 ——
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

# —— 4. 绘图 ——
fig, ax = plt.subplots(figsize=(10, 6))

for inter, base in zip(inter_feats, base_feats):
    k_mean = df.loc[inter, mean_cols].values
    b_mean = df.loc[base,  mean_cols].values
    k_std  = df.loc[inter, std_cols].values
    b_std  = df.loc[base,  std_cols].values

    # ==========================================================
    # 核心修改：自变量改为 M 后，斜率也要换单位
    # 原来：y = k_atm * (0–1) + b
    # 现在：x = 0–0.23 M
    #      k_M = k_atm / 0.23
    #      y = k_M * x + b
    # ==========================================================
    k_mean_M = k_mean
    k_std_M  = k_std

    y_mean = k_mean_M * fractions + b_mean
    y_std  = np.sqrt((fractions * k_std_M)**2 + b_std**2)

    # label 美化
    label = inter.replace('CO2', 'CO$_2$')
    label = label.replace('TBAPF6', 'TBAPF$_6$')
    label = label.replace('CsPF6', 'CsPF$_6$')
    label = label.replace('TMAPF6', 'TMAPF$_6$')
    label = label.replace('*CO$_2$', '')

    # =========================
    # y 轴：signed log10（误差带连续）
    # =========================
    if USE_SIGNED_LOG10:
        y_plot = signed_log10(y_mean)
        y_low  = signed_log10(y_mean - y_std)
        y_high = signed_log10(y_mean + y_std)

        ax.plot(fractions, y_plot, linewidth=2.5, label=label)
        ax.fill_between(
            fractions,
            np.minimum(y_low, y_high),
            np.maximum(y_low, y_high),
            alpha=0.2
        )
    else:
        # 严格 log10：只画 y_mean>0 的点，误差用传播公式
        mask = y_mean > 0
        if np.any(mask):
            y_plot = np.log10(y_mean[mask])
            y_std_log = y_std[mask] / (y_mean[mask] * np.log(10))

            ax.plot(fractions[mask], y_plot, linewidth=2.5, label=label)
            ax.fill_between(
                fractions[mask],
                y_plot - y_std_log,
                y_plot + y_std_log,
                alpha=0.2
            )

# —— 5. 坐标轴 & 样式 ——
ax.set_xlabel('Dissolved CO$_2$ (M)', fontsize=LABEL_FS, labelpad=10)

if USE_SIGNED_LOG10:
    ax.set_ylabel(r'$\mathrm{sign}(y)\log_{10}(|y|)$', fontsize=LABEL_FS, labelpad=10)
else:
    ax.set_ylabel(r'$\log_{10}(y)$', fontsize=LABEL_FS, labelpad=10)

ax.tick_params(width=1.5, length=6, labelsize=TICK_FS)
ax.grid(False)

# x 轴范围：0–0.23 M
ax.set_xlim(0, CO2_MAX_M)

# —— 6. 图例 ——
ax.legend(
    loc="lower right",
    bbox_to_anchor=(0.98, 0.15),
    bbox_transform=ax.transAxes,
    fontsize=LEGEND_FS,
    frameon=False
)

plt.tight_layout()

# —— 7. 保存 ——
plt.savefig('2.3-interaction_features_vs_co2_xM0-0p23_signedlog10_CONTINUOUS_ERR.png',
            dpi=600, bbox_inches='tight')
plt.savefig('2.3-interaction_features_vs_co2_xM0-0p23_signedlog10_CONTINUOUS_ERR.svg',
            format='svg', dpi=600, bbox_inches='tight')

plt.show()
