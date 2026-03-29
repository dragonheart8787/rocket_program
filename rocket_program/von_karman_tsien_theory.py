# -*- coding: utf-8 -*-
"""
Von Kármán (馮·卡門) 與 Tsien (錢學森) 理論模組
整合兩位大師的核心理論、公式與設計方法論
"""

from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np


# =============================================================================
# 1) Von Kármán 理論核心
# =============================================================================

class VonKarmanTheory:
    """馮·卡門理論核心公式與方法"""

    # ========== 1.1 幾何設計 ==========
    @staticmethod
    def von_karman_nose_cone(x: float, L: float, R: float, n: float = 0.75) -> float:
        """
        Von Kármán 頭錐形狀（最小波阻）: x = L * (1 - (r/R)^n)
        一般 n = 0.75（卡門建議值）
        """
        if x < 0 or x > L or R <= 0:
            return 0.0
        r = R * ((1.0 - x / max(L, 1e-9)) ** (1.0 / max(n, 1e-9)))
        return r

    @staticmethod
    def sears_haack_body_radius(x: float, L: float, R_max: float) -> float:
        """
        Sears-Haack Body（最小波阻三維體，卡門指導學生完成）
        r(x) = R_max * sqrt(1 - (2x/L - 1)^2)
        """
        if x < 0 or x > L:
            return 0.0
        xi = 2.0 * x / max(L, 1e-9) - 1.0
        return R_max * math.sqrt(max(1.0 - xi * xi, 0.0))

    # ========== 1.2 氣動理論 ==========
    @staticmethod
    def lifting_line_theory(AR: float, alpha: float) -> float:
        """
        升力線理論（有限翼）: C_L = (2π*AR / (AR+2)) * α
        AR: 縱橫比 (Aspect Ratio)
        """
        return (2.0 * math.pi * AR / (AR + 2.0)) * alpha

    @staticmethod
    def karman_tsien_compressibility(C_p0: float, M: float) -> float:
        """
        Kármán-Tsien 可壓縮性修正（比 Prandtl-Glauert 更精確）
        C_p = C_p0/√(1-M²) + (M²/(1+√(1-M²))) * C_p0²/2
        """
        if M >= 1.0:
            return C_p0  # 超音速需其他修正
        sqrt_term = math.sqrt(max(1.0 - M * M, 1e-9))
        term1 = C_p0 / sqrt_term
        term2 = (M * M / (1.0 + sqrt_term)) * (C_p0 * C_p0) / 2.0
        return term1 + term2

    # ========== 1.3 邊界層理論 ==========
    @staticmethod
    def karman_momentum_integral(dtheta_dx: float, H: float, theta: float, U: float, dU_dx: float, C_f: float) -> float:
        """
        von Kármán 動量積分方程: dθ/dx + ((2+H)*θ/U)*dU/dx = C_f/2
        返回誤差（用於迭代求解）
        """
        left = dtheta_dx + ((2.0 + H) * theta / max(U, 1e-9)) * dU_dx
        right = C_f / 2.0
        return left - right

    @staticmethod
    def shape_factor(H: float) -> float:
        """
        形狀係數: H = δ*/θ (位移厚度 / 動量厚度)
        典型值: 層流 H≈2.6, 紊流 H≈1.3-1.4
        """
        return H

    # ========== 1.4 渦街 ==========
    @staticmethod
    def karman_vortex_street_frequency(V: float, D: float, St: float = 0.2) -> float:
        """
        Kármán Vortex Street 頻率: f = St * V / D
        St (Strouhal 數) ≈ 0.2 (典型值)
        """
        return St * V / max(D, 1e-9)

    @staticmethod
    def strouhal_number(f: float, D: float, V: float) -> float:
        """Strouhal 數: St = f*D / V"""
        return f * D / max(V, 1e-9)

    # ========== 1.5 超音速 ==========
    @staticmethod
    def oblique_shock_angle(M1: float, theta: float, gamma: float = 1.4) -> float:
        """
        斜激波角（θ-β-M 關係，卡門系統化整理）
        tan(θ) = 2*cot(β) * (M1²*sin²(β)-1) / (M1²*(γ+cos(2β))+2)
        返回激波角 β (需迭代求解，此處為簡化近似)
        """
        # 簡化：使用小角度近似或查表
        # 完整解需 Newton-Raphson
        if M1 <= 1.0:
            return 0.0
        beta_approx = math.asin(1.0 / M1) + theta  # 弱激波近似
        return beta_approx

    @staticmethod
    def prandtl_meyer_function(M: float, gamma: float = 1.4) -> float:
        """
        Prandtl-Meyer 扇形膨脹: ν(M) = √((γ+1)/(γ-1)) * arctan(√((γ-1)/(γ+1)*(M²-1))) - arctan(√(M²-1))
        """
        if M <= 1.0:
            return 0.0
        sqrt_term1 = math.sqrt((gamma + 1.0) / (gamma - 1.0))
        sqrt_term2 = math.sqrt((gamma - 1.0) / (gamma + 1.0) * (M * M - 1.0))
        sqrt_term3 = math.sqrt(M * M - 1.0)
        nu = sqrt_term1 * math.atan(sqrt_term2) - math.atan(sqrt_term3)
        return nu

    @staticmethod
    def prandtl_meyer_turn_angle(M1: float, M2: float, gamma: float = 1.4) -> float:
        """Prandtl-Meyer 轉角: Δθ = ν(M2) - ν(M1)"""
        nu1 = VonKarmanTheory.prandtl_meyer_function(M1, gamma)
        nu2 = VonKarmanTheory.prandtl_meyer_function(M2, gamma)
        return nu2 - nu1

    # ========== 1.6 噴管與推進 ==========
    @staticmethod
    def critical_mass_flow_rate(C_d: float, A_star: float, p0: float, gamma: float, R: float, T0: float) -> float:
        """
        臨界質量流率（喉部，卡門校正）:
        ṁ = C_d * A* * p0 * √(γ/(R*T0)) * (2/(γ+1))^((γ+1)/(2(γ-1)))
        """
        term1 = math.sqrt(gamma / (R * T0))
        term2 = (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        return C_d * A_star * p0 * term1 * term2

    # ========== 1.7 結構屈曲 ==========
    @staticmethod
    def karman_donnell_buckling(E: float, nu: float, t: float, R: float) -> float:
        """
        Kármán-Donnell 圓柱殼屈曲應力: σ_cr ≈ E/√(3(1-ν²)) * t/R
        """
        return (E / math.sqrt(3.0 * (1.0 - nu * nu))) * (t / max(R, 1e-9))

    # ========== 1.8 卡門線 ==========
    KARMAN_LINE = 100000.0  # 100 km

    @staticmethod
    def karman_line_altitude() -> float:
        """卡門線高度: 100 km（大氣與太空分界）"""
        return VonKarmanTheory.KARMAN_LINE

    @staticmethod
    def is_above_karman_line(h: float) -> bool:
        """判斷是否在卡門線以上"""
        return h >= VonKarmanTheory.KARMAN_LINE


# =============================================================================
# 2) Tsien (錢學森) 理論核心
# =============================================================================

class TsienTheory:
    """錢學森理論核心公式與方法（Engineering Cybernetics + 飛行力學）"""

    # ========== 2.1 可壓縮邊界層 ==========
    @staticmethod
    def compressible_boundary_layer_momentum(rho: float, u: float, du_dx: float, v: float, du_dy: float,
                                             dp_dx: float, mu: float, d2u_dy2: float) -> float:
        """
        可壓縮邊界層 x 向動量方程（錢學森博士論文核心）:
        ρ*u*∂u/∂x + ρ*v*∂u/∂y = -∂p/∂x + ∂/∂y(μ*∂u/∂y)
        返回誤差（用於數值求解）
        """
        left = rho * u * du_dx + rho * v * du_dy
        right = -dp_dx + mu * d2u_dy2
        return left - right

    @staticmethod
    def compressible_boundary_layer_energy(rho: float, u: float, dh_dx: float, v: float, dh_dy: float,
                                           k: float, d2T_dy2: float, mu: float, du_dy: float) -> float:
        """
        可壓縮邊界層能量方程（總焓形式）:
        ρ*u*∂h/∂x + ρ*v*∂h/∂y = ∂/∂y(k*∂T/∂y) + μ*(∂u/∂y)²
        返回誤差
        """
        left = rho * u * dh_dx + rho * v * dh_dy
        right = k * d2T_dy2 + mu * (du_dy ** 2)
        return left - right

    # ========== 2.2 錢學森彈道（三方程） ==========
    @staticmethod
    def tsien_velocity_rate(T: float, alpha: float, D: float, m: float, g: float, gamma: float) -> float:
        """
        錢學森彈道速度方程: dV/dt = (T*cos(α) - D)/m - g*sin(γ)
        """
        return (T * math.cos(alpha) - D) / max(m, 1e-9) - g * math.sin(gamma)

    @staticmethod
    def tsien_flight_path_rate(T: float, alpha: float, L: float, m: float, V: float, g: float, gamma: float) -> float:
        """
        錢學森彈道航跡角方程: dγ/dt = (T*sin(α) + L)/(m*V) - (g*cos(γ))/V
        """
        return (T * math.sin(alpha) + L) / max(m * V, 1e-9) - (g * math.cos(gamma)) / max(V, 1e-9)

    @staticmethod
    def tsien_altitude_rate(V: float, gamma: float) -> float:
        """
        錢學森彈道高度方程: dh/dt = V*sin(γ)
        """
        return V * math.sin(gamma)

    @staticmethod
    def tsien_mass_rate(mdot_fuel: float) -> float:
        """
        錢學森彈道質量方程: dm/dt = -ṁ_fuel
        """
        return -mdot_fuel

    @staticmethod
    def tsien_trajectory_system(t: float, state: np.ndarray, T: float, alpha: float, mdot: float,
                                L_func, D_func, g: float) -> np.ndarray:
        """
        錢學森三方程系統（完整狀態向量）
        state: [V, γ, h, m]
        返回: [dV/dt, dγ/dt, dh/dt, dm/dt]
        """
        V, gamma, h, m = state[0], state[1], state[2], state[3]
        L = L_func(V, h, alpha)
        D = D_func(V, h, alpha)
        dV = TsienTheory.tsien_velocity_rate(T, alpha, D, m, g, gamma)
        dgamma = TsienTheory.tsien_flight_path_rate(T, alpha, L, m, V, g, gamma)
        dh = TsienTheory.tsien_altitude_rate(V, gamma)
        dm = TsienTheory.tsien_mass_rate(mdot)
        return np.array([dV, dgamma, dh, dm])

    # ========== 2.3 薄殼屈曲（與 von Kármán 合作） ==========
    @staticmethod
    def cylindrical_shell_buckling(E: float, nu: float, t: float, R: float) -> float:
        """
        圓柱殼軸向壓縮屈曲（Kármán-Tsien）: σ_cr ≈ E/√(3(1-ν²)) * t/R
        """
        return (E / math.sqrt(3.0 * (1.0 - nu * nu))) * (t / max(R, 1e-9))

    # ========== 2.4 工程控制論（Engineering Cybernetics） ==========
    @staticmethod
    def state_space_model(A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray,
                          x: np.ndarray, u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        線性系統狀態空間（錢學森工程控制論核心）:
        ẋ = A*x + B*u
        y = C*x + D*u
        返回: (ẋ, y)
        """
        xdot = A @ x + B @ u
        y = C @ x + D @ u
        return xdot, y

    @staticmethod
    def feedback_control_loop(G: np.ndarray, C: np.ndarray) -> np.ndarray:
        """
        閉迴路傳遞函數（SISO 簡化）: T(s) = G(s)*C(s) / (1 + G(s)*C(s))
        此處返回閉迴路系統矩陣（簡化，實際需頻域分析）
        """
        # 簡化：假設 G, C 為狀態空間形式，計算閉迴路 A_cl
        # 實際應用需用 control library (如 control.py)
        I = np.eye(G.shape[0])
        A_cl = G - G @ C @ G  # 簡化形式
        return A_cl

    @staticmethod
    def decoupling_control(B: np.ndarray, desired_B: np.ndarray) -> np.ndarray:
        """
        解耦控制設計（多變量系統）: 設計 K 使得 B*K = desired_B
        返回: K (解耦矩陣)
        """
        try:
            K = np.linalg.solve(B, desired_B) if B.shape[0] == B.shape[1] else np.linalg.pinv(B) @ desired_B
            return K
        except:
            return np.zeros((B.shape[1], desired_B.shape[1]))

    # ========== 2.5 高超音速與再入 ==========
    @staticmethod
    def hypersonic_heat_flux(rho_inf: float, V_inf: float, C: float = 1.83e-4) -> float:
        """
        高超音速熱流（Kármán-Sutton 型，錢學森推廣）: q̇ ∝ C * √(ρ_∞) * V_∞³
        """
        return C * math.sqrt(max(rho_inf, 0.0)) * (V_inf ** 3)

    # ========== 2.6 噴管設計（JPL 時期） ==========
    @staticmethod
    def nozzle_area_mach_relation(M: float, gamma: float = 1.4) -> float:
        """
        噴管面積-馬赫數關係（錢學森在 JPL 推廣）:
        A/A* = (1/M) * [2/(γ+1) * (1 + (γ-1)M²/2)]^((γ+1)/(2(γ-1)))
        """
        if M <= 0:
            return 1e30
        v = 1.0 + 0.5 * (gamma - 1.0) * M * M
        exp = (gamma + 1.0) / (2.0 * (gamma - 1.0))
        return (1.0 / M) * ((2.0 / (gamma + 1.0)) * v) ** exp

    # ========== 2.7 錢學森彈道：最優彈道框架 ==========
    @staticmethod
    def qian_trajectory_optimal_control(state: np.ndarray, T_max: float, alpha: float, 
                                        L_func, D_func, g: float, objective: str = "max_range") -> dict:
        """
        錢學森最優彈道控制框架
        objective: "max_range" (最長射程) 或 "min_fuel" (最小燃料)
        返回: 控制策略與性能指標
        """
        V, gamma, h, m = state[0], state[1], state[2], state[3]
        L = L_func(V, h, alpha)
        D = D_func(V, h, alpha)
        
        if objective == "max_range":
            # 最長射程策略：初期小攻角增速，中段零升力滑翔
            if h < 10000.0:  # 初期
                alpha_opt = 0.1  # 小攻角
            else:  # 中段滑翔
                alpha_opt = 0.0  # 零升力
        elif objective == "min_fuel":
            # 最小燃料策略：最小推力路徑
            alpha_opt = -0.05  # 略負攻角以減少阻力
        else:
            alpha_opt = alpha
        
        return {
            "alpha_optimal": alpha_opt,
            "strategy": objective,
            "current_state": {"V": V, "gamma": gamma, "h": h, "m": m}
        }

    @staticmethod
    def qian_maximum_range_trajectory(V0: float, gamma0: float, h0: float, m0: float,
                                      T: float, L_func, D_func, g: float, t_end: float, dt: float) -> dict:
        """
        錢學森最長射程彈道（分段控制策略）
        返回: 軌跡時間序列與射程
        """
        state = np.array([V0, gamma0, h0, m0])
        t = 0.0
        trajectory = []
        range_total = 0.0
        
        while t < t_end and state[2] >= 0.0:
            V, gamma, h, m = state[0], state[1], state[2], state[3]
            
            # 分段控制策略
            if h < 10000.0:  # 初期：小攻角快速增速
                alpha = 0.1
            elif h < 30000.0:  # 中段：零升力滑翔
                alpha = 0.0
            else:  # 末段：調整攻角
                alpha = -0.05
            
            L = L_func(V, h, alpha)
            D = D_func(V, h, alpha)
            dstate = TsienTheory.tsien_trajectory_system(t, state, T, alpha, 0.0, 
                                                         lambda V, h, a: L, lambda V, h, a: D, g)
            state = state + dstate * dt
            t += dt
            
            # 計算射程增量
            dx = V * math.cos(gamma) * dt
            range_total += dx
            
            trajectory.append({
                "t": t, "V": state[0], "gamma": state[1], "h": state[2], "m": state[3],
                "range": range_total, "alpha": alpha
            })
        
        return {
            "trajectory": trajectory,
            "total_range": range_total,
            "final_time": t
        }

    @staticmethod
    def qian_minimum_fuel_trajectory(V0: float, gamma0: float, h0: float, m0: float,
                                     T_max: float, mdot_max: float, L_func, D_func, g: float,
                                     target_h: float, target_V: float) -> dict:
        """
        錢學森最小燃料彈道（最佳控制問題）
        min ∫ ṁ dt subject to 三方程 + 終端約束
        返回: 最佳推力與攻角策略（簡化版）
        """
        # 簡化：使用啟發式策略
        # 完整解需用 Pontryagin 最優性原理或數值最佳化
        state = np.array([V0, gamma0, h0, m0])
        t = 0.0
        fuel_consumed = 0.0
        strategy = []
        
        # 啟發式：最小推力路徑
        while state[2] < target_h and state[0] < target_V and t < 1000.0:
            V, gamma, h, m = state[0], state[1], state[2], state[3]
            
            # 最小燃料策略：使用最小必要推力
            alpha = -0.05  # 略負攻角
            T_opt = max(0.0, min(T_max, m * g * 1.1))  # 略大於重力
            mdot_opt = T_opt / (3000.0 * 9.81)  # 假設 Isp=3000s
            
            L = L_func(V, h, alpha)
            D = D_func(V, h, alpha)
            dstate = TsienTheory.tsien_trajectory_system(t, state, T_opt, alpha, mdot_opt,
                                                         lambda V, h, a: L, lambda V, h, a: D, g)
            state = state + dstate * 0.1
            t += 0.1
            fuel_consumed += mdot_opt * 0.1
            
            strategy.append({"t": t, "T": T_opt, "alpha": alpha, "mdot": mdot_opt})
        
        return {
            "fuel_consumed": fuel_consumed,
            "strategy": strategy,
            "final_state": state,
            "time_to_target": t
        }

    # ========== 2.8 導彈飛行力學（穩定性與控制） ==========
    @staticmethod
    def missile_stability_longitudinal(C_m_alpha: float) -> bool:
        """
        縱向穩定性: C_m_alpha < 0 為穩定
        """
        return C_m_alpha < 0.0

    @staticmethod
    def missile_stability_directional(C_n_beta: float) -> bool:
        """
        方向穩定性: C_n_beta > 0 為穩定
        """
        return C_n_beta > 0.0

    @staticmethod
    def missile_stability_roll(C_l_p: float) -> bool:
        """
        滾轉穩定性: C_l_p < 0 為穩定
        """
        return C_l_p < 0.0

    @staticmethod
    def control_moment_effectiveness(C_m_delta: float, q: float, S: float, c: float, delta: float) -> float:
        """
        控制面力矩效能: M_delta = C_m_delta * q * S * c * δ
        """
        return C_m_delta * q * S * c * delta

    @staticmethod
    def proportional_navigation_guidance(V_missile: float, V_target: float, lambda_angle: float, N: float = 3.0) -> float:
        """
        比例導引律（錢學森框架的初期形式）: a_cmd = N * V * λ̇
        N: 導引常數（典型 3-5）
        """
        # 簡化：假設 λ̇ 與相對速度相關
        V_rel = abs(V_missile - V_target)
        lambda_dot = V_rel / 1000.0  # 佔位
        return N * V_missile * lambda_dot

    # ========== 2.9 高超音速與高焓氣流 ==========
    @staticmethod
    def high_enthalpy_flow_total_enthalpy(h_static: float, V: float) -> float:
        """
        高焓氣流總焓: h_t = h + V²/2
        """
        return h_static + 0.5 * V * V

    @staticmethod
    def hypersonic_chemical_reaction_effect(rho: float, T: float, species: np.ndarray, 
                                           reaction_rates: np.ndarray) -> np.ndarray:
        """
        高超音速化學反應效應（簡化模型）
        返回: 各物種濃度變化率
        """
        # 佔位：實際需化學動力學模型
        return reaction_rates * rho * math.exp(-5000.0 / max(T, 1e-9))

    @staticmethod
    def hypersonic_heat_transfer_coupling(q_aero: float, T_w: float, k_tps: float, delta_tps: float) -> float:
        """
        高超音速熱傳與氣動耦合（錢學森框架）
        返回: 表面溫度變化率
        """
        return q_aero / (k_tps / max(delta_tps, 1e-9))

    # ========== 2.10 工程控制論：系統分解 ==========
    @staticmethod
    def system_decomposition(requirements: dict, subsystems: list) -> dict:
        """
        工程控制論：大系統分解方法
        將任務需求分解為子系統需求
        """
        decomposed = {}
        for subsystem in subsystems:
            decomposed[subsystem] = {
                "mass_budget": requirements.get("total_mass", 1000.0) / len(subsystems),
                "power_budget": requirements.get("total_power", 1000.0) / len(subsystems),
                "interface_requirements": {}
            }
        return decomposed

    @staticmethod
    def design_cycle_feedback(current_design: dict, test_results: dict, requirements: dict) -> dict:
        """
        工程控制論：設計循環回饋
        實現「設計 → 模擬 → 測試 → 修正」閉環
        """
        corrections = {}
        for key in current_design:
            if key in test_results:
                error = test_results[key] - requirements.get(key, 0.0)
                corrections[key] = current_design[key] - 0.1 * error  # 簡化修正
        return corrections

    @staticmethod
    def requirement_to_specification(mission_req: dict) -> dict:
        """
        需求轉換成技術指標（工程控制論方法）
        """
        specs = {
            "delta_v": mission_req.get("range", 0.0) * 100.0,  # 佔位轉換
            "max_acceleration": mission_req.get("max_g", 5.0) * 9.81,
            "reliability": mission_req.get("reliability", 0.99),
            "mass_budget": mission_req.get("payload", 100.0) * 10.0
        }
        return specs

    # ========== 2.11 軌跡最佳化框架 ==========
    @staticmethod
    def trajectory_optimization_cost(state_history: list, control_history: list, 
                                     objective: str = "min_fuel") -> float:
        """
        軌跡最佳化成本函數
        objective: "min_fuel", "min_time", "max_range"
        """
        if objective == "min_fuel":
            # min ∫ |ṁ| dt
            cost = sum([abs(c.get("mdot", 0.0)) for c in control_history])
        elif objective == "min_time":
            # min t_f
            cost = len(state_history) * 0.1  # 假設 dt=0.1
        elif objective == "max_range":
            # max ∫ V*cos(γ) dt
            cost = -sum([s.get("V", 0.0) * math.cos(s.get("gamma", 0.0)) for s in state_history])
        else:
            cost = 0.0
        return cost

    @staticmethod
    def pontryagin_hamiltonian(state: np.ndarray, control: np.ndarray, costate: np.ndarray,
                               dynamics_func, L_func) -> float:
        """
        Pontryagin 最優性原理：Hamiltonian
        H = λ^T * f(x,u) + L(x,u)
        """
        f = dynamics_func(state, control)
        L = L_func(state, control)
        return np.dot(costate, f) + L

    # ========== 2.12 爆炸波理論 ==========
    @staticmethod
    def taylor_sedov_blast_wave_radius(E: float, rho0: float, t: float, gamma: float = 1.4) -> float:
        """
        Taylor-Sedov 爆炸波半徑（錢學森研究領域）:
        R(t) ∝ (E*t²/ρ0)^(1/5)
        """
        return (E * t * t / max(rho0, 1e-9)) ** 0.2

    @staticmethod
    def blast_wave_pressure_ratio(r: float, R: float, gamma: float = 1.4) -> float:
        """
        爆炸波壓力比（簡化）: p/p0 隨 r/R 變化
        """
        if r >= R:
            return 1.0
        # 簡化模型
        return 1.0 + 10.0 * (1.0 - r / max(R, 1e-9)) ** 2

    # ========== 2.13 工程數學方法 ==========
    @staticmethod
    def region_function_method(boundary_conditions: dict, domain: np.ndarray) -> np.ndarray:
        """
        區域函數法（錢學森工程數學）
        用於複雜邊界條件的偏微分方程求解（簡化佔位）
        """
        # 佔位：實際需完整數值求解器
        return np.zeros_like(domain)

    @staticmethod
    def nonlinear_system_analysis(A_linear: np.ndarray, nonlinear_terms: np.ndarray, 
                                  x: np.ndarray) -> np.ndarray:
        """
        非線性系統分析（錢學森方法）
        返回: 線性化後的系統矩陣修正
        """
        # 簡化：線性化
        A_eff = A_linear + np.diag(nonlinear_terms)
        return A_eff

    # ========== 2.14 火箭設計基本方程（錢學森框架） ==========
    @staticmethod
    def qian_mass_budget_equation(m_structure: float, m_propellant: float, m_payload: float) -> float:
        """
        錢學森質量預算方程: m = m_s + m_p + m_pl
        """
        return m_structure + m_propellant + m_payload

    @staticmethod
    def qian_delta_v_integral(T: np.ndarray, D: np.ndarray, m: np.ndarray, t: np.ndarray) -> float:
        """
        錢學森 Δv 積分方程: Δv = ∫ (T-D)/m dt
        """
        if len(T) < 2 or len(m) < 2 or len(t) < 2:
            return 0.0
        integrand = (T - D) / np.maximum(m, 1e-9)
        return np.trapz(integrand, t)

    @staticmethod
    def qian_optimal_expansion_ratio(p_c: float, p_a: float, gamma: float = 1.4) -> float:
        """
        錢學森噴管最佳膨脹比（低壓環境修正）
        """
        if p_a <= 0:
            return 50.0  # 真空：大膨脹比
        p_ratio = p_c / max(p_a, 1e-9)
        # 簡化：最佳膨脹比與壓力比相關
        return min(50.0, math.sqrt(p_ratio) * 5.0)

    @staticmethod
    def qian_thrust_loss_low_pressure(p_e: float, p_a: float, A_e: float) -> float:
        """
        低壓環境下的推力損失修正（錢學森）
        """
        if p_a <= 0:
            return 0.0  # 真空無損失
        return (p_e - p_a) * A_e  # 壓力推力項


# =============================================================================
# 3) 設計流程框架（Von Kármán + Tsien 方法論）
# =============================================================================

@dataclass
class DesignRequirement:
    """任務需求"""
    mission_type: str  # "satellite", "mars_probe", "intercontinental", etc.
    delta_v_required: float  # m/s
    payload_mass: float  # kg
    max_acceleration: float  # m/s²
    reliability_target: float  # 0-1
    cost_constraint: Optional[float] = None

@dataclass
class SystemInterface:
    """子系統介面定義（ICD）"""
    mass: float
    dimensions: np.ndarray  # [L, W, H] or [R, L]
    power: float
    data_rate: Optional[float] = None
    torque_capability: Optional[float] = None

class AerospaceDesignFramework:
    """
    航太設計框架（Von Kármán + Tsien 方法論）
    實現「理論 → 模型 → 試驗 → 修正 → 工程化」循環
    """

    def __init__(self):
        self.vk = VonKarmanTheory()
        self.tsien = TsienTheory()
        self.requirements: Optional[DesignRequirement] = None
        self.subsystems = {}

    def step0_mission_requirements(self, req: DesignRequirement):
        """Step 0: 任務需求定義"""
        self.requirements = req
        return {
            "target_delta_v": req.delta_v_required,
            "payload_ratio_target": req.payload_mass / 1000.0,  # 假設總重 1000 kg
            "max_g": req.max_acceleration / 9.81,
            "reliability": req.reliability_target
        }

    def step1_geometry_sizing(self, nose_type: str = "von_karman", L: float = 10.0, R_max: float = 1.0):
        """Step 1: 幾何初始設計（含 Von Kármán 頭錐）"""
        if nose_type == "von_karman":
            # 生成 Von Kármán 頭錐座標
            x = np.linspace(0, L, 100)
            r = np.array([self.vk.von_karman_nose_cone(xi, L, R_max, n=0.75) for xi in x])
            return {"x": x, "r": r, "type": "von_karman"}
        elif nose_type == "sears_haack":
            x = np.linspace(0, L, 100)
            r = np.array([self.vk.sears_haack_body_radius(xi, L, R_max) for xi in x])
            return {"x": x, "r": r, "type": "sears_haack"}
        return {}

    def step2_aerodynamics(self, M: float, alpha: float, AR: float = 5.0):
        """Step 2: 氣動設計（含 Kármán-Tsien 修正）"""
        # 低速升力線理論
        C_L_low = self.vk.lifting_line_theory(AR, alpha)
        # 可壓縮性修正
        C_p0 = 0.5 * C_L_low  # 佔位
        C_p_compressible = self.vk.karman_tsien_compressibility(C_p0, M)
        # Prandtl-Meyer（超音速）
        if M > 1.0:
            nu = self.vk.prandtl_meyer_function(M)
        else:
            nu = 0.0
        return {
            "C_L": C_L_low,
            "C_p_compressible": C_p_compressible,
            "Prandtl_Meyer_angle": nu
        }

    def step3_propulsion(self, p_c: float, A_t: float, mdot: float, gamma: float = 1.2, R_gas: float = 350.0, T0: float = 2800.0):
        """Step 3: 推進系統設計（含卡門校正）"""
        # 臨界質量流率
        C_d = 0.98
        mdot_critical = self.vk.critical_mass_flow_rate(C_d, A_t, p_c, gamma, R_gas, T0)
        # 噴管面積比
        M_e = 3.0  # 假設出口馬赫數
        A_ratio = self.tsien.nozzle_area_mach_relation(M_e, gamma)
        return {
            "mdot_critical": mdot_critical,
            "A_ratio": A_ratio,
            "M_exit": M_e
        }

    def step4_structure(self, E: float, nu: float, t: float, R: float):
        """Step 4: 結構設計（Kármán-Tsien 屈曲）"""
        sigma_cr = self.tsien.cylindrical_shell_buckling(E, nu, t, R)
        return {
            "buckling_stress": sigma_cr,
            "safety_factor": 2.0  # 佔位
        }

    def step5_trajectory(self, T: float, alpha: float, mdot: float, V0: float, gamma0: float, h0: float, m0: float, g: float):
        """Step 5: 軌跡分析（錢學森三方程）"""
        # 簡化：單步計算
        state0 = np.array([V0, gamma0, h0, m0])
        
        def L_func(V, h, alpha):
            return 0.5 * 1.2 * V * V * 10.0 * 0.5  # 佔位
        
        def D_func(V, h, alpha):
            return 0.5 * 1.2 * V * V * 10.0 * 0.1  # 佔位
        
        dstate = self.tsien.tsien_trajectory_system(0.0, state0, T, alpha, mdot, L_func, D_func, g)
        return {
            "dV_dt": dstate[0],
            "dgamma_dt": dstate[1],
            "dh_dt": dstate[2],
            "dm_dt": dstate[3]
        }

    def step6_control(self, A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray, x: np.ndarray, u: np.ndarray):
        """Step 6: 控制設計（工程控制論）"""
        xdot, y = self.tsien.state_space_model(A, B, C, D, x, u)
        # 穩定性檢查（簡化：檢查 A 的特徵值）
        eigenvals = np.linalg.eigvals(A)
        stable = np.all(np.real(eigenvals) < 0)
        return {
            "xdot": xdot,
            "output": y,
            "stable": stable,
            "eigenvalues": eigenvals
        }

    def step7_system_integration(self, design_vars: dict) -> dict:
        """
        Step 7: 系統整合（大系統循環）
        實現「理論 → 模型 → 試驗 → 修正 → 工程化」
        """
        results = {}
        # 1. 幾何
        geom = self.step1_geometry_sizing(**design_vars.get("geometry", {}))
        results["geometry"] = geom
        # 2. 氣動
        aero = self.step2_aerodynamics(**design_vars.get("aerodynamics", {}))
        results["aerodynamics"] = aero
        # 3. 推進
        prop = self.step3_propulsion(**design_vars.get("propulsion", {}))
        results["propulsion"] = prop
        # 4. 結構
        struct = self.step4_structure(**design_vars.get("structure", {}))
        results["structure"] = struct
        # 5. 軌跡
        traj = self.step5_trajectory(**design_vars.get("trajectory", {}))
        results["trajectory"] = traj
        # 6. 控制
        control = self.step6_control(**design_vars.get("control", {}))
        results["control"] = control
        # 7. 性能指標
        results["performance"] = {
            "delta_v_achieved": 0.0,  # 需從軌跡積分得到
            "mass_ratio": 0.0,
            "reliability": 0.95
        }
        return results

    def design_loop(self, initial_guess: dict, max_iter: int = 10, tolerance: float = 0.01) -> dict:
        """
        完整設計循環（Von Kármán + Tsien 方法論）
        實現迭代優化
        """
        current_design = initial_guess
        history = []
        
        for i in range(max_iter):
            results = self.step7_system_integration(current_design)
            history.append(results)
            
            # 檢查收斂（簡化）
            if i > 0:
                # 比較性能指標
                prev_perf = history[-2]["performance"]
                curr_perf = results["performance"]
                if abs(curr_perf.get("delta_v_achieved", 0) - prev_perf.get("delta_v_achieved", 0)) < tolerance:
                    break
            
            # 更新設計變數（簡化：此處需實際優化算法）
            # current_design = optimize(current_design, results)
        
        return {
            "final_design": current_design,
            "results": results,
            "history": history,
            "iterations": i + 1
        }

    # ========== 錢學森工程控制論擴充方法 ==========
    def tsien_system_engineering_cycle(self, requirements: DesignRequirement) -> dict:
        """
        錢學森工程控制論：完整系統工程循環
        實現「需求 → 系統 → 分系統 → 測試 → 修正」閉環
        """
        # Step 1: 需求轉換
        specs = self.tsien.requirement_to_specification({
            "range": requirements.delta_v_required / 100.0,
            "max_g": requirements.max_acceleration / 9.81,
            "reliability": requirements.reliability_target,
            "payload": requirements.payload_mass
        })
        
        # Step 2: 系統分解
        subsystems = ["propulsion", "aerodynamics", "structure", "control", "thermal", "avionics"]
        decomposed = self.tsien.system_decomposition(specs, subsystems)
        
        # Step 3: 子系統設計（調用各 step）
        subsystem_results = {}
        for subsystem in subsystems:
            if subsystem == "propulsion":
                subsystem_results[subsystem] = self.step3_propulsion(
                    p_c=2e6, A_t=0.005, mdot=0.8, gamma=1.2, R_gas=350.0, T0=2800.0
                )
            elif subsystem == "aerodynamics":
                subsystem_results[subsystem] = self.step2_aerodynamics(M=0.8, alpha=0.1, AR=6.0)
            elif subsystem == "structure":
                subsystem_results[subsystem] = self.step4_structure(
                    E=200e9, nu=0.3, t=0.005, R=0.5
                )
            # ... 其他子系統
        
        # Step 4: 系統整合
        integrated_results = self.step7_system_integration({
            "propulsion": {"p_c": 2e6, "A_t": 0.005, "mdot": 0.8},
            "aerodynamics": {"M": 0.8, "alpha": 0.1, "AR": 6.0},
            "structure": {"E": 200e9, "nu": 0.3, "t": 0.005, "R": 0.5}
        })
        
        # Step 5: 測試與驗證（佔位）
        test_results = {
            "delta_v_achieved": integrated_results["performance"]["delta_v_achieved"],
            "mass_total": 1000.0,
            "reliability": 0.95
        }
        
        # Step 6: 回饋修正
        corrections = self.tsien.design_cycle_feedback(
            current_design={"delta_v": test_results["delta_v_achieved"]},
            test_results=test_results,
            requirements={"delta_v": requirements.delta_v_required}
        )
        
        return {
            "specifications": specs,
            "decomposed_requirements": decomposed,
            "subsystem_results": subsystem_results,
            "integrated_results": integrated_results,
            "test_results": test_results,
            "corrections": corrections
        }

    def tsien_trajectory_optimization(self, initial_state: np.ndarray, target_state: np.ndarray,
                                     T_max: float, mdot_max: float, L_func, D_func, g: float,
                                     objective: str = "min_fuel", method: str = "heuristic") -> dict:
        """
        錢學森軌跡最佳化框架
        method: "heuristic" (啟發式) 或 "pontryagin" (最優控制)
        """
        if method == "heuristic":
            if objective == "min_fuel":
                return self.tsien.qian_minimum_fuel_trajectory(
                    initial_state[0], initial_state[1], initial_state[2], initial_state[3],
                    T_max, mdot_max, L_func, D_func, g, target_state[2], target_state[0]
                )
            elif objective == "max_range":
                return self.tsien.qian_maximum_range_trajectory(
                    initial_state[0], initial_state[1], initial_state[2], initial_state[3],
                    T_max, L_func, D_func, g, 100.0, 0.1
                )
        elif method == "pontryagin":
            # 佔位：完整 Pontryagin 求解需數值最佳化庫
            return {"method": "pontryagin", "status": "requires_optimization_solver"}
        
        return {"status": "unknown_method"}

    def tsien_missile_design_framework(self, mission_range: float, payload: float, 
                                      target_speed: float) -> dict:
        """
        錢學森導彈設計框架（完整流程）
        """
        # 1. 需求分析
        delta_v_req = mission_range * 0.1  # 佔位轉換
        
        # 2. 彈道設計（最優彈道）
        trajectory = self.tsien.qian_maximum_range_trajectory(
            V0=0.0, gamma0=math.radians(45.0), h0=0.0, m0=1000.0,
            T=50000.0,
            L_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.5,
            D_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.1,
            g=9.81, t_end=100.0, dt=0.1
        )
        
        # 3. 穩定性分析
        stability = {
            "longitudinal": self.tsien.missile_stability_longitudinal(-0.05),
            "directional": self.tsien.missile_stability_directional(0.1),
            "roll": self.tsien.missile_stability_roll(-0.02)
        }
        
        # 4. 控制設計
        control_moment = self.tsien.control_moment_effectiveness(
            C_m_delta=0.1, q=50000.0, S=10.0, c=1.0, delta=math.radians(5.0)
        )
        
        # 5. 導引律
        guidance_accel = self.tsien.proportional_navigation_guidance(
            V_missile=500.0, V_target=400.0, lambda_angle=0.1, N=3.0
        )
        
        return {
            "trajectory": trajectory,
            "stability": stability,
            "control_moment": control_moment,
            "guidance_acceleration": guidance_accel,
            "delta_v_required": delta_v_req
        }


# =============================================================================
# 4) 工具函數
# =============================================================================

def create_von_karman_nose_profile(L: float, R_max: float, n: float = 0.75, n_points: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """生成 Von Kármán 頭錐輪廓"""
    vk = VonKarmanTheory()
    x = np.linspace(0, L, n_points)
    r = np.array([vk.von_karman_nose_cone(xi, L, R_max, n) for xi in x])
    return x, r

def create_sears_haack_profile(L: float, R_max: float, n_points: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """生成 Sears-Haack Body 輪廓"""
    vk = VonKarmanTheory()
    x = np.linspace(0, L, n_points)
    r = np.array([vk.sears_haack_body_radius(xi, L, R_max) for xi in x])
    return x, r


# 實例化供外部使用
von_karman = VonKarmanTheory()
tsien = TsienTheory()
design_framework = AerospaceDesignFramework()
