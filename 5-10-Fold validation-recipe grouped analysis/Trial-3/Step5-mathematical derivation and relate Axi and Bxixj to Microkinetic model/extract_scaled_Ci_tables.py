# -*- coding: utf-8 -*-
"""
从归一化后的 Ci 数据中提取四个表格。

输入：
    modified_table_scaled*.csv
    Ci_0.05_stats_scaled*.csv
    Ci_1.00_stats_scaled*.csv

输出：
    5% CO2 1D.csv
    100% CO2 1D.csv
    5% CO2 2D coe.csv
    100% CO2 2D coe.csv

规则：
1. modified_table_scaled：
   - Feature_name + mean_Ci_0.05 + std_Ci_0.05 -> 5% CO2 1D.csv
   - Feature_name + mean_Ci_1.00 + std_Ci_1.00 -> 100% CO2 1D.csv
2. 两个 Ci_*_stats_scaled 文件：
   - 仅保留恰好由两个变量组成的二阶项；
   - 去掉 scale_factor，只输出 Feature_name、mean_Ci、std_Ci。
3. 数值按 10 位有效数字输出，与示例文件格式一致。
"""

from __future__ import annotations

import csv
import re
import traceback
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SIGNIFICANT_DIGITS = 10
OUTPUT_ENCODING = "utf-8-sig"

# 若同一输入有多个带时间戳/副本编号的版本：
# False = 自动选择修改时间最新的版本；True = 直接报错。
ERROR_IF_MULTIPLE_INPUTS = False

OUTPUT_NAMES = {
    "5d": "5% CO2 1D.csv",
    "100d": "100% CO2 1D.csv",
    "5_2d": "5% CO2 2D coe.csv",
    "100_2d": "100% CO2 2D coe.csv",
}


def find_input_csv(stem: str) -> Path:
    """查找 stem.csv、stem(1).csv 或其他 stem*.csv 版本。"""
    output_names = {name.casefold() for name in OUTPUT_NAMES.values()}
    candidates = [
        path
        for path in BASE_DIR.glob(f"{stem}*.csv")
        if path.is_file() and path.name.casefold() not in output_names
    ]

    if not candidates:
        raise FileNotFoundError(
            f'未在当前文件夹找到输入文件 "{stem}*.csv"：\n{BASE_DIR}'
        )

    candidates.sort(
        key=lambda path: (path.stat().st_mtime_ns, path.name.casefold()),
        reverse=True,
    )

    if len(candidates) > 1:
        names = "\n".join(f"  - {p.name}" for p in candidates)
        if ERROR_IF_MULTIPLE_INPUTS:
            raise RuntimeError(
                f'找到多个 "{stem}*.csv" 文件：\n{names}'
            )
        print(
            f'[提示] 找到多个 "{stem}*.csv" 文件：\n{names}\n'
            f"使用修改时间最新的文件：{candidates[0].name}\n"
        )

    return candidates[0]


def read_csv_flexibly(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """兼容 UTF-8 BOM、UTF-8 和 GB18030。"""
    last_decode_error: Exception | None = None

    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    raise ValueError(f"{path.name} 没有表头。")

                headers = [str(h).strip() for h in reader.fieldnames]
                if len(headers) != len(set(headers)):
                    raise ValueError(f"{path.name} 中存在重复列名。")

                rows: list[dict[str, str]] = []
                for row_number, raw_row in enumerate(reader, start=2):
                    if None in raw_row:
                        raise ValueError(
                            f"{path.name} 第 {row_number} 行的列数多于表头。"
                        )
                    rows.append({
                        str(key).strip(): "" if value is None else value.strip()
                        for key, value in raw_row.items()
                    })
                return headers, rows
        except UnicodeDecodeError as exc:
            last_decode_error = exc

    raise UnicodeError(
        f"无法使用 UTF-8 或 GB18030 解码 {path.name}。"
    ) from last_decode_error


def require_columns(headers: list[str], required: list[str], path: Path) -> None:
    missing = [column for column in required if column not in headers]
    if missing:
        raise KeyError(
            f"{path.name} 缺少列：{', '.join(missing)}"
        )


def format_number(raw: str, path: Path, column: str, row_number: int) -> str:
    """
    将数值按十进制 ROUND_HALF_UP 规则写为 10 位有效数字。

    使用 Decimal 可避免二进制浮点在刚好位于舍入中点时产生
    47363.70958/47363.70959 一类差异。
    """
    text = raw.strip()
    if text == "":
        return ""

    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(
            f'{path.name} 第 {row_number} 行的 "{column}" 不是数值：{raw!r}'
        ) from exc

    if value.is_nan():
        return "nan"
    if value.is_infinite():
        return "inf" if value > 0 else "-inf"
    if value == 0:
        return "0"

    # adjusted() 是最高有效位的十进制指数。
    quantize_exponent = value.copy_abs().adjusted() - SIGNIFICANT_DIGITS + 1
    quantum = Decimal(1).scaleb(quantize_exponent)

    # 提高上下文精度，确保较长原始小数也能安全 quantize。
    with localcontext() as context:
        context.prec = max(80, len(value.as_tuple().digits) + 20)
        rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)

    result = format(rounded, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if result in {"-0", "+0"} else result


def get_interaction_order(feature_name: str) -> int:
    """按 * 或 × 分割，返回特征阶数。"""
    feature_name = feature_name.strip()
    if not feature_name:
        raise ValueError("发现空白 Feature_name。")

    terms = [
        term.strip()
        for term in re.split(r"\s*(?:\*|×)\s*", feature_name)
    ]
    if any(not term for term in terms):
        raise ValueError(f"无法解析特征：{feature_name!r}")
    return len(terms)


def write_csv_atomic(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    """原子写入；目标文件在 Excel 中打开时给出明确错误。"""
    temp = path.with_name(f".{path.name}.tmp")
    with temp.open("w", encoding=OUTPUT_ENCODING, newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)

    try:
        temp.replace(path)
    except PermissionError as exc:
        temp.unlink(missing_ok=True)
        raise PermissionError(
            f"无法覆盖 {path.name}。请先在 Excel 中关闭该文件。"
        ) from exc


def extract_1d(summary_path: Path) -> tuple[Path, Path, int]:
    headers, rows = read_csv_flexibly(summary_path)

    columns_5 = ["Feature_name", "mean_Ci_0.05", "std_Ci_0.05"]
    columns_100 = ["Feature_name", "mean_Ci_1.00", "std_Ci_1.00"]
    require_columns(headers, columns_5, summary_path)
    require_columns(headers, columns_100, summary_path)

    rows_5: list[list[str]] = []
    rows_100: list[list[str]] = []

    for row_number, row in enumerate(rows, start=2):
        feature = row["Feature_name"].strip()
        if not feature:
            raise ValueError(
                f"{summary_path.name} 第 {row_number} 行 Feature_name 为空。"
            )

        rows_5.append([
            feature,
            format_number(row["mean_Ci_0.05"], summary_path, "mean_Ci_0.05", row_number),
            format_number(row["std_Ci_0.05"], summary_path, "std_Ci_0.05", row_number),
        ])
        rows_100.append([
            feature,
            format_number(row["mean_Ci_1.00"], summary_path, "mean_Ci_1.00", row_number),
            format_number(row["std_Ci_1.00"], summary_path, "std_Ci_1.00", row_number),
        ])

    output_5 = BASE_DIR / OUTPUT_NAMES["5d"]
    output_100 = BASE_DIR / OUTPUT_NAMES["100d"]
    write_csv_atomic(output_5, columns_5, rows_5)
    write_csv_atomic(output_100, columns_100, rows_100)
    return output_5, output_100, len(rows)


def extract_2d(source_path: Path, output_name: str) -> tuple[Path, int, int]:
    headers, rows = read_csv_flexibly(source_path)
    output_headers = ["Feature_name", "mean_Ci", "std_Ci"]
    require_columns(headers, output_headers, source_path)

    output_rows: list[list[str]] = []
    for row_number, row in enumerate(rows, start=2):
        feature = row["Feature_name"].strip()
        if get_interaction_order(feature) != 2:
            continue

        output_rows.append([
            feature,
            format_number(row["mean_Ci"], source_path, "mean_Ci", row_number),
            format_number(row["std_Ci"], source_path, "std_Ci", row_number),
        ])

    if not output_rows:
        raise ValueError(f"{source_path.name} 中没有找到二阶特征。")

    output_path = BASE_DIR / output_name
    write_csv_atomic(output_path, output_headers, output_rows)
    return output_path, len(rows), len(output_rows)


def main() -> int:
    print("=" * 86)
    print("提取归一化后的 5%/100% CO2 1D 和 2D 数据")
    print(f"当前文件夹：{BASE_DIR}")
    print("=" * 86)

    summary_path = find_input_csv("modified_table_scaled")
    ci_005_path = find_input_csv("Ci_0.05_stats_scaled")
    ci_100_path = find_input_csv("Ci_1.00_stats_scaled")

    print("使用输入文件：")
    print(f"  - {summary_path.name}")
    print(f"  - {ci_005_path.name}")
    print(f"  - {ci_100_path.name}")
    print("-" * 86)

    output_5_1d, output_100_1d, rows_1d = extract_1d(summary_path)
    output_5_2d, source_5_rows, rows_5_2d = extract_2d(
        ci_005_path, OUTPUT_NAMES["5_2d"]
    )
    output_100_2d, source_100_rows, rows_100_2d = extract_2d(
        ci_100_path, OUTPUT_NAMES["100_2d"]
    )

    print(f"[OK] {output_5_1d.name}：{rows_1d} 行")
    print(f"[OK] {output_100_1d.name}：{rows_1d} 行")
    print(
        f"[OK] {output_5_2d.name}：从 {source_5_rows} 行中提取 "
        f"{rows_5_2d} 个二阶项"
    )
    print(
        f"[OK] {output_100_2d.name}：从 {source_100_rows} 行中提取 "
        f"{rows_100_2d} 个二阶项"
    )

    if rows_5_2d != rows_100_2d:
        print("[警告] 5% 与 100% CO2 的二阶项数量不同。")

    print("=" * 86)
    print("全部提取完成。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n用户手动中断程序。")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\n[错误] {exc}")
        print("\n详细错误信息：")
        traceback.print_exc()
        raise SystemExit(1)
