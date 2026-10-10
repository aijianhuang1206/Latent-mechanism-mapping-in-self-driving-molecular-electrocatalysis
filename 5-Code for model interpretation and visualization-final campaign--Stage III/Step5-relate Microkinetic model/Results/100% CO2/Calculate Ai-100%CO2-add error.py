import pandas as pd
import numpy as np

# ======================
# 参数区（按你的设定）
# ======================
R = 8.314
T = 298.15
kobs = 47548.14815

CO2_solubility = 0.23   # M
CO2_fraction = 1.00     # 100% CO2
x = CO2_fraction * CO2_solubility  # 0.23 M

# 改成你的真实路径（或保持你原来的 D: 路径也行）
input_path = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\100% CO2 1D.csv"
output_path = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\100% Ai.csv"

# 你表格里用于取数的列名
mean_col = "mean_Ci_1.00"
std_col  = "std_Ci_1.00"   # 新增：用于误差传播

# ======================
# 读取数据
# ======================
df = pd.read_csv(input_path)

# 建立 Feature_name -> 数值 的映射（均值 & 标准差）
val_mean = dict(zip(df["Feature_name"], df[mean_col]))
val_std  = dict(zip(df["Feature_name"], df[std_col]))

# 找到所有“可配对”的 base feature：
# base: 不含 *CO2 且存在对应 base*CO2
base_features = sorted([
    f for f in df["Feature_name"].unique()
    if ("*CO2" not in f) and (f"{f}*CO2" in val_mean)
])

# ======================
# 批量计算
# ======================
rows = []
const = (R * T / 2.0) / kobs  # 用于 delta 的误差传播系数（取绝对值在 std 时用）

for f in base_features:
    # b, k 的均值
    b_mean = float(val_mean[f])                 # 截距
    k_mean = float(val_mean[f"{f}*CO2"])        # 斜率

    # b, k 的 std（标准差/标准误差，取决于你表里的定义）
    b_std = float(val_std.get(f, np.nan))
    k_std = float(val_std.get(f"{f}*CO2", np.nan))

    # Ai 均值
    Ai_mean = k_mean * x + b_mean

    # Ai std：误差传播（不考虑协方差项）
    # sigma_Ai = sqrt( (x*sigma_k)^2 + (sigma_b)^2 )
    if np.isfinite(b_std) and np.isfinite(k_std):
        Ai_std = np.sqrt((x * k_std) ** 2 + (b_std) ** 2)
    else:
        Ai_std = np.nan

    # delta 均值
    delta_mean = -(R * T / 2.0) * (Ai_mean / kobs)

    # delta std（可选但建议一起输出）
    # sigma_delta = |(RT/2)/kobs| * sigma_Ai
    delta_std = abs(const) * Ai_std if np.isfinite(Ai_std) else np.nan

    rows.append({
        "Feature": f,

        "Intercept_b_mean": b_mean,
        "Intercept_b_std": b_std,

        "Slope_k_mean_(Feature*CO2)": k_mean,
        "Slope_k_std_(Feature*CO2)": k_std,

        "x_(1.00*0.23_M)": x,

        "Ai_mean_(k*x+b)": Ai_mean,
        "Ai_std_(propagated)": Ai_std,

        "Delta_mean_( -RT/2 * Ai/kobs )": delta_mean,
        "Delta_std_(propagated)": delta_std
    })

out = pd.DataFrame(rows)

# ======================
# 输出：屏幕 + 保存CSV
# ======================
print(f"Matched feature pairs: {len(out)}")
print(out.to_string(index=False))

out.to_csv(output_path, index=False)
print(f"\nSaved to: {output_path}")
