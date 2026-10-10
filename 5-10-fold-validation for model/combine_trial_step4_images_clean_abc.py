import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# =========================================================
# 使用说明
# 1. 把本脚本放在 “Fold validation” 文件夹下运行；
#    或者把 ROOT_DIR 改成你的 Fold validation 路径。
# 2. 程序会自动读取 Trial-1 ~ Trial-10 中
#    Step4-Normalized unit 文件夹下的 3 类图片，
#    并分别拼成 3 张总图。
# 3. 排版方式：每行 3 张，自动换行（10 张时即 4 行，
#    前 3 行各 3 张，第 4 行 1 张）。
# 4. 本版本改动：
#    - 去掉每张子图上方的 Trial 标题；
#    - 在每张总图左上角分别加上 (a)、(b)、(c)，
#      更适合论文排版。
# =========================================================

# ====== 根目录：建议就是 “Fold validation” 文件夹 ======
ROOT_DIR = Path.cwd()
# 如果你不是在 Fold validation 文件夹中运行，请取消下面注释并改成你的路径：
# ROOT_DIR = Path(r"D:\CO2RR-Setup\0-Manuscript\important code in main text\Fold validation")

# ====== 每行放几张图 ======
N_COLS = 3

# ====== 输出分辨率 ======
DPI = 300

# ====== 总图左上角标签 ======
PANEL_LABELS = ["(a)", "(b)", "(c)"]

# ====== 需要汇总的图片（优先找 png，再找 jpg/jpeg） ======
IMAGE_TASKS = [
    {
        "target_stem": "2.3-interaction_features_vs_co2_xM0-0p23_signedlog10_CONTINUOUS_ERR",
        "output_name": "Combined_2.3_interaction_features_all_10_trials_clean_abc.png",
        "figure_title": "",
        "panel_label": PANEL_LABELS[0],
    },
    {
        "target_stem": "4-change order-second_order_Ci_stats_heatmap_no_CO2-0.05_borders_only_log10",
        "output_name": "Combined_heatmap_no_CO2_0.05_all_10_trials_clean_abc.png",
        "figure_title": "",
        "panel_label": PANEL_LABELS[1],
    },
    {
        "target_stem": "4-change order-second_order_Ci_stats_heatmap_no_CO2-1.00_borders_only_log10",
        "output_name": "Combined_heatmap_no_CO2_1.00_all_10_trials_clean_abc.png",
        "figure_title": "",
        "panel_label": PANEL_LABELS[2],
    },
]

IMAGE_EXTS = [".png", ".jpg", ".jpeg"]


