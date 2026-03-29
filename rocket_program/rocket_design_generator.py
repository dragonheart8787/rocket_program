# -*- coding: utf-8 -*-
"""
火箭外觀與引擎完整設計生成器
產出：外觀幾何（鼻錐／箭體／尾翼）、引擎完整參數（燃燒室／噴管／推力／比衝）、
      JSON／SVG 匯出與可視化用資料。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
import math
import json
import numpy as np

# 依賴既有模組
try:
    from .von_karman_tsien_theory import (
        VonKarmanTheory,
        create_von_karman_nose_profile,
        create_sears_haack_profile,
    )
except ImportError:
    VonKarmanTheory = None
    create_von_karman_nose_profile = None
    create_sears_haack_profile = None

try:
    from .aerospace_sim import EngineeringFormulas
except ImportError:
    EngineeringFormulas = None

try:
    from .cea_bridge import get_cea_properties_for_engine
except ImportError:
    get_cea_properties_for_engine = None

G0 = 9.80665  # m/s^2


# =============================================================================
# 1) 外觀設計：鼻錐、箭體、尾翼
# =============================================================================

@dataclass
class NoseConeSpec:
    """鼻錐規格"""
    type: str  # "von_karman" | "conical" | "elliptical" | "sears_haack"
    length_m: float
    base_radius_m: float
    n_points: int = 80
    von_karman_n: float = 0.75  # 僅 type=von_karman 使用


@dataclass
class BodyStageSpec:
    """單段箭體規格（圓柱）"""
    length_m: float
    radius_m: float
    name: str = ""


@dataclass
class FinSpec:
    """尾翼規格（梯形平面）"""
    count: int
    root_chord_m: float
    tip_chord_m: float
    span_m: float
    sweep_deg: float  # 前緣後掠角（度）
    position_from_tail_m: float  # 前緣根部位於箭尾起算之軸向距離


@dataclass
class RocketExteriorSpec:
    """火箭外觀輸入規格"""
    nose: NoseConeSpec
    body_stages: List[BodyStageSpec]
    fins: Optional[FinSpec] = None


@dataclass
class RocketExteriorResult:
    """火箭外觀輸出：幾何點與總尺寸"""
    profile_x_m: np.ndarray
    profile_r_m: np.ndarray
    total_length_m: float
    max_radius_m: float
    fin_polygons: List[List[Tuple[float, float]]]  # 每片翼面 (x,r) 多邊形（側視）
    spec: RocketExteriorSpec


def _nose_cone_points(spec: NoseConeSpec) -> Tuple[np.ndarray, np.ndarray]:
    """依鼻錐類型產生 (x, r) 輪廓點。x 從 0 到 L，r 從 0 到 base_radius。"""
    L = spec.length_m
    R = spec.base_radius_m
    n = spec.n_points
    x = np.linspace(0.0, L, n)
    if spec.type == "von_karman" and VonKarmanTheory is not None and create_von_karman_nose_profile is not None:
        xv, rv = create_von_karman_nose_profile(L, R, n=spec.von_karman_n, n_points=n)
        return xv, rv
    if spec.type == "sears_haack" and VonKarmanTheory is not None and create_sears_haack_profile is not None:
        xv, rv = create_sears_haack_profile(L, R, n_points=n)
        return xv, rv
    if spec.type == "conical":
        r = (x / L) * R
        return x, r
    if spec.type == "elliptical":
        # 橢圓：r/R = sqrt(1 - (1 - x/L)^2)
        xi = np.clip(1.0 - x / max(L, 1e-9), 0.0, 1.0)
        r = R * np.sqrt(1.0 - xi * xi)
        return x, r
    # 預設圓錐
    r = (x / L) * R
    return x, r


def generate_rocket_exterior(spec: RocketExteriorSpec) -> RocketExteriorResult:
    """生成火箭外觀幾何：鼻錐 + 箭體段 + 尾翼多邊形。"""
    x_list: List[np.ndarray] = []
    r_list: List[np.ndarray] = []
    x_offset = 0.0

    # 鼻錐
    xn, rn = _nose_cone_points(spec.nose)
    x_list.append(xn + x_offset)
    r_list.append(rn)
    x_offset += spec.nose.length_m

    # 箭體段
    for stage in spec.body_stages:
        n_cyl = max(2, int(stage.length_m / 0.1))
        xc = np.linspace(0.0, stage.length_m, n_cyl) + x_offset
        rc = np.full_like(xc, stage.radius_m)
        x_list.append(xc)
        r_list.append(rc)
        x_offset += stage.length_m

    # 合併輪廓（去重疊點）
    profile_x = np.concatenate(x_list)
    profile_r = np.concatenate(r_list)
    total_length = float(x_offset)
    max_radius = float(np.max(profile_r))

    # 尾翼側視多邊形（簡化：梯形在 (x,r) 平面上的投影）
    fin_polygons: List[List[Tuple[float, float]]] = []
    if spec.fins is not None:
        f = spec.fins
        x_tail = total_length - f.position_from_tail_m
        # 根弦 [x_tail, x_tail + root_chord], r = max_radius
        # 梢弦：前緣後掠 -> 前緣 x_te_tip = x_tail + span*tan(sweep), 梢弦長 tip_chord
        sweep_rad = math.radians(f.sweep_deg)
        x_te_tip = x_tail + f.span_m * math.tan(sweep_rad)
        x_le_tip = x_te_tip + f.tip_chord_m
        for _ in range(f.count):
            # 側視梯形四點：(根前,根後), (梢前,梢後)
            poly = [
                (x_tail, max_radius),
                (x_tail + f.root_chord_m, max_radius),
                (x_le_tip, max_radius + f.span_m),
                (x_te_tip, max_radius + f.span_m),
            ]
            fin_polygons.append(poly)

    return RocketExteriorResult(
        profile_x_m=profile_x,
        profile_r_m=profile_r,
        total_length_m=total_length,
        max_radius_m=max_radius,
        fin_polygons=fin_polygons,
        spec=spec,
    )


def export_exterior_json(result: RocketExteriorResult, path: str) -> None:
    """將外觀幾何匯出為 JSON。"""
    data = {
        "total_length_m": result.total_length_m,
        "max_radius_m": result.max_radius_m,
        "profile": {
            "x_m": result.profile_x_m.tolist(),
            "r_m": result.profile_r_m.tolist(),
        },
        "fins": [{"polygon_xr": p} for p in result.fin_polygons],
        "spec": {
            "nose": {
                "type": result.spec.nose.type,
                "length_m": result.spec.nose.length_m,
                "base_radius_m": result.spec.nose.base_radius_m,
            },
            "body_stages": [
                {"length_m": s.length_m, "radius_m": s.radius_m, "name": s.name}
                for s in result.spec.body_stages
            ],
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_exterior_svg(result: RocketExteriorResult, path: str, scale: float = 200.0) -> None:
    """將外觀匯出為 2D 側視 SVG（旋轉體以半剖面表示）。"""
    L = result.total_length_m
    R = result.max_radius_m
    sx = scale
    sy = scale * 0.5
    # 視圖範圍
    w = max(400, L * sx * 1.2)
    h = max(300, R * sy * 2.5)
    cx = w * 0.15
    cy = h / 2.0
    # 軸向 x -> 向右；徑向 r -> 上下對稱
    def to_svg(x: float, r: float) -> Tuple[float, float]:
        return (cx + x * sx, cy - r * sy)

    lines: List[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">')
    lines.append('<g stroke="#333" stroke-width="1.5" fill="none">')
    # 上輪廓
    pts_upper = [to_svg(x, r) for x, r in zip(result.profile_x_m, result.profile_r_m)]
    d_upper = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts_upper)
    lines.append(f'  <path d="{d_upper}"/>')
    # 下輪廓（對稱）
    pts_lower = [to_svg(x, -r) for x, r in zip(result.profile_x_m, result.profile_r_m)]
    d_lower = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts_lower)
    lines.append(f'  <path d="{d_lower}"/>')
    # 尾翼
    lines.append('  <g fill="#ccc" stroke="#555">')
    for poly in result.fin_polygons:
        pts = [to_svg(x, r) for x, r in poly]
        d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z"
        lines.append(f'    <path d="{d}"/>')
    lines.append("  </g>")
    lines.append("</g>")
    lines.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =============================================================================
# 2) 引擎設計：燃燒室、噴管、推力、比衝
# =============================================================================

# 常用推進劑參數（簡化）
PROPELLANT_DB = {
    "LOX_LH2": {"gamma": 1.24, "R_J_kgK": 4157.0, "T_c_nom_K": 3500.0, "I_sp_vac_s": 450.0, "name": "液氧/液氫"},
    "LOX_RP1": {"gamma": 1.22, "R_J_kgK": 330.0, "T_c_nom_K": 3700.0, "I_sp_vac_s": 350.0, "name": "液氧/煤油"},
    "NTO_UDMH": {"gamma": 1.25, "R_J_kgK": 320.0, "T_c_nom_K": 3400.0, "I_sp_vac_s": 320.0, "name": "四氧化二氮/UDMH"},
    "Solid_HTPB": {"gamma": 1.18, "R_J_kgK": 350.0, "T_c_nom_K": 3600.0, "I_sp_vac_s": 280.0, "name": "HTPB 固體"},
}


@dataclass
class EngineDesignSpec:
    """引擎設計輸入"""
    propellant_id: str  # 鍵入 PROPELLANT_DB
    thrust_vac_N: float
    chamber_pressure_Pa: float
    expansion_ratio: float  # A_e / A_t
    ambient_pressure_Pa: float = 101325.0
    burn_time_s: Optional[float] = None
    nozzle_efficiency: float = 0.98
    C_d: float = 0.98  # 噴管流量係數


@dataclass
class EngineDesignResult:
    """引擎設計輸出"""
    F_vac_N: float
    F_sea_N: float
    I_sp_vac_s: float
    I_sp_sea_s: float
    mdot_kg_s: float
    p_c_Pa: float
    T_c_K: float
    A_t_m2: float
    A_e_m2: float
    D_t_m: float
    D_e_m: float
    expansion_ratio: float
    M_exit: float
    p_e_Pa: float
    v_e_m_s: float
    c_star_m_s: float
    C_F_vac: float
    burn_time_s: Optional[float]
    propellant_mass_kg: Optional[float]
    nozzle_contour_x_m: np.ndarray
    nozzle_contour_r_m: np.ndarray
    spec: EngineDesignSpec


def _mach_from_area_ratio(eps: float, gamma: float, tol: float = 1e-8, itermax: int = 80) -> float:
    """由面積比 A/A* = eps 反解出口馬赫數 M (>1)。"""
    def area_ratio(M: float) -> float:
        if M <= 0:
            return 1e30
        v = 1.0 + 0.5 * (gamma - 1.0) * M * M
        exp = (gamma + 1.0) / (2.0 * (gamma - 1.0))
        return (1.0 / M) * ((2.0 / (gamma + 1.0)) * v) ** exp
    M = 2.0
    for _ in range(itermax):
        f = area_ratio(M) - eps
        if abs(f) < tol:
            return M
        # 數值微分
        dM = M * 1e-6
        fp = (area_ratio(M + dM) - area_ratio(M - dM)) / (2.0 * dM)
        M = M - f / max(abs(fp), 1e-12)
        M = max(M, 1.01)
    return M


def generate_engine_design(spec: EngineDesignSpec) -> EngineDesignResult:
    """由推力、燃燒室壓力、膨脹比與推進劑，計算完整引擎參數與噴管輪廓。
    若已安裝 RocketCEA 且推進劑有對應，則採用 NASA CEA 之 T_c、gamma、R、c*。"""
    prop = PROPELLANT_DB.get(spec.propellant_id, PROPELLANT_DB["LOX_RP1"])
    gamma = prop["gamma"]
    R = prop["R_J_kgK"]
    T_c = prop["T_c_nom_K"]
    I_sp_vac_ref = prop["I_sp_vac_s"]

    # 優先使用 NASA CEA（RocketCEA）化學平衡結果
    if get_cea_properties_for_engine is not None:
        cea = get_cea_properties_for_engine(
            spec.propellant_id,
            spec.chamber_pressure_Pa,
            spec.expansion_ratio,
        )
        if cea is not None:
            gamma = cea["gamma"]
            R = cea["R_gas"]
            T_c = cea["T_c_K"]
            # 後續 c_star 仍用等熵公式計算，但可選：用 CEA c* 時需與 C_F 一致
            # 此處保留用 gamma,R,T_c 算 c_star，與 CEA 結果接近

    # 特徵速度 c* = sqrt(gamma*R*T_c) * (2/(gamma+1))^((gamma+1)/(2*(gamma-1)))
    exp_c = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    c_star = math.sqrt(gamma * R * T_c) * (2.0 / (gamma + 1.0)) ** exp_c
    c_star *= spec.nozzle_efficiency

    # 由目標真空推力與膨脹比反推：先算 C_F_vac(eps)，再 A_t = F_vac/(p_c*C_F*eta)，mdot = p_c*A_t*Gamma*C_d/c*
    eps = spec.expansion_ratio
    M_e = _mach_from_area_ratio(eps, gamma)
    p_e = spec.chamber_pressure_Pa * (1.0 + 0.5 * (gamma - 1.0) * M_e * M_e) ** (-gamma / (gamma - 1.0))
    if EngineeringFormulas is not None:
        C_F_vac = EngineeringFormulas.thrust_coefficient_ideal(
            p_e, spec.chamber_pressure_Pa, 0.0, eps * 1.0, 1.0, gamma
        )
    else:
        term1 = (2.0 * gamma * gamma) / (gamma - 1.0)
        term2 = (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
        term3 = 1.0 - (p_e / spec.chamber_pressure_Pa) ** ((gamma - 1.0) / gamma)
        C_F_vac = math.sqrt(term1 * term2 * term3) + (p_e - 0.0) * eps / (spec.chamber_pressure_Pa * 1.0)
    A_t = spec.thrust_vac_N / (C_F_vac * spec.chamber_pressure_Pa * spec.nozzle_efficiency)
    A_e = A_t * eps
    Gamma = math.sqrt(gamma) * (2.0 / (gamma + 1.0)) ** exp_c
    mdot = spec.chamber_pressure_Pa * A_t * Gamma * spec.C_d / c_star

    # 出口溫度、速度
    T_e = T_c * (p_e / spec.chamber_pressure_Pa) ** ((gamma - 1.0) / gamma)
    a_e = math.sqrt(gamma * R * T_e)
    v_e = M_e * a_e * spec.nozzle_efficiency

    # 推力（應與輸入一致）
    F_vac = C_F_vac * spec.chamber_pressure_Pa * A_t * spec.nozzle_efficiency
    # 海平面
    C_F_sea = C_F_vac - spec.ambient_pressure_Pa * A_e / (spec.chamber_pressure_Pa * A_t)
    F_sea = C_F_sea * spec.chamber_pressure_Pa * A_t * spec.nozzle_efficiency
    I_sp_vac = F_vac / (mdot * G0)
    I_sp_sea = F_sea / (mdot * G0)

    D_t = math.sqrt(4.0 * A_t / math.pi)
    D_e = math.sqrt(4.0 * A_e / math.pi)

    # 噴管輪廓（簡化：收斂 45° 錐 + 喉部圓弧 + 擴張 15° 錐）
    r_t = math.sqrt(A_t / math.pi)
    r_e = math.sqrt(A_e / math.pi)
    L_conv = r_t * 1.5
    L_div = (r_e - r_t) / math.tan(math.radians(15.0))
    n_pt = 60
    x_n = np.linspace(-L_conv, L_div, n_pt)
    r_n = np.zeros(n_pt)
    for i, xx in enumerate(x_n):
        if xx < 0:
            r_n[i] = r_t + (-xx) * math.tan(math.radians(45.0))
        else:
            r_n[i] = r_t + xx * math.tan(math.radians(15.0))
    r_n = np.clip(r_n, 0.0, r_e * 1.01)

    propellant_mass = None
    if spec.burn_time_s is not None and spec.burn_time_s > 0:
        propellant_mass = mdot * spec.burn_time_s

    return EngineDesignResult(
        F_vac_N=F_vac,
        F_sea_N=F_sea,
        I_sp_vac_s=I_sp_vac,
        I_sp_sea_s=I_sp_sea,
        mdot_kg_s=mdot,
        p_c_Pa=spec.chamber_pressure_Pa,
        T_c_K=T_c,
        A_t_m2=A_t,
        A_e_m2=A_e,
        D_t_m=D_t,
        D_e_m=D_e,
        expansion_ratio=spec.expansion_ratio,
        M_exit=M_e,
        p_e_Pa=p_e,
        v_e_m_s=v_e,
        c_star_m_s=c_star,
        C_F_vac=C_F_vac,
        burn_time_s=spec.burn_time_s,
        propellant_mass_kg=propellant_mass,
        nozzle_contour_x_m=x_n,
        nozzle_contour_r_m=r_n,
        spec=spec,
    )


def export_engine_json(result: EngineDesignResult, path: str) -> None:
    """將引擎設計匯出為 JSON。"""
    data = {
        "F_vac_N": result.F_vac_N,
        "F_sea_N": result.F_sea_N,
        "I_sp_vac_s": result.I_sp_vac_s,
        "I_sp_sea_s": result.I_sp_sea_s,
        "mdot_kg_s": result.mdot_kg_s,
        "p_c_Pa": result.p_c_Pa,
        "T_c_K": result.T_c_K,
        "A_t_m2": result.A_t_m2,
        "A_e_m2": result.A_e_m2,
        "D_t_m": result.D_t_m,
        "D_e_m": result.D_e_m,
        "expansion_ratio": result.expansion_ratio,
        "M_exit": result.M_exit,
        "p_e_Pa": result.p_e_Pa,
        "v_e_m_s": result.v_e_m_s,
        "c_star_m_s": result.c_star_m_s,
        "C_F_vac": result.C_F_vac,
        "burn_time_s": result.burn_time_s,
        "propellant_mass_kg": result.propellant_mass_kg,
        "nozzle_contour": {
            "x_m": result.nozzle_contour_x_m.tolist(),
            "r_m": result.nozzle_contour_r_m.tolist(),
        },
        "propellant_id": result.spec.propellant_id,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================================
# 3) 一鍵生成：外觀 + 引擎 + 匯出
# =============================================================================

def generate_full_rocket_design(
    exterior_spec: RocketExteriorSpec,
    engine_spec: EngineDesignSpec,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成完整火箭設計：外觀幾何 + 引擎參數。
    若 output_dir 給定，則寫入 exterior.json、exterior.svg、engine.json。
    回傳摘要與兩個 result 物件之關鍵欄位。
    """
    exterior = generate_rocket_exterior(exterior_spec)
    engine = generate_engine_design(engine_spec)
    summary = {
        "exterior": {
            "total_length_m": exterior.total_length_m,
            "max_radius_m": exterior.max_radius_m,
            "nose_type": exterior.spec.nose.type,
            "n_body_stages": len(exterior.spec.body_stages),
            "n_fins": len(exterior.fin_polygons) if exterior.fin_polygons else 0,
        },
        "engine": {
            "F_vac_N": engine.F_vac_N,
            "F_sea_N": engine.F_sea_N,
            "I_sp_vac_s": engine.I_sp_vac_s,
            "mdot_kg_s": engine.mdot_kg_s,
            "p_c_Pa": engine.p_c_Pa,
            "expansion_ratio": engine.expansion_ratio,
            "D_t_m": engine.D_t_m,
            "D_e_m": engine.D_e_m,
            "propellant_id": engine.spec.propellant_id,
            "burn_time_s": engine.burn_time_s,
            "propellant_mass_kg": engine.propellant_mass_kg,
        },
    }
    if output_dir:
        import os
        os.makedirs(output_dir, exist_ok=True)
        export_exterior_json(exterior, os.path.join(output_dir, "exterior.json"))
        export_exterior_svg(exterior, os.path.join(output_dir, "exterior.svg"))
        export_engine_json(engine, os.path.join(output_dir, "engine.json"))
    return {
        "summary": summary,
        "exterior_result": exterior,
        "engine_result": engine,
    }
