# -*- coding: utf-8 -*-
"""
将 Trial-1 至 Trial-10 的 Step5 中三类图片分别排版成三张总图。

读取内容：
1. Step5 根目录：
   3-AiNorm_AiUsesM_xM0-0p23_signedlog10.png

2. Step5/Bxixj 5% CO2：
   Delta_2D_log_mean_heatmap_with_std_annot.png

3. Step5/Bxixj 100% CO2：
   Delta_2D_log_mean_heatmap_with_std_annot.png

每类图片均收集 Trial-1 至 Trial-10，共10张，并按照：

    第1行：1、2、3
    第2行：4、5、6
    第3行：7、8、9
    第4行：   10

进行排版。第10张图默认居中。

本版本延续前一版的简洁样式：
- 不添加 Trial 标题；
- 不添加 (a)–(j) 编号；
- 不绘制每张子图的外边框；
- 只保留原始科研图片本身。

使用方法：
将本脚本放在 Trial-1 至 Trial-10 所在的 Fold validation 根目录，
然后用与原分析脚本相同的 PyCharm Python 解释器运行。

依赖：
    Pillow

若尚未安装：
    pip install pillow
"""

from __future__ import annotations

import csv
import re
import traceback
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as exc:
    raise SystemExit(
        "缺少 Pillow 软件包。\n"
        "请在当前 PyCharm Python 环境中安装：pip install pillow"
    ) from exc


# ======================================================================
# 可修改设置
# ======================================================================

ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "10_Trials_Step5_comparison_layouts_clean"

TRIAL_NUMBERS = list(range(1, 11))

MAIN_AXI_IMAGE_STEM = "3-AiNorm_AiUsesM_xM0-0p23_signedlog10"
BXIXJ_HEATMAP_STEM = "Delta_2D_log_mean_heatmap_with_std_annot"

TARGETS = [
    {
        "key": "Axi",
        "display_name": "Step5 Axi",
        "location": "step5_root",
        "image_stem": MAIN_AXI_IMAGE_STEM,
        "output_name": (
            "10_trials_"
            "3-AiNorm_AiUsesM_xM0-0p23_signedlog10_layout_clean.png"
        ),
    },
    {
        "key": "Bxixj_5pct_CO2",
        "display_name": "Bxixj 5% CO2",
        "location": "bxixj_5",
        "image_stem": BXIXJ_HEATMAP_STEM,
        "output_name": (
            "10_trials_Bxixj_5pct_CO2_"
            "Delta_2D_log_mean_heatmap_with_std_annot_layout_clean.png"
        ),
    },
    {
        "key": "Bxixj_100pct_CO2",
        "display_name": "Bxixj 100% CO2",
        "location": "bxixj_100",
        "image_stem": BXIXJ_HEATMAP_STEM,
        "output_name": (
            "10_trials_Bxixj_100pct_CO2_"
            "Delta_2D_log_mean_heatmap_with_std_annot_layout_clean.png"
        ),
    },
]

# 排版：3列 × 4行
N_COLUMNS = 3
N_ROWS = 4

# 每张子图所占的最大区域。文字较多时可继续调大。
PANEL_WIDTH = 1600
PANEL_HEIGHT = 1200

# 总图外围和子图之间的空白
OUTER_MARGIN = 35
HORIZONTAL_GAP = 35
VERTICAL_GAP = 45

# 第10张图放在最后一行中间
CENTER_SINGLE_LAST_PANEL = True

# 简洁排版：无外框、无标题、无编号
SHOW_TRIAL_TITLES = False
SHOW_PANEL_LETTERS = False
DRAW_PANEL_BORDER = False

# 自动去除原图外围的大面积白边
AUTO_CROP_WHITE_MARGIN = True
WHITE_THRESHOLD = 248
CROP_PADDING = 14

# False：低分辨率原图不放大，只对过大的图进行缩小
# True：允许放大到单元格范围
ALLOW_UPSCALE = False

BACKGROUND_COLOR = (255, 255, 255)
OUTPUT_DPI = 300

# 可选：同时输出PDF
SAVE_PDF_COPY = False

# 栅格图片优先顺序；目录内同时有PNG和SVG时优先PNG
RASTER_EXTENSIONS = [
    ".png",
    ".tif",
    ".tiff",
    ".jpg",
    ".jpeg",
    ".bmp",
]


# ======================================================================
# 名称和路径识别
# ======================================================================

