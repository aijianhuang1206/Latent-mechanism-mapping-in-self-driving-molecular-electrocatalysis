# -*- coding: utf-8 -*-
"""
依次执行当前文件夹中的 9 个 Python 脚本。

默认执行顺序：
1. Calculate Mean and SD
2. Calculate Mean and SD-for 1.00Ci
3. Calculate Mean and SD-for 0.05Ci
4. Contribution-heat_map-0.05Ci-revision
5. Contribution-heat_map-1.00Ci-revision
6. Plot-Axi summary
7. collect_and_layout_images_default_root-Axi
8. collect_and_layout_images_default_root-Bxixj-5%CO2
9. collect_and_layout_images_default_root-Bxixj-100%CO2

请将本脚本放在上述 9 个脚本所在的同一文件夹中，并使用
与这些脚本相同的 PyCharm Python 解释器运行。
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ----------------------------------------------------------------------
# 运行顺序
# ----------------------------------------------------------------------
SCRIPT_STEMS = [
    # 第一阶段：先计算 Mean 和 SD
    "Calculate Mean and SD",
    "Calculate Mean and SD-for 1.00Ci",
    "Calculate Mean and SD-for 0.05Ci",

    # 第二阶段：根据计算结果生成分析图
    "Contribution-heat_map-0.05Ci-revision",
    "Contribution-heat_map-1.00Ci-revision",
    "Plot-Axi summary",

    # 第三阶段：最后收集并排版图片
    "collect_and_layout_images_default_root-Axi",
    "collect_and_layout_images_default_root-Bxixj-5%CO2",
    "collect_and_layout_images_default_root-Bxixj-100%CO2",
]


# True：某个脚本报错后立即停止，避免后面的脚本继续读取不完整结果。
# False：即使某个脚本报错，也继续执行后面的脚本。
STOP_ON_ERROR = True


# 当前启动脚本所在目录
BASE_DIR = Path(__file__).resolve().parent

# 运行日志文件
LOG_PATH = BASE_DIR / "run_all_9_scripts.log"


def locate_script(stem: str) -> Path:
    """
    根据不带扩展名的脚本名称查找文件。

    可识别：
    - filename.py
    - Windows 隐藏了 .py 扩展名时看到的 filename
    - 大小写存在轻微差异的文件名
    """
    direct_candidates = [
        BASE_DIR / f"{stem}.py",
        BASE_DIR / stem,
    ]

    for candidate in direct_candidates:
        if candidate.is_file():
            return candidate

    expected_names = {
        f"{stem}.py".casefold(),
        stem.casefold(),
    }

    for candidate in BASE_DIR.iterdir():
        if candidate.is_file() and candidate.name.casefold() in expected_names:
            return candidate

    raise FileNotFoundError(
        f'未在当前文件夹中找到脚本："{stem}.py"\n'
        f"当前文件夹：{BASE_DIR}"
    )


def write_log(message: str) -> None:
    """同时输出到 PyCharm 控制台和日志文件。"""
    print(message, flush=True)

    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")


def run_one_script(index: int, total: int, script_path: Path) -> int:
    """使用当前解释器运行一个脚本，并返回退出代码。"""
    separator = "=" * 86

    write_log("")
    write_log(separator)
    write_log(f"[{index}/{total}] 开始执行")
    write_log(f"脚本名称：{script_path.name}")
    write_log(f"开始时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    write_log(f"Python解释器：{sys.executable}")
    write_log(f"工作目录：{BASE_DIR}")
    write_log(separator)

    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"

    # 不使用 shell=True，因此文件名中的空格、连字符和 % 都可以安全处理。
    completed = subprocess.run(
        [sys.executable, "-u", str(script_path)],
        cwd=str(BASE_DIR),
        env=environment,
        check=False,
    )

    if completed.returncode == 0:
        write_log(
            f"[成功] {script_path.name} "
            f"完成时间：{datetime.now():%Y-%m-%d %H:%M:%S}"
        )
    else:
        write_log(
            f"[失败] {script_path.name}，"
            f"退出代码：{completed.returncode}，"
            f"结束时间：{datetime.now():%Y-%m-%d %H:%M:%S}"
        )

    return completed.returncode


def main() -> int:
    # 每次运行时重新建立日志文件。
    LOG_PATH.write_text(
        "9 个 Python 脚本批量运行日志\n"
        f"启动时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"启动目录：{BASE_DIR}\n",
        encoding="utf-8",
    )

    write_log("")
    write_log("准备依次执行以下脚本：")

    for index, stem in enumerate(SCRIPT_STEMS, start=1):
        write_log(f"{index}. {stem}.py")

    # 先检查所有文件是否存在，避免运行到一半才发现文件缺失。
    located_scripts: list[Path] = []
    missing_scripts: list[str] = []

    for stem in SCRIPT_STEMS:
        try:
            located_scripts.append(locate_script(stem))
        except FileNotFoundError:
            missing_scripts.append(f"{stem}.py")

    if missing_scripts:
        write_log("")
        write_log("[无法开始] 以下脚本未找到：")
        for name in missing_scripts:
            write_log(f"  - {name}")

        write_log("")
        write_log("请确认这些脚本与 run_all_9_scripts.py 位于同一文件夹，")
        write_log("并检查文件名是否与列表完全一致。")
        return 2

    results: list[tuple[str, int]] = []

    for index, script_path in enumerate(located_scripts, start=1):
        return_code = run_one_script(
            index=index,
            total=len(located_scripts),
            script_path=script_path,
        )
        results.append((script_path.name, return_code))

        if return_code != 0 and STOP_ON_ERROR:
            write_log("")
            write_log(
                "由于 STOP_ON_ERROR=True，已停止执行后续脚本，"
                "以避免使用不完整的中间结果。"
            )
            break

    write_log("")
    write_log("=" * 86)
    write_log("运行结果汇总")
    write_log("=" * 86)

    failure_count = 0

    for name, return_code in results:
        if return_code == 0:
            status = "SUCCESS"
        else:
            status = f"FAILED，退出代码 {return_code}"
            failure_count += 1

        write_log(f"{name:<62} {status}")

    not_run_count = len(located_scripts) - len(results)

    if not_run_count:
        write_log("")
        write_log(f"由于前面的错误，尚未执行的脚本数量：{not_run_count}")

    write_log("")
    write_log(f"日志文件：{LOG_PATH}")

    if failure_count == 0 and not_run_count == 0:
        write_log("全部 9 个脚本均已成功执行。")
        return 0

    write_log(
        f"本次运行存在 {failure_count} 个失败脚本，"
        f"{not_run_count} 个脚本未执行。"
    )
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        write_log("")
        write_log("用户手动中断了批量运行。")
        raise SystemExit(130)
