# -*- coding: utf-8 -*-
"""
Dakota 橋接模組

從 Python 以 subprocess 執行 Sandia Dakota（優化與不確定度量化）。
需本機已安裝 Dakota 並將 dakota 加入 PATH。

參考：https://dakota.sandia.gov/ 、 https://snl-dakota.github.io/
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any


def find_dakota() -> Optional[str]:
    for name in ("dakota", "Dakota"):
        exe = shutil.which(name)
        if exe:
            return exe
    dhome = os.environ.get("DAKOTA_HOME")
    if dhome:
        p = Path(dhome) / "bin" / "dakota"
        if p.exists():
            return str(p)
    return None


def is_dakota_available() -> bool:
    return find_dakota() is not None


def run_dakota(
    input_path: str,
    output_path: Optional[str] = None,
    error_path: Optional[str] = None,
    cwd: Optional[str] = None,
    dakota_exe: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """執行 dakota -i input.in [-o out] [-e err]。"""
    exe = dakota_exe or find_dakota()
    if not exe:
        raise FileNotFoundError("Dakota 未找到，請設定 PATH 或 DAKOTA_HOME")
    inp = Path(input_path).resolve()
    if not inp.exists():
        raise FileNotFoundError(f"輸入檔不存在: {input_path}")
    args = [exe, "-i", str(inp)]
    if output_path:
        args.extend(["-o", output_path])
    if error_path:
        args.extend(["-e", error_path])
    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        args,
        cwd=cwd or str(inp.parent),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def write_minimal_input(path: str, title: str = "Dakota bridge minimal") -> None:
    """寫入最小 Dakota 輸入範本（僅供測試）。"""
    content = f"""# {title}
# 最小範本，實際請依 Dakota 手冊撰寫 variables / interface / responses / method 等

environment
  tabular_data
    tabular_data_file = 'dakota_tabular.dat'

method
  sampling
    sample_type random
    samples = 2
    seed = 12345

variables
  uniform_uncertain = 1
    lower_bounds = 0.0
    upper_bounds = 1.0

interface
  fork
    analysis_driver = 'dummy_script'
    parameters_file = 'params.in'
    results_file = 'results.out'

responses
  objective_functions = 1
  no_gradients
  no_hessians
"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