def normalize_name(text: str) -> str:
    """
    用于宽松匹配文件夹名称。

    例如：
        Bxixj 5% CO2
        Bxixj-5%CO2
        Bxixj_5_CO2
    """
    text = text.casefold().replace("₂", "2")
    return re.sub(r"[\s_\-–—()\[\]]+", "", text)


def discover_trial_folders() -> dict[int, Path]:
    """
    自动发现 Trial-1 至 Trial-10。

    支持：
        Trial-1
        Trial_1
        Trial 1
    """
    pattern = re.compile(
        r"^trial[\s_-]*(\d+)(?:\s.*)?$",
        flags=re.IGNORECASE,
    )

    discovered: dict[int, Path] = {}

    for candidate in ROOT_DIR.iterdir():
        if not candidate.is_dir():
            continue

        match = pattern.match(candidate.name.strip())
        if not match:
            continue

        trial_number = int(match.group(1))

        if trial_number not in TRIAL_NUMBERS:
            continue

        if trial_number in discovered:
            raise RuntimeError(
                f"发现两个都对应 Trial-{trial_number} 的文件夹：\n"
                f"  1. {discovered[trial_number]}\n"
                f"  2. {candidate}"
            )

        discovered[trial_number] = candidate

    missing = [
        trial_number
        for trial_number in TRIAL_NUMBERS
        if trial_number not in discovered
    ]

    if missing:
        raise FileNotFoundError(
            "以下Trial文件夹未找到："
            + ", ".join(f"Trial-{number}" for number in missing)
            + f"\n根目录：{ROOT_DIR}"
        )

    return discovered


def is_step5_folder_name(folder_name: str) -> bool:
    """
    识别：
        Step5-...
        Step-5-...
        Step 5 ...
    """
    return re.match(
        r"^step[\s_-]*5(?:\D|$)",
        folder_name.strip(),
        flags=re.IGNORECASE,
    ) is not None


def find_image_by_stem(
    search_folder: Path,
    expected_stem: str,
    *,
    recursive: bool = True,
    report_multiple: bool = True,
) -> Path:
    """
    按完整stem查找图片，优先PNG。

    expected_stem不包含扩展名。
    """
    expected_folded = expected_stem.casefold()
    extension_priority = {
        extension: index
        for index, extension in enumerate(RASTER_EXTENSIONS)
    }

    iterator = (
        search_folder.rglob("*")
        if recursive
        else search_folder.iterdir()
    )

    candidates: list[Path] = []

    for path in iterator:
        if not path.is_file():
            continue

        extension = path.suffix.casefold()
        if extension not in extension_priority:
            continue

        if path.stem.casefold() != expected_folded:
            continue

        candidates.append(path)

    if not candidates:
        svg_candidates = [
            path
            for path in search_folder.rglob("*.svg")
            if path.stem.casefold() == expected_folded
        ]

        if svg_candidates:
            raise FileNotFoundError(
                f'仅找到SVG而未找到PNG/JPG/TIFF："{expected_stem}"\n'
                f"{svg_candidates[0]}\n"
                "请确认绘图脚本也输出了PNG文件。"
            )

        raise FileNotFoundError(
            f'未找到图片 "{expected_stem}.png"：\n'
            f"{search_folder}"
        )

    candidates.sort(
        key=lambda path: (
            extension_priority[path.suffix.casefold()],
            len(path.relative_to(search_folder).parts),
            -path.stat().st_mtime_ns,
            path.name.casefold(),
        )
    )

    if report_multiple and len(candidates) > 1:
        print(
            f'[提示] "{expected_stem}" 找到多个栅格版本，'
            f"将使用：{candidates[0]}"
        )

    return candidates[0]


def score_step5_folder(folder: Path) -> int:
    """
    多个Step5候选时，依据目标文件和目标子目录进行评分。
    """
    score = 0

    try:
        find_image_by_stem(
            folder,
            MAIN_AXI_IMAGE_STEM,
            recursive=False,
            report_multiple=False,
        )
    except FileNotFoundError:
        pass
    else:
        score += 10

    for descendant in folder.rglob("*"):
        if not descendant.is_dir():
            continue

        normalized = normalize_name(descendant.name)

        if "bxixj" in normalized and "co2" in normalized:
            if "100" in normalized:
                score += 3
            elif re.search(r"(^|[^0-9])5%?co2", normalized):
                score += 3

    return score


