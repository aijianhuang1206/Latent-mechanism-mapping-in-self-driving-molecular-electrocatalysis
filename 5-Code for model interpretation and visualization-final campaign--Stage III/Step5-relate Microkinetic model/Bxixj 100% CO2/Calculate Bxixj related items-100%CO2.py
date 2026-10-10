import pandas as pd
import numpy as np

# ======================
# 参数区（按你的设定）
# ======================
R = 8.314
T = 298.15
kobs = 47548.14815        # k_obs
kobs_star = 47548.14815   # k_obs*（若不同请在这里改）

bij_path = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\100% CO2 2D coe.csv"
ai_path  = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\100% Ai.csv"
out_path = r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Derivations\100% CO2-revision-add error\2D_equation-results-with-std.csv"

# ======================
# 读入 Bij (2D) 与 Ai (1D 已算好)
# ======================
bij_df = pd.read_csv(bij_path)   # columns: Feature_name, mean_Ci, std_Ci
ai_df  = pd.read_csv(ai_path)

# 你 100% Ai.csv 的列名（按你上传的文件结构）
ai_mean_col = "Ai_mean_(k*x+b)"
ai_std_col  = "Ai_std_(propagated)"

ai_mean_lookup = dict(zip(ai_df["Feature"], ai_df[ai_mean_col]))
ai_std_lookup  = dict(zip(ai_df["Feature"], ai_df[ai_std_col]))

# ======================
# 逐行解析 i,j 并计算
# ======================
rows = []

for _, r in bij_df.iterrows():
    fname = str(r["Feature_name"])
    if "*" not in fname:
        continue

    i, j = fname.split("*", 1)

    Bij_mean = float(r["mean_Ci"])
    Bij_std  = float(r["std_Ci"]) if ("std_Ci" in bij_df.columns and pd.notna(r["std_Ci"])) else np.nan

    if i not in ai_mean_lookup or j not in ai_mean_lookup:
        raise ValueError(f"Missing Ai for i={i} or j={j} in {ai_path}")

    Ai_mean = float(ai_mean_lookup[i])
    Aj_mean = float(ai_mean_lookup[j])

    Ai_std = float(ai_std_lookup.get(i, np.nan))
    Aj_std = float(ai_std_lookup.get(j, np.nan))

    # ----------------------
    # Delta_ij (mean)
    # 线性形式（推荐，且与你原脚本注释一致）：
    # Δ_ij = -RT * [ Bij/kobs* - Ai/(2*kobs) - Aj/(2*kobs*) ]
    # ----------------------
    delta_mean = -R * T * ((Bij_mean / kobs_star) - (Ai_mean / (2.0 * kobs))*(Aj_mean / (2.0 * kobs_star)))

    # 如果你“确实”要用乘积形式（你原脚本当前写法类似这个），改用下面两行并注释掉上面 delta_mean：
    # delta_mean = -R * T * ((Bij_mean / kobs_star) - (Ai_mean / (2.0 * kobs_star)) * (Aj_mean / (2.0 * kobs_star)))

    # ----------------------
    # Delta_ij (std) — 一阶误差传播（默认三者独立）
    # 对线性形式：delta = -RT*(Bij/k* - Ai/(2k) - Aj/(2k*))
    # ∂delta/∂Bij = -RT*(1/k*)
    # ∂delta/∂Ai  = +RT*(1/(2k))
    # ∂delta/∂Aj  = +RT*(1/(2k*))
    # ----------------------
    d_Bij = abs(-R * T * (1.0 / kobs_star))
    d_Ai  = abs(+R * T * (1.0 / (2.0 * kobs)))
    d_Aj  = abs(+R * T * (1.0 / (2.0 * kobs_star)))

    # 若某些 std 缺失则结果给 NaN
    if np.isfinite(Bij_std) and np.isfinite(Ai_std) and np.isfinite(Aj_std):
        delta_std = np.sqrt((d_Bij * Bij_std) ** 2 + (d_Ai * Ai_std) ** 2 + (d_Aj * Aj_std) ** 2)
    else:
        delta_std = np.nan

    rows.append({
        "i": i,
        "j": j,

        "Bij_mean": Bij_mean,
        "Bij_std": Bij_std,

        "Ai_mean": Ai_mean,
        "Ai_std": Ai_std,

        "Aj_mean": Aj_mean,
        "Aj_std": Aj_std,

        "kobs": kobs,
        "kobs_star": kobs_star,

        "Delta_ij_mean": delta_mean,
        "Delta_ij_std": delta_std
    })

out = pd.DataFrame(rows)

print(f"Computed pairs: {len(out)}")
print(out.to_string(index=False))

out.to_csv(out_path, index=False)
print(f"\nSaved to: {out_path}")
