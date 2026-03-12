# -*- coding: utf-8 -*-
"""
OpenFOAM 橋接模組

提供從 Python 驅動 OpenFOAM 案例的介面：寫入最小案例檔、以 subprocess 執行
blockMesh / 求解器（如 simpleFoam、rhoCentralFoam）等。需本機已安裝 OpenFOAM 並已 source 環境。

參考：https://www.openfoam.com/ 或 https://openfoam.org/
"""

from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

# 預設求解器（可依案例覆寫）
DEFAULT_SOLVER = "simpleFoam"  # 不可壓
# 可壓 / 超音速 常用：rhoCentralFoam, rhoSimpleFoam


def is_openfoam_available() -> bool:
    """檢查 OpenFOAM 是否在 PATH 中（例如可執行 blockMesh）。"""
    return shutil.which("blockMesh") is not None


def run_openfoam_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    """
    在指定目錄執行 OpenFOAM 指令（如 blockMesh, simpleFoam）。
    env 可傳入已 source 的環境；若為 None 則使用當前 os.environ。
    """
    env_run = os.environ if env is None else {**os.environ, **env}
    return subprocess.run(
        cmd,
        cwd=cwd or os.getcwd(),
        env=env_run,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def run_case_steps(
    case_dir: str,
    steps: List[str],
    env: Optional[Dict[str, str]] = None,
    timeout_per_step: Optional[int] = 3600,
) -> List[subprocess.CompletedProcess]:
    """
    在 case_dir 依序執行步驟。steps 為指令名稱列表，如 ["blockMesh", "simpleFoam"]。
    回傳每個步驟的 CompletedProcess。
    """
    results = []
    for step in steps:
        # 支援帶參數：如 "simpleFoam -parallel"
        parts = step.split()
        exe = shutil.which(parts[0])
        if not exe:
            raise FileNotFoundError(f"OpenFOAM 指令未找到: {parts[0]}")
        proc = run_openfoam_command(
            parts,
            cwd=case_dir,
            env=env,
            timeout=timeout_per_step,
        )
        results.append(proc)
        if proc.returncode != 0:
            break
    return results


def write_blockmesh_dict(
    path: str,
    x_min: float = 0.0,
    y_min: float = 0.0,
    z_min: float = 0.0,
    x_max: float = 1.0,
    y_max: float = 0.1,
    z_max: float = 0.1,
    nx: int = 50,
    ny: int = 5,
    nz: int = 5,
) -> None:
    """
    寫入簡化 blockMeshDict（長方體網格），用於測試或替代手寫。
    """
    content = f"""/*--------------------------------*- C++ -*----------------------------------*
// 自動生成，僅供橋接測試
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    ({x_min} {y_min} {z_min})
    ({x_max} {y_min} {z_min})
    ({x_max} {y_max} {z_min})
    ({x_min} {y_max} {z_min})
    ({x_min} {y_min} {z_max})
    ({x_max} {y_min} {z_max})
    ({x_max} {y_max} {z_max})
    ({x_min} {y_max} {z_max})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
);

boundary
(
    inlet
    {{
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
            (1 2 6 5)
        );
    }}
    walls
    {{
        type wall;
        faces
        (
            (0 3 2 1)
            (0 1 5 4)
            (3 7 6 2)
            (4 5 6 7)
        );
    }}
);

// ************************************************************************* //
"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_run_summary(results: List[subprocess.CompletedProcess], steps: List[str]) -> Dict[str, Any]:
    """由 run_case_steps 的結果組出摘要（通過與否、最後 returncode）。"""
    n = len(results)
    return {
        "steps_run": n,
        "steps_requested": len(steps),
        "all_passed": n == len(steps) and all(r.returncode == 0 for r in results),
        "last_returncode": results[-1].returncode if results else None,
        "step_names": steps[:n],
    }
