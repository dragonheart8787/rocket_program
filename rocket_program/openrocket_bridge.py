# -*- coding: utf-8 -*-
"""
OpenRocket 橋接模組

從 Python 啟動 OpenRocket（Java JAR），可開啟指定 .ork 設計檔。
完整程式化模擬可搭配 orhelper（JPype + OpenRocket 15.03）。需本機已安裝 Java 與 OpenRocket。

參考：https://openrocket.info/ 、 https://github.com/openrocket/openrocket
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def find_java() -> Optional[str]:
    """尋找 java 可執行檔。"""
    return shutil.which("java")


def find_openrocket_jar() -> Optional[str]:
    """
    尋找 OpenRocket JAR：環境變數 OPENROCKET_HOME 或 PATH 中的 OpenRocket.jar。
    """
    home = os.environ.get("OPENROCKET_HOME")
    if home:
        p = Path(home)
        for name in ("OpenRocket.jar", "openrocket.jar"):
            j = p / name
            if j.exists():
                return str(j)
        if p.is_dir():
            for j in p.rglob("OpenRocket*.jar"):
                return str(j)
    return shutil.which("OpenRocket.jar") or None


def is_openrocket_available() -> bool:
    """檢查 Java 與 OpenRocket JAR 是否可用。"""
    return find_java() is not None and find_openrocket_jar() is not None


def run_openrocket(
    open_file: Optional[str] = None,
    jar_path: Optional[str] = None,
    java_exe: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    headless: bool = False,
) -> subprocess.CompletedProcess:
    """
    啟動 OpenRocket。若提供 open_file（.ork 路徑）則傳入作為引數（部分版本支援開檔）。
    headless=True 時加 -Dopenrocket.headless=true（若支援）。
    """
    java = java_exe or find_java()
    jar = jar_path or find_openrocket_jar()
    if not java:
        raise FileNotFoundError("Java 未找到，請安裝 JRE 並加入 PATH")
    if not jar:
        raise FileNotFoundError("OpenRocket.jar 未找到，請設定 OPENROCKET_HOME 或 PATH")

    cmd: List[str] = [java]
    if headless:
        cmd.append("-Dopenrocket.headless=true")
    cmd.extend(["-jar", jar])
    if open_file:
        path = Path(open_file).resolve()
        if path.exists():
            cmd.append(str(path))

    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        cmd,
        cwd=cwd or os.getcwd(),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def get_run_summary(proc: subprocess.CompletedProcess, open_file: Optional[str]) -> Dict[str, Any]:
    """由 run_openrocket 的結果組出摘要。"""
    return {
        "open_file": open_file,
        "returncode": proc.returncode,
        "success": proc.returncode == 0,
        "stdout_length": len(proc.stdout or ""),
        "stderr_length": len(proc.stderr or ""),
    }


def note_on_orhelper() -> str:
    """
    回傳關於 orhelper（Python + JPype 驅動 OpenRocket 模擬）的簡短說明。
    """
    return (
        "程式化模擬可搭配 orhelper (JPype)，需 OpenRocket 15.03 與 Java。"
        " 見 https://github.com/SilentSys/orhelper 與 "
        "https://wiki.openrocket.info/Scripting_with_Python_and_JPype"
    )
