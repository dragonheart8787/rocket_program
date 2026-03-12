# -*- coding: utf-8 -*-
"""
工程公式庫使用範例
展示如何使用 aerospace_sim.py 中的 EngineeringFormulas 類
"""

import numpy as np
import math
from aerospace_sim import eng_formulas, ISA, Earth

# ========== 範例 1: 大氣/環境 ==========
print("=== 範例 1: 大氣/環境 ===")
atm = ISA()
earth = Earth()
h = 10000.0  # 10 km
props = atm.properties(h)
rho, V = props["rho"], 300.0  # m/s

q = eng_formulas.dynamic_pressure(rho, V)
print(f"高度 {h/1000:.1f} km, 速度 {V:.0f} m/s")
print(f"動壓 q = {q/1000:.2f} kPa")

Re = eng_formulas.reynolds(rho, V, 1.0, props["mu"])
print(f"雷諾數 Re = {Re:.2e}")

w_gust = 5.0  # m/s 陣風
delta_alpha = eng_formulas.gust_alpha_increment(w_gust, V)
print(f"陣風等效迎角增量 Δα = {math.degrees(delta_alpha):.3f}°")

# ========== 範例 2: 氣動 ==========
print("\n=== 範例 2: 氣動 ===")
C_L0, C_La = 0.1, 0.08
alpha = math.radians(5.0)
C_L = eng_formulas.lift_linearized(C_L0, C_La, alpha)
C_D = eng_formulas.drag_polar(0.02, 0.05, C_L)

L = eng_formulas.lift_force(q, 10.0, C_L)  # S = 10 m²
D = eng_formulas.drag_force(q, 10.0, C_D)
print(f"迎角 α = {math.degrees(alpha):.1f}°")
print(f"C_L = {C_L:.3f}, C_D = {C_D:.3f}")
print(f"升力 L = {L/1000:.2f} kN, 阻力 D = {D/1000:.2f} kN")

x_NP, x_CG, c = 0.5, 0.45, 1.0
SM = eng_formulas.static_margin(x_NP, x_CG, c)
print(f"靜穩定裕度 SM = {SM:.3f} ({'穩定' if SM > 0 else '不穩定'})")

# ========== 範例 3: 可壓縮流 ==========
print("\n=== 範例 3: 可壓縮流 ===")
M1 = 2.0
p2_p1 = eng_formulas.normal_shock_pressure_ratio(M1)
rho2_rho1 = eng_formulas.normal_shock_density_ratio(M1)
M2 = eng_formulas.normal_shock_mach2(M1)
print(f"正激波: M1 = {M1:.1f}")
print(f"壓力比 p2/p1 = {p2_p1:.3f}")
print(f"密度比 ρ2/ρ1 = {rho2_rho1:.3f}")
print(f"下游馬赫數 M2 = {M2:.3f}")

M = 0.8
T_ratio = eng_formulas.isentropic_temperature_ratio(M)
p_ratio = eng_formulas.isentropic_pressure_ratio(M)
print(f"\n等熵流: M = {M:.1f}")
print(f"總溫比 Tt/T = {T_ratio:.3f}")
print(f"總壓比 pt/p = {p_ratio:.3f}")

# ========== 範例 4: 熱傳 ==========
print("\n=== 範例 4: 熱傳 ===")
T_w, T_env = 1200.0, 220.0
eps, sigma = 0.8, 5.67e-8
q_rad = eng_formulas.radiation_heat_flux(eps, sigma, T_w, T_env)
print(f"輻射熱通量 q_rad = {q_rad/1000:.2f} kW/m^2")

h_conv = 500.0  # W/m^2/K
T_aw = 1500.0
q_conv = eng_formulas.convective_heat_flux(h_conv, T_aw, T_w)
print(f"對流熱通量 q_conv = {q_conv/1000:.2f} kW/m^2")

Re, Pr = 1e6, 0.7
Nu = eng_formulas.nusselt_correlation(Re, Pr)
print(f"Nusselt 數 Nu = {Nu:.2f}")

