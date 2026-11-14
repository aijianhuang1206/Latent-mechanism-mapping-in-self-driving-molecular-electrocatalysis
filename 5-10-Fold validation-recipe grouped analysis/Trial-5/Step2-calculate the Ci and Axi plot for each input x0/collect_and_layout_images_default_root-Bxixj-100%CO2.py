#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math
import argparse
import re

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

TARGET_KEYWORD_DEFAULT = "second_order_Ci_1.00"
OUTPUT_DEFAULT = "second_order_Ci_1.00_layout.png"


def extract_leading_number(folder_name: str):
    """
    提取文件夹名前面的数字，例如：
    1-0.60, 0.0, ...  -> 1
    10-0.25, 0.05,... -> 10
    若没有匹配到，则返回一个很大的数，排到后面
    """
    m = re.match(r"^\s*(\d+)\s*[-_ ]?", folder_name)
    if m:
        return int(m.group(1))
    return 10**9


def sort_key_by_parent_number(p: Path, root_dir: Path):
    """
    按父文件夹编号排序，其次按父文件夹名和文件名排序
    """
    parent_name = p.parent.name
    parent_num = extract_leading_number(parent_name)
    rel_parent = str(p.parent.relative_to(root_dir)).lower()
    return (parent_num, rel_parent, p.stem.lower(), p.suffix.lower())


def find_target_images(root_dir: Path, keyword: str):
    """
    在 root_dir 下递归查找：
    文件扩展名属于图片，且文件名 stem 中包含 keyword
    然后按照父文件夹前缀数字排序
    """
    results = []
    for p in root_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            if keyword.lower() in p.stem.lower():
                results.append(p)

    results.sort(key=lambda x: sort_key_by_parent_number(x, root_dir))
    return results


