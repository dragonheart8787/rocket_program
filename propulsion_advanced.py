# -*- coding: utf-8 -*-
"""
推進系統進階模組：燃燒室、噴注器、渦輪泵、燃燒穩定性、Rao 噴管輪廓
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
from enum import Enum
import math
import numpy as np

G0 = 9.80665


class PropulsionCycle(Enum):
    PRESSURE_FED = "PressureFed"
    GAS_GENERATOR = "GasGenerator"
    STAGED_COMBUSTION = "StagedCombustion"
    FULL_FLOW = "FullFlow"
    EXPANDER = "Expander"


CYCLE_CHARACTERISTICS = {
    PropulsionCycle.PRESSURE_FED: {"complexity": 1, "isp_penalty": 0.92, "max_pc_MPa": 3.0},
    PropulsionCycle.GAS_GENERATOR: {"complexity": 2, "isp_penalty": 0.95, "max_pc_MPa": 12.0},
    PropulsionCycle.STAGED_COMBUSTION: {"complexity": 4, "isp_penalty": 0.98, "max_pc_MPa": 25.0},
    PropulsionCycle.FULL_FLOW: {"complexity": 5, "isp_penalty": 0.99, "max_pc_MPa": 30.0},
    PropulsionCycle.EXPANDER: {"complexity": 3, "isp_penalty": 0.96, "max_pc_MPa": 8.0},
}


@dataclass
class CombustionChamberSpec:
    p_c_Pa: float
    T_c_K: float
    mdot_kg_s: float
    gamma: float = 1.2
    R_gas: float = 350.0
    L_star_m: float = 1.0  # 特徵長度 L* (通常 0.8–3.0 m)
    contraction_ratio: float = 3.0  # A_c / A_t


@dataclass
class CombustionChamberResult:
    A_t_m2: float
    D_t_m: float
    A_c_m2: float
    D_c_m: float
    V_c_m3: float
    L_c_m: float
    L_star_m: float
    c_star_m_s: float
    stay_time_ms: float


@dataclass
class InjectorResult:
    n_elements: int
    orifice_diameter_mm: float
    injection_velocity_m_s: float
    pressure_drop_ratio: float
    spray_angle_deg: float
    pattern: str


@dataclass
class TurbopumpResult:
    pump_power_kW: float
    turbine_power_kW: float
    shaft_speed_rpm: float
    pump_delta_p_Pa: float
    npsh_required_m: float
    npsh_available_m: float
    cavitation_margin: float
    efficiency: float


@dataclass
class CombustionStabilityResult:
    first_tangential_freq_Hz: float
    first_longitudinal_freq_Hz: float
    crocco_n: float
    crocco_tau_ms: float
    stability_margin: float
    is_stable: bool
    note: str


@dataclass
class NozzleContourResult:
    x_m: np.ndarray
    r_m: np.ndarray
    theta_init_deg: float
    theta_exit_deg: float
    L_nozzle_m: float
    expansion_ratio: float


@dataclass
class PropulsionSystemResult:
    cycle: PropulsionCycle
    chamber: CombustionChamberResult
    injector: InjectorResult
    turbopump: Optional[TurbopumpResult]
    stability: CombustionStabilityResult
    nozzle: NozzleContourResult
    F_vac_N: float
    F_sea_N: float
    I_sp_vac_s: float
    I_sp_sea_s: float
    mdot_kg_s: float


def design_combustion_chamber(spec: CombustionChamberSpec) -> CombustionChamberResult:
    """設計燃燒室：由 p_c, T_c, mdot 計算幾何。"""
    g = spec.gamma
    R = spec.R_gas
    T = spec.T_c_K
    pc = spec.p_c_Pa
    mdot = spec.mdot_kg_s

    exp_c = (g + 1.0) / (2.0 * (g - 1.0))
    c_star = math.sqrt(g * R * T) / (g * math.sqrt((2.0 / (g + 1.0)) ** ((g + 1.0) / (g - 1.0))))
    A_t = mdot * c_star / pc
    A_c = A_t * spec.contraction_ratio
    D_t = math.sqrt(4.0 * A_t / math.pi)
    D_c = math.sqrt(4.0 * A_c / math.pi)
    V_c = A_t * spec.L_star_m
    L_c = V_c / A_c
    rho_c = pc / (R * T)
    stay_time = rho_c * V_c / mdot * 1000.0  # ms

    return CombustionChamberResult(
        A_t_m2=A_t, D_t_m=D_t, A_c_m2=A_c, D_c_m=D_c,
        V_c_m3=V_c, L_c_m=L_c, L_star_m=spec.L_star_m,
        c_star_m_s=c_star, stay_time_ms=stay_time,
    )


def design_injector(
    mdot_kg_s: float,
    p_c_Pa: float,
    rho_prop: float = 1000.0,
    pressure_drop_ratio: float = 0.20,
    element_mdot_kg_s: float = 0.5,
) -> InjectorResult:
    """噴注器設計。"""
    dp = pressure_drop_ratio * p_c_Pa
    v_inj = math.sqrt(2.0 * dp / max(rho_prop, 1.0))
    n_elem = max(1, int(math.ceil(mdot_kg_s / element_mdot_kg_s)))
    mdot_per = mdot_kg_s / n_elem
    A_orifice = mdot_per / (rho_prop * v_inj)
    d_orifice_mm = math.sqrt(4.0 * A_orifice / math.pi) * 1000.0
    spray_angle = 30.0 + 20.0 * pressure_drop_ratio

    return InjectorResult(
        n_elements=n_elem,
        orifice_diameter_mm=d_orifice_mm,
        injection_velocity_m_s=v_inj,
        pressure_drop_ratio=pressure_drop_ratio,
        spray_angle_deg=spray_angle,
        pattern="coaxial_swirl" if n_elem > 20 else "impinging_doublet",
    )


def design_turbopump(
    mdot_kg_s: float,
    p_c_Pa: float,
    tank_pressure_Pa: float = 300000.0,
    rho_prop: float = 1000.0,
    eta_pump: float = 0.70,
    eta_turbine: float = 0.65,
    npsh_available_m: float = 15.0,
) -> TurbopumpResult:
    """渦輪泵設計。"""
    dp = p_c_Pa * 1.3 - tank_pressure_Pa
    Q = mdot_kg_s / rho_prop
    P_pump = dp * Q / eta_pump
    P_turbine = P_pump / eta_turbine
    head = dp / (rho_prop * G0)
    # 轉速估計：典型火箭泵 10000–40000 rpm，由 Ns 經驗公式反推
    Ns_dim = 25.0  # 量綱比轉速 (US customary ~1500–4000)
    Q_gpm = Q * 15850.3  # m^3/s -> gpm
    head_ft = head * 3.28084
    rpm = Ns_dim * head_ft ** 0.75 / max(Q_gpm ** 0.5, 1e-6)
    rpm = max(5000.0, min(rpm, 50000.0))
    npsh_req = 0.1 * head

    return TurbopumpResult(
        pump_power_kW=P_pump / 1000.0,
        turbine_power_kW=P_turbine / 1000.0,
        shaft_speed_rpm=rpm,
        pump_delta_p_Pa=dp,
        npsh_required_m=npsh_req,
        npsh_available_m=npsh_available_m,
        cavitation_margin=npsh_available_m / max(npsh_req, 1e-9),
        efficiency=eta_pump,
    )


def analyze_combustion_stability(
    D_c_m: float,
    L_c_m: float,
    c_star_m_s: float,
    gamma: float = 1.2,
    n_crocco: float = 0.5,
    tau_crocco_ms: float = 1.0,
) -> CombustionStabilityResult:
    """燃燒穩定性分析（Crocco 時延模型 + 聲學模態）。"""
    a = c_star_m_s * math.sqrt(gamma)  # 近似音速
    # 第一切向模態：f_1T ≈ 1.84 * a / (pi * D_c)
    f_1T = 1.84 * a / (math.pi * D_c_m)
    # 第一縱向模態：f_1L = a / (2 * L_c)
    f_1L = a / (2.0 * max(L_c_m, 0.01))
    tau_s = tau_crocco_ms / 1000.0
    # Crocco stability: n < 1/(2*pi*f*tau) for stability
    critical_n_1T = 1.0 / (2.0 * math.pi * f_1T * tau_s) if f_1T * tau_s > 0 else 10.0
    margin = (critical_n_1T - n_crocco) / max(critical_n_1T, 1e-9)
    stable = n_crocco < critical_n_1T

    return CombustionStabilityResult(
        first_tangential_freq_Hz=f_1T,
        first_longitudinal_freq_Hz=f_1L,
        crocco_n=n_crocco,
        crocco_tau_ms=tau_crocco_ms,
        stability_margin=margin,
        is_stable=stable,
        note="穩定" if stable else "需加裝擋板或聲學腔",
    )


def design_rao_nozzle(
    r_t_m: float,
    expansion_ratio: float,
    theta_n_deg: float = 30.0,
    theta_e_deg: float = 8.0,
    n_points: int = 80,
) -> NozzleContourResult:
    """
    Rao 最佳化噴管輪廓（簡化拋物線近似）。
    使用初始膨脹角 theta_n 與出口角 theta_e 的拋物線內插。
    """
    r_e = r_t_m * math.sqrt(expansion_ratio)
    # 噴管長度（Rao 80% bell 長度）
    L_cone_15 = (r_e - r_t_m) / math.tan(math.radians(15.0))
    L_nozzle = 0.80 * L_cone_15

    t = np.linspace(0.0, 1.0, n_points)
    theta_n_r = math.radians(theta_n_deg)
    theta_e_r = math.radians(theta_e_deg)

    # 拋物線近似 (Rao bell)
    x_n = np.zeros(n_points)
    r_n = np.zeros(n_points)
    for i, ti in enumerate(t):
        theta = theta_n_r * (1.0 - ti) + theta_e_r * ti
        x_n[i] = L_nozzle * ti
        r_n[i] = r_t_m + (r_e - r_t_m) * (3.0 * ti * ti - 2.0 * ti * ti * ti)

    return NozzleContourResult(
        x_m=x_n, r_m=r_n,
        theta_init_deg=theta_n_deg, theta_exit_deg=theta_e_deg,
        L_nozzle_m=L_nozzle, expansion_ratio=expansion_ratio,
    )


def design_propulsion_system(
    F_vac_N: float,
    p_c_Pa: float,
    expansion_ratio: float,
    cycle: PropulsionCycle = PropulsionCycle.GAS_GENERATOR,
    gamma: float = 1.2,
    R_gas: float = 350.0,
    T_c_K: float = 3500.0,
    L_star_m: float = 1.0,
    p_ambient_Pa: float = 101325.0,
) -> PropulsionSystemResult:
    """一鍵設計完整推進系統。"""
    cyc = CYCLE_CHARACTERISTICS[cycle]
    eta = cyc["isp_penalty"]

    exp_c = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    # c* = sqrt(gamma * R * T_c) / (gamma * sqrt((2/(gamma+1))^((gamma+1)/(gamma-1))))
    # 等同 c* = p_c * A_t / mdot = sqrt(R*T_c) / (gamma * sqrt((2/(g+1))^((g+1)/(g-1))))
    inner = (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
    c_star_ideal = math.sqrt(R_gas * T_c_K / gamma) / math.sqrt(inner)
    c_star = c_star_ideal * eta

    # 出口 Mach
    def area_ratio_func(M):
        v = 1.0 + 0.5 * (gamma - 1.0) * M * M
        return (1.0 / M) * ((2.0 / (gamma + 1.0)) * v) ** exp_c

    M_e = 2.0
    for _ in range(100):
        f = area_ratio_func(M_e) - expansion_ratio
        dM = M_e * 1e-6
        fp = (area_ratio_func(M_e + dM) - area_ratio_func(M_e - dM)) / (2.0 * dM)
        M_e -= f / max(abs(fp), 1e-12)
        M_e = max(M_e, 1.01)
        if abs(f) < 1e-8:
            break

    p_e = p_c_Pa * (1.0 + 0.5 * (gamma - 1.0) * M_e ** 2) ** (-gamma / (gamma - 1.0))
    T_e = T_c_K * (p_e / p_c_Pa) ** ((gamma - 1.0) / gamma)
    v_e = M_e * math.sqrt(gamma * R_gas * T_e) * eta

    # C_F: momentum + pressure terms (A_e/A_t = expansion_ratio)
    term1 = (2.0 * gamma ** 2) / (gamma - 1.0)
    term2 = (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
    term3 = 1.0 - (p_e / p_c_Pa) ** ((gamma - 1.0) / gamma)
    C_F_momentum = math.sqrt(max(term1 * term2 * term3, 0.0))
    C_F_pressure = (p_e / p_c_Pa) * expansion_ratio  # vacuum: p_a = 0
    C_F_vac = C_F_momentum + C_F_pressure
    A_t = F_vac_N / (C_F_vac * p_c_Pa * eta)
    mdot = p_c_Pa * A_t / c_star

    F_vac = C_F_vac * p_c_Pa * A_t * eta
    C_F_sea = C_F_vac - p_ambient_Pa * A_t * expansion_ratio / (p_c_Pa * A_t)
    F_sea = C_F_sea * p_c_Pa * A_t * eta

    I_sp_vac = F_vac / (mdot * G0)
    I_sp_sea = F_sea / (mdot * G0)

    # Sub-designs
    chamber_spec = CombustionChamberSpec(p_c_Pa, T_c_K, mdot, gamma, R_gas, L_star_m)
    chamber = design_combustion_chamber(chamber_spec)
    injector = design_injector(mdot, p_c_Pa)
    tp = None
    if cycle != PropulsionCycle.PRESSURE_FED:
        tp = design_turbopump(mdot, p_c_Pa)
    stability = analyze_combustion_stability(chamber.D_c_m, chamber.L_c_m, c_star, gamma,
                                              n_crocco=0.3, tau_crocco_ms=0.5)
    r_t = math.sqrt(A_t / math.pi)
    nozzle = design_rao_nozzle(r_t, expansion_ratio)

    return PropulsionSystemResult(
        cycle=cycle, chamber=chamber, injector=injector, turbopump=tp,
        stability=stability, nozzle=nozzle,
        F_vac_N=F_vac, F_sea_N=F_sea, I_sp_vac_s=I_sp_vac, I_sp_sea_s=I_sp_sea,
        mdot_kg_s=mdot,
    )