# ========== 範例 5: 結構 ==========
print("\n=== 範例 5: 結構 ===")
p, r, t = 2e6, 0.5, 0.005  # Pa, m, m
sigma_hoop = eng_formulas.stress_thin_cylinder_hoop(p, r, t)
sigma_axial = eng_formulas.stress_thin_cylinder_axial(p, r, t)
print(f"薄壁圓筒: p = {p/1e6:.1f} MPa, r = {r:.3f} m, t = {t*1000:.1f} mm")
print(f"環向應力 sigma_theta = {sigma_hoop/1e6:.1f} MPa")
print(f"軸向應力 sigma_z = {sigma_axial/1e6:.1f} MPa")

sigma_v = eng_formulas.von_mises_stress(sigma_hoop, sigma_axial, 0.0)
print(f"von Mises 應力 sigma_v = {sigma_v/1e6:.1f} MPa")

E, I, L = 200e9, 1e-6, 2.0  # Pa, m^4, m
P_cr = eng_formulas.euler_buckling_load(E, I, L)
print(f"Euler 屈曲載荷 P_cr = {P_cr/1000:.1f} kN")

allowable, actual = 500e6, 300e6  # Pa
MS = eng_formulas.margin_of_safety(allowable, actual)
print(f"安全裕度 MS = {MS:.3f} ({MS*100:.1f}%)")

# ========== 範例 6: 推進 ==========
print("\n=== 範例 6: 推進 ===")
mdot, v_e = 0.8, 3000.0  # kg/s, m/s
p_e, p_a, A_e = 50000.0, 10000.0, 0.01  # Pa, m^2
F = eng_formulas.thrust_equation(mdot, v_e, p_e, p_a, A_e)
I_sp = eng_formulas.specific_impulse(F, mdot, earth.g0)
print(f"推力 F = {F/1000:.2f} kN")
print(f"比衝 I_sp = {I_sp:.1f} s")

m0, mf = 1000.0, 200.0  # kg
delta_v = eng_formulas.delta_v_rocket_equation(I_sp, earth.g0, m0, mf)
print(f"delta_v = {delta_v/1000:.2f} km/s")

M_e = 3.0
eps = eng_formulas.area_ratio_from_mach(M_e)
print(f"噴管膨脹比 (M={M_e:.1f}): A_e/A* = {eps:.2f}")

# ========== 範例 7: 電推進 ==========
print("\n=== 範例 7: 電推進 ===")
P_in, eta, v_e_ep = 5000.0, 0.6, 30000.0  # W, m/s
F_ep = eng_formulas.electric_thrust_from_power(eta, P_in, v_e_ep)
mdot_ep = F_ep / v_e_ep
I_sp_ep = eng_formulas.specific_impulse(F_ep, mdot_ep, earth.g0)
print(f"電推進: P_in = {P_in/1000:.1f} kW, eta = {eta:.1%}")
print(f"推力 F = {F_ep:.3f} N, 比衝 I_sp = {I_sp_ep:.0f} s")

q, V_acc, m_i = 1.6e-19, 1000.0, 131.0 * 1.67e-27  # 氙離子
v_e_ion = eng_formulas.exhaust_velocity_ion(q, V_acc, m_i)
print(f"離子推進 (V_acc={V_acc:.0f} V): v_e = {v_e_ion/1000:.1f} km/s")

# ========== 範例 8: 系統工程 ==========
print("\n=== 範例 8: 系統工程 ===")
tolerances = np.array([0.1, 0.05, 0.02, 0.03])  # mm
T_rss = eng_formulas.tolerance_rss(tolerances)
print(f"RSS 公差堆疊: T_RSS = {T_rss:.3f} mm")

R_components = np.array([0.99, 0.95, 0.98])
R_series = eng_formulas.reliability_series(R_components)
R_parallel = eng_formulas.reliability_parallel(R_components)
print(f"串聯可靠度: R = {R_series:.4f}")
print(f"並聯可靠度: R = {R_parallel:.4f}")

alpha_thermal = 23e-6  # 1/K (鋁)
L, delta_T = 1.0, 100.0  # m, K
delta_L = eng_formulas.thermal_expansion(alpha_thermal, L, delta_T)
print(f"熱膨脹 (delta_T={delta_T:.0f} K): delta_L = {delta_L*1e6:.2f} um")

print("\n=== 所有範例完成 ===")
