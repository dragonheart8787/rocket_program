# -*- coding: utf-8 -*-
"""
資料契約與版本控管：氣動係數、模型版本、適用範圍、一致性檢查
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import numpy as np
import json
from datetime import datetime


@dataclass
class AeroCoefficientSchema:
    """氣動係數資料契約"""
    name: str
    version: str
    Mach_range: Tuple[float, float]
    Re_range: Tuple[float, float]
    alpha_range: Tuple[float, float]  # deg
    beta_range: Tuple[float, float]   # deg
    grid_Mach: np.ndarray
    grid_alpha: np.ndarray
    C_L_table: np.ndarray
    C_D_table: np.ndarray
    C_m_table: np.ndarray
    grid_Re: Optional[np.ndarray] = None
    interpolation_method: str = "bilinear"  # "bilinear", "cubic", etc.
    extrapolation_strategy: str = "clamp"   # "clamp", "linear", "forbid"
    source: str = "placeholder"  # "CFD", "wind_tunnel", "surrogate", "placeholder"
    date: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().isoformat()

    def validate_input(self, M: float, alpha: float, Re: float, beta: float) -> Dict:
        """驗證輸入是否在適用範圍內"""
        errors = []
        warnings = []
        
        if not (self.Mach_range[0] <= M <= self.Mach_range[1]):
            errors.append(f"Mach {M:.3f} 超出範圍 [{self.Mach_range[0]}, {self.Mach_range[1]}]")
        
        alpha_deg = np.degrees(alpha)
        if not (self.alpha_range[0] <= alpha_deg <= self.alpha_range[1]):
            errors.append(f"Alpha {alpha_deg:.2f}° 超出範圍 [{self.alpha_range[0]}, {self.alpha_range[1]}]")
        
        if self.grid_Re is not None:
            if not (self.Re_range[0] <= Re <= self.Re_range[1]):
                warnings.append(f"Re {Re:.2e} 超出範圍 [{self.Re_range[0]:.2e}, {self.Re_range[1]:.2e}]")
        
        beta_deg = np.degrees(beta)
        if not (self.beta_range[0] <= beta_deg <= self.beta_range[1]):
            warnings.append(f"Beta {beta_deg:.2f}° 超出範圍 [{self.beta_range[0]}, {self.beta_range[1]}]")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def check_physical_sanity(self) -> Dict:
        """物理合理性檢查"""
        issues = []
        
        # C_D 應 >= 0
        if np.any(self.C_D_table < 0):
            issues.append("C_D 有負值（不合理）")
        
        # 高 Mach 時 C_D 應上升（波阻）
        if len(self.grid_Mach) > 1:
            M_supersonic = self.grid_Mach[self.grid_Mach > 1.0]
            if len(M_supersonic) > 0:
                idx_sup = np.where(self.grid_Mach > 1.0)[0]
                C_D_sup = self.C_D_table[:, idx_sup]
                if np.any(np.diff(C_D_sup, axis=1) < 0):
                    issues.append("超音速區 C_D 未單調上升（波阻不合理）")
        
        # C_M_alpha 符號一致性（通常 < 0 為穩定）
        # 簡化檢查
        
        return {
            "sane": len(issues) == 0,
            "issues": issues
        }


@dataclass
class ModelVersion:
    """模型版本資訊"""
    model_name: str
    version: str
    date: str
    author: str = ""
    changes: str = ""
    applicable_range: Dict = field(default_factory=dict)
    validation_status: str = "unvalidated"  # "unvalidated", "partial", "validated"
    reference: str = ""

    def to_dict(self) -> dict:
        """轉換為字典（用於 JSON 序列化）"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "date": self.date,
            "author": self.author,
            "changes": self.changes,
            "applicable_range": self.applicable_range,
            "validation_status": self.validation_status,
            "reference": self.reference
        }


class DataVersionControl:
    """資料版本控管"""

    def __init__(self):
        self.versions: Dict[str, List[ModelVersion]] = {}

    def register_version(self, model_name: str, version: ModelVersion):
        """註冊模型版本"""
        if model_name not in self.versions:
            self.versions[model_name] = []
        self.versions[model_name].append(version)

    def get_latest_version(self, model_name: str) -> Optional[ModelVersion]:
        """獲取最新版本"""
        if model_name in self.versions and len(self.versions[model_name]) > 0:
            return self.versions[model_name][-1]
        return None

    def get_version_history(self, model_name: str) -> List[ModelVersion]:
        """獲取版本歷史"""
        return self.versions.get(model_name, [])

    def export_versions(self, filepath: str):
        """匯出版本資訊到 JSON"""
        data = {}
        for model_name, versions in self.versions.items():
            data[model_name] = [v.to_dict() for v in versions]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class AeroDataManager:
    """氣動資料管理器"""

    def __init__(self):
        self.schemas: Dict[str, AeroCoefficientSchema] = {}
        self.version_control = DataVersionControl()

    def register_schema(self, name: str, schema: AeroCoefficientSchema):
        """註冊氣動係數 schema"""
        self.schemas[name] = schema
        
        # 註冊版本
        version = ModelVersion(
            model_name=name,
            version=schema.version,
            date=schema.date,
            applicable_range={
                "Mach": schema.Mach_range,
                "Re": schema.Re_range,
                "alpha": schema.alpha_range
            },
            validation_status="unvalidated"
        )
        self.version_control.register_version(name, version)

    def get_schema(self, name: str) -> Optional[AeroCoefficientSchema]:
        """獲取 schema"""
        return self.schemas.get(name)

    def validate_interpolation(self, schema: AeroCoefficientSchema, M: float, alpha: float, 
                             Re: float, beta: float) -> Dict:
        """驗證插值輸入並執行插值"""
        # 輸入驗證
        validation = schema.validate_input(M, alpha, Re, beta)
        if not validation["valid"]:
            return {
                "valid": False,
                "errors": validation["errors"],
                "coeffs": None
            }
        
        # 執行插值（簡化：雙線性）
        # 實際應根據 interpolation_method 選擇方法
        
        # 外插處理
        if schema.extrapolation_strategy == "forbid":
            if not validation["valid"]:
                return {"valid": False, "errors": ["外插被禁止"], "coeffs": None}
        elif schema.extrapolation_strategy == "clamp":
            M = np.clip(M, schema.Mach_range[0], schema.Mach_range[1])
            alpha = np.clip(np.degrees(alpha), schema.alpha_range[0], schema.alpha_range[1])
        
        # 執行插值（佔位）
        C_L = 0.0
        C_D = 0.0
        C_m = 0.0
        
        return {
            "valid": True,
            "warnings": validation["warnings"],
            "coeffs": {"C_L": C_L, "C_D": C_D, "C_m": C_m}
        }


# 實例化
data_version_control = DataVersionControl()
aero_data_manager = AeroDataManager()
