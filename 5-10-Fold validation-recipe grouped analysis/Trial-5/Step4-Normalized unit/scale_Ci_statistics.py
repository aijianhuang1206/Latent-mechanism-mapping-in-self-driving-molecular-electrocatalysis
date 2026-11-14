# -*- coding: utf-8 -*-
"""
对 Ci 统计数据按照变量量纲系数进行缩放/归一化。

使用方法
--------
1. 将本脚本放到以下三个原始 CSV 文件所在的同一文件夹：

   - Ci_0.05_stats.csv
     或带时间戳的文件，例如 Ci_0.05_stats(20260831-143834).csv
   - Ci_1.00_stats.csv
   - summary_Ci_stats.csv

2. 在 PyCharm 中使用原分析程序相同的 Python 解释器运行本脚本。

3. 脚本会在当前文件夹输出：

   - Ci_0.05_stats_scaled.csv
   - Ci_1.00_stats_scaled.csv
   - modified_table_scaled.csv

缩放系数
--------
Phenol                                              × 1
TFE                                                 × 1
1,1,1,3,3,3-Hexafluoro-2-methyl-2-propanol         × 1
TBAPF6                                              × 10
CsPF6                                               × 10
TMAPF6                                              × 10
Perylene                                            × 800
CO2                                                 × 4.35

对于二阶及更高阶特征，缩放系数为各组成变量系数的乘积，并且
重复出现的变量会重复相乘。例如：

CO2*CO2                 = 4.35 × 4.35 = 18.9225
TBAPF6*CO2              = 10 × 4.35 = 43.5
Perylene*CO2            = 800 × 4.35 = 3480
Perylene*Perylene       = 800 × 800 = 640000

本脚本默认复现用户提供的归一化示例文件结构：

- Ci_0.05_stats_scaled.csv 和 Ci_1.00_stats_scaled.csv：
  只保留二阶及更高阶特征，并增加 scale_factor 列；
- modified_table_scaled.csv：
  保留 summary_Ci_stats.csv 的全部一阶和二阶特征，并在第二列增加
  multiplier 列。

本脚本仅使用 Python 标准库，无需额外安装 pandas、numpy 等软件包。
"""

from __future__ import print_function

import csv
import io
import os
import re
import sys
import traceback
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


# ----------------------------------------------------------------------
# 可修改设置
# ----------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# 用户提供的两个 scaled Ci 示例文件均删除了 8 个一阶特征。
# 若以后希望在 Ci_*_stats_scaled.csv 中也保留一阶特征，改为 False。
REMOVE_FIRST_ORDER_FROM_CI_OUTPUTS = True

# 当同一类输入存在多个带时间戳版本时：
# False：自动选择“修改时间最新”的文件；
# True：停止并要求手动清理重复文件。
ERROR_IF_MULTIPLE_INPUTS = False

# 使用 utf-8-sig，使输出 CSV 在 Windows Excel 中可直接正常打开。
OUTPUT_ENCODING = "utf-8-sig"

# 提高 Decimal 运算精度，避免高阶系数相乘造成额外舍入误差。
getcontext().prec = 80

HFIP_FULL_NAME = "1,1,1,3,3,3-Hexafluoro-2-methyl-2-propanol"

BASE_FACTORS: Dict[str, Decimal] = {
    "Phenol": Decimal("1"),
    "TFE": Decimal("1"),
    HFIP_FULL_NAME: Decimal("1"),
    "TBAPF6": Decimal("10"),
    "CsPF6": Decimal("10"),
    "TMAPF6": Decimal("10"),
    "Perylene": Decimal("800"),
    "CO2": Decimal("4.35"),
}

# 可识别的备用写法。输出文件中的 Feature_name 不会被重命名。
FEATURE_ALIASES: Dict[str, str] = {
    "HFIP": HFIP_FULL_NAME,
    "CO₂": "CO2",
}

CI_FILE_CONFIGS: Sequence[Tuple[str, str]] = (
    ("Ci_0.05_stats", "Ci_0.05_stats_scaled.csv"),
    ("Ci_1.00_stats", "Ci_1.00_stats_scaled.csv"),
)

