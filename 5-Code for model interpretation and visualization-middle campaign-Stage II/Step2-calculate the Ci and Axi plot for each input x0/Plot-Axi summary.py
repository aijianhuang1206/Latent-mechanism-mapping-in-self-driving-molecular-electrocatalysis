import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# —— 全局样式 & 字体 ——
plt.rcParams['font.family']     = 'Arial'
plt.rcParams['axes.linewidth']  = 1.5

# 字体大小设置
LABEL_FS   = 16   # 坐标轴标题字体
TICK_FS    = 14   # 刻度字体
LEGEND_FS  = 14   # 图例字体

# —— 1. 读取统计汇总表 ——
csv_path = 'summary_Ci_stats.csv'
df = pd.read_csv(csv_path, index_col=0)

# —— 2. 提取 CO₂ 分数列并排序 ——
mean_cols = sorted(
    [c for c in df.columns if c.startswith('mean_Ci_')],
    key=lambda x: float(x.split('_')[-1])
)
std_cols = ['std_' + c.split('mean_')[1] for c in mean_cols]
fractions = np.array([float(c.split('_')[-1]) for c in mean_cols])

# —— 3. 定义交互特征及一阶特征（已去掉 CO2*CO2） ——
inter_feats = [
    'Phenol*CO2',
    'TFE*CO2',
    '1,1,1,3,3,3-Hexafluoro-2-methyl-2-propanol*CO2',
    'TBAPF6*CO2',
    'CsPF6*CO2',
    'TMAPF6*CO2',
    'Perylene*CO2'
]
base_feats = [f.split('*')[0] for f in inter_feats]

# —— 4. 绘图 ——
fig, ax = plt.subplots(figsize=(10, 6))

for inter, base in zip(inter_feats, base_feats):
    k_mean = df.loc[inter, mean_cols].values
    b_mean = df.loc[base,  mean_cols].values
    k_std  = df.loc[inter, std_cols].values
    b_std  = df.loc[base,  std_cols].values

    y_mean = k_mean * fractions + b_mean
    y_std  = np.sqrt((fractions * k_std)**2 + b_std**2)

    # 原始 label
    label = inter.replace('CO2', 'CO$_2$')
    # 对 PF6 中的 6 进行下标化
    label = label.replace('TBAPF6', 'TBAPF$_6$')
    label = label.replace('CsPF6', 'CsPF$_6$')
    label = label.replace('TMAPF6', 'TMAPF$_6$')

    ax.plot(fractions, y_mean, linewidth=2.5, label=label)
    ax.fill_between(fractions,
                    y_mean - y_std,
                    y_mean + y_std,
                    alpha=0.2)

# —— 5. 坐标轴 & 样式 ——
ax.set_xlabel('CO$_2$ concentration', fontsize=LABEL_FS, labelpad=10)
ax.set_ylabel(r'Axi', fontsize=LABEL_FS, labelpad=10)
ax.tick_params(width=1.5, length=6, labelsize=TICK_FS)
ax.grid(False)

# —— 6. 延长 x 轴 5% 空白 ——
ax.set_xlim(0, 1)

# —— 7. 图例放置在中央空白处，并增大字体 ——
# ax.legend(
#     loc='upper left',
#     bbox_to_anchor=(0.4, 0.5),
#     fontsize=LEGEND_FS,
#     frameon=False
# )

plt.tight_layout()
plt.savefig('interaction_features_vs_co2_stats_no_CO2xCO2.png', dpi=600, bbox_inches='tight')
plt.savefig(
    'interaction_features_vs_co2_stats_no_CO2xCO2.svg',
    format='svg',
    dpi=600,
    bbox_inches='tight'
)
plt.show()