def find_step5_folder(trial_folder: Path) -> Path:
    """
    优先检查Trial的一级子目录；若找不到，再递归查找。
    """
    direct_candidates = [
        path
        for path in trial_folder.iterdir()
        if path.is_dir() and is_step5_folder_name(path.name)
    ]

    candidates = direct_candidates

    if not candidates:
        candidates = [
            path
            for path in trial_folder.rglob("*")
            if path.is_dir() and is_step5_folder_name(path.name)
        ]

    if not candidates:
        raise FileNotFoundError(
            f"{trial_folder.name} 中没有找到Step5文件夹。"
        )

    if len(candidates) == 1:
        return candidates[0]

    scored = [
        (score_step5_folder(folder), folder)
        for folder in candidates
    ]
    scored.sort(
        key=lambda item: (
            item[0],
            -len(item[1].relative_to(trial_folder).parts),
            item[1].name.casefold(),
        ),
        reverse=True,
    )

    best_score = scored[0][0]
    best_folders = [
        folder
        for score, folder in scored
        if score == best_score
    ]

    if best_score <= 0 or len(best_folders) != 1:
        candidate_text = "\n".join(
            f"  - {folder}"
            for folder in candidates
        )
        raise RuntimeError(
            f"{trial_folder.name} 中存在多个无法唯一确定的Step5文件夹：\n"
            f"{candidate_text}"
        )

    return best_folders[0]


def folder_matches_condition(folder_name: str, percent: int) -> bool:
    """
    判断文件夹是否对应 Bxixj 5% CO2 或 Bxixj 100% CO2。
    """
    normalized = normalize_name(folder_name)

    if "bxixj" not in normalized or "co2" not in normalized:
        return False

    if percent == 100:
        return (
            "100%co2" in normalized
            or "100co2" in normalized
        )

    if percent == 5:
        if "100" in normalized:
            return False

        return (
            "5%co2" in normalized
            or "5co2" in normalized
        )

    raise ValueError(f"不支持的CO2条件：{percent}")


def find_bxixj_condition_folder(
    step5_folder: Path,
    percent: int,
) -> Path:
    """
    查找 Step5/Bxixj 5% CO2 或 Step5/Bxixj 100% CO2。
    """
    candidates = [
        folder
        for folder in step5_folder.rglob("*")
        if (
            folder.is_dir()
            and folder_matches_condition(folder.name, percent)
        )
    ]

    if not candidates:
        raise FileNotFoundError(
            f"{step5_folder} 中没有找到 "
            f'Bxixj {percent}% CO2 文件夹。'
        )

    # 优先选择包含目标热图的、层级最浅的目录
    scored: list[tuple[int, int, Path]] = []

    for folder in candidates:
        try:
            find_image_by_stem(
                folder,
                BXIXJ_HEATMAP_STEM,
                recursive=False,
                report_multiple=False,
            )
        except FileNotFoundError:
            contains_image = 0
        else:
            contains_image = 1

        depth = len(folder.relative_to(step5_folder).parts)
        scored.append((contains_image, -depth, folder))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2].name.casefold(),
        ),
        reverse=True,
    )

    best_image_score = scored[0][0]
    best_depth_score = scored[0][1]
    best = [
        folder
        for image_score, depth_score, folder in scored
        if (
            image_score == best_image_score
            and depth_score == best_depth_score
        )
    ]

    if len(best) != 1:
        candidate_text = "\n".join(
            f"  - {folder}"
            for folder in candidates
        )
        raise RuntimeError(
            f"发现多个可能对应 Bxixj {percent}% CO2 的文件夹：\n"
            f"{candidate_text}"
        )

    return best[0]


# ======================================================================
# 图片处理
# ======================================================================

def flatten_to_white(image: Image.Image) -> Image.Image:
    """
    将透明背景合并为白色，并统一转换成RGB。
    """
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P"
        and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        white = Image.new(
            "RGBA",
            rgba.size,
            (255, 255, 255, 255),
        )
        white.alpha_composite(rgba)
        return white.convert("RGB")

    return image.convert("RGB")