SUMMARY_INPUT_STEM = "summary_Ci_stats"
SUMMARY_OUTPUT_NAME = "modified_table_scaled.csv"


# ----------------------------------------------------------------------
# CSV 读取、查找和写入
# ----------------------------------------------------------------------

def find_input_csv(stem: str) -> Path:
    """
    在当前文件夹中寻找原始 CSV。

    支持：
      Ci_0.05_stats.csv
      Ci_0.05_stats(20260831-143834).csv

    名称中包含 _scaled 的文件会被排除，避免把输出再次作为输入。
    """
    candidates = [
        path
        for path in BASE_DIR.glob(stem + "*.csv")
        if path.is_file() and "_scaled" not in path.stem.casefold()
    ]

    if not candidates:
        raise FileNotFoundError(
            '未在当前文件夹找到输入文件 "{}*.csv"：\n{}'.format(
                stem, BASE_DIR
            )
        )

    candidates.sort(
        key=lambda path: (path.stat().st_mtime_ns, path.name.casefold()),
        reverse=True,
    )

    if len(candidates) > 1:
        candidate_text = "\n".join(
            "  - " + path.name for path in candidates
        )

        if ERROR_IF_MULTIPLE_INPUTS:
            raise RuntimeError(
                '找到多个与 "{}*.csv" 匹配的原始文件：\n{}\n'
                "请删除或重命名多余版本，或者将 "
                "ERROR_IF_MULTIPLE_INPUTS 改为 False。".format(
                    stem, candidate_text
                )
            )

        print(
            '[提示] 找到多个与 "{}*.csv" 匹配的文件：\n{}\n'
            "将使用修改时间最新的文件：{}\n".format(
                stem, candidate_text, candidates[0].name
            )
        )

    return candidates[0]


def decode_csv_text(path: Path) -> str:
    """兼容 UTF-8、UTF-8 BOM 和常见中文 Windows 编码。"""
    errors: List[str] = []

    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            errors.append("{}: {}".format(encoding, exc))

    raise UnicodeError(
        "无法读取 {}。已尝试 UTF-8、UTF-8 BOM 和 GB18030。\n{}".format(
            path.name, "\n".join(errors)
        )
    )


