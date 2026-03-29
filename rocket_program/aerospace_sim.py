# -*- coding: utf-8 -*-
"""
Conceptual Aerospace Vehicle Simulator (Educational / Concept Design)
- ISA 分層大氣（完整層 + μ,k,Pr,Re,Nu）
- 6DoF: r_I, v_I, q_IB, w_B, m, T_w, T_int, throttle_act
- 地球座標/自轉/風場: ECEF/NED, Coriolis, 風場佔位
- 氣動: L,D 占位 → 查表/代理模型介面 (C_L, C_D, C_M)
- 推進: chemical / electric / pulse 統一介面 → 燃燒室、噴管膨脹、節流動態、延遲
- 熱: Sutton–Graves + lumped TPS（可選 Nu/Re 修正）
- 結構: 屈曲 knockdown、載荷交互查表介面
- GNC: 感測器、延遲、飽和、EKF/UKF 介面、控制分配
- V&V: 守恆檢查、收斂性測試、不確定度分析
- 工程化: 事件系統、資料契約、版本控管、可追溯性

適用範圍：
- 概念設計階段性能估算
- 教育與研究用途
- 算法開發與理論驗證

限制：
- 未經完整 V&V 驗證，不適用於最終設計
- 部分模型使用簡化假設，需專業工具交叉驗證
- 氣動係數為占位或查表，需真實 CFD/風洞數據

Dependencies: numpy (required), matplotlib (optional), scipy (optional, for interp)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable
import math
import numpy as np

# Optional scipy for 2D interp (fallback to simple bilinear if missing)
try:
    from scipy.interpolate import RegularGridInterpolator
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# =============================================================================
# 1) Utilities: Quaternions
# =============================================================================

def quat_normalize(q: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(q)
    if n == 0:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return q / n

def quat_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ])

def quat_conj(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.array([w, -x, -y, -z])

def quat_to_rotmat(q: np.ndarray) -> np.ndarray:
    q = quat_normalize(q)
    w, x, y, z = q
    return np.array([
        [1 - 2*(y*y + z*z),     2*(x*y - z*w),     2*(x*z + y*w)],
        [    2*(x*y + z*w), 1 - 2*(x*x + z*z),     2*(y*z - x*w)],
        [    2*(x*z - y*w),     2*(y*z + x*w), 1 - 2*(x*x + y*y)]
    ])

def omega_matrix(w_B: np.ndarray) -> np.ndarray:
    wx, wy, wz = w_B
    return np.array([
        [0.0, -wx, -wy, -wz],
        [wx,  0.0,  wz, -wy],
        [wy, -wz,  0.0,  wx],
        [wz,  wy, -wx,  0.0]
    ])

def quat_derivative(q: np.ndarray, w_B: np.ndarray) -> np.ndarray:
    return 0.5 * omega_matrix(w_B) @ q


# =============================================================================
# 2) 地球座標 / 自轉 / 風場: ECEF, NED, Coriolis, 風場佔位
# =============================================================================

OMEGA_EARTH = 7.2921159e-5  # rad/s

def R_z(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def ecef_from_eci(r_eci: np.ndarray, t: float) -> np.ndarray:
    return R_z(-OMEGA_EARTH * t) @ r_eci

def eci_from_ecef(r_ecef: np.ndarray, t: float) -> np.ndarray:
    return R_z(OMEGA_EARTH * t) @ r_ecef

def geodetic_from_ecef(r_ecef: np.ndarray, R_earth: float = 6371000.0) -> tuple:
    """簡化球形: lat (rad), lon (rad), h (m)."""
    x, y, z = r_ecef
    r = np.linalg.norm(r_ecef)
    h = max(0.0, r - R_earth)
    if r < 1e-6:
        return 0.0, 0.0, 0.0
    lat = math.asin(z / r)
    lon = math.atan2(y, x)
    return lat, lon, h

def R_NED_to_ECEF(lat: float, lon: float) -> np.ndarray:
    """NED 到 ECEF 的旋轉矩陣 (col = N,E,D 在 ECEF 的分量)."""
    clat, slat = math.cos(lat), math.sin(lat)
    clon, slon = math.cos(lon), math.sin(lon)
    N = np.array([-slat*clon, -slat*slon, clat])
    E = np.array([-slon, clon, 0.0])
    D = np.array([-clat*clon, -clat*slon, -slat])
    return np.column_stack([N, E, D])

def wind_model_ned(lat: float, lon: float, h: float) -> np.ndarray:
    """佔位風場: 僅高度剪切 (v_north, v_east, v_down) m/s."""
    # 典型對流層風剪: 隨高度增大
    v_n = 5.0 * (1.0 - math.exp(-h / 5000.0))  # 北風
    v_e = 2.0 * (1.0 - math.exp(-h / 8000.0))  # 東風
    v_d = 0.0
    return np.array([v_n, v_e, v_d])


# =============================================================================
# 3) Environment: Gravity + ISA 完整層 + μ, k, Pr, Re
# =============================================================================

@dataclass
class Earth:
    mu: float = 3.986004418e14
    R: float = 6371000.0
    g0: float = 9.80665
    omega: float = OMEGA_EARTH
    use_ecef: bool = False  # 若 True：狀態為 ECEF，並加入 Coriolis

@dataclass
class AtmosLayer:
    h0: float
    T0: float
    p0: float
    L: float  # K/m; 0 => isothermal

@dataclass
class ISA:
    """擴充 ISA：多層 (至 ~86 km) + Sutherland μ(T), k(T), Pr."""
    layers: tuple = (
        AtmosLayer(0.0,      288.15, 101325.0,    -0.0065),
        AtmosLayer(11000.0,  216.65, 22632.06,    0.0),
        AtmosLayer(20000.0,  216.65, 5474.89,     0.001),
        AtmosLayer(32000.0,  228.65, 868.02,     0.0028),
        AtmosLayer(47000.0,  270.65, 110.91,     0.0),
        AtmosLayer(51000.0,  270.65, 66.94,      -0.0028),
        AtmosLayer(71000.0,  214.65, 3.96,       -0.002),
        AtmosLayer(86000.0,  186.95, 0.373,      0.0),
    )
    R_air: float = 287.05287
    gamma: float = 1.4
    cp: float = 1005.0
    # Sutherland (air): T_ref=273.15, S=110.4, mu_ref=1.716e-5
    T_ref: float = 273.15
    S_suth: float = 110.4
    mu_ref: float = 1.716e-5
    k_ref: float = 0.0241  # W/m/K @ 273 K
    Pr_ref: float = 0.71

    def _find_layer(self, h: float) -> AtmosLayer:
        h = max(0.0, float(h))
        layer = self.layers[0]
        for L in self.layers:
            if h >= L.h0:
                layer = L
            else:
                break
        return layer

    def properties(self, h: float) -> dict:
        h = max(0.0, float(h))
        layer = self._find_layer(h)
        R = self.R_air

        if layer.L != 0.0:
            T = layer.T0 + layer.L * (h - layer.h0)
            p = layer.p0 * (T / layer.T0) ** (-Earth().g0 / (R * layer.L))
        else:
            T = layer.T0
            p = layer.p0 * math.exp(-Earth().g0 * (h - layer.h0) / (R * T))

        rho = p / (R * T)
        a = math.sqrt(self.gamma * R * T)

        # Sutherland 黏度
        mu = self.mu_ref * (T / self.T_ref) ** 1.5 * (self.T_ref + self.S_suth) / (T + self.S_suth)

        # 導熱係數 (幂律近似): k/k_ref ≈ (T/T_ref)^0.8
        k = self.k_ref * (T / self.T_ref) ** 0.8

        # Prandtl
        Pr = mu * self.cp / max(k, 1e-12)

        return {
            "T": T, "p": p, "rho": rho, "a": a, "gamma": self.gamma, "R": R,
            "mu": mu, "k": k, "Pr": Pr, "cp": self.cp
        }

    @staticmethod
    def reynolds(rho: float, V: float, L: float, mu: float) -> float:
        return rho * V * L / max(mu, 1e-12)

    @staticmethod
    def nu_laminar_flatplate(Re: float, Pr: float) -> float:
        """層流平板 Nu ≈ 0.332 * Re^0.5 * Pr^(1/3)."""
        return 0.332 * (max(Re, 1e-6) ** 0.5) * (Pr ** (1.0/3.0))


# =============================================================================
# 4) 氣動: 占位係數 → 查表/代理模型介面 (C_L, C_D, C_M)
# =============================================================================

def _bilinear_interp2(x: float, y: float, xs: np.ndarray, ys: np.ndarray, Z: np.ndarray) -> float:
    """2D 雙線性插值。xs, ys 單調遞增。"""
    ix = np.searchsorted(xs, x, side="right") - 1
    iy = np.searchsorted(ys, y, side="right") - 1
    ix = max(0, min(ix, len(xs) - 2))
    iy = max(0, min(iy, len(ys) - 2))
    x0, x1 = xs[ix], xs[ix+1]
    y0, y1 = ys[iy], ys[iy+1]
    tx = (x - x0) / max(x1 - x0, 1e-12)
    ty = (y - y0) / max(y1 - y0, 1e-12)
    z00, z10 = Z[iy, ix], Z[iy, ix+1]
    z01, z11 = Z[iy+1, ix], Z[iy+1, ix+1]
    return (1-tx)*(1-ty)*z00 + tx*(1-ty)*z10 + (1-tx)*ty*z01 + tx*ty*z11

@dataclass
class AeroTable:
    """查表：alpha (deg) x M，可選 Re 縮放因子 (佔位)."""
    alpha_deg: np.ndarray
    M: np.ndarray
    C_L: np.ndarray   # (nalpha, nM)
    C_D: np.ndarray
    C_m: np.ndarray
    Re_scale: Optional[Callable[[float], float]] = None  # f(Re) 乘到 C_D 上，None 則不縮放

    def coeffs(self, alpha: float, beta: float, M: float, Re: float) -> dict:
        alpha_deg = math.degrees(alpha)
        cl = _bilinear_interp2(alpha_deg, M, self.alpha_deg, self.M, self.C_L)
        cd = _bilinear_interp2(alpha_deg, M, self.alpha_deg, self.M, self.C_D)
        cm = _bilinear_interp2(alpha_deg, M, self.alpha_deg, self.M, self.C_m)
        if self.Re_scale is not None:
            cd *= self.Re_scale(Re)
        # 側向/滾轉佔位
        C_Y = 0.0
        C_l = 0.0
        C_n = 0.0
        return {"C_L": cl, "C_D": cd, "C_Y": C_Y, "C_l": C_l, "C_m": cm, "C_n": C_n}

def make_placeholder_aero_table() -> AeroTable:
    """佔位 C_L, C_D, C_m 網格 (可替換為 CFD/風洞/代理)."""
    alpha_deg = np.array([0.0, 5.0, 10.0, 15.0, 20.0])
    M = np.array([0.3, 0.6, 0.9, 1.2, 1.5])
    # C_L: 線性隨 alpha，隨 M 略降
    C_L = np.outer(0.08 * alpha_deg, 1.0 - 0.05 * (M - 0.5))
    # C_D: 隨 alpha^2, M 增
    C_D = np.outer(0.02 + 0.001 * (alpha_deg ** 2), 0.8 + 0.15 * M)
    # C_m: 負斜率
    C_m = np.outer(-0.03 * alpha_deg, 1.0 + 0.1 * M)
    return AeroTable(alpha_deg=alpha_deg, M=M, C_L=C_L, C_D=C_D, C_m=C_m, Re_scale=None)

@dataclass
class AeroModel:
    S_ref: float = 0.3
    L_ref: float = 0.5   # 用於 Re
    C_D0: float = 0.3
    k_ind: float = 0.08
    C_La: float = 2.5
    C_Yb: float = 0.0
    table: Optional[AeroTable] = None  # 若給定則用查表取代占位公式

    def coeffs(self, alpha: float, beta: float, M: float, Re: float) -> dict:
        if self.table is not None:
            return self.table.coeffs(alpha, beta, M, Re)
        C_L = self.C_La * alpha
        C_D = self.C_D0 + self.k_ind * (C_L ** 2)
        C_Y = self.C_Yb * beta
        C_l, C_m, C_n = 0.0, -0.05 * alpha, 0.0
        return {"C_L": C_L, "C_D": C_D, "C_Y": C_Y, "C_l": C_l, "C_m": C_m, "C_n": C_n}


# =============================================================================
# 5) 推進: chemical / electric / pulse 統一介面
#        + 燃燒室、噴管膨脹、節流動態、延遲
# =============================================================================

def _mach_from_area_ratio(eps: float, gamma: float, tol: float = 1e-8, itermax: int = 50) -> float:
    """從面積比 A/A* = eps 反解 M (>1 膨脹)."""
    def f(M):
        if M <= 0:
            return 1e30
        v = 1.0 + 0.5 * (gamma - 1) * M * M
        return (1.0 / M) * (v) ** ((gamma + 1) / (2 * (gamma - 1))) - eps
    M = 2.0
    for _ in range(itermax):
        v = 1.0 + 0.5 * (gamma - 1) * M * M
        fp = (-1.0 / (M * M)) * (v) ** ((gamma + 1) / (2 * (gamma - 1))) + (1.0 / M) * ((gamma + 1) / (2 * (gamma - 1))) * (gamma - 1) * M * (v) ** ((gamma + 1) / (2 * (gamma - 1)) - 1)
        fv = f(M)
        if abs(fv) < tol:
            return M
        M = M - fv / max(fp, 1e-12)
        M = max(M, 1.01)
    return M

@dataclass
class Propulsion:
    mode: str = "chemical"
    thrust_max: float = 2000.0
    Isp: float = 250.0
    eta: float = 0.6
    P_in: float = 2000.0
    I_b: float = 0.02
    f_pulse: float = 5.0
    mdot_max: float = 0.8
    Ae: float = 0.01
    pe: float = 101325.0
    # --- 燃燒室、噴管、節流動態、延遲 ---
    p_c: float = 2.0e6          # Pa
    T_c: float = 2800.0         # K
    R_gas: float = 350.0        # J/kg/K (燃氣)
    gamma_g: float = 1.2
    A_throat: float = 0.005
    eta_cf: float = 0.98        # c* 效率
    use_isen: bool = True       # chemical 時用等熵噴管
    tau_throttle: float = 0.05  # 節流一階時間常數
    tau_delay: float = 0.02     # 節流指令延遲 (用一階近似)

    @property
    def expansion_ratio(self) -> float:
        return self.Ae / max(self.A_throat, 1e-12)

    def thrust_and_mdot(self, throttle_act: float, p_a: float, g0: float) -> tuple[float, float]:
        throttle_act = float(np.clip(throttle_act, 0.0, 1.0))
        if self.mode == "off":
            return 0.0, 0.0

        if self.mode == "chemical":
            if self.use_isen and self.A_throat > 0:
                # 等熵噴管: M_e, p_e, T_e, v_e
                eps = self.expansion_ratio
                M_e = _mach_from_area_ratio(eps, self.gamma_g)
                p_e = self.p_c * (1.0 + 0.5 * (self.gamma_g - 1) * M_e * M_e) ** (-self.gamma_g / (self.gamma_g - 1))
                T_e = self.T_c * (p_e / self.p_c) ** ((self.gamma_g - 1) / self.gamma_g)
                a_e = math.sqrt(self.gamma_g * self.R_gas * T_e)
                v_e = M_e * a_e * self.eta_cf
                mdot = throttle_act * self.mdot_max
                F = mdot * v_e + (p_e - p_a) * self.Ae
                return max(F, 0.0), max(mdot, 0.0)
            v_e = self.Isp * g0
            mdot = throttle_act * self.mdot_max
            F = mdot * v_e + (self.pe - p_a) * self.Ae
            return max(F, 0.0), max(mdot, 0.0)

        v_e = self.Isp * g0
        if self.mode == "electric":
            P = max(0.0, self.P_in * throttle_act)
            F = (2.0 * self.eta * P) / max(v_e, 1e-9)
            mdot = F / max(v_e, 1e-9)
            return max(F, 0.0), max(mdot, 0.0)
        if self.mode == "pulse":
            F = self.I_b * max(0.0, self.f_pulse) * throttle_act
            mdot = F / max(v_e, 1e-9)
            return max(F, 0.0), max(mdot, 0.0)
        raise ValueError(f"Unknown propulsion mode: {self.mode}")


# =============================================================================
# 6) 熱: Sutton–Graves + lumped TPS（可選 Re/Nu）
# =============================================================================

@dataclass
class ThermalTPS:
    k_sg: float = 1.83e-4
    R_n: float = 0.15
    A_h: float = 0.1
    eps: float = 0.8
    sigma: float = 5.670374419e-8
    m_w: float = 2.0
    c_w: float = 900.0
    m_int: float = 8.0
    c_int: float = 900.0
    k_s: float = 0.5
    delta: float = 0.02
    T_env: float = 220.0
    T_sink: float = 300.0
    h_int: float = 2.0
    A_int: float = 0.05
    use_nu_model: bool = False  # 若 True 可與 Re, Pr, Nu 結合 (此處保留 Sutton 為預設)

    def heating_rate(self, rho: float, V: float, Re: float = 0.0, Pr: float = 0.7, k: float = 0.02) -> float:
        q_sg = self.k_sg * math.sqrt(max(rho, 0.0) / max(self.R_n, 1e-9)) * (max(V, 0.0) ** 3)
        if self.use_nu_model and Re > 1e3:
            Nu = ISA.nu_laminar_flatplate(Re, Pr)
            # 簡單修正: 用 Nu 的比例縮放 (佔位)
            q_nu = Nu * k * (500.0 - self.T_env) / max(self.R_n, 1e-9)  # 假設 delta_T
            return 0.7 * q_sg + 0.3 * max(q_nu, 0.0)
        return q_sg

    def tps_derivatives(self, qdot_conv: float, T_w: float, T_int: float) -> tuple[float, float]:
        q_rad = self.eps * self.sigma * (T_w**4 - self.T_env**4)
        q_cond = (self.k_s * (T_w - T_int) / max(self.delta, 1e-9))
        dT_w = (qdot_conv * self.A_h - q_rad * self.A_h - q_cond * self.A_h) / max(self.m_w * self.c_w, 1e-9)
        q_into_int = q_cond * self.A_h
        q_out_int = self.h_int * self.A_int * (T_int - self.T_sink)
        dT_int = (q_into_int - q_out_int) / max(self.m_int * self.c_int, 1e-9)
        return dT_w, dT_int


# =============================================================================
# 7) 結構: 屈曲 knockdown、載荷交互查表介面
# =============================================================================

def _bilinear_interp2_simple(x: float, y: float, xs: np.ndarray, ys: np.ndarray, Z: np.ndarray) -> float:
    ix = max(0, min(int(np.searchsorted(xs, x, side="right") - 1), len(xs) - 2))
    iy = max(0, min(int(np.searchsorted(ys, y, side="right") - 1), len(ys) - 2))
    x0, x1 = xs[ix], xs[ix+1]
    y0, y1 = ys[iy], ys[iy+1]
    tx = (x - x0) / max(x1 - x0, 1e-12)
    ty = (y - y0) / max(y1 - y0, 1e-12)
    z00, z10 = Z[iy, ix], Z[iy, ix+1]
    z01, z11 = Z[iy+1, ix], Z[iy+1, ix+1]
    return (1-tx)*(1-ty)*z00 + tx*(1-ty)*z10 + (1-tx)*ty*z01 + tx*ty*z11

@dataclass
class StructuralCheck:
    """屈曲 knockdown 與 載荷交互 (P/P_allow, M/M_allow)."""
    R: float = 0.5          # 殼半徑 m
    t: float = 0.005        # 厚度 m
    L: float = 2.0          # 柱長 m
    P_allow: float = 1e5    # N 軸向許用
    M_allow: float = 500.0  # Nm 彎矩許用
    T_max: float = 1200.0   # K 表面溫度上限
    # 屈曲 knockdown: (R/t) x (L/R)
    R_t: np.ndarray = field(default_factory=lambda: np.array([50.0, 100.0, 200.0, 400.0]))
    L_R: np.ndarray = field(default_factory=lambda: np.array([2.0, 5.0, 10.0, 20.0]))
    knockdown: np.ndarray = field(default_factory=lambda: np.array([
        [0.9, 0.85, 0.75, 0.6 ],
        [0.85, 0.78, 0.65, 0.5 ],
        [0.78, 0.68, 0.55, 0.42],
        [0.7,  0.58, 0.45, 0.35]
    ]))

    def buckling_knockdown(self) -> float:
        Rt = self.R / max(self.t, 1e-9)
        Lr = self.L / max(self.R, 1e-9)
        return _bilinear_interp2_simple(Rt, Lr, self.R_t, self.L_R, self.knockdown)

    def load_interaction(self, P_axial: float, M_bend: float) -> float:
        """線性交互: util = P/P_allow + M/M_allow. 可改為包絡公式."""
        return (P_axial / max(self.P_allow, 1e-6)) + (M_bend / max(self.M_allow, 1e-6))

    def check(self, F_aero_B: np.ndarray, F_thrust_B: np.ndarray, tau_aero_B: np.ndarray,
              T_w: float, t_hat_B: np.ndarray = np.array([0.0, 0.0, 1.0])) -> dict:
        """t_hat_B: 推力軸 (body +Z). 軸向力取推力軸分量；彎矩取 |tau_aero| 近似."""
        P_axial = max(0.0, np.dot(F_thrust_B + F_aero_B, t_hat_B))
        M_bend = np.linalg.norm(tau_aero_B)
        kd = self.buckling_knockdown()
        util = self.load_interaction(P_axial, M_bend) / max(kd, 0.01)
        passed = util < 1.0 and T_w < self.T_max
        return {"buckling_knockdown": kd, "utilization": util, "P_axial": P_axial, "M_bend": M_bend, "passed": passed}


# =============================================================================
# 8) GNC: 感測器、延遲、飽和、EKF/UKF 介面、控制分配
# =============================================================================

@dataclass
class SensorModel:
    bias_a: np.ndarray = field(default_factory=lambda: np.zeros(3))
    bias_g: np.ndarray = field(default_factory=lambda: np.zeros(3))
    sigma_a: float = 0.1
    sigma_g: float = 1e-3
    sigma_gps_r: float = 2.0
    sigma_gps_v: float = 0.2
    tau_delay_gps: float = 0.1

    def measure_imu(self, a_B: np.ndarray, w_B: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        a_meas = a_B + self.bias_a + np.random.randn(3) * self.sigma_a
        w_meas = w_B + self.bias_g + np.random.randn(3) * self.sigma_g
        return a_meas, w_meas

    def measure_gps(self, r: np.ndarray, v: np.ndarray, r_hist: Optional[list] = None,
                    t: float = 0.0, t_hist: Optional[list] = None) -> tuple[np.ndarray, np.ndarray]:
        r_use, v_use = r, v
        if r_hist is not None and t_hist is not None and self.tau_delay_gps > 0 and len(r_hist) > 1:
            t_tgt = t - self.tau_delay_gps
            if t_tgt <= t_hist[0]:
                r_use, v_use = r_hist[0], (r_hist[1] - r_hist[0]) / max(t_hist[1] - t_hist[0], 1e-9) if len(r_hist) > 1 else v
            else:
                for i in range(len(t_hist) - 1, -1, -1):
                    if t_hist[i] <= t_tgt:
                        r_use = r_hist[i]
                        v_use = (r_hist[i+1] - r_hist[i]) / max(t_hist[i+1] - t_hist[i], 1e-9) if i+1 < len(r_hist) else v
                        break
        z_r = r_use + np.random.randn(3) * self.sigma_gps_r
        z_v = v_use + np.random.randn(3) * self.sigma_gps_v
        return z_r, z_v

@dataclass
class ActuatorModel:
    tau_max: float = 50.0
    rate_max: float = 20.0  # Nm/s per axis

    def rate_limit_saturate(self, tau_des: np.ndarray, tau_prev: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
        delta = np.clip(tau_des - tau_prev, -self.rate_max * dt, self.rate_max * dt)
        tau_cmd = np.clip(tau_prev + delta, -self.tau_max, self.tau_max)
        return tau_cmd, tau_cmd

@dataclass
class ControlAllocator:
    """B @ u = tau. u = pinv(B) @ tau, clip 後 tau_actual = B @ u."""
    B: np.ndarray = field(default_factory=lambda: np.eye(3))
    u_min: np.ndarray = field(default_factory=lambda: -np.ones(3))
    u_max: np.ndarray = field(default_factory=lambda: np.ones(3))

    def allocate(self, tau_cmd: np.ndarray) -> np.ndarray:
        B = self.B
        if B.shape[0] == B.shape[1] and np.linalg.det(B) != 0:
            u = np.linalg.solve(B, tau_cmd)
        else:
            u = np.linalg.pinv(B) @ tau_cmd
        u = np.clip(u, self.u_min, self.u_max)
        return B @ u  # tau_actual

class EKFStub:
    """簡化 EKF：狀態 [r,v,q,w]。Predict 用動力學；Update 用 GPS(r,v) + 陀螺(w)."""
    def __init__(self, x0: np.ndarray, P0: np.ndarray, Q: np.ndarray, R: np.ndarray):
        self.x = np.copy(x0)   # (13,)
        self.P = np.copy(P0)   # (13,13)
        self.Q = Q
        self.R = R

    def predict(self, dt: float, f_func, veh, x_full: np.ndarray, throttle: float) -> None:
        # 用 f_func 的 (r,v,q,w) 部分積分
        dx = f_func(0.0, x_full, veh=veh, throttle=throttle, tau_prev=np.zeros(3))
        if isinstance(dx, tuple):
            dx = dx[0]
        dr, dv = dx[0:3], dx[3:6]
        dq, dw = dx[6:10], dx[10:13]
        self.x[0:3]  += dr * dt
        self.x[3:6]  += dv * dt
        self.x[6:10] += dq * dt
        self.x[6:10] = quat_normalize(self.x[6:10])
        self.x[10:13] += dw * dt
        F = np.eye(13)  # 簡化
        self.P = F @ self.P @ F.T + self.Q * dt

    def update(self, z_r: np.ndarray, z_v: np.ndarray, z_w: np.ndarray) -> None:
        # h = [r, v, w]
        H = np.zeros((9, 13))
        H[0:3, 0:3] = np.eye(3)
        H[3:6, 3:6] = np.eye(3)
        H[6:9, 10:13] = np.eye(3)
        z = np.concatenate([z_r, z_v, z_w])
        hx = np.concatenate([self.x[0:3], self.x[3:6], self.x[10:13]])
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.solve(S, np.eye(9))
        self.x = self.x + K @ (z - hx)
        self.x[6:10] = quat_normalize(self.x[6:10])
        self.P = (np.eye(13) - K @ H) @ self.P


# =============================================================================
# 9) Vehicle
# =============================================================================

@dataclass
class Vehicle:
    earth: Earth = field(default_factory=Earth)
    atm: ISA = field(default_factory=ISA)
    aero: AeroModel = field(default_factory=AeroModel)
    prop: Propulsion = field(default_factory=Propulsion)
    tps: ThermalTPS = field(default_factory=ThermalTPS)
    struct: Optional[StructuralCheck] = field(default_factory=StructuralCheck)
    sensor: Optional[SensorModel] = None
    actuator: Optional[ActuatorModel] = None
    allocator: Optional[ControlAllocator] = None
    use_pd_control: bool = True
    I_B: np.ndarray = field(default_factory=lambda: np.diag([8.0, 8.0, 2.0]))
    Kp_att: float = 10.0
    Kd_att: float = 5.0


# =============================================================================
# 10) Guidance/Control: PD 姿態（可關閉）
# =============================================================================

def unit(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    return v / max(np.linalg.norm(v), eps)

def attitude_pd_torque(q_IB: np.ndarray, w_B: np.ndarray, v_I: np.ndarray, veh: Vehicle) -> np.ndarray:
    v_hat_I = unit(v_I)
    R_IB = quat_to_rotmat(q_IB)
    z_hat_I = R_IB @ np.array([0.0, 0.0, 1.0])
    e_I = np.cross(z_hat_I, v_hat_I)
    e_B = R_IB.T @ e_I
    return -veh.Kp_att * e_B - veh.Kd_att * w_B


# =============================================================================
# 11) Core Dynamics (ODE) — 整合 ECEF/風/Coriolis、Re、查表、節流、GNC
# =============================================================================

def dynamics(t: float, x: np.ndarray, veh: Vehicle, throttle: float = 1.0,
             tau_prev: Optional[np.ndarray] = None) -> tuple:
    """
    x: [0:3] r, [3:6] v, [6:10] q, [10:13] w, [13] m, [14] T_w, [15] T_int, [16] throttle_act
    回傳: (dx, tau_next, aux)
    """
    if tau_prev is None:
        tau_prev = np.zeros(3)

    earth = veh.earth
    r_I = x[0:3]
    v_I = x[3:6]
    q_IB = quat_normalize(x[6:10])
    w_B = x[10:13]
    m = float(x[13])
    T_w = float(x[14])
    T_int = float(x[15])
    throttle_act = float(x[16])

    # --- 重力 ---
    r_norm = np.linalg.norm(r_I)
    a_g = -earth.mu * r_I / max(r_norm**3, 1e-9)

    # --- ECEF / 風場 / 空速 ---
    r_ecef = r_I if earth.use_ecef else ecef_from_eci(r_I, t)
    lat, lon, h = geodetic_from_ecef(r_ecef, earth.R)
    wind_ned = wind_model_ned(lat, lon, h)
    R_ned2ecef = R_NED_to_ECEF(lat, lon)
    v_wind_ecef = R_ned2ecef @ wind_ned
    v_wind_inertial = v_wind_ecef if earth.use_ecef else (R_z(OMEGA_EARTH * t) @ v_wind_ecef)
    v_air_I = v_I - v_wind_inertial

    # --- Coriolis (僅 ECEF) ---
    if earth.use_ecef:
        omega_vec = np.array([0.0, 0.0, earth.omega])
        a_cor = -2.0 * np.cross(omega_vec, v_I)
        a_g = a_g + a_cor

    # --- 大氣、Re ---
    atm = veh.atm.properties(h)
    rho, p_a, a_sound = atm["rho"], atm["p"], atm["a"]
    mu, k_air, Pr = atm["mu"], atm["k"], atm["Pr"]
    V = float(np.linalg.norm(v_air_I))
    M = V / max(a_sound, 1e-9)
    Re = ISA.reynolds(rho, V, veh.aero.L_ref, mu)

    # --- 體軸空速、alpha/beta、氣動係數 ---
    R_IB = quat_to_rotmat(q_IB)
    v_air_B = R_IB.T @ v_air_I
    vx, vy, vz = v_air_B
    alpha = math.atan2(-vx, max(vz, 1e-9))
    beta = math.atan2(vy, max(np.linalg.norm([vx, vz]), 1e-9))

    c = veh.aero.coeffs(alpha, beta, M, Re)
    S = veh.aero.S_ref
    q_dyn = 0.5 * rho * V * V

    L = q_dyn * S * c["C_L"]
    D = q_dyn * S * c["C_D"]
    Y = q_dyn * S * c["C_Y"]
    F_aero_B = np.array([-D, Y, -L])

    b, c_ref = 0.5, 0.5
    tau_aero_B = q_dyn * S * np.array([b * c["C_l"], c_ref * c["C_m"], b * c["C_n"]])

    # --- 推進 (用 throttle_act，節流動態在 dx[16]) ---
    F_th, mdot = veh.prop.thrust_and_mdot(throttle_act, p_a, earth.g0)
    t_hat_B = np.array([0.0, 0.0, 1.0])
    F_th_B = F_th * t_hat_B
    tau_th_B = np.zeros(3)

    # --- 控制：PD → 感測器/延遲/飽和/分配 (若啟用) ---
    if veh.use_pd_control:
        tau_des = attitude_pd_torque(q_IB, w_B, v_I, veh)
        if veh.actuator is not None and veh.allocator is not None:
            tau_cmd, tau_next = veh.actuator.rate_limit_saturate(tau_des, tau_prev, 0.02)  # dt 暫用 0.02
            tau_ctrl_B = veh.allocator.allocate(tau_cmd)
        else:
            tau_ctrl_B = tau_des
            tau_next = tau_des
    else:
        tau_ctrl_B = np.zeros(3)
        tau_next = np.zeros(3)

    # --- 平動 ---
    F_total_I = R_IB @ (F_aero_B + F_th_B)
    a_I = (F_total_I / max(m, 1e-9)) + a_g

    # --- 轉動 ---
    I = veh.I_B
    Iw = I @ w_B
    wdot = np.linalg.solve(I, (tau_aero_B + tau_ctrl_B + tau_th_B) - np.cross(w_B, Iw))

    # --- 質量、節流動態 ---
    mdot_total = -mdot
    d_throttle = (throttle - throttle_act) / max(veh.prop.tau_throttle, 1e-9)

    # --- 熱 (可選 Re, Pr, k) ---
    qdot_conv = veh.tps.heating_rate(rho, V, Re=Re, Pr=Pr, k=k_air)
    dT_w, dT_int = veh.tps.tps_derivatives(qdot_conv, T_w, T_int)

    # --- 四元數 ---
    qdot = quat_derivative(q_IB, w_B)

    # --- 結構檢查 (aux) ---
    struct_result = {}
    if veh.struct is not None:
        struct_result = veh.struct.check(F_aero_B, F_th_B, tau_aero_B, T_w, t_hat_B)

    dx = np.zeros_like(x)
    dx[0:3] = v_I
    dx[3:6] = a_I
    dx[6:10] = qdot
    dx[10:13] = wdot
    dx[13] = mdot_total
    dx[14] = dT_w
    dx[15] = dT_int
    dx[16] = d_throttle

    # 質量、節流邊界
    if dx[13] != 0 and x[13] + dx[13] * 0.02 < 1e-6:
        dx[13] = 0.0
    dx[16] = np.clip(dx[16], -10.0, 10.0)

    aux = {"F_aero_B": F_aero_B, "F_th_B": F_th_B, "struct": struct_result}
    return (dx, tau_next, aux)


# =============================================================================
# 12) RK4 (需解包 dynamics 的 dx)
# =============================================================================

def rk4_step(f, t: float, x: np.ndarray, dt: float, veh: Vehicle, throttle: float,
             tau_prev: np.ndarray) -> tuple:
    k1, tau1, _ = f(t, x, veh, throttle, tau_prev)
    k2, tau2, _ = f(t + 0.5*dt, x + 0.5*dt*k1, veh, throttle, tau_prev)
    k3, tau3, _ = f(t + 0.5*dt, x + 0.5*dt*k2, veh, throttle, tau_prev)
    k4, tau4, _ = f(t + dt, x + dt*k3, veh, throttle, tau_prev)

    x_next = x + (dt/6.0) * (k1 + 2*k2 + 2*k3 + k4)
    x_next[6:10] = quat_normalize(x_next[6:10])
    x_next[13] = max(x_next[13], 0.0)
    x_next[16] = np.clip(x_next[16], 0.0, 1.0)
    return x_next, tau4


# =============================================================================
# 13) Demo
# =============================================================================

def run_demo(mode: str = "chemical", use_ecef: bool = False, use_aero_table: bool = True,
             use_actuator: bool = False, T_end: float = 25.0):
    veh = Vehicle()
    veh.prop.mode = mode
    veh.earth.use_ecef = use_ecef
    if use_aero_table:
        veh.aero.table = make_placeholder_aero_table()
    if use_actuator:
        veh.actuator = ActuatorModel(tau_max=50.0, rate_max=20.0)
        veh.allocator = ControlAllocator(B=np.eye(3), u_min=-np.ones(3), u_max=np.ones(3))

    earth = veh.earth
    r0 = np.array([earth.R + 1.0, 0.0, 0.0])
    v0 = np.array([0.0, 0.0, 0.0])
    q0 = np.array([1.0, 0.0, 0.0, 0.0])
    w0 = np.zeros(3)
    m0, Tw0, Tint0 = 50.0, 300.0, 300.0
    throttle0 = 1.0

    x = np.zeros(17)
    x[0:3], x[3:6], x[6:10], x[10:13] = r0, v0, q0, w0
    x[13], x[14], x[15], x[16] = m0, Tw0, Tint0, throttle0

    t, dt = 0.0, 0.02
    tau_prev = np.zeros(3)
    hist = []

    while t <= T_end and x[13] > 1e-6:
        r, v = x[0:3], x[3:6]
        h = np.linalg.norm(r) - earth.R
        V = np.linalg.norm(v)
        atm = veh.atm.properties(max(h, 0.0))
        qdyn = 0.5 * atm["rho"] * V * V
        row = [t, h, V, qdyn, x[13], x[14], x[15]]
        hist.append(row)

        throttle = 1.0 if t < 12.0 else 0.0
        x, tau_prev = rk4_step(dynamics, t, x, dt, veh, throttle, tau_prev)
        t += dt

    return np.array(hist, dtype=float)


# =============================================================================
# 14) 工程級公式庫：大氣/環境、氣動、可壓縮流、熱傳、結構、推進、控制、系統工程
# =============================================================================

class EngineeringFormulas:
    """工程級公式庫：可直接用於設計計算器/模擬器的核心方程組。"""

    # ========== 1) 大氣/環境 ==========
    @staticmethod
    def dynamic_pressure(rho: float, V: float) -> float:
        """動壓: q = 0.5 * ρ * V²"""
        return 0.5 * rho * V * V

    @staticmethod
    def dynamic_pressure_load(q: float, S: float, C: float) -> float:
        """動壓載荷: F_q = q * S * C"""
        return q * S * C

    @staticmethod
    def gust_alpha_increment(w_g: float, V: float) -> float:
        """風擾動等效迎角增量: Δα ≈ w_g / V"""
        return w_g / max(V, 1e-9)

    @staticmethod
    def gust_lift_increment(q: float, S: float, C_La: float, delta_alpha: float) -> float:
        """風擾動升力增量: ΔL ≈ q * S * C_Lα * Δα"""
        return q * S * C_La * delta_alpha

    @staticmethod
    def reynolds(rho: float, V: float, L: float, mu: float) -> float:
        """雷諾數: Re = ρ * V * L / μ"""
        return rho * V * L / max(mu, 1e-12)

    # ========== 2) 氣動 ==========
    @staticmethod
    def lift_force(q: float, S: float, C_L: float) -> float:
        """升力: L = q * S * C_L"""
        return q * S * C_L

    @staticmethod
    def drag_force(q: float, S: float, C_D: float) -> float:
        """阻力: D = q * S * C_D"""
        return q * S * C_D

    @staticmethod
    def moment(q: float, S: float, c: float, C_M: float) -> float:
        """力矩: M = q * S * c * C_M"""
        return q * S * c * C_M

    @staticmethod
    def drag_polar(C_D0: float, k: float, C_L: float) -> float:
        """阻力極線: C_D = C_D0 + k * C_L²"""
        return C_D0 + k * (C_L ** 2)

    @staticmethod
    def lift_linearized(C_L0: float, C_La: float, alpha: float) -> float:
        """升力線性化: C_L ≈ C_L0 + C_Lα * α"""
        return C_L0 + C_La * alpha

    @staticmethod
    def static_margin(x_NP: float, x_CG: float, c: float) -> float:
        """靜穩定裕度: SM = (x_NP - x_CG) / c"""
        return (x_NP - x_CG) / max(c, 1e-9)

    @staticmethod
    def pressure_coefficient(p: float, p_inf: float, rho_inf: float, V_inf: float) -> float:
        """壓力係數: C_p = (p - p_∞) / (0.5 * ρ_∞ * V_∞²)"""
        q_inf = 0.5 * rho_inf * V_inf * V_inf
        return (p - p_inf) / max(q_inf, 1e-9)

    # ========== 3) 可壓縮流 ==========
    @staticmethod
    def normal_shock_pressure_ratio(M1: float, gamma: float = 1.4) -> float:
        """正激波壓力比: p2/p1 = 1 + (2γ/(γ+1)) * (M1² - 1)"""
        return 1.0 + (2.0 * gamma / (gamma + 1.0)) * (M1 * M1 - 1.0)

    @staticmethod
    def normal_shock_density_ratio(M1: float, gamma: float = 1.4) -> float:
        """正激波密度比: ρ2/ρ1 = (γ+1)M1² / ((γ-1)M1² + 2)"""
        return ((gamma + 1.0) * M1 * M1) / ((gamma - 1.0) * M1 * M1 + 2.0)

    @staticmethod
    def normal_shock_mach2(M1: float, gamma: float = 1.4) -> float:
        """正激波後馬赫數: M2² = (1 + (γ-1)M1²/2) / (γ*M1² - (γ-1)/2)"""
        num = 1.0 + 0.5 * (gamma - 1.0) * M1 * M1
        den = gamma * M1 * M1 - 0.5 * (gamma - 1.0)
        return math.sqrt(num / max(den, 1e-9))

    @staticmethod
    def isentropic_temperature_ratio(M: float, gamma: float = 1.4) -> float:
        """等熵總溫比: Tt/T = 1 + (γ-1)M²/2"""
        return 1.0 + 0.5 * (gamma - 1.0) * M * M

    @staticmethod
    def isentropic_pressure_ratio(M: float, gamma: float = 1.4) -> float:
        """等熵總壓比: pt/p = (1 + (γ-1)M²/2)^(γ/(γ-1))"""
        T_ratio = 1.0 + 0.5 * (gamma - 1.0) * M * M
        return T_ratio ** (gamma / (gamma - 1.0))

    @staticmethod
    def prandtl_glauert_correction(C_p0: float, M_inf: float) -> float:
        """Prandtl-Glauert 壓縮性修正: C_p ≈ C_p0 / √(1 - M_∞²)"""
        if M_inf >= 1.0:
            return C_p0  # 超音速需其他修正
        return C_p0 / math.sqrt(max(1.0 - M_inf * M_inf, 1e-9))

    # ========== 4) 熱環境/熱傳 ==========
    @staticmethod
    def radiation_heat_flux(eps: float, sigma: float, T_w: float, T_env: float) -> float:
        """輻射熱通量: q_rad = ε * σ * (T_w⁴ - T_env⁴)"""
        return eps * sigma * (T_w**4 - T_env**4)

    @staticmethod
    def convective_heat_flux(h: float, T_aw: float, T_w: float) -> float:
        """對流熱通量: q_conv = h * (T_aw - T_w)"""
        return h * (T_aw - T_w)

    @staticmethod
    def nusselt_number(h: float, L: float, k_f: float) -> float:
        """Nusselt 數: Nu = h * L / k_f"""
        return h * L / max(k_f, 1e-12)

    @staticmethod
    def nusselt_correlation(Re: float, Pr: float, C: float = 0.332, m: float = 0.5, n: float = 0.333) -> float:
        """Nusselt 關聯式: Nu = C * Re^m * Pr^n (層流平板: C=0.332, m=0.5, n=1/3)"""
        return C * (Re ** m) * (Pr ** n)

    @staticmethod
    def heat_conduction_1d(k: float, dT_dx: float) -> float:
        """1D 導熱熱通量: q = -k * dT/dx (簡化，實際需解 PDE)"""
        return -k * dT_dx

    @staticmethod
    def stagnation_temperature(T: float, M: float, gamma: float = 1.4) -> float:
        """停滯溫度: T0 = T * (1 + (γ-1)M²/2)"""
        return T * (1.0 + 0.5 * (gamma - 1.0) * M * M)

    # ========== 5) 結構/材料 ==========
    @staticmethod
    def stress_axial(F: float, A: float) -> float:
        """軸向應力: σ = F / A"""
        return F / max(A, 1e-9)

    @staticmethod
    def stress_bending(M: float, y: float, I: float) -> float:
        """彎曲應力: σ_b = M * y / I"""
        return M * y / max(I, 1e-9)

    @staticmethod
    def stress_shear(T: float, r: float, J: float) -> float:
        """剪應力: τ = T * r / J"""
        return T * r / max(J, 1e-9)

    @staticmethod
    def stress_thin_cylinder_hoop(p: float, r: float, t: float) -> float:
        """薄壁圓筒環向應力: σ_θ = p * r / t"""
        return p * r / max(t, 1e-9)

    @staticmethod
    def stress_thin_cylinder_axial(p: float, r: float, t: float) -> float:
        """薄壁圓筒軸向應力: σ_z = p * r / (2*t)"""
        return p * r / max(2.0 * t, 1e-9)

    @staticmethod
    def von_mises_stress(sigma1: float, sigma2: float, sigma3: float) -> float:
        """von Mises 等效應力: σ_v = √(0.5 * [(σ1-σ2)² + (σ2-σ3)² + (σ3-σ1)²])"""
        s12 = (sigma1 - sigma2) ** 2
        s23 = (sigma2 - sigma3) ** 2
        s31 = (sigma3 - sigma1) ** 2
        return math.sqrt(0.5 * (s12 + s23 + s31))

    @staticmethod
    def euler_buckling_load(E: float, I: float, L: float, K: float = 1.0) -> float:
        """Euler 柱屈曲載荷: P_cr = π² * E * I / (K*L)²"""
        return (math.pi ** 2) * E * I / max((K * L) ** 2, 1e-9)

    @staticmethod
    def miner_damage(n_i: float, N_i: float) -> float:
        """Miner 累積損傷: D = Σ(n_i / N_i)"""
        return n_i / max(N_i, 1e-9)

    @staticmethod
    def paris_erdogan_da_dN(C: float, delta_K: float, m: float) -> float:
        """Paris-Erdogan 裂紋成長率: da/dN = C * (ΔK)^m"""
        return C * (delta_K ** m)

    @staticmethod
    def stress_intensity_factor(beta: float, delta_sigma: float, a: float) -> float:
        """應力強度因子: ΔK = β * Δσ * √(π*a)"""
        return beta * delta_sigma * math.sqrt(math.pi * a)

    @staticmethod
    def margin_of_safety(allowable: float, actual: float) -> float:
        """安全裕度: MS = (Allowable / Actual) - 1"""
        return (allowable / max(actual, 1e-9)) - 1.0

    @staticmethod
    def natural_frequency(k: float, m: float) -> float:
        """自然頻率: ω_n = √(k / m)"""
        return math.sqrt(k / max(m, 1e-9))

    @staticmethod
    def damping_ratio(c: float, k: float, m: float) -> float:
        """阻尼比: ζ = c / (2 * √(k*m))"""
        return c / max(2.0 * math.sqrt(k * m), 1e-9)

    # ========== 6) 飛行力學 ==========
    @staticmethod
    def velocity_rate_3dof(T: float, D: float, m: float, g: float, gamma: float) -> float:
        """3DoF 速度變化率: m*V̇ = T - D - m*g*sin(γ)"""
        return (T - D) / max(m, 1e-9) - g * math.sin(gamma)

    @staticmethod
    def flight_path_rate_3dof(L: float, m: float, g: float, gamma: float, V: float) -> float:
        """3DoF 航跡角變化率: m*V*γ̇ = L - m*g*cos(γ)"""
        return (L / max(m, 1e-9) - g * math.cos(gamma)) / max(V, 1e-9)

    @staticmethod
    def turn_radius(V: float, g: float, n: float) -> float:
        """轉彎半徑: R = V² / (g * √(n² - 1))"""
        return (V * V) / (g * math.sqrt(max(n * n - 1.0, 1e-9)))

    # ========== 7) 推進（擴充） ==========
    @staticmethod
    def thrust_equation(mdot: float, v_e: float, p_e: float, p_a: float, A_e: float) -> float:
        """推力方程: F = ṁ*v_e + (p_e - p_a)*A_e"""
        return mdot * v_e + (p_e - p_a) * A_e

    @staticmethod
    def specific_impulse(F: float, mdot: float, g0: float) -> float:
        """比衝: I_sp = F / (ṁ * g0)"""
        return F / max(mdot * g0, 1e-9)

    @staticmethod
    def total_impulse(F_t: np.ndarray, t: np.ndarray) -> float:
        """總衝量: I_tot = ∫ F(t) dt (梯形積分)"""
        if len(F_t) < 2:
            return 0.0
        return np.trapz(F_t, t)

    @staticmethod
    def delta_v_rocket_equation(I_sp: float, g0: float, m0: float, mf: float) -> float:
        """火箭方程 Δv: Δv = I_sp * g0 * ln(m0/mf)"""
        return I_sp * g0 * math.log(m0 / max(mf, 1e-9))

    @staticmethod
    def area_ratio_from_mach(M: float, gamma: float = 1.4) -> float:
        """面積比-馬赫數關係: A/A* = (1/M) * [2/(γ+1) * (1 + (γ-1)M²/2)]^((γ+1)/(2(γ-1)))"""
        if M <= 0:
            return 1e30
        v = 1.0 + 0.5 * (gamma - 1.0) * M * M
        exp = (gamma + 1.0) / (2.0 * (gamma - 1.0))
        return (1.0 / M) * ((2.0 / (gamma + 1.0)) * v) ** exp

    @staticmethod
    def characteristic_velocity(p_c: float, A_t: float, mdot: float) -> float:
        """特徵速度: c* = p_c * A_t / ṁ"""
        return p_c * A_t / max(mdot, 1e-9)

    @staticmethod
    def thrust_coefficient(F: float, p_c: float, A_t: float) -> float:
        """推力係數: C_F = F / (p_c * A_t)"""
        return F / max(p_c * A_t, 1e-9)

    @staticmethod
    def gravity_loss(g: float, gamma: float, t: np.ndarray) -> float:
        """重力損失: Δv_gravity = ∫ g*sin(γ) dt"""
        if len(t) < 2:
            return 0.0
        g_sin_gamma = g * np.sin(gamma)
        return np.trapz(g_sin_gamma, t)

    # ========== 8) 電推進 ==========
    @staticmethod
    def kinetic_power(mdot: float, v_e: float) -> float:
        """動能功率: P_k = 0.5 * ṁ * v_e²"""
        return 0.5 * mdot * v_e * v_e

    @staticmethod
    def electric_thrust_from_power(eta: float, P_in: float, v_e: float) -> float:
        """電推進推力: F = 2*η*P_in / v_e"""
        return 2.0 * eta * P_in / max(v_e, 1e-9)

    @staticmethod
    def exhaust_velocity_ion(q: float, V_acc: float, m_i: float) -> float:
        """離子推進排氣速度: v_e ≈ √(2*q*V_acc / m_i)"""
        return math.sqrt(2.0 * q * V_acc / max(m_i, 1e-9))

    @staticmethod
    def propellant_mass_electric(m_d: float, delta_v: float, I_sp: float, g0: float) -> float:
        """電推進推進劑質量: m_p = m_d * (e^(Δv/(I_sp*g0)) - 1)"""
        return m_d * (math.exp(delta_v / max(I_sp * g0, 1e-9)) - 1.0)

    @staticmethod
    def pulse_impulse_bit(I_b: float, f: float) -> float:
        """脈衝平均推力: F_avg = I_b * f"""
        return I_b * f

    # ========== 9) 核熱推進 ==========
    @staticmethod
    def nuclear_thermal_power(mdot: float, c_p: float, T_hot: float, T_in: float) -> float:
        """核熱功率: Q̇ = ṁ * c_p * (T_hot - T_in)"""
        return mdot * c_p * (T_hot - T_in)

    # ========== 10) 核脈衝/外部脈衝 ==========
    @staticmethod
    def nuclear_pulse_isp(C_0: float, V_e: float, g0: float) -> float:
        """核脈衝比衝: I_sp ≈ C_0 * V_e / g0"""
        return C_0 * V_e / g0

    # ========== 11) 渦輪泵/流體機械 ==========
    @staticmethod
    def pump_power(delta_p: float, V_dot: float, eta_pump: float) -> float:
        """泵功率: P_pump = Δp * V̇ / η_pump"""
        return delta_p * V_dot / max(eta_pump, 1e-9)

    @staticmethod
    def volume_flow_rate(mdot: float, rho: float) -> float:
        """體積流率: V̇ = ṁ / ρ"""
        return mdot / max(rho, 1e-9)

    @staticmethod
    def darcy_weisbach_pressure_drop(f: float, L: float, D: float, rho: float, V: float) -> float:
        """Darcy-Weisbach 壓降: Δp = f * (L/D) * (ρ*V²/2)"""
        return f * (L / max(D, 1e-9)) * (0.5 * rho * V * V)

    # ========== 12) 控制/導航 ==========
    @staticmethod
    def pid_control(Kp: float, Ki: float, Kd: float, e: float, e_int: float, e_dot: float) -> float:
        """PID 控制: u = Kp*e + Ki*∫e + Kd*de/dt"""
        return Kp * e + Ki * e_int + Kd * e_dot

    @staticmethod
    def state_space_output(A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray,
                           x: np.ndarray, u: np.ndarray) -> np.ndarray:
        """狀態空間輸出: y = C*x + D*u (ẋ = A*x + B*u 需數值積分)"""
        return C @ x + D @ u

    @staticmethod
    def lqr_gain(A: np.ndarray, B: np.ndarray, Q: np.ndarray, R: np.ndarray) -> np.ndarray:
        """LQR 增益: K (解 Riccati 方程，簡化版需 scipy.linalg.solve_continuous_are)"""
        try:
            from scipy.linalg import solve_continuous_are
            P = solve_continuous_are(A, B, Q, R)
            K = np.linalg.solve(R, B.T @ P)
            return K
        except ImportError:
            # 簡化：若無 scipy，回傳佔位
            return np.zeros((B.shape[1], A.shape[0]))

    # ========== 13) 系統工程 ==========
    @staticmethod
    def tolerance_rss(tolerances: np.ndarray) -> float:
        """RSS 公差堆疊: T_RSS = √(Σ T_i²)"""
        return math.sqrt(np.sum(tolerances ** 2))

    @staticmethod
    def reliability_series(reliabilities: np.ndarray) -> float:
        """串聯可靠度: R_series = Π R_i"""
        return np.prod(reliabilities)

    @staticmethod
    def reliability_parallel(reliabilities: np.ndarray) -> float:
        """並聯可靠度: R_parallel = 1 - Π(1 - R_i)"""
        return 1.0 - np.prod(1.0 - reliabilities)

    @staticmethod
    def thermal_expansion(alpha: float, L: float, delta_T: float) -> float:
        """熱膨脹: ΔL = α * L * ΔT"""
        return alpha * L * delta_T

    @staticmethod
    def mass_budget(m_dry: float, m_prop: float, m_payload: float) -> float:
        """質量預算: m_0 = m_dry + m_prop + m_payload"""
        return m_dry + m_prop + m_payload

    # ========== 14) 推進進階：推力係數、等效速度、多級火箭 ==========
    @staticmethod
    def thrust_coefficient_ideal(p_e: float, p_c: float, p_a: float, A_e: float, A_t: float,
                                  gamma: float = 1.4) -> float:
        """理想推力係數: c_F = √(2γ²/(γ-1) * (2/(γ+1))^((γ+1)/(γ-1)) * [1-(p_e/p_c)^((γ-1)/γ)]) + (p_e-p_a)*A_e/(p_c*A_t)"""
        term1 = (2.0 * gamma * gamma) / (gamma - 1.0)
        term2 = (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
        term3 = 1.0 - (p_e / max(p_c, 1e-9)) ** ((gamma - 1.0) / gamma)
        c_F_momentum = math.sqrt(term1 * term2 * term3)
        c_F_pressure = (p_e - p_a) * A_e / max(p_c * A_t, 1e-9)
        return c_F_momentum + c_F_pressure

    @staticmethod
    def thrust_from_coefficient(c_F: float, p_c: float, A_t: float) -> float:
        """由推力係數計算推力: F = c_F * p_c * A_t"""
        return c_F * p_c * A_t

    @staticmethod
    def equivalent_exhaust_velocity(v_e: float, p_e: float, p_a: float, A_e: float, mdot: float) -> float:
        """等效排氣速度: V_eq = v_e + (p_e - p_a)*A_e / ṁ"""
        return v_e + (p_e - p_a) * A_e / max(mdot, 1e-9)

    @staticmethod
    def specific_impulse_from_equivalent(V_eq: float, g0: float) -> float:
        """由等效速度計算比衝: I_sp = V_eq / g0"""
        return V_eq / g0

    @staticmethod
    def thrust_to_weight_ratio(F: float, m: float, g0: float) -> float:
        """推重比: T/W = F / (m * g0)"""
        return F / max(m * g0, 1e-9)

    @staticmethod
    def multi_stage_delta_v(v_e_list: np.ndarray, m0_list: np.ndarray, mf_list: np.ndarray) -> float:
        """多級火箭總 Δv: Δv_total = Σ v_e,i * ln(m0,i/mf,i)"""
        if len(v_e_list) != len(m0_list) or len(m0_list) != len(mf_list):
            return 0.0
        delta_v_total = 0.0
        for i in range(len(v_e_list)):
            delta_v_total += v_e_list[i] * math.log(m0_list[i] / max(mf_list[i], 1e-9))
        return delta_v_total

    @staticmethod
    def payload_ratio(m_payload: float, m0: float) -> float:
        """有效載荷比: m_payload / m0"""
        return m_payload / max(m0, 1e-9)

    @staticmethod
    def payload_ratio_from_delta_v(delta_v: float, v_e: float) -> float:
        """由 Δv 計算有效載荷比: m_payload/m0 = 1 - e^(-Δv/v_e)"""
        return 1.0 - math.exp(-delta_v / max(v_e, 1e-9))

    @staticmethod
    def initial_mass_from_delta_v(mf: float, delta_v: float, v_e: float) -> float:
        """由 Δv 反解起始質量: m0 = mf * e^(Δv/v_e)"""
        return mf * math.exp(delta_v / max(v_e, 1e-9))

    @staticmethod
    def propellant_mass_from_delta_v(m0: float, delta_v: float, v_e: float) -> float:
        """由 Δv 計算推進劑質量: m_prop = m0 - mf = m0 * (1 - e^(-Δv/v_e))"""
        return m0 * (1.0 - math.exp(-delta_v / max(v_e, 1e-9)))

    @staticmethod
    def instantaneous_acceleration(F: float, D: float, m: float, g: float) -> float:
        """瞬時加速度: a = (F - D) / m - g"""
        return (F - D) / max(m, 1e-9) - g

    @staticmethod
    def specific_impulse_altitude_dependent(F_h: float, mdot: float, g0: float) -> float:
        """高度相關比衝: I_sp(h) = F(h) / (ṁ * g0)"""
        return F_h / max(mdot * g0, 1e-9)

    # ========== 15) 推進熱力學進階 ==========
    @staticmethod
    def exhaust_velocity_isentropic(c_p: float, T_c: float, p_e: float, p_c: float, gamma: float = 1.4) -> float:
        """等熵出口流速: v_e = √(2*c_p*T_c*[1 - (p_e/p_c)^((γ-1)/γ)])"""
        term = 1.0 - (p_e / max(p_c, 1e-9)) ** ((gamma - 1.0) / gamma)
        return math.sqrt(2.0 * c_p * T_c * max(term, 0.0))

    @staticmethod
    def mixed_gas_cp(n_moles: np.ndarray, cp_values: np.ndarray) -> float:
        """混合氣體定壓比熱: C_p,mix = Σ(n_j * C_p,j) / Σ(n_j)"""
        if len(n_moles) != len(cp_values) or len(n_moles) == 0:
            return 0.0
        numerator = np.sum(n_moles * cp_values)
        denominator = np.sum(n_moles)
        return numerator / max(denominator, 1e-9)

    @staticmethod
    def mixed_gas_gamma(C_p_mix: float, R: float) -> float:
        """混合氣體比熱比: γ_mix = C_p,mix / (C_p,mix - R)"""
        return C_p_mix / max(C_p_mix - R, 1e-9)

    @staticmethod
    def propulsion_efficiency(I_sp_actual: float, I_sp_ideal: float) -> float:
        """推進效率: η_prop = I_sp,actual / I_sp,ideal"""
        return I_sp_actual / max(I_sp_ideal, 1e-9)

    @staticmethod
    def nozzle_efficiency(v_e_actual: float, v_e_ideal: float) -> float:
        """噴管效率: η_nozzle = v_e,actual / v_e,ideal"""
        return v_e_actual / max(v_e_ideal, 1e-9)

    @staticmethod
    def combustion_efficiency(c_star_actual: float, c_star_ideal: float) -> float:
        """燃燒效率: η_combustion = c*_actual / c*_ideal"""
        return c_star_actual / max(c_star_ideal, 1e-9)

    # ========== 16) 燃燒化學與混合比 ==========
    @staticmethod
    def oxidizer_fuel_ratio(m_ox: float, m_f: float) -> float:
        """混合比: O/F = m_ox / m_f"""
        return m_ox / max(m_f, 1e-9)

    @staticmethod
    def reaction_enthalpy_change(nu_i: np.ndarray, h_f0_i: np.ndarray) -> float:
        """反應焓變: ΔH_r = Σ(ν_i * h_f0,i) (標準生成焓)"""
        if len(nu_i) != len(h_f0_i):
            return 0.0
        return np.sum(nu_i * h_f0_i)

    @staticmethod
    def mass_flow_from_density(rho_e: float, v_e: float, A_e: float) -> float:
        """由密度計算質量流率: ṁ = ρ_e * v_e * A_e"""
        return rho_e * v_e * A_e

    # ========== 17) 電推進進階 ==========
    @staticmethod
    def electric_propulsion_thrust(eta_T: float, mdot: float, v_e: float) -> float:
        """電推進總推力: F = η_T * ṁ * v_e"""
        return eta_T * mdot * v_e

    @staticmethod
    def electric_propulsion_efficiency(eta_e: float, eta_m: float, eta_c: float) -> float:
        """電推進總效率: η_T = η_e * η_m * η_c"""
        return eta_e * eta_m * eta_c

    @staticmethod
    def electric_thermal_exhaust_velocity(c_p: float, T_e: float, T_a: float) -> float:
        """電熱式排氣速度: v_e = √(2*c_p*(T_e - T_a))"""
        return math.sqrt(2.0 * c_p * max(T_e - T_a, 0.0))

    @staticmethod
    def electromagnetic_thrust_approx(B: float, mu_0: float, A: float) -> float:
        """電磁式推力近似: F ~ B²/(2*μ0) * A"""
        return (B * B) / (2.0 * mu_0) * A

    @staticmethod
    def pulsed_inductive_thrust(E_p: float, v_e: float, delta_t: float) -> float:
        """脈衝感應推進器推力: F = 2*E_p / (v_e * Δt)"""
        return 2.0 * E_p / max(v_e * delta_t, 1e-9)

    @staticmethod
    def pulsed_inductive_avg_thrust(F_pulse: float, f: float) -> float:
        """脈衝感應平均推力: F_avg = F_pulse * f"""
        return F_pulse * f

    @staticmethod
    def pulse_impulse_bit_integral(F_t: np.ndarray, t: np.ndarray) -> float:
        """脈衝衝量位元: I_b = ∫ F(t) dt"""
        if len(F_t) < 2 or len(t) < 2:
            return 0.0
        return np.trapz(F_t, t)

    @staticmethod
    def pulse_specific_impulse(I_b: float, m_b: float, g0: float) -> float:
        """脈衝比衝: I_sp = I_b / (m_b * g0)"""
        return I_b / max(m_b * g0, 1e-9)

    # ========== 18) 核熱推進進階 ==========
    @staticmethod
    def nuclear_thermal_exhaust_velocity(gamma: float, R: float, T_h: float) -> float:
        """核熱推進排氣速度: v_e ≈ √(2*γ*R*T_h)"""
        return math.sqrt(2.0 * gamma * R * T_h)

    @staticmethod
    def nuclear_electric_power(eta_gen: float, P_nuclear: float) -> float:
        """核電推進功率: P_elec = η_gen * P_nuclear"""
        return eta_gen * P_nuclear

    @staticmethod
    def nuclear_pulse_thrust_power(F: float, v_e: float) -> float:
        """核脈衝推力與功率: P = 0.5 * F * v_e"""
        return 0.5 * F * v_e

    @staticmethod
    def nuclear_pulse_isp_proportional(E_pulse: float, mdot_p: float, g0: float, C: float = 1.0) -> float:
        """核脈衝比衝: I_sp ∝ C * E_pulse / (ṁ_p * g0)"""
        return C * E_pulse / max(mdot_p * g0, 1e-9)

    # ========== 19) 6-DoF 動力學擴充 ==========
    @staticmethod
    def mass_rate_change(mdot_fuel: float) -> float:
        """質量變化率: ṁ = -ṁ_fuel"""
        return -mdot_fuel

    @staticmethod
    def center_of_gravity_position(r_positions: np.ndarray, dm: np.ndarray, m_total: float) -> np.ndarray:
        """重心位置: r_CG = (1/m) * ∫ r * dm (離散: Σ(r_i * dm_i) / m_total)"""
        if len(r_positions) == 0 or len(dm) == 0 or m_total <= 0:
            return np.zeros(3)
        if r_positions.shape[0] != len(dm):
            return np.zeros(3)
        r_weighted = np.sum(r_positions * dm.reshape(-1, 1), axis=0)
        return r_weighted / m_total

    # ========== 20) 最優控制與軌跡最佳化 ==========
    @staticmethod
    def hamiltonian(lambda_vec: np.ndarray, f_xu: np.ndarray, L: float) -> float:
        """Hamiltonian: H = λ^T * f(x,u) + L(x,u)"""
        if len(lambda_vec) != len(f_xu):
            return 0.0
        return np.dot(lambda_vec, f_xu) + L

    @staticmethod
    def low_thrust_cost_function(u_t: np.ndarray, t: np.ndarray) -> float:
        """低推力成本函數: J = ∫ |u(t)| dt (L1 範數)"""
        if len(u_t) < 2 or len(t) < 2:
            return 0.0
        u_norm = np.linalg.norm(u_t, axis=0) if u_t.ndim > 1 else np.abs(u_t)
        return np.trapz(u_norm, t)

    # ========== 21) 多學科設計優化 (MDO) ==========
    @staticmethod
    def mdo_objective_function(x: np.ndarray, weights: np.ndarray, objectives: np.ndarray) -> float:
        """MDO 目標函數: J = Σ(w_i * f_i(x))"""
        if len(weights) != len(objectives):
            return 0.0
        return np.sum(weights * objectives)

    @staticmethod
    def mdo_constraint_violation(g: np.ndarray) -> float:
        """MDO 約束違反量: max(0, g_i) 的總和"""
        return np.sum(np.maximum(g, 0.0))

    # ========== 22) 燃料燃燒與 regression rate ==========
    @staticmethod
    def hybrid_regression_rate(a: float, G: float, n: float) -> float:
        """混合火箭 regression rate: ṙ = a * G^n"""
        return a * (G ** n)

    @staticmethod
    def mass_consumption_rate(rho_fuel: float, r_dot: float, A_burn: float) -> float:
        """質量消耗率: ṁ = ρ_fuel * ṙ * A_burn"""
        return rho_fuel * r_dot * A_burn

    # ========== 23) 能量分析 ==========
    @staticmethod
    def kinetic_energy(m: float, v: float) -> float:
        """動能: E_k = 0.5 * m * v²"""
        return 0.5 * m * v * v

    @staticmethod
    def kinetic_power_from_thrust(F: float, v_e: float) -> float:
        """推力動能功率: P_k = 0.5 * F * v_e"""
        return 0.5 * F * v_e

    @staticmethod
    def energy_conservation_ideal(mdot: float, v_e: float, P_source: float) -> float:
        """理想能量守恆: 0.5 * ṁ * v_e² = P_source (誤差)"""
        P_k = 0.5 * mdot * v_e * v_e
        return P_k - P_source

    @staticmethod
    def total_enthalpy_balance(mdot_e: float, h_t: float, V_e: float, mdot_f: float, delta_H_r: float) -> float:
        """總焓平衡: ṁ_e*(h_t + V_e²/2) = ṁ_f*ΔH_r (誤差)"""
        left = mdot_e * (h_t + 0.5 * V_e * V_e)
        right = mdot_f * delta_H_r
        return left - right

    # ========== 24) 特徵速度理論公式 ==========
    @staticmethod
    def characteristic_velocity_theoretical(gamma: float, R: float, T_c: float) -> float:
        """
        特徵速度理論值: c* = √(R*T_c/γ) * (2/(γ+1))^((γ+1)/(2(γ-1)))
        """
        term1 = math.sqrt(R * T_c / gamma)
        term2 = (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        return term1 * term2

    @staticmethod
    def isp_from_cf_cstar(c_F: float, c_star: float, g0: float) -> float:
        """
        比衝與推力係數、特徵速度關係: I_sp = (c_F * c*) / g0
        """
        return (c_F * c_star) / g0

    # ========== 25) 阻力分解 ==========
    @staticmethod
    def drag_skin_friction(C_f: float, S_wet: float, q: float) -> float:
        """皮膚摩擦阻力: D_skin = C_f * S_wet * q"""
        return C_f * S_wet * q

    @staticmethod
    def drag_form(C_D0: float, S_ref: float, q: float) -> float:
        """形狀阻力: D_form = C_D0 * S_ref * q"""
        return C_D0 * S_ref * q

    @staticmethod
    def drag_wave(C_D_wave: float, S_ref: float, q: float) -> float:
        """波阻力（超音速）: D_wave = C_D_wave * S_ref * q"""
        return C_D_wave * S_ref * q

    @staticmethod
    def drag_induced(k: float, C_L: float, S_ref: float, q: float) -> float:
        """誘導阻力: D_induced = k * C_L² * S_ref * q"""
        return k * (C_L ** 2) * S_ref * q

    @staticmethod
    def total_drag_decomposed(C_f: float, S_wet: float, C_D0: float, C_D_wave: float,
                              k: float, C_L: float, S_ref: float, q: float) -> dict:
        """總阻力分解"""
        D_skin = C_f * S_wet * q
        D_form = C_D0 * S_ref * q
        D_wave = C_D_wave * S_ref * q
        D_induced = k * (C_L ** 2) * S_ref * q
        D_total = D_skin + D_form + D_wave + D_induced
        return {
            "D_skin": D_skin,
            "D_form": D_form,
            "D_wave": D_wave,
            "D_induced": D_induced,
            "D_total": D_total
        }

    # ========== 26) 實際 Δv 損失 ==========
    @staticmethod
    def delta_v_drag_loss(D: np.ndarray, m: np.ndarray, t: np.ndarray) -> float:
        """阻力損失: Δv_drag = ∫ (D/m) dt"""
        if len(D) < 2 or len(m) < 2 or len(t) < 2:
            return 0.0
        integrand = D / np.maximum(m, 1e-9)
        return np.trapz(integrand, t)

    @staticmethod
    def delta_v_gravity_loss(g: float, gamma: np.ndarray, t: np.ndarray) -> float:
        """重力損失: Δv_gravity = ∫ g*sin(γ) dt"""
        if len(gamma) < 2 or len(t) < 2:
            return 0.0
        integrand = g * np.sin(gamma)
        return np.trapz(integrand, t)

    @staticmethod
    def delta_v_real(delta_v_ideal: float, delta_v_drag: float, delta_v_gravity: float) -> float:
        """實際 Δv: Δv_real = Δv_ideal - Δv_drag - Δv_gravity"""
        return delta_v_ideal - delta_v_drag - delta_v_gravity

    # ========== 27) 質量比與燃料效率 ==========
    @staticmethod
    def mass_ratio(m0: float, mf: float) -> float:
        """質量比: MR = m0 / mf"""
        return m0 / max(mf, 1e-9)

    @staticmethod
    def propellant_fraction(m_prop: float, m0: float) -> float:
        """推進劑分數: ζ = m_prop / m0 = 1 - mf/m0"""
        return m_prop / max(m0, 1e-9)

    # ========== 28) 火箭瞬時質量模型 ==========
    @staticmethod
    def mass_linear_burnout(m0: float, mf: float, t: float, t_b: float) -> float:
        """
        線性燃燒質量模型: m(t) = m0 - (m0 - mf) * (t/t_b)
        """
        if t < 0:
            return m0
        if t >= t_b:
            return mf
        return m0 - (m0 - mf) * (t / max(t_b, 1e-9))

    @staticmethod
    def velocity_with_gravity(I_sp: float, g0: float, m0: float, m: float, t: float) -> float:
        """
        含重力修正的速度: u = g0 * [I_sp * ln(m0/m) - t]
        """
        return g0 * (I_sp * math.log(m0 / max(m, 1e-9)) - t)

    # ========== 29) 推進能量轉換 ==========
    @staticmethod
    def combustion_heat_power(mdot_f: float, delta_H_r: float) -> float:
        """燃燒熱功率: Q_comb = ṁ_f * ΔH_r"""
        return mdot_f * delta_H_r

    @staticmethod
    def exhaust_kinetic_power(mdot: float, v_e: float) -> float:
        """排氣動能功率: P_k = 0.5 * ṁ * v_e²"""
        return 0.5 * mdot * v_e * v_e

    @staticmethod
    def propulsion_energy_efficiency(P_k: float, Q_comb: float) -> float:
        """推進能量效率: η = P_k / Q_comb"""
        return P_k / max(Q_comb, 1e-9)

    # ========== 30) Oberth 效應 ==========
    @staticmethod
    def oberth_effect_delta_v(mu: float, r1: float, r2: float, v_at_r1: float) -> float:
        """
        Oberth 效應 Δv 增益（簡化）:
        Δv_Oberth ≈ √(μ/r1) * (√(2*r2/(r1+r2)) - 1) + ...
        """
        v_circ = math.sqrt(mu / max(r1, 1e-9))
        term = math.sqrt(2.0 * r2 / max(r1 + r2, 1e-9)) - 1.0
        return v_circ * term

    # ========== 31) 推重比與起飛性能 ==========
    @staticmethod
    def takeoff_capability(T_W: float, g0: float) -> bool:
        """起飛能力判斷: T/W > 1.0"""
        return T_W > 1.0

    @staticmethod
    def acceleration_from_twr(T_W: float, g0: float, D_W: float = 0.0) -> float:
        """
        由推重比計算加速度: a = (T/W - D/W - 1) * g0
        D/W: 阻重比
        """
        return (T_W - D_W - 1.0) * g0

    # ========== 32) 多級火箭質量分配 ==========
    @staticmethod
    def stage_mass_allocation(m0_i: float, m_i: float, m_i_plus_1: float) -> dict:
        """
        級間質量分配: m0,i = m_i + m_i+1
        m_i: 第 i 級乾重+推進系統
        m_i+1: 下一級全部（作為載荷）
        """
        m0_calc = m_i + m_i_plus_1
        error = abs(m0_calc - m0_i)
        return {
            "m0_calculated": m0_calc,
            "m0_given": m0_i,
            "error": error,
            "valid": error < 0.01 * m0_i
        }

    # ========== 33) 固體火箭 regression rate ==========
    @staticmethod
    def solid_regression_rate(a: float, G: float, n: float) -> float:
        """
        固體火箭 regression rate: ṙ = a * G^n
        G: 單位截面質量流率 (kg/m²/s)
        """
        return a * (G ** n)

    # ========== 34) 相對論火箭方程（極端情況） ==========
    @staticmethod
    def relativistic_rocket_equation(v_e: float, c: float, m0: float, mf: float) -> float:
        """
        相對論火箭方程: v/c = tanh((v_e/c) * ln(m0/mf))
        c: 光速 ≈ 3e8 m/s
        """
        if v_e >= c:
            return 1.0  # 光速上限
        arg = (v_e / c) * math.log(m0 / max(mf, 1e-9))
        return math.tanh(arg)

    # ========== 35) 最大高度估算（簡化） ==========
    @staticmethod
    def max_altitude_simplified(g: float, t_b: float, I_sp: float, m0: float, mf: float) -> float:
        """
        最大高度估算（不含大氣阻力，簡化）:
        h_b ≈ g * [-t_b*I_sp*ln(m0/mf-1) + t_b*I_sp - 0.5*t_b²]
        """
        term1 = -t_b * I_sp * math.log(m0 / max(mf, 1e-9) - 1.0)
        term2 = t_b * I_sp
        term3 = -0.5 * t_b * t_b
        return g * (term1 + term2 + term3)


# =============================================================================
# 15) 擴充：將公式庫整合到現有類中（作為類方法或工具函數）
# =============================================================================

# 將公式庫實例化供外部使用
eng_formulas = EngineeringFormulas()

# 擴充 ISA 類以包含更多派生量
def _isa_extended_properties(self, h: float) -> dict:
    """擴充 ISA.properties 以包含更多工程量"""
    base = self.properties(h)
    rho, V = base["rho"], 0.0  # V 需從外部傳入
    mu = base.get("mu", self.mu_ref * (base["T"] / self.T_ref) ** 1.5 * 
                  (self.T_ref + self.S_suth) / (base["T"] + self.S_suth))
    # 可選：加入動壓、Re 等（需 V）
    return base

# 擴充 AeroModel 以包含靜穩定計算
def _aero_static_stability(self, x_NP: float, x_CG: float, c_ref: float) -> dict:
    """計算靜穩定裕度與 C_Mα"""
    SM = eng_formulas.static_margin(x_NP, x_CG, c_ref)
    # 假設 C_Mα 與 SM 相關（簡化）
    C_M_alpha = -SM * 0.1  # 佔位關係
    return {"SM": SM, "C_M_alpha": C_M_alpha, "stable": C_M_alpha < 0.0}

# 擴充 Propulsion 以包含更多推進性能計算
def _prop_performance_metrics(self, p_c: float, A_t: float, mdot: float, 
                              F: float, I_sp: float, g0: float) -> dict:
    """計算推進性能指標"""
    c_star = eng_formulas.characteristic_velocity(p_c, A_t, mdot)
    C_F = eng_formulas.thrust_coefficient(F, p_c, A_t)
    I_sp_calc = eng_formulas.specific_impulse(F, mdot, g0)
    return {"c_star": c_star, "C_F": C_F, "I_sp_calc": I_sp_calc}


if __name__ == "__main__":
    hist = run_demo(mode="chemical", use_aero_table=True, use_actuator=True)
    print("t(s)  h(m)   V(m/s)  q(Pa)   m(kg)  Tw(K)  Tint(K)")
    for row in hist[:: max(1, len(hist)//10)]:
        print(f"{row[0]:5.2f} {row[1]:7.1f} {row[2]:7.1f} {row[3]:7.1f} {row[4]:6.2f} {row[5]:6.1f} {row[6]:7.1f}")

    try:
        import matplotlib.pyplot as plt
        t = hist[:, 0]
        fig, ax = plt.subplots(2, 2, figsize=(10, 8))
        ax[0,0].plot(t, hist[:,1]); ax[0,0].set_xlabel("t (s)"); ax[0,0].set_ylabel("h (m)"); ax[0,0].set_title("Altitude")
        ax[0,1].plot(t, hist[:,2]); ax[0,1].set_xlabel("t (s)"); ax[0,1].set_ylabel("V (m/s)"); ax[0,1].set_title("Speed")
        ax[1,0].plot(t, hist[:,3]); ax[1,0].set_xlabel("t (s)"); ax[1,0].set_ylabel("q (Pa)"); ax[1,0].set_title("Dynamic Pressure")
        ax[1,1].plot(t, hist[:,5]); ax[1,1].set_xlabel("t (s)"); ax[1,1].set_ylabel("Tw (K)"); ax[1,1].set_title("Surface Temp")
        plt.tight_layout(); plt.show()
    except Exception:
        pass