def natural_trial_key(path_obj: Path):
    """
    按 Trial-数字 的数字部分排序，例如 Trial-2 < Trial-10
    """
    m = re.search(r"trial[-_ ]*(\d+)", path_obj.name, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    return float("inf")


def find_trial_dirs(root_dir: Path):
    """
    找到根目录下所有 Trial-* 文件夹
    """
    trial_dirs = [
        p for p in root_dir.iterdir()
        if p.is_dir() and re.match(r"trial[-_ ]*\d+$", p.name, flags=re.IGNORECASE)
    ]
    return sorted(trial_dirs, key=natural_trial_key)


def find_step4_dir(trial_dir: Path):
    """
    在每个 Trial 文件夹中寻找 Step4-Normalized unit 文件夹
    采用较宽松匹配：包含 Step4 且包含 Normalized
    """
    # 先检查一级子文件夹
    for sub in trial_dir.iterdir():
        if sub.is_dir():
            name_low = sub.name.lower()
            if "step4" in name_low and "normalized" in name_low:
                return sub

    # 如果一级没找到，再递归搜索
    for sub in trial_dir.rglob("*"):
        if sub.is_dir():
            name_low = sub.name.lower()
            if "step4" in name_low and "normalized" in name_low:
                return sub

    return None


def find_image_file(step4_dir: Path, target_stem: str):
    """
    在 Step4 文件夹中寻找目标图片。
    只读取 png/jpg/jpeg，优先 png。
    """
    for ext in IMAGE_EXTS:
        candidate = step4_dir / f"{target_stem}{ext}"
        if candidate.exists():
            return candidate

    # 如果文件名不完全一致，则做一次 stem 精确匹配
    for file in step4_dir.iterdir():
        if file.is_file() and file.suffix.lower() in IMAGE_EXTS and file.stem == target_stem:
            return file

    return None


def collect_images(root_dir: Path, target_stem: str):
    """
    收集所有 Trial 的目标图片
    返回列表：[(trial_name, image_path), ...]
    """
    results = []
    trial_dirs = find_trial_dirs(root_dir)

    if not trial_dirs:
        raise FileNotFoundError(f"在 {root_dir} 下没有找到 Trial-* 文件夹。")

    for trial_dir in trial_dirs:
        step4_dir = find_step4_dir(trial_dir)
        if step4_dir is None:
            print(f"[警告] {trial_dir.name} 中未找到 Step4-Normalized unit 文件夹，已跳过。")
            continue

        img_path = find_image_file(step4_dir, target_stem)
        if img_path is None:
            print(f"[警告] {trial_dir.name} 的 {step4_dir.name} 中未找到图片：{target_stem}")
            continue

        results.append((trial_dir.name, img_path))

    return results


def add_panel_label(fig, text, x=0.012, y=0.988, fontsize=20):
    """
    在整张总图左上角添加 (a)/(b)/(c) 标签
    坐标使用 figure fraction
    """
    fig.text(
        x, y, text,
        ha="left", va="top",
        fontsize=fontsize,
        fontweight="bold"
    )


def make_combined_figure(image_items, output_path: Path, panel_label: str = "", figure_title: str = "", n_cols: int = 3):
    """
    将图片排版成总图
    """
    n = len(image_items)
    if n == 0:
        print(f"[警告] 没有可用于拼图的图片：{output_path.name}")
        return

    n_rows = math.ceil(n / n_cols)

    # 每个子图给一个合适空间
    fig_w = n_cols * 5.2
    fig_h = n_rows * 4.4
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_w, fig_h))

    # 统一处理 axes 为一维列表
    if n_rows == 1 and n_cols == 1:
        axes = [axes]
    elif n_rows == 1:
        axes = list(axes)
    elif n_cols == 1:
        axes = list(axes)
    else:
        axes = axes.flatten()

    for ax in axes:
        ax.axis("off")

    for i, (trial_name, img_path) in enumerate(image_items):
        ax = axes[i]
        try:
            img = mpimg.imread(str(img_path))
            ax.imshow(img)
            # 不再显示每张子图上方的 Trial 标题
            ax.axis("off")
        except Exception as e:
            ax.text(
                0.5, 0.5,
                f"Failed to load\n{trial_name}\n{img_path.name}",
                ha="center", va="center", fontsize=10
            )
            ax.axis("off")
            print(f"[警告] 读取图片失败：{img_path}\n原因：{e}")

    if figure_title:
        fig.suptitle(figure_title, fontsize=16, y=0.995)

    if panel_label:
        add_panel_label(fig, panel_label)

    plt.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")


def main():
    print(f"当前根目录：{ROOT_DIR}")
    if not ROOT_DIR.exists():
        raise FileNotFoundError(f"ROOT_DIR 不存在：{ROOT_DIR}")

    for task in IMAGE_TASKS:
        print("\n" + "=" * 70)
        print(f"正在处理：{task['target_stem']}")

        image_items = collect_images(ROOT_DIR, task["target_stem"])

        # 按 Trial 数字排序再保险
        image_items = sorted(image_items, key=lambda x: natural_trial_key(Path(x[0])))

        print(f"找到 {len(image_items)} 张图片：")
        for trial_name, img_path in image_items:
            print(f"  - {trial_name}: {img_path.name}")

        output_path = ROOT_DIR / task["output_name"]
        make_combined_figure(
            image_items=image_items,
            output_path=output_path,
            panel_label=task["panel_label"],
            figure_title=task["figure_title"],
            n_cols=N_COLS
        )

    print("\n全部完成。")


if __name__ == "__main__":
    main()