def trim_white_border(img: Image.Image, white_threshold=245, keep_margin=12):
    """
    自动去除图片四周的大白边 / 近白边
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    gray = img.convert("L")
    mask = gray.point(lambda p: 255 if p < white_threshold else 0)
    bbox = mask.getbbox()

    if bbox is None:
        return img

    left, upper, right, lower = bbox

    left = max(0, left - keep_margin)
    upper = max(0, upper - keep_margin)
    right = min(img.width, right + keep_margin)
    lower = min(img.height, lower + keep_margin)

    return img.crop((left, upper, right, lower))


def fit_image(img: Image.Image, target_width: int):
    """
    按目标宽度等比缩放
    """
    w, h = img.size
    if w == 0 or h == 0:
        return img
    new_h = int(h * target_width / w)
    return img.resize((target_width, new_h), Image.LANCZOS)


def get_label_text(img_path: Path, root_dir: Path, label_mode: str):
    """
    label_mode:
      - none   : 不显示标签
      - parent : 显示父文件夹名
      - relpath: 显示相对路径
    """
    if label_mode == "none":
        return ""
    if label_mode == "parent":
        return img_path.parent.name
    if label_mode == "relpath":
        return str(img_path.relative_to(root_dir).parent)
    return ""


def get_font(font_size: int):
    possible_fonts = [
        "arial.ttf",
        "Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in possible_fonts:
        try:
            return ImageFont.truetype(fp, font_size)
        except Exception:
            pass
    return ImageFont.load_default()


def measure_multiline_text(draw, text, font):
    if not text:
        return 0, 0
    try:
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return draw.multiline_textsize(text, font=font, spacing=4)


def wrap_text(draw, text, font, max_width):
    if not text:
        return ""

    lines = []
    current = ""
    for ch in text:
        test = current + ch
        w, _ = measure_multiline_text(draw, test, font)
        if w <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return "\n".join(lines)


def create_contact_sheet(
    image_paths,
    root_dir: Path,
    output_path: Path,
    cols=3,
    thumb_width=700,
    padding=40,
    label_mode="parent",
    label_font_size=26,
    trim_white=False,
    white_threshold=245,
    keep_margin=12,
    bg_color=(255, 255, 255),
):
    if not image_paths:
        raise FileNotFoundError("未找到目标图片。")

    font = get_font(label_font_size)
    dummy = Image.new("RGB", (100, 100), bg_color)
    draw_dummy = ImageDraw.Draw(dummy)

    processed = []
    max_label_h = 0
    max_img_h = 0

    for p in image_paths:
        img = Image.open(p).convert("RGB")

        if trim_white:
            img = trim_white_border(
                img,
                white_threshold=white_threshold,
                keep_margin=keep_margin
            )

        img = fit_image(img, thumb_width)

        label = get_label_text(p, root_dir, label_mode)
        label = wrap_text(draw_dummy, label, font, thumb_width)

        _, label_h = measure_multiline_text(draw_dummy, label, font)
        if label:
            label_h += 10

        max_label_h = max(max_label_h, label_h)
        max_img_h = max(max_img_h, img.height)
        processed.append((p, img, label))

    rows = math.ceil(len(processed) / cols)

    cell_w = thumb_width
    cell_h = max_img_h + max_label_h

    canvas_w = padding + cols * (cell_w + padding)
    canvas_h = padding + rows * (cell_h + padding)

    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(canvas)

    for idx, (p, img, label) in enumerate(processed):
        r = idx // cols
        c = idx % cols

        x0 = padding + c * (cell_w + padding)
        y0 = padding + r * (cell_h + padding)

        img_x = x0 + (cell_w - img.width) // 2
        img_y = y0

        canvas.paste(img, (img_x, img_y))

        if label:
            text_w, _ = measure_multiline_text(draw, label, font)
            text_x = x0 + (cell_w - text_w) // 2
            text_y = y0 + max_img_h + 10
            draw.multiline_text(
                (text_x, text_y),
                label,
                font=font,
                fill=(0, 0, 0),
                spacing=4,
                align="center"
            )

    canvas.save(output_path, quality=95)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="递归读取当前脚本所在文件夹中的所有子文件夹，搜集指定关键字图片并自动排版。"
    )
    parser.add_argument(
        "--keyword",
        default=TARGET_KEYWORD_DEFAULT,
        help="目标图片文件名关键字（只要文件名中包含它即可）"
    )
    parser.add_argument(
        "-o", "--output",
        default=OUTPUT_DEFAULT,
        help="输出拼图文件名"
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=3,
        help="每行图片数，默认 3"
    )
    parser.add_argument(
        "--thumb-width",
        type=int,
        default=700,
        help="每张图缩放宽度，默认 700"
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=40,
        help="间距，默认 40"
    )
    parser.add_argument(
        "--label-mode",
        choices=["none", "parent", "relpath"],
        default="parent",
        help="标签模式：none / parent / relpath"
    )
    parser.add_argument(
        "--label-font-size",
        type=int,
        default=26,
        help="标签字体大小"
    )
    parser.add_argument(
        "--trim-white",
        action="store_true",
        help="自动裁掉四周大白边"
    )
    parser.add_argument(
        "--white-threshold",
        type=int,
        default=245,
        help="白边判定阈值，默认 245"
    )
    parser.add_argument(
        "--keep-margin",
        type=int,
        default=12,
        help="裁白边后保留的边距像素，默认 12"
    )

    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent
    output_path = root_dir / args.output

    print(f"[根目录] {root_dir}")
    print(f"[搜索关键字] {args.keyword}")

    image_paths = find_target_images(root_dir, args.keyword)

    if not image_paths:
        print(f"[未找到] 在目录 {root_dir} 及其子目录下，没有找到文件名中包含：{args.keyword} 的图片。")
        return

    print(f"[找到 {len(image_paths)} 张图片，排序如下]")
    for i, p in enumerate(image_paths, 1):
        print(f"{i:02d}. {p.parent.name} -> {p.name}")

    out = create_contact_sheet(
        image_paths=image_paths,
        root_dir=root_dir,
        output_path=output_path,
        cols=args.cols,
        thumb_width=args.thumb_width,
        padding=args.padding,
        label_mode=args.label_mode,
        label_font_size=args.label_font_size,
        trim_white=args.trim_white,
        white_threshold=args.white_threshold,
        keep_margin=args.keep_margin,
    )

    print(f"[完成] 拼图已保存到：{out}")


if __name__ == "__main__":
    main()
