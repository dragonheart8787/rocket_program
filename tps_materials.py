# -*- coding: utf-8 -*-
"""
TPS 材料模型：材料性質隨溫度變化、失效判據、耦合策略
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import numpy as np
import math


@dataclass
class MaterialProperty:
    """材料性質（隨溫度變化）"""
    name: str
    T_ref: float = 300.0  # K
    # 基礎值
    k_ref: float = 0.5  # W/m/K (導熱率)
    c_ref: float = 900.0  # J/kg/K (比熱)
    rho_ref: float = 2000.0  # kg/m³ (密度)
    # 溫度依賴性（分段線性或幂律）
    k_T_coeffs: List[float] = field(default_factory=lambda: [1.0, 0.0])  # k = a + b*T
    c_T_coeffs: List[float] = field(default_factory=lambda: [1.0, 0.0])  # c = a + b*T
    rho_T_coeffs: List[float] = field(default_factory=lambda: [1.0, 0.0])  # rho = a + b*T
    # 失效判據
    T_glass: Optional[float] = None  # K (玻璃化溫度)
    T_melt: Optional[float] = None  # K (熔點)
    T_max_structural: Optional[float] = None  # K (結構允許上限)
    T_max_bond: Optional[float] = None  # K (黏結層上限)

    def thermal_conductivity(self, T: float) -> float:
        """導熱率隨溫度"""
        if len(self.k_T_coeffs) >= 2:
            return self.k_ref * (self.k_T_coeffs[0] + self.k_T_coeffs[1] * (T - self.T_ref) / self.T_ref)
        return self.k_ref

    def specific_heat(self, T: float) -> float:
        """比熱隨溫度"""
        if len(self.c_T_coeffs) >= 2:
            return self.c_ref * (self.c_T_coeffs[0] + self.c_T_coeffs[1] * (T - self.T_ref) / self.T_ref)
        return self.c_ref

    def density(self, T: float) -> float:
        """密度隨溫度（熱膨脹）"""
        if len(self.rho_T_coeffs) >= 2:
            return self.rho_ref * (self.rho_T_coeffs[0] + self.rho_T_coeffs[1] * (T - self.T_ref) / self.T_ref)
        return self.rho_ref

    def check_failure(self, T: float) -> Dict:
        """檢查失效判據"""
        failures = []
        warnings = []
        
        if self.T_melt and T >= self.T_melt:
            failures.append(f"超過熔點 T_melt = {self.T_melt} K")
        elif self.T_glass and T >= self.T_glass:
            warnings.append(f"超過玻璃化溫度 T_glass = {self.T_glass} K")
        
        if self.T_max_structural and T >= self.T_max_structural:
            failures.append(f"超過結構允許上限 T_max = {self.T_max_structural} K")
        
        if self.T_max_bond and T >= self.T_max_bond:
            failures.append(f"超過黏結層上限 T_bond = {self.T_max_bond} K")
        
        return {
            "failed": len(failures) > 0,
            "failures": failures,
            "warnings": warnings,
            "T": T,
            "margin": self.T_max_structural - T if self.T_max_structural else None
        }


@dataclass
class MaterialStrengthDegradation:
    """材料強度隨溫度折減"""
    T_ref: float = 300.0
    sigma_y_ref: float = 300e6  # Pa (屈服強度)
    E_ref: float = 200e9  # Pa (彈性模數)
    # 折減模型（簡化：線性）
    sigma_y_T_factor: float = 0.5  # 每 1000K 折減因子
    E_T_factor: float = 0.3

    def yield_strength(self, T: float) -> float:
        """屈服強度隨溫度"""
        if T <= self.T_ref:
            return self.sigma_y_ref
        # 簡化：線性折減
        T_ratio = (T - self.T_ref) / 1000.0
        factor = max(0.1, 1.0 - self.sigma_y_T_factor * T_ratio)
        return self.sigma_y_ref * factor

    def elastic_modulus(self, T: float) -> float:
        """彈性模數隨溫度"""
        if T <= self.T_ref:
            return self.E_ref
        T_ratio = (T - self.T_ref) / 1000.0
        factor = max(0.1, 1.0 - self.E_T_factor * T_ratio)
        return self.E_ref * factor


class TPSMaterialLibrary:
    """TPS 材料庫"""

    def __init__(self):
        self.materials: Dict[str, MaterialProperty] = {}
        self.strength_models: Dict[str, MaterialStrengthDegradation] = {}

    def register_material(self, name: str, material: MaterialProperty):
        """註冊材料"""
        self.materials[name] = material

    def register_strength_model(self, name: str, model: MaterialStrengthDegradation):
        """註冊強度折減模型"""
        self.strength_models[name] = model

    def get_material(self, name: str) -> Optional[MaterialProperty]:
        """獲取材料"""
        return self.materials.get(name)

    def get_strength_model(self, name: str) -> Optional[MaterialStrengthDegradation]:
        """獲取強度模型"""
        return self.strength_models.get(name)

    def create_default_materials(self):
        """創建預設材料（佔位）"""
        # 碳-碳複合材料（佔位）
        c_carbon = MaterialProperty(
            name="C-C_composite",
            k_ref=50.0,
            c_ref=700.0,
            rho_ref=1800.0,
            T_melt=3800.0,
            T_max_structural=2500.0,
            T_max_bond=2000.0
        )
        self.register_material("C-C", c_carbon)
        
        # 陶瓷瓦（佔位）
        ceramic = MaterialProperty(
            name="ceramic_tile",
            k_ref=0.1,
            c_ref=1000.0,
            rho_ref=150.0,
            T_glass=1200.0,
            T_max_structural=1500.0
        )
        self.register_material("ceramic", ceramic)


class TPSFailureAnalysis:
    """TPS 失效分析"""

    def __init__(self, material_lib: TPSMaterialLibrary):
        self.material_lib = material_lib

    def analyze_thermal_failure(self, material_name: str, T_w: float, T_int: float) -> Dict:
        """分析熱失效"""
        material = self.material_lib.get_material(material_name)
        if not material:
            return {"error": f"材料 {material_name} 不存在"}
        
        surface_failure = material.check_failure(T_w)
        internal_failure = material.check_failure(T_int)
        
        return {
            "material": material_name,
            "surface": surface_failure,
            "internal": internal_failure,
            "overall_failed": surface_failure["failed"] or internal_failure["failed"]
        }

    def analyze_structural_degradation(self, material_name: str, T: float, 
                                      stress_applied: float) -> Dict:
        """分析結構強度折減"""
        strength_model = self.material_lib.get_strength_model(material_name)
        if not strength_model:
            return {"error": f"強度模型 {material_name} 不存在"}
        
        sigma_y = strength_model.yield_strength(T)
        E = strength_model.elastic_modulus(T)
        
        MS = (sigma_y / max(stress_applied, 1e-9)) - 1.0
        
        return {
            "material": material_name,
            "T": T,
            "sigma_y_at_T": sigma_y,
            "E_at_T": E,
            "stress_applied": stress_applied,
            "margin_of_safety": MS,
            "failed": MS < 0.0
        }

    def coupled_thermal_structural(self, material_name: str, T_w: float, 
                                   stress_applied: float) -> Dict:
        """熱-結構耦合分析"""
        thermal = self.analyze_thermal_failure(material_name, T_w, T_w)
        structural = self.analyze_structural_degradation(material_name, T_w, stress_applied)
        
        return {
            "thermal": thermal,
            "structural": structural,
            "coupled_failed": thermal.get("overall_failed", False) or structural.get("failed", False)
        }


# 實例化
tps_material_lib = TPSMaterialLibrary()
tps_material_lib.create_default_materials()
tps_failure = TPSFailureAnalysis(tps_material_lib)