def crop_white_margin(image: Image.Image) -> Image.Image:
    """
    仅裁除图片外围连续的大面积近白色空白。
    """
    if not AUTO_CROP_WHITE_MARGIN:
        return image

    gray = ImageOps.grayscale(image)

    mask = gray.point(
        lambda pixel: (
            255 if pixel < WHITE_THRESHOLD else 0
        )
    )
    bounding_box = mask.getbbox()

    if bounding_box is None:
        return image

    left, top, right, bottom = bounding_box

    left = max(0, left - CROP_PADDING)
    top = max(0, top - CROP_PADDING)
    right = min(image.width, right + CROP_PADDING)
    bottom = min(image.height, bottom + CROP_PADDING)

    return image.crop((left, top, right, bottom))


def prepare_panel_image(image_path: Path) -> Image.Image:
    """
    打开图片、处理透明背景、裁白边，并等比例缩放。
    """
    with Image.open(image_path) as source:
        source.load()
        image = flatten_to_white(source)

    image = crop_white_margin(image)

    scale = min(
        PANEL_WIDTH / image.width,
        PANEL_HEIGHT / image.height,
    )

    if not ALLOW_UPSCALE:
        scale = min(scale, 1.0)

    target_width = max(
        1,
        round(image.width * scale),
    )
    target_height = max(
        1,
        round(image.height * scale),
    )

    if (target_width, target_height) != image.size:
        image = image.resize(
            (target_width, target_height),
            Image.Resampling.LANCZOS,
        )

    return image


def panel_position(panel_index: int) -> tuple[int, int]:
    """
    返回每张图所在的(row, column)。

    Trial-10默认放在第4行第2列，即居中。
    """
    if (
        panel_index == len(TRIAL_NUMBERS) - 1
        and CENTER_SINGLE_LAST_PANEL
    ):
        return N_ROWS - 1, 1

    return divmod(panel_index, N_COLUMNS)


def create_contact_sheet(
    target_name: str,
    trial_sources: list[tuple[int, Path]],
    output_path: Path,
) -> None:
    """
    创建一张 3列 × 4行 的总图。
    """
    canvas_width = (
        2 * OUTER_MARGIN
        + N_COLUMNS * PANEL_WIDTH
        + (N_COLUMNS - 1) * HORIZONTAL_GAP
    )

    canvas_height = (
        2 * OUTER_MARGIN
        + N_ROWS * PANEL_HEIGHT
        + (N_ROWS - 1) * VERTICAL_GAP
    )

    canvas = Image.new(
        "RGB",
        (canvas_width, canvas_height),
        BACKGROUND_COLOR,
    )

    for panel_index, (_trial_number, image_path) in enumerate(
        trial_sources
    ):
        row, column = panel_position(panel_index)

        cell_x = (
            OUTER_MARGIN
            + column * (PANEL_WIDTH + HORIZONTAL_GAP)
        )
        cell_y = (
            OUTER_MARGIN
            + row * (PANEL_HEIGHT + VERTICAL_GAP)
        )

        panel_image = prepare_panel_image(image_path)

        paste_x = (
            cell_x
            + (PANEL_WIDTH - panel_image.width) // 2
        )
        paste_y = (
            cell_y
            + (PANEL_HEIGHT - panel_image.height) // 2
        )

        canvas.paste(
            panel_image,
            (paste_x, paste_y),
        )
        panel_image.close()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    canvas.save(
        output_path,
        format="PNG",
        dpi=(OUTPUT_DPI, OUTPUT_DPI),
        optimize=True,
        compress_level=6,
    )

    if SAVE_PDF_COPY:
        canvas.save(
            output_path.with_suffix(".pdf"),
            format="PDF",
            resolution=float(OUTPUT_DPI),
        )

    canvas.close()

    print(
        f"[完成] {target_name}\n"
        f"       -> {output_path}"
    )


# ======================================================================
# 主程序
# ======================================================================

