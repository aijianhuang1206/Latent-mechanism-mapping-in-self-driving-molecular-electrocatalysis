import os
import glob
import pandas as pd

def aggregate_ci05_stats(root_dir):
    """
    在 root_dir 下查找每个子文件夹中的 'Ci_0.05.csv' 文件，
    读取它们，计算每个 Feature 的平均值和标准差，并输出到新的 CSV。
    """
    pattern = os.path.join(root_dir, '*', 'Ci_0.05.csv')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"在目录 {root_dir} 下未找到任何 Ci_0.05.csv 文件。")

    # 读取所有文件，构建一个 DataFrame 列表
    dfs = []
    for fp in files:
        df = pd.read_csv(fp)
        # 假定文件中第 1 列是 Feature_name，第 2 列是数值
        df = df.rename(columns={df.columns[1]: 'Ci'})
        df = df.set_index(df.columns[0])  # 将 Feature_name 设为索引
        dfs.append(df['Ci'])

    # 检查所有 Series 的索引是否一致
    idx0 = dfs[0].index
    for i, s in enumerate(dfs[1:], start=1):
        if not s.index.equals(idx0):
            raise ValueError(f"文件 {files[i]} 与 {files[0]} 的 Feature 列不一致。")

    # 合并成一个 DataFrame：列名用文件夹名区分
    names = [os.path.basename(os.path.dirname(fp)) for fp in files]
    combined = pd.concat(dfs, axis=1)
    combined.columns = names

    # 计算平均值和标准差
    stats = pd.DataFrame({
        'mean_Ci': combined.mean(axis=1),
        'std_Ci':  combined.std(axis=1, ddof=1)
    })

    # 保存结果
    out_path = os.path.join(root_dir, 'Ci_0.05_stats.csv')
    stats.to_csv(out_path, encoding='utf-8-sig')
    print(f"✅ 统计结果已保存到：{out_path}")

if __name__ == "__main__":
    # TODO: 将下面路径改为你的根目录
    root_directory = r"D:\\CO2RR-Setup\\0-Manuscript\\important code in main text\\Fold validation\\Trial-9\\Step2-calculate the Ci and Axi plot for each input x0"
    aggregate_ci05_stats(root_directory)








































