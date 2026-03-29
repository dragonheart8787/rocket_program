# -*- coding: utf-8 -*-
"""
進階推進公式使用範例
展示新增的進階火箭與推進公式
"""

import numpy as np
import math
from .aerospace_sim import eng_formulas, Earth

earth = Earth()

print("=== 進階推進公式範例 ===\n")

# ========== 範例 1: 推力係數與等效速度 ==========
print("1) 推力係數與等效速度")
p_c, p_e, p_a = 2e6, 50000.0, 10000.0  # Pa
A_t, A_e = 0.005, 0.01  # m^2
gamma = 1.2

c_F = eng_formulas.thrust_coefficient_ideal(p_e, p_c, p_a, A_e, A_t, gamma)
F = eng_formulas.thrust_from_coefficient(c_F, p_c, A_t)
print(f"推力係數 c_F = {c_F:.3f}")
print(f"推力 F = {F/1000:.2f} kN")

v_e = 3000.0  # m/s
mdot = 0.8  # kg/s
V_eq = eng_formulas.equivalent_exhaust_velocity(v_e, p_e, p_a, A_e, mdot)
I_sp_eq = eng_formulas.specific_impulse_from_equivalent(V_eq, earth.g0)
print(f"等效排氣速度 V_eq = {V_eq:.1f} m/s")
print(f"等效比衝 I_sp = {I_sp_eq:.1f} s\n")

# ========== 範例 2: 多級火箭 ==========
print("2) 多級火箭 Δv 計算")
v_e_list = np.array([3000.0, 3200.0, 3500.0])  # m/s
m0_list = np.array([1000.0, 300.0, 100.0])  # kg
mf_list = np.array([300.0, 100.0, 30.0])  # kg

delta_v_total = eng_formulas.multi_stage_delta_v(v_e_list, m0_list, mf_list)
print(f"三級火箭總 Δv = {delta_v_total/1000:.2f} km/s")
for i in range(len(v_e_list)):
    dv_i = v_e_list[i] * math.log(m0_list[i] / mf_list[i])
    print(f"  第 {i+1} 級: Δv = {dv_i/1000:.2f} km/s")

# 有效載荷比
m_payload = 10.0  # kg
payload_ratio = eng_formulas.payload_ratio(m_payload, m0_list[0])
print(f"有效載荷比 = {payload_ratio:.3f} ({payload_ratio*100:.1f}%)\n")

# ========== 範例 3: 推進熱力學 ==========
print("3) 推進熱力學")
c_p = 1200.0  # J/kg/K
T_c = 2800.0  # K
v_e_isen = eng_formulas.exhaust_velocity_isentropic(c_p, T_c, p_e, p_c, gamma)
print(f"等熵出口流速 v_e = {v_e_isen:.1f} m/s")

# 混合氣體比熱
n_moles = np.array([0.5, 0.3, 0.2])  # H2O, CO2, N2
cp_values = np.array([1800.0, 900.0, 1000.0])  # J/kg/K
C_p_mix = eng_formulas.mixed_gas_cp(n_moles, cp_values)
R = 287.0  # J/kg/K
gamma_mix = eng_formulas.mixed_gas_gamma(C_p_mix, R)
print(f"混合氣體 C_p = {C_p_mix:.1f} J/kg/K, γ = {gamma_mix:.3f}\n")

# ========== 範例 4: 電推進進階 ==========
print("4) 電推進進階")
eta_e, eta_m, eta_c = 0.85, 0.90, 0.95
eta_T = eng_formulas.electric_propulsion_efficiency(eta_e, eta_m, eta_c)
print(f"電推進總效率 η_T = {eta_T:.3f}")

mdot_ep = 0.001  # kg/s
v_e_ep = 30000.0  # m/s
F_ep = eng_formulas.electric_propulsion_thrust(eta_T, mdot_ep, v_e_ep)
print(f"電推進推力 F = {F_ep:.3f} N")

# 電熱式
c_p_ep = 5000.0  # J/kg/K
T_e, T_a = 2000.0, 300.0  # K
v_e_thermal = eng_formulas.electric_thermal_exhaust_velocity(c_p_ep, T_e, T_a)
print(f"電熱式排氣速度 v_e = {v_e_thermal/1000:.1f} km/s\n")

# ========== 範例 5: 脈衝推進 ==========
print("5) 脈衝推進")
E_p = 10.0  # J
delta_t = 0.001  # s
F_pulse = eng_formulas.pulsed_inductive_thrust(E_p, v_e_ep, delta_t)
f = 100.0  # Hz
F_avg = eng_formulas.pulsed_inductive_avg_thrust(F_pulse, f)
print(f"單脈衝推力 F_pulse = {F_pulse:.3f} N")
print(f"平均推力 (f={f} Hz) F_avg = {F_avg:.3f} N")

