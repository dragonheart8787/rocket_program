# -*- coding: utf-8 -*-
"""
Abaqus 橋接模組

從 Python 以 subprocess 提交 Abaqus 作業（.inp 輸入檔或 .py 腳本）。
需本機已安裝 SIMULIA Abaqus 且指令在 PATH 中（或傳入 abaqus_cmd）。

參考：Abaqus 指令列文件
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def find_abaqus_command() -> Optional[str]:
    """
    尋找 Abaqus 指令：常見環境變數或 PATH 中的 abq2023、abaqus、abq6145 等。
    """
    for name in ("abaqus", "abq2024", "abq2023", "abq2022", "abq6145"):
        exe = shutil.which(name)
        if exe:
            return exe
    # Windows 常見安裝路徑
    simulia = os.environ.get("SIMULIA_PATH") or os.environ.get("ABAQUS_HOME")
    if simulia:
        for sub in ("Commands", "command"):
            p = Path(simulia) / sub
            if p.is_dir():
                for f in p.glob("abq*.bat"):
                    return str(f)
                for f in p.glob("abaqus*.bat"):
                    return str(f)
    return None


def is_abaqus_available() -> bool:
    """檢查 Abaqus 指令是否可用。"""
    return find_abaqus_command() is not None


def run_abaqus_job(
    inp_path: str,
    job_name: Optional[str] = None,
    abaqus_cmd: Optional[str] = None,
    cwd: Optional[str] = None,
    ask_delete: str = "OFF",
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    執行 Abaqus 分析：job=JobName input=file.inp。
    job_name 預設為 inp 檔名去掉 .inp；abaqus_cmd 未給則自動尋找。
    """
    cmd_exe = abaqus_cmd or find_abaqus_command()
    if not cmd_exe:
        raise FileNotFoundError("Abaqus 指令未找到，請設定 PATH 或傳入 abaqus_cmd")

    inp = Path(inp_path).resolve()
    if not inp.exists():
        raise FileNotFoundError(f"輸入檔不存在: {inp_path}")

    jname = job_name or inp.stem
    run_dir = cwd or str(inp.parent)

    args: List[str] = [
        f"job={jname}",
        f"input={inp.name}",
        f"ask_delete={ask_delete}",
    ]

    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        [cmd_exe] + args,
        cwd=run_dir,
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def run_abaqus_cae_script(
    script_path: str,
    no_gui: bool = True,
    abaqus_cmd: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    執行 Abaqus CAE 腳本：abaqus cae script=model.py [-noGUI]。
    """
    cmd_exe = abaqus_cmd or find_abaqus_command()
    if not cmd_exe:
        raise FileNotFoundError("Abaqus 指令未找到")

    args = ["cae", f"script={script_path}"]
    if no_gui:
        args.append("-noGUI")

    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        [cmd_exe] + args,
        cwd=cwd or os.path.dirname(os.path.abspath(script_path)),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def write_minimal_inp(
    path: str,
    title: str = "Rocket bridge minimal",
    node_list: Optional[List[tuple]] = None,
    element_list: Optional[List[tuple]] = None,
) -> None:
    """
    寫入最小 .inp 範本（僅結構頭與一個節點/單元示例），用於測試驅動。
    實際分析請用 Abaqus CAE 或完整關鍵字產生。
    """
    nodes = node_list or [(1, 0.0, 0.0, 0.0)]
    elems = element_list or [(1, 1, 1)]
    lines = [
        f"** {title}",
        "** 最小範本，僅供橋接測試",
        "*Heading",
        title,
        "*Node",
    ]
    for n in nodes:
        lines.append(f"  {n[0]}, {n[1]}, {n[2]}, {n[3]}")
    lines.append("*Element, type=C3D8")
    for e in elems:
        lines.append("  " + ", ".join(str(x) for x in e))
    lines.append("*Step, name=Step-1")
    lines.append("*Static")
    lines.append("1., 1., 1e-5, 1.")
    lines.append("*End Step")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def get_run_summary(proc: subprocess.CompletedProcess, job_name: str) -> Dict[str, Any]:
    """由 run_abaqus_job 的結果組出摘要。"""
    return {
        "job": job_name,
        "returncode": proc.returncode,
        "success": proc.returncode == 0,
        "stdout_length": len(proc.stdout or ""),
        "stderr_length": len(proc.stderr or ""),
    }
