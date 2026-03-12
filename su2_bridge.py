# -*- coding: utf-8 -*-
"""
SU2 橋接模組

從 Python 驅動 SU2_CFD 求解器：透過環境變數 SU2_RUN 或 PATH 找到可執行檔，
以 subprocess 執行指定 config 檔。需本機已安裝並編譯 SU2。

參考：https://su2code.github.io/
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def find_su2_cfd() -> Optional[str]:
    """
    尋找 SU2_CFD 可執行檔：先查 SU2_RUN，再查 PATH。
    """
    su2_run = os.environ.get("SU2_RUN")
    if su2_run:
        # 可能是目錄或腳本路徑
        p = Path(su2_run)
        if p.is_dir():
            exe = p / "SU2_CFD"
            if exe.exists():
                return str(exe)
            py_script = p / "SU2_CFD.py"
            if py_script.exists():
                return f"{shutil.which('python') or 'python'} {py_script}"
        elif p.exists():
            return str(p)
    return shutil.which("SU2_CFD")


def is_su2_available() -> bool:
    """檢查 SU2 是否可用（SU2_CFD 可找到）。"""
    exe = find_su2_cfd()
    if not exe:
        return False
    if " " in exe:
        return True  # python path/to/SU2_CFD.py
    return os.path.isfile(exe) or os.access(exe, os.X_OK)


def run_su2_cfd(
    config_path: str,
    cwd: Optional[str] = None,
    n_cores: int = 1,
    extra_args: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    執行 SU2_CFD。config_path 為 .cfg 設定檔路徑。
    n_cores > 1 時會加上 -n 參數（若求解器支援 MPI）。
    """
    exe = find_su2_cfd()
    if not exe:
        raise FileNotFoundError("SU2_CFD 未找到，請設定 SU2_RUN 或將 SU2 加入 PATH")

    cmd: List[str] = []
    if " " in exe:
        cmd.extend(exe.split())
    else:
        cmd.append(exe)

    cmd.append(config_path)
    if n_cores > 1:
        cmd.extend(["-n", str(n_cores)])
    if extra_args:
        cmd.extend(extra_args)

    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        cmd,
        cwd=cwd or os.path.dirname(os.path.abspath(config_path)),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def write_minimal_config(
    path: str,
    mesh_file: str = "mesh.su2",
    mach: float = 0.5,
    aoa: float = 0.0,
    output_dir: str = "SU2_output",
) -> None:
    """
    寫入最小 SU2 設定檔（可壓歐拉/NS），用於測試或範本。
    實際使用請依案例修改。
    """
    content = f"""% -------------------------------
% SU2 最小設定（橋接範本）
% -------------------------------
PHYSICAL_PROBLEM= EULER
MATH_PROBLEM= DIRECT

% 網格
MESH_FILENAME= {mesh_file}

% 自由流
MACH_NUMBER= {mach}
AOA= {aoa}
SIDESLIP_ANGLE= 0.0
FREESTREAM_PRESSURE= 101325.0
FREESTREAM_TEMPERATURE= 288.15

% 輸出
OUTPUT_FORMAT= PARAVIEW
CONV_FILENAME= history
VOLUME_FILENAME= flow
OUTPUT_WRT_FREQ= 100
CONV_WRT_FREQ= 1

% 迭代
ITER= 1000
CFL_NUMBER= 1.5
"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_run_summary(proc: subprocess.CompletedProcess, config_path: str) -> Dict[str, Any]:
    """由 run_su2_cfd 的 CompletedProcess 組出摘要。"""
    return {
        "config": config_path,
        "returncode": proc.returncode,
        "success": proc.returncode == 0,
        "stdout_length": len(proc.stdout or ""),
        "stderr_length": len(proc.stderr or ""),
    }
