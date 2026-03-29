# -*- coding: utf-8 -*-
"""
可重現性包：完整 config、版本資訊、回歸測試
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
import json
import hashlib
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
from typing import Optional, Dict, List, Any


@dataclass
class SimulationConfig:
    """模擬配置（完整可重現）"""
    simulation_id: str
    timestamp: str
    random_seed: Optional[int] = None
    dt: float = 0.01
    t_end: float = 100.0
    initial_conditions: Dict = field(default_factory=dict)
    parameters: Dict = field(default_factory=dict)
    model_versions: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def compute_hash(self) -> str:
        """計算配置 hash（用於驗證）"""
        config_str = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


@dataclass
class ModelVersionInfo:
    """模型版本資訊"""
    model_name: str
    version: str
    hash: str  # 資料 hash
    source: str
    date: str
    notes: str = ""


class ReproducibilityPack:
    """可重現性包管理器"""

    def __init__(self):
        self.config: Optional[SimulationConfig] = None
        self.model_versions: Dict[str, ModelVersionInfo] = {}
        self.git_commit: Optional[str] = None
        self.dependencies: Dict[str, str] = {}
        self.output_summary: Dict = {}

    def set_config(self, config: SimulationConfig):
        """設置配置"""
        self.config = config

    def register_model_version(self, model_name: str, version: str, data: Any, source: str):
        """註冊模型版本（計算 hash）"""
        # 計算資料 hash
        if isinstance(data, np.ndarray):
            data_str = data.tobytes().hex()
        elif isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True, default=str)
        else:
            data_str = str(data)
        
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        
        model_info = ModelVersionInfo(
            model_name=model_name,
            version=version,
            hash=data_hash,
            source=source,
            date=datetime.now().isoformat()
        )
        self.model_versions[model_name] = model_info

    def get_git_commit(self) -> Optional[str]:
        """獲取 git commit（如果可用）"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).resolve().parents[1]
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def get_dependencies(self) -> Dict[str, str]:
        """獲取依賴版本"""
        deps = {}
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "==" in line:
                        pkg, version = line.split("==", 1)
                        deps[pkg] = version
        except Exception:
            pass
        return deps

    def create_pack(self, output_dir: str = "reproducible_pack") -> Dict:
        """創建可重現包"""
        pack_dir = Path(output_dir)
        pack_dir.mkdir(exist_ok=True)
        
        # 獲取 git commit 和依賴
        self.git_commit = self.get_git_commit()
        self.dependencies = self.get_dependencies()
        
        # 保存配置
        if self.config:
            config_file = pack_dir / "config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=2, default=str)
        
        # 保存模型版本
        model_versions_file = pack_dir / "model_versions.json"
        model_versions_dict = {
            name: {
                "model_name": info.model_name,
                "version": info.version,
                "hash": info.hash,
                "source": info.source,
                "date": info.date,
                "notes": info.notes
            }
            for name, info in self.model_versions.items()
        }
        with open(model_versions_file, 'w', encoding='utf-8') as f:
            json.dump(model_versions_dict, f, indent=2, ensure_ascii=False)
        
        # 保存版本資訊
        version_info = {
            "git_commit": self.git_commit,
            "dependencies": self.dependencies,
            "python_version": sys.version,
            "timestamp": datetime.now().isoformat()
        }
        version_file = pack_dir / "version_info.json"
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, indent=2, ensure_ascii=False)
        
        # 保存輸出摘要
        if self.output_summary:
            summary_file = pack_dir / "output_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(self.output_summary, f, indent=2, default=str)
        
        # 生成 Artifact Manifest（檔案 SHA256）
        manifest_file = pack_dir / "artifact_manifest.json"
        manifest = {}
        for file_path in pack_dir.glob("*"):
            if file_path.is_file() and file_path.name != "artifact_manifest.json":
                try:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    manifest[file_path.name] = {
                        "sha256": file_hash,
                        "size": file_path.stat().st_size
                    }
                except Exception:
                    pass
        
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        # Determinism Checklist
        determinism_file = pack_dir / "determinism_checklist.json"
        determinism = {
            "random_seed": self.config.random_seed if self.config else None,
            "numpy_random_state": "需設置 np.random.seed()",
            "blas_threads": "需設置環境變數 OMP_NUM_THREADS=1",
            "sorting_stability": "需使用穩定排序算法",
            "floating_point": "需使用相同精度（float64）",
            "note": "確保所有隨機性來源都被固定"
        }
        with open(determinism_file, 'w', encoding='utf-8') as f:
            json.dump(determinism, f, indent=2, ensure_ascii=False)
        
        # 生成 README
        readme_file = pack_dir / "README.md"
        readme_content = f"""# 可重現性包

## 配置
- 模擬 ID: {self.config.simulation_id if self.config else 'N/A'}
- 時間戳: {self.config.timestamp if self.config else 'N/A'}
- 配置 Hash: {self.config.compute_hash() if self.config else 'N/A'}
- 隨機種子: {self.config.random_seed if self.config else 'N/A'}

## 版本資訊
- Git Commit: {self.git_commit or 'N/A'}
- Python: {sys.version.split()[0]}

## 模型版本
"""
        for name, info in self.model_versions.items():
            readme_content += f"- {name}: v{info.version} (hash: {info.hash})\n"
        
        readme_content += f"""
## 依賴
見 version_info.json

## Artifact Manifest
所有檔案的 SHA256 hash 見 artifact_manifest.json

## Determinism Checklist
見 determinism_checklist.json

## 使用方法
1. 安裝依賴: `pip install -r requirements.txt` 或使用 Docker/Conda
2. 設置環境變數: `export OMP_NUM_THREADS=1` (BLAS 線程)
3. 運行模擬: 使用 config.json 中的參數
4. 驗證結果: 對照 output_summary.json 和 artifact_manifest.json
"""
        
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        return {
            "pack_dir": str(pack_dir),
            "config_hash": self.config.compute_hash() if self.config else None,
            "n_models": len(self.model_versions),
            "has_git": self.git_commit is not None
        }

    def set_output_summary(self, kpis: Dict[str, Any], plots: Optional[List[str]] = None):
        """設置輸出摘要（KPI + plots）"""
        self.output_summary = {
            "kpis": kpis,
            "plots": plots or [],
            "timestamp": datetime.now().isoformat()
        }


