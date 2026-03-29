# -*- coding: utf-8 -*-
"""
任務規劃模組：ΔV 預算、多級質量最佳化、質量分配、發射窗口
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math
import numpy as np


G0 = 9.80665
MU_EARTH = 3.986004418e14  # m^3/s^2
R_EARTH = 6371000.0


class OrbitType(Enum):
    LEO = "LEO"
    SSO = "SSO"
    GTO = "GTO"
    GEO = "GEO"
    TLI = "TLI"
    SUBORBITAL = "Suborbital"


# Typical ΔV budgets (m/s) for reference
ORBIT_DV_REFERENCE = {
    OrbitType.LEO: 9400.0,
    OrbitType.SSO: 9800.0,
    OrbitType.GTO: 12000.0,
    OrbitType.GEO: 14000.0,
    OrbitType.TLI: 15900.0,
    OrbitType.SUBORBITAL: 3000.0,
}


@dataclass
class MissionSpec:
    """任務規格"""
    orbit_type: OrbitType
    target_altitude_km: float
    payload_mass_kg: float
    launch_latitude_deg: float = 28.5  # Cape Canaveral default
    target_inclination_deg: Optional[float] = None
    n_stages: int = 2
    stage_isp_s: List[float] = field(default_factory=lambda: [300.0, 350.0])
    stage_structural_fraction: List[float] = field(default_factory=lambda: [0.08, 0.10])


@dataclass
class DeltaVBudget:
    """ΔV 預算明細"""
    dv_ideal_m_s: float
    dv_gravity_loss_m_s: float
    dv_drag_loss_m_s: float
    dv_steering_loss_m_s: float
    dv_total_m_s: float
    orbit_type: OrbitType
    target_altitude_km: float


@dataclass
class StageDesign:
    """單級設計結果"""
    stage_index: int
    m0_kg: float          # 該級起始總質量（含上面級 + 載荷）
    m_prop_kg: float      # 推進劑質量
    m_struct_kg: float    # 結構質量
    m_payload_kg: float   # 該級的有效載荷（= 上面級總質量 + 最終載荷）
    dv_m_s: float         # 該級提供的 ΔV
    isp_s: float
    mass_ratio: float
    structural_fraction: float


@dataclass
class StagingResult:
    """多級最佳化結果"""
    stages: List[StageDesign]
    total_mass_kg: float
    payload_ratio: float
    dv_total_m_s: float


@dataclass
class MassBudget:
    """質量分配"""
    total_mass_kg: float
    payload_mass_kg: float
    total_propellant_kg: float
    total_structure_kg: float
    payload_fraction: float
    propellant_fraction: float
    structure_fraction: float


@dataclass
class LaunchWindowResult:
    """發射窗口分析"""
    latitude_deg: float
    target_inclination_deg: float
    eastward_velocity_m_s: float
    dv_plane_change_m_s: float
    launch_azimuth_deg: float
    accessible: bool
    note: str


def compute_delta_v_budget(spec: MissionSpec) -> DeltaVBudget:
    """計算含損失的 ΔV 預算。"""
    h = spec.target_altitude_km * 1000.0
    r = R_EARTH + h

    if spec.orbit_type == OrbitType.SUBORBITAL:
        v_orbit = math.sqrt(2.0 * MU_EARTH * h / (R_EARTH * r))
        dv_ideal = v_orbit
    else:
        v_orbit = math.sqrt(MU_EARTH / r)
        dv_ideal = v_orbit

    dv_grav = 1200.0 + 100.0 * (h / 1e6)  # 典型重力損失
    dv_drag = 150.0 if h < 200000 else 100.0
    dv_steer = 50.0 + 20.0 * (spec.n_stages - 1)

    if spec.orbit_type == OrbitType.GTO:
        v_geo = math.sqrt(MU_EARTH / (R_EARTH + 35786000.0))
        dv_transfer = abs(v_geo * (math.sqrt(2.0 * r / (r + R_EARTH + 35786000.0)) - 1.0))
        dv_ideal += dv_transfer + 1500.0
    elif spec.orbit_type == OrbitType.GEO:
        dv_ideal = ORBIT_DV_REFERENCE[OrbitType.GEO]
        dv_grav = 1500.0
    elif spec.orbit_type == OrbitType.TLI:
        dv_ideal = ORBIT_DV_REFERENCE[OrbitType.TLI]
        dv_grav = 1600.0

    if spec.orbit_type == OrbitType.SUBORBITAL:
        dv_grav = 600.0
        dv_drag = 50.0
        dv_steer = 20.0

    dv_total = dv_ideal + dv_grav + dv_drag + dv_steer

    return DeltaVBudget(
        dv_ideal_m_s=dv_ideal,
        dv_gravity_loss_m_s=dv_grav,
        dv_drag_loss_m_s=dv_drag,
        dv_steering_loss_m_s=dv_steer,
        dv_total_m_s=dv_total,
        orbit_type=spec.orbit_type,
        target_altitude_km=spec.target_altitude_km,
    )


def optimize_staging(spec: MissionSpec, dv_total_m_s: float) -> StagingResult:
    """
    多級質量最佳化（Lagrange 乘子法）。
    對 n 級火箭，在各級 Isp / structural fraction 固定下，以最小總質量分配各級 ΔV。
    """
    n = spec.n_stages
    isp_list = spec.stage_isp_s[:n]
    sf_list = spec.stage_structural_fraction[:n]
    ve_list = [isp * G0 for isp in isp_list]

    # Lagrange 最佳化：各級 ΔV 分配使總質量最小
    weight = [ve / (1.0 - sf) for ve, sf in zip(ve_list, sf_list)]
    w_sum = sum(weight)
    dv_alloc = [(w / w_sum) * dv_total_m_s for w in weight]

    # 從最高級（上面級）往第一級遞推：m0_i = m_payload_i * MR_i / (1 - ε_i * (MR_i - 1))
    # m_payload_i = 上面級 m0 + ... ，最高級的 payload = spec.payload_mass_kg
    stages: List[StageDesign] = []
    m_payload_above = spec.payload_mass_kg

    for i in reversed(range(n)):
        dv_i = dv_alloc[i]
        ve_i = ve_list[i]
        sf_i = sf_list[i]
        mr = math.exp(dv_i / ve_i)
        # m0_i = m_payload_above * mr / (1 - sf_i*(mr - 1))
        denom = 1.0 - sf_i * (mr - 1.0)
        if denom <= 0.01:
            denom = 0.01
        m0_i = m_payload_above * mr / denom
        m_burnout_i = m0_i / mr
        m_stage_inert = m0_i - m_payload_above - (m0_i - m_burnout_i) * (1.0 - sf_i)
        m_prop_i = (m0_i - m_burnout_i)
        m_struct_i = m_prop_i * sf_i / (1.0 - sf_i) if sf_i < 1 else 0.0

        stages.insert(0, StageDesign(
            stage_index=i + 1,
            m0_kg=m0_i,
            m_prop_kg=m_prop_i,
            m_struct_kg=m_struct_i,
            m_payload_kg=m_payload_above,
            dv_m_s=dv_i,
            isp_s=isp_list[i],
            mass_ratio=mr,
            structural_fraction=sf_i,
        ))
        m_payload_above = m0_i

    total_mass = stages[0].m0_kg
    return StagingResult(
        stages=stages,
        total_mass_kg=total_mass,
        payload_ratio=spec.payload_mass_kg / max(total_mass, 1e-9),
        dv_total_m_s=dv_total_m_s,
    )


def compute_mass_budget(staging: StagingResult, payload_kg: float) -> MassBudget:
    """從多級結果計算總質量分配。"""
    total = staging.total_mass_kg
    prop = sum(s.m_prop_kg for s in staging.stages)
    struct = sum(s.m_struct_kg for s in staging.stages)
    return MassBudget(
        total_mass_kg=total,
        payload_mass_kg=payload_kg,
        total_propellant_kg=prop,
        total_structure_kg=struct,
        payload_fraction=payload_kg / max(total, 1e-9),
        propellant_fraction=prop / max(total, 1e-9),
        structure_fraction=struct / max(total, 1e-9),
    )


def compute_launch_window(
    latitude_deg: float,
    target_inclination_deg: Optional[float] = None,
    target_altitude_km: float = 400.0,
) -> LaunchWindowResult:
    """計算發射窗口：東向速度增量、軌道面變換 ΔV、發射方位角。"""
    lat_rad = math.radians(latitude_deg)
    v_earth_surface = 465.1 * math.cos(lat_rad)  # m/s at equator ≈ 465 m/s

    inc = target_inclination_deg if target_inclination_deg is not None else latitude_deg
    if inc < abs(latitude_deg):
        return LaunchWindowResult(
            latitude_deg=latitude_deg,
            target_inclination_deg=inc,
            eastward_velocity_m_s=v_earth_surface,
            dv_plane_change_m_s=0.0,
            launch_azimuth_deg=0.0,
            accessible=False,
            note=f"目標傾角 {inc}° < 發射緯度 {latitude_deg}°，無法直接入軌",
        )

    sin_az = math.cos(math.radians(inc)) / math.cos(lat_rad)
    sin_az = max(-1.0, min(1.0, sin_az))
    azimuth_deg = math.degrees(math.asin(sin_az))

    r = R_EARTH + target_altitude_km * 1000.0
    v_orbit = math.sqrt(MU_EARTH / r)
    dv_plane = 0.0
    if target_inclination_deg is not None and target_inclination_deg != latitude_deg:
        delta_inc = abs(target_inclination_deg - latitude_deg)
        dv_plane = 2.0 * v_orbit * math.sin(math.radians(delta_inc / 2.0))

    return LaunchWindowResult(
        latitude_deg=latitude_deg,
        target_inclination_deg=inc,
        eastward_velocity_m_s=v_earth_surface,
        dv_plane_change_m_s=dv_plane,
        launch_azimuth_deg=azimuth_deg,
        accessible=True,
        note="可直接入軌" if dv_plane < 100 else f"需 {dv_plane:.0f} m/s 面變換",
    )


def run_mission_planning(spec: MissionSpec) -> Dict:
    """一鍵執行完整任務規劃。"""
    dv = compute_delta_v_budget(spec)
    staging = optimize_staging(spec, dv.dv_total_m_s)
    budget = compute_mass_budget(staging, spec.payload_mass_kg)
    window = compute_launch_window(
        spec.launch_latitude_deg,
        spec.target_inclination_deg,
        spec.target_altitude_km,
    )
    return {
        "delta_v_budget": dv,
        "staging": staging,
        "mass_budget": budget,
        "launch_window": window,
    }