def read_csv_table(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """以字典行形式读取 CSV，并检查列数是否一致。"""
    text = decode_csv_text(path)
    reader = csv.DictReader(io.StringIO(text, newline=""))

    if not reader.fieldnames:
        raise ValueError("{} 没有表头。".format(path.name))

    fieldnames = list(reader.fieldnames)
    rows: List[Dict[str, str]] = []

    for csv_row_number, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(
                "{} 第 {} 行的字段数量超过表头列数。".format(
                    path.name, csv_row_number
                )
            )

        normalized_row = {
            column: ("" if value is None else value)
            for column, value in row.items()
        }
        rows.append(normalized_row)

    return fieldnames, rows


def write_csv_atomically(
    output_path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Dict[str, str]],
) -> None:
    """先写入临时文件，成功后再替换正式输出，避免生成半截文件。"""
    temporary_path = output_path.with_name("." + output_path.name + ".tmp")

    try:
        with temporary_path.open(
            "w", encoding=OUTPUT_ENCODING, newline=""
        ) as file_handle:
            writer = csv.DictWriter(
                file_handle,
                fieldnames=list(fieldnames),
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

        os.replace(str(temporary_path), str(output_path))

    except PermissionError as exc:
        try:
            temporary_path.unlink()
        except OSError:
            pass

        raise PermissionError(
            "无法写入 {}。请先关闭 Excel 中已经打开的同名文件，"
            "然后重新运行脚本。".format(output_path.name)
        ) from exc


# ----------------------------------------------------------------------
# 特征解析和缩放系数计算
# ----------------------------------------------------------------------

def split_feature_terms(feature_name: str) -> List[str]:
    """按 * 或 × 拆分特征表达式，并保留重复变量。"""
    text = str(feature_name).strip()

    if not text:
        raise ValueError("发现空的 Feature_name。")

    terms = [
        term.strip()
        for term in re.split(r"\s*(?:\*|×)\s*", text)
    ]

    if not terms or any(not term for term in terms):
        raise ValueError("无效的 Feature_name：{!r}".format(feature_name))

    return terms


def get_feature_multiplier(feature_name: str) -> Tuple[Decimal, int]:
    """返回（缩放系数乘积，特征阶数）。"""
    terms = split_feature_terms(feature_name)
    multiplier = Decimal("1")
    unknown_terms: List[str] = []

    for original_term in terms:
        recognized_term = FEATURE_ALIASES.get(original_term, original_term)

        if recognized_term not in BASE_FACTORS:
            unknown_terms.append(original_term)
            continue

        multiplier *= BASE_FACTORS[recognized_term]

    if unknown_terms:
        raise ValueError(
            "Feature_name={!r} 中存在无法识别的变量：{}。\n"
            "目前可识别变量为：{}".format(
                feature_name,
                ", ".join(repr(term) for term in unknown_terms),
                ", ".join(BASE_FACTORS.keys()),
            )
        )

    return multiplier, len(terms)


def decimal_to_plain_string(value: Decimal) -> str:
    """
    将 Decimal 写成干净的十进制文本：
    - 不产生 18.922499999999996 一类浮点误差；
    - 删除无意义的末尾 0；
    - 大数也保持完整数值。
    """
    if value.is_nan() or value.is_infinite():
        return str(value)

    if value == 0:
        return "0"

    text = format(value, "f")

    if "." in text:
        text = text.rstrip("0").rstrip(".")

    if text == "-0":
        return "0"

    return text


def factor_to_string(multiplier: Decimal, force_decimal_for_integer: bool) -> str:
    """格式化 scale_factor 或 multiplier 列。"""
    text = decimal_to_plain_string(multiplier)

    if force_decimal_for_integer and "." not in text:
        text += ".0"

    return text


def scale_numeric_text(
    raw_value: str,
    multiplier: Decimal,
    source_name: str,
    column_name: str,
    csv_row_number: int,
) -> str:
    """把 CSV 数字文本乘以精确系数。空单元格保持为空。"""
    text = str(raw_value).strip()

    if text == "":
        return ""

    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(
            "{} 第 {} 行、列 {!r} 的值 {!r} 不是有效数字。".format(
                source_name, csv_row_number, column_name, raw_value
            )
        ) from exc

    return decimal_to_plain_string(value * multiplier)


def require_columns(
    fieldnames: Sequence[str],
    required_columns: Sequence[str],
    source_path: Path,
) -> None:
    missing = [
        column for column in required_columns if column not in fieldnames
    ]

    if missing:
        raise KeyError(
            "{} 缺少必要列：{}".format(
                source_path.name, ", ".join(missing)
            )
        )


# ----------------------------------------------------------------------
# 三个文件的处理逻辑
# ----------------------------------------------------------------------

def scale_ci_stats_file(
    input_path: Path,
    output_path: Path,
) -> Tuple[int, int]:
    """
    处理 Ci_0.05_stats 或 Ci_1.00_stats。

    输出列：
      Feature_name, mean_Ci, std_Ci, scale_factor
    """
    fieldnames, source_rows = read_csv_table(input_path)
    require_columns(
        fieldnames,
        ("Feature_name", "mean_Ci", "std_Ci"),
        input_path,
    )

    output_rows: List[Dict[str, str]] = []

    for csv_row_number, row in enumerate(source_rows, start=2):
        feature_name = row["Feature_name"].strip()

        try:
            multiplier, interaction_order = get_feature_multiplier(
                feature_name
            )
        except Exception as exc:
            raise ValueError(
                "{} 第 {} 行：{}".format(
                    input_path.name, csv_row_number, exc
                )
            ) from exc

        if (
            REMOVE_FIRST_ORDER_FROM_CI_OUTPUTS
            and interaction_order < 2
        ):
            continue

        output_rows.append(
            {
                "Feature_name": feature_name,
                "mean_Ci": scale_numeric_text(
                    row["mean_Ci"],
                    multiplier,
                    input_path.name,
                    "mean_Ci",
                    csv_row_number,
                ),
                "std_Ci": scale_numeric_text(
                    row["std_Ci"],
                    multiplier,
                    input_path.name,
                    "std_Ci",
                    csv_row_number,
                ),
                "scale_factor": factor_to_string(
                    multiplier,
                    force_decimal_for_integer=False,
                ),
            }
        )

    output_fieldnames = (
        "Feature_name",
        "mean_Ci",
        "std_Ci",
        "scale_factor",
    )

    write_csv_atomically(output_path, output_fieldnames, output_rows)

    return len(source_rows), len(output_rows)


def scale_summary_file(
    input_path: Path,
    output_path: Path,
) -> Tuple[int, int]:
    """
    处理 summary_Ci_stats.csv。

    除 Feature_name 外，所有 mean_Ci_* 和 std_Ci_* 数值列都乘以
    当前行特征对应的 multiplier；全部特征行均保留。
    """
    fieldnames, source_rows = read_csv_table(input_path)
    require_columns(fieldnames, ("Feature_name",), input_path)

    numeric_columns = [
        column
        for column in fieldnames
        if column not in ("Feature_name", "multiplier", "scale_factor")
    ]

    if not numeric_columns:
        raise ValueError(
            "{} 中没有可缩放的 Ci 数值列。".format(input_path.name)
        )

    output_fieldnames = ["Feature_name", "multiplier"] + numeric_columns
    output_rows: List[Dict[str, str]] = []

    for csv_row_number, row in enumerate(source_rows, start=2):
        feature_name = row["Feature_name"].strip()

        try:
            multiplier, _interaction_order = get_feature_multiplier(
                feature_name
            )
        except Exception as exc:
            raise ValueError(
                "{} 第 {} 行：{}".format(
                    input_path.name, csv_row_number, exc
                )
            ) from exc

        output_row: Dict[str, str] = {
            "Feature_name": feature_name,
            "multiplier": factor_to_string(
                multiplier,
                force_decimal_for_integer=True,
            ),
        }

        for column_name in numeric_columns:
            output_row[column_name] = scale_numeric_text(
                row[column_name],
                multiplier,
                input_path.name,
                column_name,
                csv_row_number,
            )

        output_rows.append(output_row)

    write_csv_atomically(output_path, output_fieldnames, output_rows)

    return len(output_rows), len(numeric_columns)


# ----------------------------------------------------------------------
# 主程序
# ----------------------------------------------------------------------

def main() -> int:
    print("=" * 88)
    print("Ci 数据缩放/归一化")
    print("工作文件夹：{}".format(BASE_DIR))
    print("=" * 88)

    created_outputs: List[Path] = []

    for input_stem, output_name in CI_FILE_CONFIGS:
        input_path = find_input_csv(input_stem)
        output_path = BASE_DIR / output_name

        source_count, output_count = scale_ci_stats_file(
            input_path, output_path
        )
        created_outputs.append(output_path)

        print("[成功] {}".format(input_path.name))
        print("       -> {}".format(output_path.name))
        print(
            "       原始行数：{}；输出行数：{}".format(
                source_count, output_count
            )
        )

    summary_input_path = find_input_csv(SUMMARY_INPUT_STEM)
    summary_output_path = BASE_DIR / SUMMARY_OUTPUT_NAME

    summary_rows, numeric_column_count = scale_summary_file(
        summary_input_path, summary_output_path
    )
    created_outputs.append(summary_output_path)

    print("[成功] {}".format(summary_input_path.name))
    print("       -> {}".format(summary_output_path.name))
    print(
        "       保留行数：{}；缩放数值列数：{}".format(
            summary_rows, numeric_column_count
        )
    )

    co2_squared, _ = get_feature_multiplier("CO2*CO2")
    perylene_co2, _ = get_feature_multiplier("Perylene*CO2")

    print("-" * 88)
    print(
        "校验：CO2*CO2 的系数 = {}".format(
            decimal_to_plain_string(co2_squared)
        )
    )
    print(
        "校验：Perylene*CO2 的系数 = {}".format(
            decimal_to_plain_string(perylene_co2)
        )
    )
    print("已生成：")
    for output_path in created_outputs:
        print("  - {}".format(output_path.name))
    print("=" * 88)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n用户手动中断了运行。")
        raise SystemExit(130)
    except Exception as exc:
        print("\n[错误] {}".format(exc))
        print("\n详细错误信息：")
        traceback.print_exc()
        raise SystemExit(1)
