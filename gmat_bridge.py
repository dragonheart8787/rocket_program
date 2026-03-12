# -*- coding: utf-8 -*-
"""
GMAT 橋接模組

從 Python 以 subprocess 執行 NASA GMAT（General Mission Analysis Tool）批次腳本。
使用 GMATConsole 可無 GUI 執行。需本機已安裝 GMAT 並將 GMAT 或 GMATConsole 加入 PATH。

參考：https://github.com/nasa/GMAT 、 https://gmat.atlassian.net/
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def find_gmat() -> Optional[str]:
    """
    尋找 GMAT 可執行檔：優先 GMATConsole（無 GUI），其次 GMAT。
    """
    for name in ("GMATConsole", "GMAT"):
        exe = shutil.which(name)
        if exe:
            return exe
    gmat_home = os.environ.get("GMAT_HOME")
    if gmat_home:
        for name in ("GMATConsole", "GMAT"):
            p = Path(gmat_home) / "bin" / name
            if p.exists():
                return str(p)
            p = Path(gmat_home) / name
            if p.exists():
                return str(p)
    return None


def is_gmat_available() -> bool:
    """檢查 GMAT 是否可用。"""
    return find_gmat() is not None


def run_gmat_script(
    script_path: str,
    run_and_exit: bool = True,
    use_console: bool = True,
    gmat_exe: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    logfile: Optional[str] = None,
    verbose: bool = False,
) -> subprocess.CompletedProcess:
    """
    執行 GMAT 腳本（.script）。
    - run_and_exit: 執行完後結束（-r 腳本 -x）
    - use_console: 使用 GMATConsole（無 GUI）；若 False 則用 GMAT
    - logfile: 指定 -l logfile 輸出日誌
    - verbose: 加上 --verbose
    """
    exe = gmat_exe or find_gmat()
    if not exe:
        raise FileNotFoundError("GMAT 未找到，請設定 PATH 或 GMAT_HOME")

    script = Path(script_path).resolve()
    if not script.exists():
        raise FileNotFoundError(f"腳本不存在: {script_path}")

    args: List[str] = []
    if run_and_exit:
        args.extend(["-r", str(script), "-x"])
    else:
        args.append(str(script))
    if logfile:
        args.extend(["-l", logfile])
    if verbose:
        args.append("--verbose")
    # 無 GUI 時常用
    if use_console and "Console" not in exe:
        exe = find_gmat() or exe  # 再試一次 GMATConsole

    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        [exe] + args,
        cwd=cwd or str(script.parent),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def write_minimal_script(
    path: str,
    title: str = "GMAT bridge minimal",
    create_earth: bool = True,
    create_satellite: bool = True,
) -> None:
    """
    寫入最小 GMAT .script 範本（建立 Earth、衛星與軌道等），僅供測試驅動。
    實際任務請在 GMAT GUI 中編輯或參考 GMAT 腳本語法。
    """
    content = f"""%----------------------------------------
% {title}
% 最小範本，僅供橋接測試
%----------------------------------------
Create Spacecraft Sat1;
Create ForceModel DefaultProp_DefaultForceModel;
Create Propagator DefaultProp;
Create OrbitState DefaultProp_DefaultOrbitState;
Create Burn DefaultProp_DefaultOrbitState_DefaultBurn1;
Create CoordinateSystem DefaultProp_DefaultOrbitState_J2000EarthEquator;
Create Subscriber ReportFile DefaultProp_DefaultOrbitState_DefaultReportFile1;

DefaultProp_DefaultOrbitState.Epoch = '1 Jan 2000 12:00:00.000';
DefaultProp_DefaultOrbitState.CoordinateSystem = DefaultProp_DefaultOrbitState_J2000EarthEquator;
DefaultProp_DefaultOrbitState.X = 6800;
DefaultProp_DefaultOrbitState.Y = 0;
DefaultProp_DefaultOrbitState.Z = 0;
DefaultProp_DefaultOrbitState.VX = 0;
DefaultProp_DefaultOrbitState.VY = 7.7;
DefaultProp_DefaultOrbitState.VZ = 0;

Sat1.DefaultProp = DefaultProp;

% Mission sequence (minimal)
BeginMissionSequence;
"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_run_summary(proc: subprocess.CompletedProcess, script_path: str) -> Dict[str, Any]:
    """由 run_gmat_script 的結果組出摘要。"""
    return {
        "script": script_path,
        "returncode": proc.returncode,
        "success": proc.returncode == 0,
        "stdout_length": len(proc.stdout or ""),
        "stderr_length": len(proc.stderr or ""),
    }
