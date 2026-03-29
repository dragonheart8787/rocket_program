# -*- coding: utf-8 -*-
"""
MATLAB / Simulink 橋接模組

從 Python 呼叫 MATLAB：以 matlab.engine 啟動引擎並執行指令/腳本，或以 subprocess 呼叫 matlab -batch。
需本機已安裝 MATLAB（Engine API 需 MATLAB 安裝，非僅 Runtime）。

參考：https://www.mathworks.com/help/matlab/matlab-engine-for-python.html
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Any, Dict

def _get_engine():
    try:
        import matlab.engine
        return matlab.engine
    except ImportError:
        return None


def is_matlab_engine_available() -> bool:
    """是否可 import matlab.engine（需已安裝 MATLAB 並 pip install matlabengine）。"""
    return _get_engine() is not None


def start_engine() -> Any:
    """啟動 MATLAB 引擎，回傳 engine 物件。未安裝則回傳 None。"""
    eng = _get_engine()
    if eng is None:
        return None
    return eng.start_matlab()


def run_script(script_path: str, engine: Optional[Any] = None, nargout: int = 0) -> Any:
    """在 MATLAB 中執行 .m 腳本。若未傳 engine 則臨時啟動並結束。"""
    path = Path(script_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"腳本不存在: {script_path}")
    eng = engine or start_engine()
    if eng is None:
        raise RuntimeError("MATLAB Engine 不可用，請安裝 MATLAB 並 pip install matlabengine")
    try:
        name = path.stem
        eng.cd(str(path.parent))
        out = eng.run(name, nargout=nargout)
        return out
    finally:
        if engine is None:
            eng.quit()


def run_matlab_batch(
    script_path: str,
    matlab_exe: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """以 subprocess 執行 matlab -batch \"run('script')\"（無 GUI，適合自動化）。"""
    exe = matlab_exe or shutil.which("matlab")
    if not exe:
        raise FileNotFoundError("MATLAB 未找到，請將 matlab 加入 PATH")
    path = Path(script_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"腳本不存在: {script_path}")
    cmd = [exe, "-batch", f"run('{path.as_posix()}');"]
    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        cmd,
        cwd=cwd or str(path.parent),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )
