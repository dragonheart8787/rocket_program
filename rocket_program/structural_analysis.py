# -*- coding: utf-8 -*-
"""
結構分析模組：薄壁圓筒應力、屈曲、von Mises 應力場、疲勞壽命、熱應力
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math
import numpy as np

G0 = 9.80665


@dataclass
class StructuralMaterial:
    name: str
    E_Pa: float           # 楊氏模量
    nu: float             # 泊松比
    sigma_y_Pa: float     # 屈服強度
    sigma_u_Pa: float     # 極限強度
    rho_kg_m3: float      # 密度
    alpha_per_K: float    # 熱膨脹係數
    fatigue_S_f: float = 0.0   # 疲勞強度係數 (Paris law C)
    fatigue_b: float = 0.0     # 疲勞指數 (Paris law m)


MATERIAL_DB = {
    "Al7075_T6": StructuralMaterial("Al 7075-T6", 71.7e9, 0.33, 503e6, 572e6, 2810.0, 23.6e-6, 2.0e-11, 3.0),
    "Ti6Al4V": StructuralMaterial("Ti-6Al-4V", 113.8e9, 0.34, 880e6, 950e6, 4430.0, 8.6e-6, 5.0e-12, 3.5),
    "Inconel718": StructuralMaterial("Inconel 718", 205e9, 0.29, 1035e6, 1240e6, 8190.0, 13.0e-6, 1.0e-12, 3.8),
    "SS304": StructuralMaterial("SS 304", 193e9, 0.29, 215e6, 505e6, 8000.0, 17.3e-6, 3.0e-11, 3.2),
    "CFRP": StructuralMaterial("CFRP", 150e9, 0.30, 600e6, 800e6, 1600.0, 2.0e-6, 1e-13, 4.0),
}


@dataclass
class ShellSection:
    """箭體截面"""
    x_from_nose_m: float
    radius_m: float
    thickness_m: float
    material_id: str = "Al7075_T6"
    internal_pressure_Pa: float = 0.0
    axial_force_N: float = 0.0
    bending_moment_Nm: float = 0.0
    temperature_K: float = 300.0
    temperature_inner_K: float = 300.0


@dataclass
class SectionStressResult:
    x_m: float
    sigma_axial_Pa: float      # 軸壓 + 內壓軸向
    sigma_hoop_Pa: float       # 環向應力
    sigma_bending_Pa: float    # 彎曲應力
    sigma_thermal_Pa: float    # 熱應力
    sigma_von_mises_Pa: float  # von Mises 等效應力
    sigma_buckling_Pa: float   # 屈曲臨界應力 (含 knockdown)
    MS_yield: float            # 屈服安全裕度
    MS_buckling: float         # 屈曲安全裕度


@dataclass
class FatigueResult:
    n_cycles_to_failure: float
    damage_per_cycle: float
    cumulative_damage: float
    remaining_life_cycles: float
    crack_growth_rate_m_per_cycle: float
    method: str


@dataclass
class StructuralResult:
    sections: List[SectionStressResult]
    min_MS_yield: float
    min_MS_buckling: float
    critical_section_index: int
    fatigue: Optional[FatigueResult]
    total_structural_mass_kg: float


def compute_section_stress(sec: ShellSection) -> SectionStressResult:
    """計算單截面的應力與安全裕度。"""
    mat = MATERIAL_DB.get(sec.material_id, MATERIAL_DB["Al7075_T6"])
    R = sec.radius_m
    t = sec.thickness_m
    A_cross = 2.0 * math.pi * R * t
    I_section = math.pi * R ** 3 * t  # 薄壁圓筒慣性矩

    # 軸壓
    sigma_axial = sec.axial_force_N / max(A_cross, 1e-12)
    # 環向 (內壓)
    sigma_hoop = sec.internal_pressure_Pa * R / max(t, 1e-9)
    # 彎曲
    sigma_bend = sec.bending_moment_Nm * R / max(I_section, 1e-12)
    # 熱應力
    dT = abs(sec.temperature_K - sec.temperature_inner_K)
    sigma_thermal = mat.E_Pa * mat.alpha_per_K * dT / (1.0 - mat.nu)

    # von Mises (軸壓 + 彎曲 為軸向, 環向為另一主應力)
    sx = sigma_axial + sigma_bend + sigma_thermal
    sy = sigma_hoop
    sigma_vm = math.sqrt(sx * sx - sx * sy + sy * sy)

    # Kármán-Donnell 屈曲 (含 knockdown factor γ ≈ 0.65 for cylinders)
    knockdown = 0.65
    sigma_buck = knockdown * mat.E_Pa / math.sqrt(3.0 * (1.0 - mat.nu ** 2)) * (t / max(R, 1e-9))

    MS_y = mat.sigma_y_Pa / max(sigma_vm, 1.0) - 1.0
    MS_b = sigma_buck / max(abs(sigma_axial), 1.0) - 1.0

    return SectionStressResult(
        x_m=sec.x_from_nose_m,
        sigma_axial_Pa=sigma_axial,
        sigma_hoop_Pa=sigma_hoop,
        sigma_bending_Pa=sigma_bend,
        sigma_thermal_Pa=sigma_thermal,
        sigma_von_mises_Pa=sigma_vm,
        sigma_buckling_Pa=sigma_buck,
        MS_yield=MS_y,
        MS_buckling=MS_b,
    )


def compute_fatigue(
    sigma_max_Pa: float,
    sigma_min_Pa: float = 0.0,
    n_applied_cycles: int = 1000,
    material_id: str = "Al7075_T6",
    initial_crack_m: float = 0.5e-3,
    beta: float = 1.12,
) -> FatigueResult:
    """疲勞壽命：Miner 累積 + Paris-Erdogan 裂紋成長。"""
    mat = MATERIAL_DB.get(material_id, MATERIAL_DB["Al7075_T6"])
    delta_sigma = abs(sigma_max_Pa - sigma_min_Pa)
    # S-N 簡化：N_f = (sigma_u / delta_sigma)^b_inv * 1e6
    b_inv = 8.0  # typical exponent
    N_f = (mat.sigma_u_Pa / max(delta_sigma, 1.0)) ** b_inv * 1e3
    N_f = max(N_f, 1.0)
    damage_per_cycle = 1.0 / N_f
    cumulative = n_applied_cycles * damage_per_cycle

    # Paris-Erdogan: da/dN = C * (ΔK)^m
    delta_K = beta * delta_sigma * math.sqrt(math.pi * initial_crack_m)
    C = mat.fatigue_S_f if mat.fatigue_S_f > 0 else 2e-11
    m = mat.fatigue_b if mat.fatigue_b > 0 else 3.0
    da_dN = C * (delta_K ** m) if delta_K > 0 else 0.0

    return FatigueResult(
        n_cycles_to_failure=N_f,
        damage_per_cycle=damage_per_cycle,
        cumulative_damage=cumulative,
        remaining_life_cycles=max(0.0, (1.0 - cumulative) * N_f),
        crack_growth_rate_m_per_cycle=da_dN,
        method="Miner + Paris-Erdogan",
    )


def analyze_structure(
    sections: List[ShellSection],
    n_fatigue_cycles: int = 1000,
) -> StructuralResult:
    """分析所有截面並彙總。"""
    results: List[SectionStressResult] = []
    for sec in sections:
        results.append(compute_section_stress(sec))

    min_y = min(r.MS_yield for r in results)
    min_b = min(r.MS_buckling for r in results)
    crit_idx = int(np.argmin([r.MS_yield for r in results]))

    # 疲勞分析用最大 von Mises
    vm_max = max(r.sigma_von_mises_Pa for r in results)
    fatigue = compute_fatigue(vm_max, 0.0, n_fatigue_cycles, sections[crit_idx].material_id)

    # 結構質量
    total_mass = 0.0
    for sec in sections:
        mat = MATERIAL_DB.get(sec.material_id, MATERIAL_DB["Al7075_T6"])
        # 該截面對應的長度段（近似 1m 間距或以 x 差計算）
        segment_length = 1.0  # 預設
        total_mass += 2.0 * math.pi * sec.radius_m * sec.thickness_m * segment_length * mat.rho_kg_m3

    return StructuralResult(
        sections=results,
        min_MS_yield=min_y,
        min_MS_buckling=min_b,
        critical_section_index=crit_idx,
        fatigue=fatigue,
        total_structural_mass_kg=total_mass,
    )
