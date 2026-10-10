import os
import glob
import numpy as np
import pandas as pd

# 1. 指定根目录，下面会遍历其所有子文件夹
root_dir = 'D:\\CO2RR-Setup\\0-Manuscript\\important code in main text\\Fold validation\\Trial-10\\Step2-calculate the Ci and Axi plot for each input x0'

# 2. 找到所有名为 summary_Ci.csv 的文件
pattern = os.path.join(root_dir, '*', 'summary_Ci.csv')
file_paths = glob.glob(pattern)
if not file_paths:
    raise FileNotFoundError(f"No summary_Ci.csv found under {root_dir}")

# 3. 读取所有文件到 DataFrame 列表
dfs = [pd.read_csv(fp, index_col=0) for fp in file_paths]

# 4. 检查所有表格的行列一致性
base_idx = dfs[0].index
base_cols = dfs[0].columns
for df in dfs[1:]:
    if not df.index.equals(base_idx) or not df.columns.equals(base_cols):
        raise ValueError("Found summary_Ci.csv with mismatched rows/columns")

# 5. 将所有 DataFrame 的值堆叠到一个 3D 数组 (features, cols, n_files)
data = np.stack([df.values for df in dfs], axis=2)

# 6. 计算每个 Feature×Column 的平均值和标准差
mean_vals = data.mean(axis=2)
std_vals  = data.std(axis=2, ddof=1)  # ddof=1 计算样本标准差

mean_df = pd.DataFrame(mean_vals, index=base_idx, columns=base_cols)
std_df  = pd.DataFrame(std_vals,  index=base_idx, columns=base_cols)

# 7. 合并成一个统计表：mean_*, std_* 列
out_df = pd.concat([
    mean_df.add_prefix('mean_'),
    std_df.add_prefix('std_')
], axis=1)

# 8. 保存到新的 CSV
out_path = os.path.join(root_dir, 'summary_Ci_stats.csv')
out_df.to_csv(out_path, encoding='utf-8-sig')

print(f"▶️ 已生成统计表：{out_path}")







