class RegressionGate:
    """回歸閘門（分層）"""
    HARD_INVARIANT = "hard_invariant"  # 必須不變
    SOFT_KPI = "soft_kpi"  # 允許小變動
    MODEL_UPDATE_EXPECTED = "model_update_expected"  # 預期變動


class RegressionTest:
    """回歸測試：模型更新後 KPI 變化檢查（分層閘門）"""

    def __init__(self):
        self.baseline_kpis: Dict[str, Dict] = {}
        self.tolerance_gates: Dict[str, Dict] = {}
        self.gate_types: Dict[str, str] = {}  # KPI -> gate type

    def set_baseline(self, kpi_name: str, value: float, model_version: str):
        """設置基準 KPI"""
        self.baseline_kpis[kpi_name] = {
            "value": value,
            "model_version": model_version,
            "timestamp": datetime.now().isoformat()
        }

    def set_tolerance(self, kpi_name: str, absolute_tol: Optional[float] = None,
                    relative_tol: Optional[float] = None, allow_change: bool = False,
                    gate_type: str = RegressionGate.SOFT_KPI):
        """
        設置容許閾值（分層閘門）
        allow_change: True 表示允許變化（只檢查是否在範圍內），False 表示不允許變化
        gate_type: hard_invariant / soft_kpi / model_update_expected
        """
        self.tolerance_gates[kpi_name] = {
            "absolute_tolerance": absolute_tol,
            "relative_tolerance": relative_tol,
            "allow_change": allow_change
        }
        self.gate_types[kpi_name] = gate_type

    def check_regression(self, current_kpis: Dict[str, float], model_version: str) -> Dict:
        """檢查回歸（分層閘門）"""
        results = {}
        gate_results = {
            RegressionGate.HARD_INVARIANT: {"passed": [], "failed": []},
            RegressionGate.SOFT_KPI: {"passed": [], "failed": []},
            RegressionGate.MODEL_UPDATE_EXPECTED: {"passed": [], "failed": []}
        }
        any_failure = False
        
        for kpi_name, current_value in current_kpis.items():
            if kpi_name not in self.baseline_kpis:
                results[kpi_name] = {
                    "status": "no_baseline",
                    "note": "無基準值"
                }
                continue
            
            baseline = self.baseline_kpis[kpi_name]
            baseline_value = baseline["value"]
            tolerance = self.tolerance_gates.get(kpi_name, {})
            gate_type = self.gate_types.get(kpi_name, RegressionGate.SOFT_KPI)
            
            # 計算變化
            absolute_change = abs(current_value - baseline_value)
            relative_change = absolute_change / max(abs(baseline_value), 1e-9)
            
            # 根據閘門類型檢查
            passed = True
            if gate_type == RegressionGate.HARD_INVARIANT:
                # 硬約束：必須不變
                passed = absolute_change < 1e-9  # 數值精度
            elif gate_type == RegressionGate.SOFT_KPI:
                # 軟約束：允許小變動
                if tolerance.get("absolute_tolerance"):
                    passed = absolute_change < tolerance["absolute_tolerance"]
                if tolerance.get("relative_tolerance"):
                    passed = passed and (relative_change < tolerance["relative_tolerance"])
            elif gate_type == RegressionGate.MODEL_UPDATE_EXPECTED:
                # 預期變動：允許合理變動但需說明
                if tolerance.get("absolute_tolerance"):
                    passed = absolute_change < tolerance["absolute_tolerance"]
                if tolerance.get("relative_tolerance"):
                    passed = passed and (relative_change < tolerance["relative_tolerance"])
                # 即使通過，也標記為預期變動
                results[kpi_name] = {
                    "status": "passed_with_expected_change" if passed else "failed",
                    "baseline_value": baseline_value,
                    "current_value": current_value,
                    "absolute_change": absolute_change,
                    "relative_change": relative_change,
                    "baseline_version": baseline["model_version"],
                    "current_version": model_version,
                    "gate_type": gate_type,
                    "note": "模型更新預期變動，需說明與簽核"
                }
                gate_results[gate_type]["passed" if passed else "failed"].append(kpi_name)
                if not passed:
                    any_failure = True
                continue
            
            results[kpi_name] = {
                "status": "passed" if passed else "failed",
                "baseline_value": baseline_value,
                "current_value": current_value,
                "absolute_change": absolute_change,
                "relative_change": relative_change,
                "baseline_version": baseline["model_version"],
                "current_version": model_version,
                "gate_type": gate_type,
                "tolerance": tolerance
            }
            
            gate_results[gate_type]["passed" if passed else "failed"].append(kpi_name)
            
            if not passed:
                any_failure = True
        
        return {
            "results": results,
            "any_failure": any_failure,
            "n_checked": len(results),
            "n_passed": sum(1 for r in results.values() if r.get("status") in ["passed", "passed_with_expected_change"]),
            "n_failed": sum(1 for r in results.values() if r.get("status") == "failed"),
            "gate_results": gate_results,
            "summary": {
                "hard_invariant": {
                    "passed": len(gate_results[RegressionGate.HARD_INVARIANT]["passed"]),
                    "failed": len(gate_results[RegressionGate.HARD_INVARIANT]["failed"])
                },
                "soft_kpi": {
                    "passed": len(gate_results[RegressionGate.SOFT_KPI]["passed"]),
                    "failed": len(gate_results[RegressionGate.SOFT_KPI]["failed"])
                },
                "model_update_expected": {
                    "passed": len(gate_results[RegressionGate.MODEL_UPDATE_EXPECTED]["passed"]),
                    "failed": len(gate_results[RegressionGate.MODEL_UPDATE_EXPECTED]["failed"])
                }
            }
        }


# 實例化
reproducibility_pack = ReproducibilityPack()
regression_test = RegressionTest()
