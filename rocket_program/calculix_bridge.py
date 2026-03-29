# -*- coding: utf-8 -*-
"""
CalculiX 橋接模組

從 Python 以 subprocess 執行 CalculiX (ccx) 求解器。使用 Abaqus 相容的 .inp 關鍵字格式，
輸出 .dat、.frd 等。需本機已安裝 CalculiX 並將 ccx 加入 PATH。

參考：http://www.calculix.de/ 、 https://github.com/calculix/CalculiX
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def find_ccx() -> Optional[str]:
    """
    尋找 CalculiX 可執行檔：ccx 或 ccx_static（Windows 常見）。
    """
    for name in ("ccx", "ccx_static"):
        exe = shutil.which(name)
        if exe:
            return exe
    ccx_home = os.environ.get("CALCULIX_HOME") or os.environ.get("CCX_HOME")
    if ccx_home:
        for name in ("ccx", "ccx_static"):
            p = Path(ccx_home) / name
            if p.exists():
                return str(p)
    return None


def is_calculix_available() -> bool:
    """檢查 CalculiX 是否可用。"""
    return find_ccx() is not None


def run_ccx(
    jobname: str,
    cwd: Optional[str] = None,
    ccx_exe: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    執行 CalculiX：ccx jobname（會讀取 jobname.inp，不帶副檔名）。
    輸出為 jobname.dat、jobname.frd 等。
    """
    exe = ccx_exe or find_ccx()
    if not exe:
        raise FileNotFoundError("CalculiX (ccx) 未找到，請設定 PATH 或 CALCULIX_HOME")

    # jobname 不含 .inp
    base = Path(jobname).stem if jobname.endswith(".inp") else jobname
    run_dir = cwd or os.getcwd()
    inp_path = Path(run_dir) / f"{base}.inp"
    if not inp_path.exists():
        raise FileNotFoundError(f"輸入檔不存在: {inp_path}")

    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        [exe, base],
        cwd=run_dir,
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def write_minimal_inp(
    path: str,
    title: str = "CalculiX bridge minimal",
    node_list: Optional[List[tuple]] = None,
    element_list: Optional[List[tuple]] = None,
) -> None:
    """
    寫入最小 .inp 範本（與 Abaqus 關鍵字相容之格式，CalculiX 可讀）。
    僅供橋接測試；實際分析請用前處理或完整關鍵字。
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


def get_run_summary(proc: subprocess.CompletedProcess, jobname: str) -> Dict[str, Any]:
    """由 run_ccx 的結果組出摘要。"""
    return {
        "jobname": jobname,
        "returncode": proc.returncode,
        "success": proc.returncode == 0,
        "stdout_length": len(proc.stdout or ""),
        "stderr_length": len(proc.stderr or ""),
    }
