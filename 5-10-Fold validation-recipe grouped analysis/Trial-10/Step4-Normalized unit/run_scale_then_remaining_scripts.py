# -*- coding: utf-8 -*-
"""
先执行当前文件夹中的 scale_Ci_statistics.py，成功后再依次执行其余分析脚本。

使用方法：
1. 将本脚本放到 scale_Ci_statistics.py 和其他分析脚本所在的同一文件夹；
2. 使用与原分析脚本相同的 PyCharm Python 解释器运行本脚本。

截图所示文件夹中，默认只执行名称以“Normalized unit-”开头的后续脚本，
从而避免误执行其他辅助 Python 文件。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ======================================================================
# 可修改设置
# ======================================================================

# 必须最先执行的脚本名称（不包含 .py）
FIRST_SCRIPT_STEM = "scale_Ci_statistics"

# True：某个后续脚本失败后立即停止。
# False：某个后续脚本失败后仍继续执行剩余脚本。
STOP_ON_ERROR = True

# True：只执行名称以“Normalized unit-”开头的其余脚本。
# False：执行当前文件夹中除本启动脚本、scale_Ci_statistics.py
#        和 __init__.py 以外的所有 .py 文件。
ONLY_RUN_NORMALIZED_UNIT_SCRIPTS = True
NORMALIZED_UNIT_PREFIX = "Normalized unit-"


# ======================================================================
# 路径和日志
# ======================================================================

BASE_DIR = Path(__file__).resolve().parent
THIS_SCRIPT = Path(__file__).resolve()
LOG_PATH = BASE_DIR / "run_scale_then_remaining_scripts.log"


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_log(message: str = "") -> None:
    """同时输出到 PyCharm 控制台和日志文件。"""
    print(message, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")


def natural_sort_key(path: Path) -> list[object]:
    """文件名自然排序，使 0.05Ci 位于 1.00Ci 之前。"""
    parts = re.split(r"(\d+(?:\.\d+)?)", path.name.casefold())
    key: list[object] = []

    for part in parts:
        if re.fullmatch(r"\d+(?:\.\d+)?", part):
            key.append(float(part))
        else:
            key.append(part)

    return key


def locate_first_script() -> Path:
    """大小写不敏感地查找 scale_Ci_statistics.py。"""
    exact_path = BASE_DIR / f"{FIRST_SCRIPT_STEM}.py"
    if exact_path.is_file():
        return exact_path

    expected_name = f"{FIRST_SCRIPT_STEM}.py".casefold()
    for candidate in BASE_DIR.iterdir():
        if candidate.is_file() and candidate.name.casefold() == expected_name:
            return candidate

    raise FileNotFoundError(
        f'未在当前文件夹找到 "{FIRST_SCRIPT_STEM}.py"：\n{BASE_DIR}'
    )


def discover_remaining_scripts(first_script: Path) -> list[Path]:
    """发现需要在归一化脚本之后运行的 Python 脚本。"""
    scripts: list[Path] = []

    for candidate in BASE_DIR.iterdir():
        if not candidate.is_file() or candidate.suffix.casefold() != ".py":
            continue

        resolved = candidate.resolve()
        if resolved in {THIS_SCRIPT, first_script.resolve()}:
            continue

        if candidate.name.casefold() == "__init__.py":
            continue

        if (
            ONLY_RUN_NORMALIZED_UNIT_SCRIPTS
            and not candidate.stem.casefold().startswith(
                NORMALIZED_UNIT_PREFIX.casefold()
            )
        ):
            continue

        scripts.append(candidate)

    return sorted(scripts, key=natural_sort_key)


def run_one_script(script_path: Path, stage_label: str) -> tuple[int, float]:
    """使用当前 PyCharm 解释器运行单个脚本。"""
    separator = "=" * 96

    write_log()
    write_log(separator)
    write_log(f"开始执行：{stage_label}")
    write_log(f"脚本名称：{script_path.name}")
    write_log(f"工作目录：{BASE_DIR}")
    write_log(f"Python 解释器：{sys.executable}")
    write_log(f"开始时间：{timestamp()}")
    write_log(separator)

    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"

    start_time = time.perf_counter()

    # 不使用 shell=True，因此文件名中的空格、连字符和小数点都可安全处理。
    completed = subprocess.run(
        [sys.executable, "-u", str(script_path)],
        cwd=str(BASE_DIR),
        env=environment,
        check=False,
    )

    elapsed_seconds = time.perf_counter() - start_time

    if completed.returncode == 0:
        write_log(
            f"[成功] {script_path.name}；结束时间：{timestamp()}；"
            f"耗时：{elapsed_seconds:.1f} 秒"
        )
    else:
        write_log(
            f"[失败] {script_path.name}；退出代码：{completed.returncode}；"
            f"结束时间：{timestamp()}；耗时：{elapsed_seconds:.1f} 秒"
        )

    return completed.returncode, elapsed_seconds


def print_summary(
    results: list[tuple[str, int, float]],
    remaining_not_run: int,
) -> None:
    """输出最终运行汇总。"""
    write_log()
    write_log("=" * 96)
    write_log("最终运行结果汇总")
    write_log("=" * 96)

    for script_name, return_code, elapsed in results:
        status = (
            "SUCCESS"
            if return_code == 0
            else f"FAILED（退出代码 {return_code}）"
        )
        write_log(
            f"{script_name:<66} {status:<26} {elapsed:.1f} 秒"
        )

    failure_count = sum(code != 0 for _, code, _ in results)

    if remaining_not_run:
        write_log()
        write_log(f"未执行的脚本数量：{remaining_not_run}")

    write_log()
    write_log(f"已执行：{len(results)}")
    write_log(f"失败：{failure_count}")
    write_log(f"未执行：{remaining_not_run}")
    write_log(f"日志文件：{LOG_PATH}")
    write_log(f"全部结束时间：{timestamp()}")

    if failure_count == 0 and remaining_not_run == 0:
        write_log("全部脚本均已成功执行。")
    else:
        write_log("本次批量运行未全部成功，请查看上方结果和日志。")


def main() -> int:
    LOG_PATH.write_text(
        "先运行 scale_Ci_statistics.py，随后运行其余分析脚本\n"
        f"启动时间：{timestamp()}\n"
        f"当前文件夹：{BASE_DIR}\n"
        f"Python 解释器：{sys.executable}\n",
        encoding="utf-8",
    )

    try:
        first_script = locate_first_script()
    except FileNotFoundError as exc:
        write_log()
        write_log(f"[无法开始] {exc}")
        return 2

    remaining_scripts = discover_remaining_scripts(first_script)

    write_log()
    write_log("计划执行顺序：")
    write_log(f"1. {first_script.name}")
    for index, script_path in enumerate(remaining_scripts, start=2):
        write_log(f"{index}. {script_path.name}")

    if not remaining_scripts:
        write_log()
        if ONLY_RUN_NORMALIZED_UNIT_SCRIPTS:
            write_log(
                '[无法开始] 未找到名称以 "Normalized unit-" 开头的后续脚本。'
            )
            write_log(
                "若希望执行所有其他 .py 文件，请把 "
                "ONLY_RUN_NORMALIZED_UNIT_SCRIPTS 改为 False。"
            )
        else:
            write_log("[无法开始] 未发现其他需要执行的 Python 脚本。")
        return 2

    results: list[tuple[str, int, float]] = []

    # 第一阶段：归一化脚本必须成功，否则停止。
    return_code, elapsed = run_one_script(
        first_script,
        "第一阶段：生成归一化数据",
    )
    results.append((first_script.name, return_code, elapsed))

    if return_code != 0:
        write_log()
        write_log(
            "scale_Ci_statistics.py 执行失败。"
            "由于后续脚本依赖归一化结果，本次已停止。"
        )
        print_summary(results, remaining_not_run=len(remaining_scripts))
        return 1

    # 第二阶段：按照自然文件名顺序执行后续脚本。
    for index, script_path in enumerate(remaining_scripts, start=1):
        return_code, elapsed = run_one_script(
            script_path,
            f"第二阶段：后续脚本 {index}/{len(remaining_scripts)}",
        )
        results.append((script_path.name, return_code, elapsed))

        if return_code != 0 and STOP_ON_ERROR:
            write_log()
            write_log("STOP_ON_ERROR=True，因此停止执行剩余脚本。")
            break

    total_planned = 1 + len(remaining_scripts)
    remaining_not_run = total_planned - len(results)
    print_summary(results, remaining_not_run)

    all_successful = (
        remaining_not_run == 0
        and all(code == 0 for _, code, _ in results)
    )
    return 0 if all_successful else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        write_log()
        write_log("用户手动中断了批量运行。")
        raise SystemExit(130)