# 衝量位元
t_pulse = np.linspace(0, delta_t, 100)
F_t = F_pulse * np.exp(-t_pulse / (delta_t/3))  # 指數衰減
I_b = eng_formulas.pulse_impulse_bit_integral(F_t, t_pulse)
m_b = 1e-6  # kg
I_sp_pulse = eng_formulas.pulse_specific_impulse(I_b, m_b, earth.g0)
print(f"衝量位元 I_b = {I_b*1e6:.3f} mN*s")
print(f"脈衝比衝 I_sp = {I_sp_pulse:.0f} s\n")

# ========== 範例 6: 核熱推進 ==========
print("6) 核熱推進")
T_h = 2500.0  # K
R_gas = 350.0  # J/kg/K
v_e_ntp = eng_formulas.nuclear_thermal_exhaust_velocity(gamma, R_gas, T_h)
I_sp_ntp = v_e_ntp / earth.g0
print(f"核熱推進排氣速度 v_e = {v_e_ntp:.1f} m/s")
print(f"比衝 I_sp = {I_sp_ntp:.1f} s")

# 核電推進
eta_gen = 0.4
P_nuclear = 1e6  # W
P_elec = eng_formulas.nuclear_electric_power(eta_gen, P_nuclear)
print(f"核電推進功率 P_elec = {P_elec/1e6:.2f} MW\n")

# ========== 範例 7: 6-DoF 與重心 ==========
print("7) 6-DoF 動力學")
mdot_fuel = 0.8  # kg/s
m_dot = eng_formulas.mass_rate_change(mdot_fuel)
print(f"質量變化率 ṁ = {m_dot:.3f} kg/s")

# 重心位置
r_positions = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
dm = np.array([10.0, 20.0, 30.0])  # kg
m_total = np.sum(dm)
r_CG = eng_formulas.center_of_gravity_position(r_positions, dm, m_total)
print(f"重心位置 r_CG = [{r_CG[0]:.2f}, {r_CG[1]:.2f}, {r_CG[2]:.2f}] m\n")

# ========== 範例 8: 最優控制 ==========
print("8) 最優控制")
lambda_vec = np.array([1.0, 2.0, 3.0])
f_xu = np.array([0.1, 0.2, 0.3])
L = 0.5
H = eng_formulas.hamiltonian(lambda_vec, f_xu, L)
print(f"Hamiltonian H = {H:.3f}")

# 低推力成本
u_t = np.array([0.1, 0.15, 0.12, 0.1])  # 控制向量
t = np.array([0.0, 1.0, 2.0, 3.0])
J = eng_formulas.low_thrust_cost_function(u_t, t)
print(f"低推力成本函數 J = {J:.3f}\n")

# ========== 範例 9: MDO ==========
print("9) 多學科設計優化")
x = np.array([1.0, 2.0, 3.0])
weights = np.array([0.5, 0.3, 0.2])
objectives = np.array([10.0, 20.0, 30.0])
J_mdo = eng_formulas.mdo_objective_function(x, weights, objectives)
print(f"MDO 目標函數 J = {J_mdo:.1f}")

g = np.array([-1.0, 0.5, -0.3])  # 約束（負值表示滿足）
violation = eng_formulas.mdo_constraint_violation(g)
print(f"約束違反量 = {violation:.3f}\n")

# ========== 範例 10: 燃料燃燒 ==========
print("10) 燃料燃燒")
a, n = 0.01, 0.5
G = 100.0  # kg/m^2/s
r_dot = eng_formulas.hybrid_regression_rate(a, G, n)
print(f"Regression rate ṙ = {r_dot*1000:.3f} mm/s")

rho_fuel = 900.0  # kg/m^3
A_burn = 0.1  # m^2
mdot_consume = eng_formulas.mass_consumption_rate(rho_fuel, r_dot, A_burn)
print(f"質量消耗率 ṁ = {mdot_consume:.3f} kg/s\n")

# ========== 範例 11: 能量分析 ==========
print("11) 能量分析")
m, v = 1000.0, 5000.0  # kg, m/s
E_k = eng_formulas.kinetic_energy(m, v)
print(f"動能 E_k = {E_k/1e9:.2f} GJ")

P_k = eng_formulas.kinetic_power_from_thrust(F, v_e)
print(f"推力動能功率 P_k = {P_k/1e6:.2f} MW")

# 能量守恆檢查
P_source = 5e6  # W
error = eng_formulas.energy_conservation_ideal(mdot, v_e, P_source)
print(f"能量守恆誤差 = {error/1e6:.3f} MW\n")

print("=== 所有進階範例完成 ===")
