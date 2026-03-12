# -*- coding: utf-8 -*-
"""
ANSYS Fluent 自動化腳本橋接模組

撰寫 TUI 日誌檔並以 subprocess 執行 Fluent 批次模式（fluent 3d -g -i journal.jou）。
需本機已安裝 ANSYS Fluent 並將 fluent 加入 PATH。

參考：ANSYS Fluent 使用者手冊（Batch Execution）、TUI 指令。
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def find_fluent() -> Optional[str]:
    for name in ("fluent", "fluent2024", "fluent2023"):
        exe = shutil.which(name)
        if exe:
            return exe
    return os.environ.get("FLUENT_BIN")


def is_fluent_available() -> bool:
    return find_fluent() is not None


def write_journal(
    path: str,
    case_file: Optional[str] = None,
    data_file: Optional[str] = None,
    n_iters: int = 100,
    write_data_at_end: bool = True,
) -> None:
    """
    寫入最小 Fluent TUI 日誌範本：讀 case、初始化、迭代、可選寫 data、exit。
    case_file / data_file 為相對或絕對路徑；若為 None 則以佔位字串代替，需手動替換。
    """
    lines = [
        "; Fluent journal - bridge minimal",
        "; Read case",
        f"/file/read-case {case_file or 'case.cas'}",
        "; Initialize",
        "/solve/initialize/initialize-flow",
        "; Iterate",
        f"/solve/iterate {n_iters}",
    ]
    if write_data_at_end and data_file:
        lines.append(f"/file/write-data {data_file}")
    lines.extend(["exit", "yes"])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_fluent_batch(
    journal_path: str,
    dimension: str = "3d",
    fluent_exe: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    stdout_path: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """
    以批次模式執行 Fluent：fluent 3d -g -i journal.jou。
    -g 為無 GUI。輸出可重導向至 stdout_path。
    """
    exe = fluent_exe or find_fluent()
    if not exe:
        raise FileNotFoundError("Fluent 未找到，請設定 PATH 或 FLUENT_BIN")
    j = Path(journal_path).resolve()
    if not j.exists():
        raise FileNotFoundError(f"日誌檔不存在: {journal_path}")
    cmd = [exe, dimension, "-g", "-i", str(j)]
    run_env = {**os.environ} if env is None else {**os.environ, **env}
    if stdout_path:
        with open(stdout_path, "w", encoding="utf-8") as fout:
            return subprocess.run(
                cmd,
                cwd=cwd or str(j.parent),
                env=run_env,
                timeout=timeout,
                stdout=fout,
                stderr=subprocess.PIPE,
                text=True,
            )
    return subprocess.run(
        cmd,
        cwd=cwd or str(j.parent),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )
