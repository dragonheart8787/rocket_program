# -*- coding: utf-8 -*-
"""
系統整合驅動器：串接所有模組、傳遞資料、匯出結果
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import json
import os
import math
import numpy as np

from mission_planning import (
    MissionSpec, OrbitType, run_mission_planning,
    DeltaVBudget, StagingResult, MassBudget, LaunchWindowResult,
)
from propulsion_advanced import (
    PropulsionCycle, design_propulsion_system, PropulsionSystemResult,
)
from structural_analysis import (
    ShellSection, analyze_structure, StructuralResult, MATERIAL_DB,
)
from thermal_analysis import (
    run_thermal_analysis, ThermalResult,
)
from guidance_navigation import (
    GravityTurnParams, TVCSpec, AttitudeControllerParams,
    simulate_gravity_turn, GNCResult,
)
from rocket_design_generator import (
    NoseConeSpec, BodyStageSpec, FinSpec, RocketExteriorSpec,
    EngineDesignSpec, generate_full_rocket_design,
)

try:
    from cea_bridge import get_cea_properties_for_engine
except ImportError:
    get_cea_properties_for_engine = None

G0 = 9.80665


@dataclass
class RocketSystemConfig:
    """全系統輸入配置"""
    name: str = "MyRocket"
    # 任務
    orbit_type: OrbitType = OrbitType.LEO
    target_altitude_km: float = 400.0
    payload_mass_kg: float = 500.0
    launch_latitude_deg: float = 28.5
    n_stages: int = 2
    stage_isp_s: list = field(default_factory=lambda: [300.0, 350.0])
    stage_struct_frac: list = field(default_factory=lambda: [0.08, 0.10])
    # 推進
    propulsion_cycle: PropulsionCycle = PropulsionCycle.GAS_GENERATOR
    propellant_id: str = "LOX_RP1"
    chamber_pressure_MPa: float = 7.0
    expansion_ratio: float = 25.0
    gamma: float = 1.22
    R_gas: float = 330.0
    T_c_K: float = 3500.0
    # 外觀
    nose_type: str = "von_karman"
    nose_length_m: float = 2.0
    body_radius_m: float = 0.5
    n_fins: int = 4
    # 結構
    wall_thickness_m: float = 0.004
    material_id: str = "Al7075_T6"
    # GNC
    pitchover_speed_m_s: float = 100.0
    pitch_kick_deg: float = 2.0
    # 冷卻
    coolant_id: str = "RP1"
    wall_temp_limit_K: float = 900.0


@dataclass
class DesignState:
    """模組間傳遞的設計狀態"""
    config: RocketSystemConfig
    mission: Optional[Dict] = None
    propulsion: Optional[PropulsionSystemResult] = None
    exterior: Optional[Dict] = None
    structural: Optional[StructuralResult] = None
    thermal: Optional[ThermalResult] = None
    gnc: Optional[GNCResult] = None


def run_full_design(cfg: RocketSystemConfig) -> DesignState:
    """依序呼叫所有模組，傳遞資料，回傳完整 DesignState。"""
    state = DesignState(config=cfg)

    # 1) 任務規劃
    mission_spec = MissionSpec(
        orbit_type=cfg.orbit_type,
        target_altitude_km=cfg.target_altitude_km,
        payload_mass_kg=cfg.payload_mass_kg,
        launch_latitude_deg=cfg.launch_latitude_deg,
        n_stages=cfg.n_stages,
        stage_isp_s=cfg.stage_isp_s,
        stage_structural_fraction=cfg.stage_struct_frac,
    )
    state.mission = run_mission_planning(mission_spec)

    # 2) 推進系統（若已安裝 RocketCEA 且推進劑有對應，則用 NASA CEA 之 gamma, R, T_c）
    staging: StagingResult = state.mission["staging"]
    first_stage = staging.stages[0]
    thrust_first = first_stage.m0_kg * G0 * 1.3  # T/W ≈ 1.3
    p_c_Pa = cfg.chamber_pressure_MPa * 1e6

    gamma = cfg.gamma
    R_gas = cfg.R_gas
    T_c_K = cfg.T_c_K
    if get_cea_properties_for_engine is not None:
        cea = get_cea_properties_for_engine(
            cfg.propellant_id, p_c_Pa, cfg.expansion_ratio
        )
        if cea is not None:
            gamma = cea["gamma"]
            R_gas = cea["R_gas"]
            T_c_K = cea["T_c_K"]

    state.propulsion = design_propulsion_system(
        F_vac_N=thrust_first,
        p_c_Pa=p_c_Pa,
        expansion_ratio=cfg.expansion_ratio,
        cycle=cfg.propulsion_cycle,
        gamma=gamma,
        R_gas=R_gas,
        T_c_K=T_c_K,
    )

    # 3) 外觀
    total_body_length = 0.0
    body_stages = []
    for s in staging.stages:
        length = max(1.0, s.m_prop_kg / (800.0 * math.pi * cfg.body_radius_m ** 2))
        body_stages.append(BodyStageSpec(length, cfg.body_radius_m, f"Stage {s.stage_index}"))
        total_body_length += length

    nose = NoseConeSpec(type=cfg.nose_type, length_m=cfg.nose_length_m, base_radius_m=cfg.body_radius_m)
    fins = FinSpec(count=cfg.n_fins, root_chord_m=0.6, tip_chord_m=0.2, span_m=0.3,
                   sweep_deg=35.0, position_from_tail_m=0.1)
    ext_spec = RocketExteriorSpec(nose=nose, body_stages=body_stages, fins=fins)
    eng_spec = EngineDesignSpec(
        propellant_id=cfg.propellant_id,
        thrust_vac_N=state.propulsion.F_vac_N,
        chamber_pressure_Pa=p_c_Pa,
        expansion_ratio=cfg.expansion_ratio,
        burn_time_s=first_stage.m_prop_kg / max(state.propulsion.mdot_kg_s, 0.01),
    )
    ext_result = generate_full_rocket_design(ext_spec, eng_spec)
    state.exterior = ext_result["summary"]

    # 4) 結構
    n_sec = max(5, int(total_body_length))
    sections = []
    for i in range(n_sec):
        x = cfg.nose_length_m + i * total_body_length / n_sec
        axial = first_stage.m0_kg * G0 * (1.0 - i / n_sec) * 1.3
        bend = axial * 0.02 * cfg.body_radius_m
        sections.append(ShellSection(
            x_from_nose_m=x,
            radius_m=cfg.body_radius_m,
            thickness_m=cfg.wall_thickness_m,
            material_id=cfg.material_id,
            internal_pressure_Pa=p_c_Pa * 0.01,
            axial_force_N=axial,
            bending_moment_Nm=bend,
            temperature_K=350.0,
            temperature_inner_K=300.0,
        ))
    state.structural = analyze_structure(sections)

    # 5) 熱力（與推進一致：使用 CEA 之 T_c、gamma 若已取得）
    noz = state.propulsion.nozzle
    state.thermal = run_thermal_analysis(
        T_c_K=T_c_K,
        p_c_Pa=p_c_Pa,
        mdot_kg_s=state.propulsion.mdot_kg_s,
        gamma=gamma,
        nozzle_x_m=noz.x_m,
        nozzle_r_m=noz.r_m,
        coolant_id=cfg.coolant_id,
        wall_limit_K=cfg.wall_temp_limit_K,
    )

    # 6) GNC — 模擬全部級別的總飛行
    total_prop = sum(s.m_prop_kg for s in staging.stages)
    avg_isp = sum(s.isp_s * s.m_prop_kg for s in staging.stages) / max(total_prop, 1)
    avg_mdot = state.propulsion.mdot_kg_s * 0.8  # 上面級流率較低
    total_burn_time = total_prop / max(avg_mdot, 0.01)
    avg_thrust = avg_isp * G0 * avg_mdot

    state.gnc = simulate_gravity_turn(
        params=GravityTurnParams(
            V_pitchover_m_s=cfg.pitchover_speed_m_s,
            pitch_kick_deg=cfg.pitch_kick_deg,
            target_altitude_m=cfg.target_altitude_km * 1000.0,
            target_velocity_m_s=math.sqrt(3.986e14 / (6371000.0 + cfg.target_altitude_km * 1000.0)),
        ),
        m0_kg=staging.total_mass_kg,
        F_vac_N=avg_thrust,
        mdot_kg_s=avg_mdot,
        I_sp_s=avg_isp,
        S_ref_m2=math.pi * cfg.body_radius_m ** 2,
        tvc=TVCSpec(),
        ctrl=AttitudeControllerParams(),
        t_max_s=total_burn_time * 1.2,
    )

    return state


def export_design_state(state: DesignState, output_dir: str) -> None:
    """匯出 DesignState 至 JSON。"""
    os.makedirs(output_dir, exist_ok=True)

    def _safe(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _safe(v) for k, v in obj.__dict__.items()}
        if isinstance(obj, dict):
            return {k: _safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_safe(v) for v in obj]
        if isinstance(obj, Enum):
            return obj.value
        return obj

    from enum import Enum
    summary = {
        "name": state.config.name,
        "mission": _safe(state.mission) if state.mission else None,
        "propulsion": {
            "F_vac_N": state.propulsion.F_vac_N,
            "I_sp_vac_s": state.propulsion.I_sp_vac_s,
            "mdot_kg_s": state.propulsion.mdot_kg_s,
            "cycle": state.propulsion.cycle.value,
        } if state.propulsion else None,
        "structural": {
            "min_MS_yield": state.structural.min_MS_yield,
            "min_MS_buckling": state.structural.min_MS_buckling,
            "total_mass_kg": state.structural.total_structural_mass_kg,
        } if state.structural else None,
        "thermal": {
            "max_wall_temp_K": state.thermal.max_wall_temp_K,
            "margin_K": state.thermal.thermal_margin_K,
            "tps_mass_kg": state.thermal.tps_mass_kg,
        } if state.thermal else None,
        "gnc": {
            "final_altitude_m": state.gnc.final_altitude_m,
            "final_velocity_m_s": state.gnc.final_velocity_m_s,
            "max_q_Pa": state.gnc.max_q_Pa,
            "orbit_achieved": state.gnc.is_orbit_achieved,
        } if state.gnc else None,
    }
    with open(os.path.join(output_dir, "design_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
