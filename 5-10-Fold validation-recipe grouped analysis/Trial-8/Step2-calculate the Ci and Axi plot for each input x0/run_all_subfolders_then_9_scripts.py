# -*- coding: utf-8 -*-
"""
主控脚本：先运行当前文件夹下各编号子文件夹中的 run_all_5_scripts.py，
全部成功后，再运行当前文件夹中的 run_all_9_scripts.py。

推荐目录结构：

当前文件夹
├─ 1-......
│  └─ run_all_5_scripts.py
├─ 2-......
│  └─ run_all_5_scripts.py
├─ ...
├─ 20-......
│  └─ run_all_5_scripts.py
├─ run_all_9_scripts.py
└─ run_all_subfolders_then_9_scripts.py   ← 本脚本

请使用与原分析脚本相同的 PyCharm Python 解释器运行本脚本。
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

# 子文件夹中的启动脚本
CHILD_LAUNCHER_STEM = "run_all_5_scripts"

# 当前根文件夹中的最终启动脚本
ROOT_LAUNCHER_STEM = "run_all_9_scripts"

# True：
#   只处理名称以数字开头的一级子文件夹，例如：
#   1-0.60, 0.0, ...
#   20-0.35, 0.65, ...
#
# False：
#   处理当前文件夹下所有包含 run_all_5_scripts.py 的一级子文件夹。
ONLY_NUMBERED_SUBFOLDERS = True

# True：任一子文件夹执行失败后立即停止，不再运行后续子文件夹，
#       也不会运行根目录中的 run_all_9_scripts.py。
#
# False：即使某个子文件夹失败，也继续尝试其余子文件夹；
#        但只要存在失败，默认仍不会运行 run_all_9_scripts.py。
STOP_ON_CHILD_ERROR = True

# True：只有所有子文件夹中的 run_all_5_scripts.py 都成功，
#       才运行根目录中的 run_all_9_scripts.py。
RUN_ROOT_ONLY_IF_ALL_CHILDREN_SUCCEED = True

# True：启动前检查所有目标子文件夹是否都存在 run_all_5_scripts.py。
#       只要有缺失，就不开始执行，避免运行一半才发现问题。
PREFLIGHT_CHECK_ALL_CHILDREN = True


# ======================================================================
# 路径和日志
# ======================================================================

BASE_DIR = Path(__file__).resolve().parent
MASTER_LOG_PATH = BASE_DIR / "run_all_subfolders_then_9_scripts.log"


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_log(message: str = "") -> None:
    """同时输出到 PyCharm 控制台和主日志文件。"""
    print(message, flush=True)
    with MASTER_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")


def locate_python_script(folder: Path, stem: str) -> Path:
    """
    在指定文件夹内查找 Python 脚本。

    优先查找：
    1. stem.py
    2. stem（兼容极少数无扩展名文件）
    3. 大小写不完全一致但名称相同的文件

    不会将 .log 或 .txt 文件误认为 Python 脚本。
    """
    exact_py = folder / f"{stem}.py"
    if exact_py.is_file():
        return exact_py

    exact_no_extension = folder / stem
    if exact_no_extension.is_file():
        return exact_no_extension

    expected_py_name = f"{stem}.py".casefold()
    expected_no_extension = stem.casefold()

    for candidate in folder.iterdir():
        if not candidate.is_file():
            continue

        name_folded = candidate.name.casefold()

        if name_folded == expected_py_name:
            return candidate

        if (
            name_folded == expected_no_extension
            and candidate.suffix == ""
        ):
            return candidate

    raise FileNotFoundError(
        f'未在文件夹中找到 "{stem}.py"：\n{folder}'
    )


def numbered_folder_key(folder: Path) -> tuple[int, int, str]:
    """
    按文件夹名称开头的数字进行自然排序：
    1-...、2-...、...、10-...、20-...
    """
    match = re.match(r"^\s*(\d+)", folder.name)

    if match:
        return (0, int(match.group(1)), folder.name.casefold())

    return (1, 0, folder.name.casefold())


def discover_target_subfolders() -> list[Path]:
    """查找需要执行 run_all_5_scripts.py 的一级子文件夹。"""
    all_subfolders = [
        path
        for path in BASE_DIR.iterdir()
        if path.is_dir()
    ]

    if ONLY_NUMBERED_SUBFOLDERS:
        target_subfolders = [
            folder
            for folder in all_subfolders
            if re.match(r"^\s*\d+\s*[-_]", folder.name)
        ]
    else:
        target_subfolders = []
        for folder in all_subfolders:
            try:
                locate_python_script(folder, CHILD_LAUNCHER_STEM)
            except FileNotFoundError:
                continue
            else:
                target_subfolders.append(folder)

    return sorted(target_subfolders, key=numbered_folder_key)


def run_python_script(
    script_path: Path,
    working_directory: Path,
    label: str,
) -> int:
    """
    使用运行本主控脚本的同一个 Python 解释器执行目标脚本。

    cwd 被设置为目标脚本所在文件夹，因此原脚本中的相对路径
    会继续相对于其自身文件夹解析。
    """
    separator = "=" * 100

    write_log()
    write_log(separator)
    write_log(f"开始执行：{label}")
    write_log(f"脚本：{script_path}")
    write_log(f"工作目录：{working_directory}")
    write_log(f"Python 解释器：{sys.executable}")
    write_log(f"开始时间：{timestamp()}")
    write_log(separator)

    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"

    start_time = time.perf_counter()

    # 不使用 shell=True，因此文件夹名称中的空格、逗号、百分号、
    # 连字符和小数点都能够被安全处理。
    completed = subprocess.run(
        [sys.executable, "-u", str(script_path)],
        cwd=str(working_directory),
        env=environment,
        check=False,
    )

    elapsed_seconds = time.perf_counter() - start_time

    if completed.returncode == 0:
        write_log(
            f"[成功] {label}；"
            f"结束时间：{timestamp()}；"
            f"耗时：{elapsed_seconds:.1f} 秒"
        )
    else:
        write_log(
            f"[失败] {label}；"
            f"退出代码：{completed.returncode}；"
            f"结束时间：{timestamp()}；"
            f"耗时：{elapsed_seconds:.1f} 秒"
        )

    return completed.returncode


def main() -> int:
    MASTER_LOG_PATH.write_text(
        "批量执行子文件夹 run_all_5_scripts.py，"
        "随后执行根目录 run_all_9_scripts.py\n"
        f"启动时间：{timestamp()}\n"
        f"根目录：{BASE_DIR}\n"
        f"Python 解释器：{sys.executable}\n",
        encoding="utf-8",
    )

    write_log()
    write_log("正在扫描目标子文件夹……")

    target_subfolders = discover_target_subfolders()

    if not target_subfolders:
        write_log()
        write_log("[无法开始] 没有发现符合条件的目标子文件夹。")

        if ONLY_NUMBERED_SUBFOLDERS:
            write_log(
                "当前设置只识别名称以“数字-”或“数字_”开头的一级子文件夹。"
            )
        else:
            write_log(
                f'当前设置只识别包含 "{CHILD_LAUNCHER_STEM}.py" '
                "的一级子文件夹。"
            )

        return 2

    write_log(f"共发现 {len(target_subfolders)} 个目标子文件夹：")
    for index, folder in enumerate(target_subfolders, start=1):
        write_log(f"{index:>3}. {folder.name}")

    # ------------------------------------------------------------------
    # 启动前检查
    # ------------------------------------------------------------------
    child_jobs: list[tuple[Path, Path]] = []
    missing_child_launchers: list[Path] = []

    for folder in target_subfolders:
        try:
            launcher = locate_python_script(
                folder,
                CHILD_LAUNCHER_STEM,
            )
        except FileNotFoundError:
            missing_child_launchers.append(folder)
        else:
            child_jobs.append((folder, launcher))

    try:
        root_launcher = locate_python_script(
            BASE_DIR,
            ROOT_LAUNCHER_STEM,
        )
    except FileNotFoundError:
        write_log()
        write_log(
            f'[无法开始] 根目录中未找到 "{ROOT_LAUNCHER_STEM}.py"：'
        )
        write_log(str(BASE_DIR))
        return 2

    if missing_child_launchers:
        write_log()
        write_log(
            f"[检查结果] 有 {len(missing_child_launchers)} 个目标子文件夹"
            f'缺少 "{CHILD_LAUNCHER_STEM}.py"：'
        )
        for folder in missing_child_launchers:
            write_log(f"  - {folder.name}")

        if PREFLIGHT_CHECK_ALL_CHILDREN:
            write_log()
            write_log(
                "PREFLIGHT_CHECK_ALL_CHILDREN=True，"
                "因此本次没有开始执行任何脚本。"
            )
            return 2

        write_log()
        write_log("将跳过上述缺少启动脚本的文件夹。")

    if not child_jobs:
        write_log()
        write_log("[无法开始] 没有可执行的子文件夹任务。")
        return 2

    # ------------------------------------------------------------------
    # 第一阶段：执行各子文件夹中的 run_all_5_scripts.py
    # ------------------------------------------------------------------
    write_log()
    write_log("=" * 100)
    write_log("第一阶段：依次执行各子文件夹中的 run_all_5_scripts.py")
    write_log("=" * 100)

    child_results: list[tuple[str, int]] = []

    for index, (folder, launcher) in enumerate(child_jobs, start=1):
        label = (
            f"子文件夹 {index}/{len(child_jobs)}："
            f"{folder.name} / {launcher.name}"
        )

        return_code = run_python_script(
            script_path=launcher,
            working_directory=folder,
            label=label,
        )

        child_results.append((folder.name, return_code))

        if return_code != 0 and STOP_ON_CHILD_ERROR:
            write_log()
            write_log(
                "STOP_ON_CHILD_ERROR=True，"
                "因此停止执行后续子文件夹。"
            )
            break

    attempted_count = len(child_results)
    success_count = sum(
        return_code == 0
        for _, return_code in child_results
    )
    failed_count = sum(
        return_code != 0
        for _, return_code in child_results
    )
    not_attempted_count = len(child_jobs) - attempted_count
    missing_count = len(missing_child_launchers)

    all_children_successful = (
        success_count == len(child_jobs)
        and failed_count == 0
        and not_attempted_count == 0
        and missing_count == 0
    )

    # ------------------------------------------------------------------
    # 第二阶段：执行根目录中的 run_all_9_scripts.py
    # ------------------------------------------------------------------
    root_return_code: int | None = None

    if (
        RUN_ROOT_ONLY_IF_ALL_CHILDREN_SUCCEED
        and not all_children_successful
    ):
        write_log()
        write_log("=" * 100)
        write_log("第二阶段未执行")
        write_log("=" * 100)
        write_log(
            f'由于并非所有子文件夹中的 "{CHILD_LAUNCHER_STEM}.py" '
            f'均成功完成，根目录中的 "{ROOT_LAUNCHER_STEM}.py" '
            "不会执行。"
        )
    else:
        write_log()
        write_log("=" * 100)
        write_log("第二阶段：执行根目录中的 run_all_9_scripts.py")
        write_log("=" * 100)

        root_return_code = run_python_script(
            script_path=root_launcher,
            working_directory=BASE_DIR,
            label=f"根目录：{root_launcher.name}",
        )

    # ------------------------------------------------------------------
    # 最终汇总
    # ------------------------------------------------------------------
    write_log()
    write_log("=" * 100)
    write_log("最终运行结果汇总")
    write_log("=" * 100)

    for folder_name, return_code in child_results:
        if return_code == 0:
            status = "SUCCESS"
        else:
            status = f"FAILED（退出代码 {return_code}）"

        write_log(f"{folder_name:<75} {status}")

    if not_attempted_count:
        write_log()
        write_log(
            f"由于前面的错误，未执行的子文件夹数量："
            f"{not_attempted_count}"
        )

    if missing_count:
        write_log(
            f"缺少 run_all_5_scripts.py 的子文件夹数量："
            f"{missing_count}"
        )

    write_log()
    write_log(
        f"子文件夹总数：{len(target_subfolders)}；"
        f"成功：{success_count}；"
        f"失败：{failed_count}；"
        f"未执行：{not_attempted_count}；"
        f"缺少启动脚本：{missing_count}"
    )

    if root_return_code is None:
        write_log(
            f"根目录 {ROOT_LAUNCHER_STEM}.py：未执行"
        )
    elif root_return_code == 0:
        write_log(
            f"根目录 {ROOT_LAUNCHER_STEM}.py：SUCCESS"
        )
    else:
        write_log(
            f"根目录 {ROOT_LAUNCHER_STEM}.py："
            f"FAILED（退出代码 {root_return_code}）"
        )

    write_log()
    write_log(f"主日志文件：{MASTER_LOG_PATH}")
    write_log(f"全部结束时间：{timestamp()}")

    if all_children_successful and root_return_code == 0:
        write_log("所有子文件夹分析和根目录汇总均已成功完成。")
        return 0

    write_log("本次批量分析未全部成功完成，请查看上方结果和日志。")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        write_log()
        write_log("用户手动中断了批量运行。")
        raise SystemExit(130)
