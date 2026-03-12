# -*- coding: utf-8 -*-
"""
NASA Trick 仿真橋接模組

從 Python 以 subprocess 執行 Trick 仿真：S_main_${TRICK_HOST_CPU}.exe RUN_<name>/<input_file> [-O output_dir]。
需本機已編譯 Trick 仿真並設定 TRICK_HOME 或 PATH。

參考：https://nasa.github.io/trick/
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def find_trick_s_main(run_dir: Optional[str] = None) -> Optional[str]:
    """
    尋找 S_main_*.exe（或無副檔名之 S_main_*）。先查 run_dir，再 TRICK_HOME/RUN_*，再 PATH。
    """
    if run_dir:
        for p in Path(run_dir).glob("S_main*"):
            if p.is_file():
                return str(p)
    trick_home = os.environ.get("TRICK_HOME")
    if trick_home:
        for pattern in ("RUN_*/S_main_*", "S_main_*"):
            for p in Path(trick_home).rglob(pattern):
                if p.is_file():
                    return str(p)
    for name in ("S_main_Linux-x86_64.exe", "S_main_Linux-x86_64", "S_main_*.exe"):
        exe = shutil.which(name) if "*" not in name else None
        if exe:
            return exe
    return None


def is_trick_available(run_dir: Optional[str] = None) -> bool:
    return find_trick_s_main(run_dir) is not None


def run_trick_sim(
    run_input: str,
    output_dir: Optional[str] = None,
    s_main_exe: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    執行 Trick 仿真。run_input 格式如 RUN_<name>/input_<name>.py 或 RUN_<name>。
    -O 指定輸出目錄。
    """
    exe = s_main_exe or find_trick_s_main(cwd)
    if not exe:
        raise FileNotFoundError("Trick S_main 未找到，請設定 TRICK_HOME 或於 run_dir 提供可執行檔")
    args = [exe, run_input]
    if output_dir:
        args.extend(["-O", output_dir])
    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        args,
        cwd=cwd or os.getcwd(),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )
