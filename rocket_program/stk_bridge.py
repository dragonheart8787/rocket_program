# -*- coding: utf-8 -*-
"""
STK (Systems Tool Kit) 橋接模組

說明與驅動介面：STK 可透過 Connect 指令（TCP/IP 或檔案）或 COM/API 自動化。
本模組提供撰寫 Connect 指令檔、以 subprocess 啟動 STK 並載入場景的輔助；
完整自動化需 STK 安裝與 AgConnect / Object Model 文件。

參考：https://www.agi.com/ 、 STK Help: Automating STK, Connect Commands.
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


def find_stk() -> Optional[str]:
    """尋找 STK 可執行檔（Windows 常見為 AgiSTK.exe 或 STK 安裝目錄）。"""
    for name in ("AgiSTK", "STK"):
        exe = shutil.which(name)
        if exe:
            return exe
    stk_home = os.environ.get("AGI_STK_HOME") or os.environ.get("STK_HOME")
    if stk_home:
        for sub in ("bin", ""):
            p = Path(stk_home) / sub / "AgiSTK.exe"
            if p.exists():
                return str(p)
    return None


def is_stk_available() -> bool:
    return find_stk() is not None


def write_connect_script(
    path: str,
    commands: List[str],
    header: str = "STK Connect script - bridge",
) -> None:
    """
    寫入 Connect 指令腳本（每行一條 Connect 指令）。實際語法請參照 STK Connect 文件。
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("// " + header + "\n")
        for c in commands:
            f.write(c.strip() + "\n")


def run_stk_with_script(
    script_path: str,
    stk_exe: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    啟動 STK 並載入/執行腳本（若 STK 支援指令列參數傳腳本）。部分版本需透過 Connect 或 GUI 手動載入。
    此處以 subprocess 啟動 STK；實際批次多採 Connect over TCP 或 STK Engine 無頭模式。
    """
    exe = stk_exe or find_stk()
    if not exe:
        raise FileNotFoundError("STK 未找到，請設定 PATH 或 AGI_STK_HOME")
    args = [exe]
    script = Path(script_path).resolve()
    if script.exists():
        args.append(str(script))
    run_env = {**os.environ} if env is None else {**os.environ, **env}
    return subprocess.run(
        args,
        cwd=cwd or os.getcwd(),
        env=run_env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def note_on_stk_automation() -> str:
    return (
        "完整自動化請使用 STK Connect (TCP/檔案) 或 STK Object Model (COM)。"
        " 見 AGI 文件：Automating STK, Connect Command Listings, Containerize STK。"
    )
