# -*- coding: utf-8 -*-
"""
熱力分析模組：再生冷卻、輻射冷卻、燒蝕 TPS、噴管壁溫分佈
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import math
import numpy as np

SIGMA_SB = 5.670374419e-8  # Stefan-Boltzmann W/(m^2 K^4)


@dataclass
class CoolantProperties:
    """冷卻劑性質"""
    name: str
    cp_J_kgK: float
    rho_kg_m3: float
    mu_Pa_s: float      # 動力黏度
    k_W_mK: float       # 熱傳導率
    T_inlet_K: float
    T_boiling_K: float


COOLANT_DB = {
    "RP1": CoolantProperties("RP-1", 2010.0, 810.0, 0.0012, 0.12, 300.0, 489.0),
    "LH2": CoolantProperties("LH2", 14300.0, 70.8, 1.3e-5, 0.10, 20.0, 20.3),
    "LOX": CoolantProperties("LOX", 1700.0, 1141.0, 0.0002, 0.15, 90.0, 90.2),
    "CH4": CoolantProperties("CH4", 3500.0, 422.0, 0.0001, 0.19, 111.0, 111.7),
}


@dataclass
class RegenerativeCoolingResult:
    """再生冷卻結果"""
    wall_temps_K: np.ndarray     # 沿軸向壁溫
    coolant_temps_K: np.ndarray  # 冷卻劑溫度
    heat_flux_W_m2: np.ndarray
    x_stations_m: np.ndarray
    max_wall_temp_K: float
    coolant_outlet_temp_K: float
    total_heat_load_W: float
    coolant_velocity_m_s: float
    margin_K: float              # max_wall_temp 相對材料限制的裕度


@dataclass
class RadiativeCoolingResult:
    equilibrium_temp_K: float
    heat_radiated_W_m2: float
    emissivity: float


@dataclass
class AblativeTPSResult:
    required_thickness_m: float
    mass_kg: float
    recession_rate_m_s: float
    surface_temp_K: float
    exposure_time_s: float


@dataclass
class NozzleThermalProfile:
    x_m: np.ndarray
    gas_temp_K: np.ndarray
    wall_temp_K: np.ndarray
    heat_flux_W_m2: np.ndarray
    mach_number: np.ndarray


@dataclass
class ThermalResult:
    regen_cooling: Optional[RegenerativeCoolingResult]
    radiative: Optional[RadiativeCoolingResult]
    ablative_tps: Optional[AblativeTPSResult]
    nozzle_profile: Optional[NozzleThermalProfile]
    max_wall_temp_K: float
    thermal_margin_K: float
    tps_mass_kg: float


def analyze_regenerative_cooling(
    T_c_K: float,
    p_c_Pa: float,
    mdot_coolant_kg_s: float,
    nozzle_x_m: np.ndarray,
    nozzle_r_m: np.ndarray,
    gamma: float = 1.2,
    coolant_id: str = "RP1",
    wall_thickness_m: float = 0.002,
    wall_k_W_mK: float = 25.0,
    T_wall_limit_K: float = 900.0,
) -> RegenerativeCoolingResult:
    """再生冷卻：計算壁溫、冷卻劑溫度沿軸向分佈。"""
    cool = COOLANT_DB.get(coolant_id, COOLANT_DB["RP1"])
    n = len(nozzle_x_m)
    wall_T = np.zeros(n)
    cool_T = np.zeros(n)
    q_flux = np.zeros(n)
    T_cool = cool.T_inlet_K

    r_t = np.min(nozzle_r_m)
    A_channel = 2.0 * math.pi * r_t * 0.003  # 通道截面近似
    v_cool = mdot_coolant_kg_s / (cool.rho_kg_m3 * max(A_channel, 1e-9))

    for i in range(n):
        r = max(nozzle_r_m[i], 0.001)
        local_ratio = (r_t / r) ** 0.8
        # Bartz 近似：h_g ∝ (p_c^0.8 / D_t^0.2) * (r_t/r)^0.8
        h_g = 0.026 * (p_c_Pa ** 0.8) / (2.0 * r_t) ** 0.2 * local_ratio * 0.001
        T_aw = T_c_K * (1.0 + 0.85 * (gamma - 1.0) / 2.0 * (r_t / r) ** 2) / (
            1.0 + (gamma - 1.0) / 2.0 * (r_t / r) ** 2
        )
        T_aw = min(T_aw, T_c_K)

        # 冷卻側熱傳係數（Dittus-Boelter）
        Re = cool.rho_kg_m3 * v_cool * 0.006 / max(cool.mu_Pa_s, 1e-9)
        Pr = cool.cp_J_kgK * cool.mu_Pa_s / max(cool.k_W_mK, 1e-9)
        Nu = 0.023 * Re ** 0.8 * Pr ** 0.4
        h_c = Nu * cool.k_W_mK / 0.006

        # 總熱阻
        R_total = 1.0 / max(h_g, 1.0) + wall_thickness_m / wall_k_W_mK + 1.0 / max(h_c, 1.0)
        q = (T_aw - T_cool) / R_total
        q = max(q, 0.0)

        T_wall_hot = T_aw - q / max(h_g, 1.0)
        wall_T[i] = T_wall_hot
        cool_T[i] = T_cool
        q_flux[i] = q

        if i < n - 1:
            dx = abs(nozzle_x_m[i + 1] - nozzle_x_m[i])
            perimeter = 2.0 * math.pi * r
            dQ = q * perimeter * dx
            T_cool += dQ / (mdot_coolant_kg_s * cool.cp_J_kgK)
            T_cool = min(T_cool, cool.T_boiling_K * 0.95)

    max_Tw = float(np.max(wall_T))
    return RegenerativeCoolingResult(
        wall_temps_K=wall_T,
        coolant_temps_K=cool_T,
        heat_flux_W_m2=q_flux,
        x_stations_m=nozzle_x_m,
        max_wall_temp_K=max_Tw,
        coolant_outlet_temp_K=float(cool_T[-1]),
        total_heat_load_W=float((getattr(np, "trapezoid", None) or getattr(np, "trapz"))(q_flux * 2.0 * math.pi * nozzle_r_m, nozzle_x_m)),
        coolant_velocity_m_s=v_cool,
        margin_K=T_wall_limit_K - max_Tw,
    )


def analyze_radiative_cooling(
    heat_flux_W_m2: float,
    emissivity: float = 0.85,
    T_env_K: float = 3.0,
) -> RadiativeCoolingResult:
    """輻射冷卻平衡溫度。"""
    # q_in = ε σ (T^4 - T_env^4) => T = (q_in/(ε σ) + T_env^4)^0.25
    T_eq = (heat_flux_W_m2 / (emissivity * SIGMA_SB) + T_env_K ** 4) ** 0.25
    q_rad = emissivity * SIGMA_SB * (T_eq ** 4 - T_env_K ** 4)
    return RadiativeCoolingResult(
        equilibrium_temp_K=T_eq, heat_radiated_W_m2=q_rad, emissivity=emissivity,
    )


def analyze_ablative_tps(
    heat_flux_W_m2: float,
    exposure_time_s: float,
    ablation_enthalpy_J_kg: float = 8e6,
    density_kg_m3: float = 1400.0,
    area_m2: float = 1.0,
    T_surface_limit_K: float = 3000.0,
) -> AblativeTPSResult:
    """燒蝕 TPS 厚度估算。"""
    recession_rate = heat_flux_W_m2 / (density_kg_m3 * ablation_enthalpy_J_kg)
    thickness = recession_rate * exposure_time_s * 1.5  # 1.5x 安全係數
    mass = thickness * area_m2 * density_kg_m3
    T_surf = min(T_surface_limit_K, (heat_flux_W_m2 / (0.9 * SIGMA_SB)) ** 0.25)

    return AblativeTPSResult(
        required_thickness_m=thickness,
        mass_kg=mass,
        recession_rate_m_s=recession_rate,
        surface_temp_K=T_surf,
        exposure_time_s=exposure_time_s,
    )


def compute_nozzle_thermal_profile(
    T_c_K: float,
    gamma: float,
    nozzle_x_m: np.ndarray,
    nozzle_r_m: np.ndarray,
    regen_result: Optional[RegenerativeCoolingResult] = None,
) -> NozzleThermalProfile:
    """噴管沿軸向的氣體溫度、壁溫、熱通量。"""
    r_t = float(np.min(nozzle_r_m))
    n = len(nozzle_x_m)
    M = np.zeros(n)
    T_gas = np.zeros(n)
    for i in range(n):
        r = max(nozzle_r_m[i], 0.001)
        area_ratio = (r / r_t) ** 2
        M_local = 1.0 + (area_ratio - 1.0) * 0.5 if area_ratio >= 1.0 else 0.5 + 0.5 / max(area_ratio, 0.1)
        M[i] = max(M_local, 0.1)
        T_gas[i] = T_c_K / (1.0 + 0.5 * (gamma - 1.0) * M[i] ** 2)

    wall_T = regen_result.wall_temps_K if regen_result is not None else T_gas * 0.8
    q_flux = regen_result.heat_flux_W_m2 if regen_result is not None else np.zeros(n)

    return NozzleThermalProfile(
        x_m=nozzle_x_m, gas_temp_K=T_gas, wall_temp_K=wall_T,
        heat_flux_W_m2=q_flux, mach_number=M,
    )


def run_thermal_analysis(
    T_c_K: float,
    p_c_Pa: float,
    mdot_kg_s: float,
    gamma: float,
    nozzle_x_m: np.ndarray,
    nozzle_r_m: np.ndarray,
    coolant_id: str = "RP1",
    wall_limit_K: float = 900.0,
    exposure_s: float = 180.0,
) -> ThermalResult:
    """一鍵執行完整熱分析。"""
    regen = analyze_regenerative_cooling(
        T_c_K, p_c_Pa, mdot_kg_s * 0.4, nozzle_x_m, nozzle_r_m,
        gamma=gamma, coolant_id=coolant_id, T_wall_limit_K=wall_limit_K,
    )
    rad = analyze_radiative_cooling(float(np.max(regen.heat_flux_W_m2)))
    noz = compute_nozzle_thermal_profile(T_c_K, gamma, nozzle_x_m, nozzle_r_m, regen)
    abl = analyze_ablative_tps(float(np.max(regen.heat_flux_W_m2)), exposure_s)

    return ThermalResult(
        regen_cooling=regen,
        radiative=rad,
        ablative_tps=abl,
        nozzle_profile=noz,
        max_wall_temp_K=regen.max_wall_temp_K,
        thermal_margin_K=regen.margin_K,
        tps_mass_kg=abl.mass_kg,
    )
