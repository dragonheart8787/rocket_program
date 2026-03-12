# -*- coding: utf-8 -*-
"""
導引與控制模組：重力轉彎、推力向量控制、姿態控制器、軌跡追蹤
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import math
import numpy as np

G0 = 9.80665


@dataclass
class GravityTurnParams:
    """重力轉彎參數"""
    V_pitchover_m_s: float = 100.0    # 開始轉彎的速度
    pitch_kick_deg: float = 2.0       # 初始俯仰偏移
    target_altitude_m: float = 200000.0
    target_velocity_m_s: float = 7800.0
    dt_s: float = 0.5


@dataclass
class TVCSpec:
    """推力向量控制規格"""
    max_gimbal_deg: float = 6.0
    gimbal_rate_deg_s: float = 20.0
    moment_arm_m: float = 5.0         # 推力作用點到質心距離


@dataclass
class AttitudeControllerParams:
    Kp: float = 2.0
    Kd: float = 0.5
    Ki: float = 0.01
    max_torque_Nm: float = 50000.0


@dataclass
class TrajectoryPoint:
    t_s: float
    h_m: float
    V_m_s: float
    gamma_rad: float
    x_downrange_m: float
    mass_kg: float
    pitch_cmd_deg: float
    thrust_N: float
    accel_g: float


@dataclass
class GNCResult:
    trajectory: List[TrajectoryPoint]
    final_altitude_m: float
    final_velocity_m_s: float
    final_gamma_deg: float
    max_q_Pa: float
    max_accel_g: float
    tvc_max_gimbal_used_deg: float
    tracking_error_rms_m_s: float
    is_orbit_achieved: bool


def _isa_density(h: float) -> float:
    if h < 11000:
        T = 288.15 - 0.0065 * h
        rho = 1.225 * (T / 288.15) ** 4.256
    elif h < 25000:
        rho = 0.3639 * math.exp(-0.000157 * (h - 11000))
    else:
        rho = 0.3639 * math.exp(-0.000157 * 14000) * math.exp(-0.00005 * (h - 25000))
    return max(rho, 1e-12)


def simulate_gravity_turn(
    params: GravityTurnParams,
    m0_kg: float,
    F_vac_N: float,
    mdot_kg_s: float,
    I_sp_s: float,
    C_D: float = 0.3,
    S_ref_m2: float = 1.0,
    tvc: Optional[TVCSpec] = None,
    ctrl: Optional[AttitudeControllerParams] = None,
    t_max_s: float = 600.0,
) -> GNCResult:
    """模擬重力轉彎飛行。"""
    dt = params.dt_s
    R_E = 6371000.0

    V = 0.01
    gamma = math.radians(90.0)  # 初始垂直
    h = 0.0
    x = 0.0
    m = m0_kg
    t = 0.0
    pitched = False
    max_q = 0.0
    max_accel = 0.0
    max_gimbal_used = 0.0
    traj: List[TrajectoryPoint] = []

    err_integral = 0.0
    err_prev = 0.0

    while t < t_max_s and h >= -100.0 and m > mdot_kg_s * dt * 2:
        rho = _isa_density(h)
        q = 0.5 * rho * V * V
        D = q * C_D * S_ref_m2
        g = G0 * (R_E / (R_E + h)) ** 2

        F = F_vac_N if m > mdot_kg_s * dt else 0.0
        # 海平面推力修正
        p_a = 101325.0 * math.exp(-h / 8500.0) if h < 100000 else 0.0

        # 重力轉彎控制
        if not pitched and V >= params.V_pitchover_m_s:
            gamma -= math.radians(params.pitch_kick_deg)
            pitched = True

        # PD 控制（TVC 角度限制）
        gimbal_angle = 0.0
        if pitched and tvc and ctrl:
            gamma_target = math.atan2(
                params.target_velocity_m_s * math.sin(math.radians(0.5)),
                V
            ) if V > 100 else gamma
            err = gamma - gamma_target
            err_integral += err * dt
            err_dot = (err - err_prev) / max(dt, 1e-6)
            err_prev = err
            gimbal_cmd = -(ctrl.Kp * err + ctrl.Kd * err_dot + ctrl.Ki * err_integral)
            gimbal_angle = max(-math.radians(tvc.max_gimbal_deg),
                               min(math.radians(tvc.max_gimbal_deg), gimbal_cmd))
            max_gimbal_used = max(max_gimbal_used, abs(math.degrees(gimbal_angle)))

        # 3-DoF 動力學
        a_thrust = F / max(m, 1.0)
        dV = (a_thrust * math.cos(gimbal_angle) - D / max(m, 1.0) - g * math.sin(gamma)) * dt
        dg = (a_thrust * math.sin(gimbal_angle) / max(V, 0.1) - g * math.cos(gamma) / max(V, 0.1)) * dt if V > 1 else 0.0
        dh = V * math.sin(gamma) * dt
        dx = V * math.cos(gamma) * dt

        V += dV
        V = max(V, 0.01)
        gamma += dg
        h += dh
        x += dx
        m -= mdot_kg_s * dt if F > 0 else 0.0
        t += dt

        accel = a_thrust / G0
        max_q = max(max_q, q)
        max_accel = max(max_accel, accel)

        traj.append(TrajectoryPoint(
            t_s=t, h_m=h, V_m_s=V, gamma_rad=gamma, x_downrange_m=x,
            mass_kg=m, pitch_cmd_deg=math.degrees(gamma),
            thrust_N=F, accel_g=accel,
        ))

        if h > params.target_altitude_m and abs(gamma) < math.radians(5.0):
            break

    final_h = traj[-1].h_m if traj else 0.0
    final_V = traj[-1].V_m_s if traj else 0.0
    final_g = math.degrees(traj[-1].gamma_rad) if traj else 90.0
    orbit_ok = final_h >= params.target_altitude_m * 0.9 and final_V >= params.target_velocity_m_s * 0.9

    vel_errors = [abs(p.V_m_s - params.target_velocity_m_s) for p in traj[-10:]] if len(traj) > 10 else [0]
    rms_err = math.sqrt(sum(e ** 2 for e in vel_errors) / max(len(vel_errors), 1))

    return GNCResult(
        trajectory=traj,
        final_altitude_m=final_h,
        final_velocity_m_s=final_V,
        final_gamma_deg=final_g,
        max_q_Pa=max_q,
        max_accel_g=max_accel,
        tvc_max_gimbal_used_deg=max_gimbal_used,
        tracking_error_rms_m_s=rms_err,
        is_orbit_achieved=orbit_ok,
    )