def main() -> int:
    print("=" * 104)
    print("10个Trial的Step5图片排版")
    print("样式：无Trial标题、无(a)-(j)编号、无子图外边框")
    print(f"根目录：{ROOT_DIR}")
    print("=" * 104)

    trial_folders = discover_trial_folders()

    sources_by_target: dict[
        str,
        list[tuple[int, Path]],
    ] = {
        target["key"]: []
        for target in TARGETS
    }

    manifest_rows: list[list[str | int]] = [[
        "Trial",
        "Trial_folder",
        "Step5_folder",
        "Image_group",
        "Search_folder",
        "Source_image",
    ]]

    errors: list[str] = []

    # 先完整检查全部10个Trial的30张图片
    for trial_number in TRIAL_NUMBERS:
        trial_folder = trial_folders[trial_number]

        try:
            step5_folder = find_step5_folder(trial_folder)
        except Exception as exc:
            errors.append(
                f"Trial-{trial_number}: Step5识别失败：{exc}"
            )
            continue

        print(
            f"Trial-{trial_number}: "
            f"{step5_folder.relative_to(ROOT_DIR)}"
        )

        # Axi主图
        try:
            axi_image = find_image_by_stem(
                step5_folder,
                MAIN_AXI_IMAGE_STEM,
                recursive=False,
            )
        except Exception as exc:
            errors.append(
                f"Trial-{trial_number}: "
                f"{MAIN_AXI_IMAGE_STEM}：{exc}"
            )
        else:
            sources_by_target["Axi"].append(
                (trial_number, axi_image)
            )
            manifest_rows.append([
                trial_number,
                str(trial_folder.relative_to(ROOT_DIR)),
                str(step5_folder.relative_to(ROOT_DIR)),
                "Axi",
                str(step5_folder.relative_to(ROOT_DIR)),
                str(axi_image.relative_to(ROOT_DIR)),
            ])

        # Bxixj 5% CO2
        try:
            bxixj_5_folder = find_bxixj_condition_folder(
                step5_folder,
                5,
            )
            bxixj_5_image = find_image_by_stem(
                bxixj_5_folder,
                BXIXJ_HEATMAP_STEM,
                recursive=False,
            )
        except Exception as exc:
            errors.append(
                f"Trial-{trial_number}: "
                f"Bxixj 5% CO2：{exc}"
            )
        else:
            sources_by_target["Bxixj_5pct_CO2"].append(
                (trial_number, bxixj_5_image)
            )
            manifest_rows.append([
                trial_number,
                str(trial_folder.relative_to(ROOT_DIR)),
                str(step5_folder.relative_to(ROOT_DIR)),
                "Bxixj 5% CO2",
                str(bxixj_5_folder.relative_to(ROOT_DIR)),
                str(bxixj_5_image.relative_to(ROOT_DIR)),
            ])

        # Bxixj 100% CO2
        try:
            bxixj_100_folder = find_bxixj_condition_folder(
                step5_folder,
                100,
            )
            bxixj_100_image = find_image_by_stem(
                bxixj_100_folder,
                BXIXJ_HEATMAP_STEM,
                recursive=False,
            )
        except Exception as exc:
            errors.append(
                f"Trial-{trial_number}: "
                f"Bxixj 100% CO2：{exc}"
            )
        else:
            sources_by_target["Bxixj_100pct_CO2"].append(
                (trial_number, bxixj_100_image)
            )
            manifest_rows.append([
                trial_number,
                str(trial_folder.relative_to(ROOT_DIR)),
                str(step5_folder.relative_to(ROOT_DIR)),
                "Bxixj 100% CO2",
                str(bxixj_100_folder.relative_to(ROOT_DIR)),
                str(bxixj_100_image.relative_to(ROOT_DIR)),
            ])

    if errors:
        print("\n" + "=" * 104)
        print("发现以下缺失或识别问题，因此尚未开始排版：")
        print("=" * 104)

        for index, error in enumerate(errors, start=1):
            print(f"{index}. {error}")

        raise RuntimeError(
            f"共发现 {len(errors)} 个问题。"
            "请处理后重新运行。"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path = OUTPUT_DIR / "source_manifest.csv"

    with manifest_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(
            file,
            lineterminator="\n",
        )
        writer.writerows(manifest_rows)

    # 分别生成三张10-Trial总图
    for target in TARGETS:
        target_sources = sources_by_target[target["key"]]

        if len(target_sources) != 10:
            raise RuntimeError(
                f'{target["display_name"]} 找到 '
                f"{len(target_sources)} 张，应当为10张。"
            )

        # 确保始终按Trial编号排列
        target_sources.sort(
            key=lambda item: item[0]
        )

        create_contact_sheet(
            target_name=target["display_name"],
            trial_sources=target_sources,
            output_path=(
                OUTPUT_DIR / target["output_name"]
            ),
        )

    print("-" * 104)
    print("全部三张10-Trial总图已生成。")
    print(f"输出目录：{OUTPUT_DIR}")
    print(f"源图片清单：{manifest_path}")
    print("=" * 104)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n用户手动中断了程序。")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\n[错误] {exc}")
        print("\n详细错误信息：")
        traceback.print_exc()
        raise SystemExit(1)
