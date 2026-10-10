# -*- coding: utf-8 -*-
"""
将 Trial-1 至 Trial-10 中 Step2 文件夹内的三类图片分别排版成三张总图（简洁版）。

与上一版相比，本脚本默认：
1. 去掉每张子图外侧边框；
2. 去掉每张子图上方的 Trial 标题；
3. 去掉 (a)(b)(c) 等编号；
4. 保持 3 列排版，前 3 行各 3 张，第 4 行 1 张（默认居中）。

目录结构示例：

Fold validation
├─ Trial-1
│  └─ Step2-calculate the Ci and Axi plot for each input x0
│     ├─ interaction_features_vs_co2_stats_no_CO2xCO2.png
│     ├─ second_order_Ci_0.05.png
│     └─ second_order_Ci_1.00.png
├─ Trial-2
├─ ...
├─ Trial-10
└─ layout_10_trials_step2_images_clean.py   ← 将本脚本放在这里

输出目录：
    10_Trials_comparison_layouts_clean

输出图片：
    10_trials_interaction_features_vs_co2_stats_no_CO2xCO2_layout_clean.png
    10_trials_second_order_Ci_0.05_layout_clean.png
    10_trials_second_order_Ci_1.00_layout_clean.png

依赖：
    Pillow
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
OUTPUT_DIR = ROOT_DIR / "10_Trials_comparison_layouts_clean"

TRIAL_NUMBERS = list(range(1, 11))

TARGET_IMAGES = [
    {
        "source_stem": "interaction_features_vs_co2_stats_no_CO2xCO2",
        "output_name": (
            "10_trials_"
            "interaction_features_vs_co2_stats_no_CO2xCO2_layout_clean.png"
        ),
    },
    {
        "source_stem": "second_order_Ci_0.05",
        "output_name": "10_trials_second_order_Ci_0.05_layout_clean.png",
    },
    {
        "source_stem": "second_order_Ci_1.00",
        "output_name": "10_trials_second_order_Ci_1.00_layout_clean.png",
    },
]

# 3列 × 4行，前三行各3张，最后一行1张
N_COLUMNS = 3
N_ROWS = 4

# 每个子图区域大小
PANEL_WIDTH = 1500
PANEL_HEIGHT = 1050

# 页面和子图间距
OUTER_MARGIN = 40
HORIZONTAL_GAP = 35
VERTICAL_GAP = 45

# 简洁版设置：无标题、无编号、无边框
SHOW_TRIAL_LABELS = False
SHOW_PANEL_LETTERS = False
DRAW_PANEL_BORDER = False

# Trial-10 最后一行居中
CENTER_SINGLE_LAST_PANEL = True

# 自动裁去外围大面积白边
AUTO_CROP_WHITE_MARGIN = True
WHITE_THRESHOLD = 248
CROP_PADDING = 12

BACKGROUND_COLOR = (255, 255, 255)
OUTPUT_DPI = 300

# 优先读取栅格图像
RASTER_EXTENSIONS = [
    ".png",
    ".tif",
    ".tiff",
    ".jpg",
    ".jpeg",
    ".bmp",
]


# ======================================================================
# 路径发现
# ======================================================================

def discover_trial_folders() -> dict[int, Path]:
    trial_pattern = re.compile(
        r"^trial[\s_-]*(\d+)(?:\s.*)?$",
        flags=re.IGNORECASE,
    )

    discovered: dict[int, Path] = {}

    for candidate in ROOT_DIR.iterdir():
        if not candidate.is_dir():
            continue

        match = trial_pattern.match(candidate.name.strip())
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

    missing = [n for n in TRIAL_NUMBERS if n not in discovered]
    if missing:
        raise FileNotFoundError(
            "以下 Trial 文件夹未找到："
            + ", ".join(f"Trial-{n}" for n in missing)
        )

    return discovered


def is_step2_folder_name(folder_name: str) -> bool:
    return re.match(
        r"^step[\s_-]*2(?:\D|$)",
        folder_name.strip(),
        flags=re.IGNORECASE,
    ) is not None


def count_target_images_in_folder(folder: Path) -> int:
    found_count = 0
    for target in TARGET_IMAGES:
        try:
            find_image_by_stem(folder, target["source_stem"], report_multiple=False)
        except FileNotFoundError:
            continue
        else:
            found_count += 1
    return found_count


def find_step2_folder(trial_folder: Path) -> Path:
    direct_candidates = [
        path for path in trial_folder.iterdir()
        if path.is_dir() and is_step2_folder_name(path.name)
    ]

    candidates = direct_candidates
    if not candidates:
        candidates = [
            path for path in trial_folder.rglob("*")
            if path.is_dir() and is_step2_folder_name(path.name)
        ]

    if not candidates:
        raise FileNotFoundError(f"{trial_folder.name} 中没有找到 Step2 文件夹。")

    if len(candidates) == 1:
        return candidates[0]

    scored = [(count_target_images_in_folder(folder), folder) for folder in candidates]
    scored.sort(
        key=lambda item: (
            item[0],
            -len(item[1].relative_to(trial_folder).parts),
            item[1].name.casefold(),
        ),
        reverse=True,
    )

    best_score = scored[0][0]
    best_candidates = [folder for score, folder in scored if score == best_score]

    if best_score == 0 or len(best_candidates) != 1:
        raise RuntimeError(
            f"{trial_folder.name} 中存在多个无法唯一判定的 Step2 文件夹。"
        )

    return best_candidates[0]


def find_image_by_stem(search_folder: Path, expected_stem: str, *, report_multiple: bool = True) -> Path:
    expected_folded = expected_stem.casefold()
    extension_priority = {
        extension: index for index, extension in enumerate(RASTER_EXTENSIONS)
    }

    candidates: list[Path] = []

    for path in search_folder.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.casefold() not in extension_priority:
            continue
        if path.stem.casefold() != expected_folded:
            continue
        candidates.append(path)

    if not candidates:
        svg_candidates = [
            path for path in search_folder.rglob("*.svg")
            if path.stem.casefold() == expected_folded
        ]
        if svg_candidates:
            raise FileNotFoundError(
                f'找到 "{expected_stem}.svg"，但没有找到 PNG/JPG/TIFF 版本：\n'
                f"{svg_candidates[0]}"
            )
        raise FileNotFoundError(
            f'未找到图片 "{expected_stem}.png"：\n{search_folder}'
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
        print(f'[提示] "{expected_stem}" 找到多个版本，将使用：{candidates[0]}')

    return candidates[0]


# ======================================================================
# 图片处理
# ======================================================================

def flatten_to_white(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        white.alpha_composite(rgba)
        return white.convert("RGB")

    return image.convert("RGB")


def crop_white_margin(image: Image.Image) -> Image.Image:
    if not AUTO_CROP_WHITE_MARGIN:
        return image

    gray = ImageOps.grayscale(image)
    mask = gray.point(lambda pixel: 255 if pixel < WHITE_THRESHOLD else 0)
    bbox = mask.getbbox()

    if bbox is None:
        return image

    left, top, right, bottom = bbox
    left = max(0, left - CROP_PADDING)
    top = max(0, top - CROP_PADDING)
    right = min(image.width, right + CROP_PADDING)
    bottom = min(image.height, bottom + CROP_PADDING)

    return image.crop((left, top, right, bottom))


def prepare_panel_image(image_path: Path) -> Image.Image:
    with Image.open(image_path) as source:
        source.load()
        image = flatten_to_white(source)

    image = crop_white_margin(image)

    scale = min(
        PANEL_WIDTH / image.width,
        PANEL_HEIGHT / image.height,
        1.0,
    )

    target_width = max(1, round(image.width * scale))
    target_height = max(1, round(image.height * scale))

    if (target_width, target_height) != image.size:
        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    return image


def panel_position(panel_index: int) -> tuple[int, int]:
    if panel_index == len(TRIAL_NUMBERS) - 1 and CENTER_SINGLE_LAST_PANEL:
        return N_ROWS - 1, 1
    return divmod(panel_index, N_COLUMNS)


def create_contact_sheet(
    target_stem: str,
    trial_sources: list[tuple[int, Path]],
    output_path: Path,
) -> None:
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

    canvas = Image.new("RGB", (canvas_width, canvas_height), BACKGROUND_COLOR)

    for panel_index, (_trial_number, image_path) in enumerate(trial_sources):
        row, column = panel_position(panel_index)

        cell_x = OUTER_MARGIN + column * (PANEL_WIDTH + HORIZONTAL_GAP)
        cell_y = OUTER_MARGIN + row * (PANEL_HEIGHT + VERTICAL_GAP)

        panel_image = prepare_panel_image(image_path)

        paste_x = cell_x + (PANEL_WIDTH - panel_image.width) // 2
        paste_y = cell_y + (PANEL_HEIGHT - panel_image.height) // 2

        canvas.paste(panel_image, (paste_x, paste_y))
        panel_image.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(
        output_path,
        format="PNG",
        dpi=(OUTPUT_DPI, OUTPUT_DPI),
        optimize=True,
        compress_level=6,
    )
    canvas.close()

    print(f"[完成] {target_stem}\n       -> {output_path}")


# ======================================================================
# 主程序
# ======================================================================

def main() -> int:
    print("=" * 100)
    print("10个Trial的Step2图片排版（简洁版：无边框、无标题、无编号）")
    print(f"根目录：{ROOT_DIR}")
    print("=" * 100)

    trial_folders = discover_trial_folders()

    manifest_rows: list[list[str | int]] = [
        ["Trial", "Trial_folder", "Step2_folder", "Image_type", "Source_image"]
    ]

    sources_by_target: dict[str, list[tuple[int, Path]]] = {
        target["source_stem"]: []
        for target in TARGET_IMAGES
    }

    for trial_number in TRIAL_NUMBERS:
        trial_folder = trial_folders[trial_number]
        step2_folder = find_step2_folder(trial_folder)

        print(f"Trial-{trial_number}: {step2_folder.relative_to(ROOT_DIR)}")

        for target in TARGET_IMAGES:
            target_stem = target["source_stem"]
            image_path = find_image_by_stem(step2_folder, target_stem)

            sources_by_target[target_stem].append((trial_number, image_path))

            manifest_rows.append([
                trial_number,
                str(trial_folder.relative_to(ROOT_DIR)),
                str(step2_folder.relative_to(ROOT_DIR)),
                target_stem,
                str(image_path.relative_to(ROOT_DIR)),
            ])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = OUTPUT_DIR / "source_manifest.csv"
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerows(manifest_rows)

    for target in TARGET_IMAGES:
        target_stem = target["source_stem"]
        trial_sources = sources_by_target[target_stem]

        if len(trial_sources) != 10:
            raise RuntimeError(f"{target_stem} 只找到 {len(trial_sources)} 张，应为10张。")

        output_path = OUTPUT_DIR / target["output_name"]

        create_contact_sheet(
            target_stem=target_stem,
            trial_sources=trial_sources,
            output_path=output_path,
        )

    print("-" * 100)
    print("全部三张简洁版排版图已经生成。")
    print(f"输出目录：{OUTPUT_DIR}")
    print(f"源文件清单：{manifest_path}")
    print("=" * 100)

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
