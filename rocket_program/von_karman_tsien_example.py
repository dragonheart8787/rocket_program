# -*- coding: utf-8 -*-
"""
Von Kármán 與 Tsien 理論使用範例
展示兩位大師的理論在航太設計中的應用
"""

import numpy as np
import math
from .von_karman_tsien_theory import von_karman, tsien, design_framework, create_von_karman_nose_profile, create_sears_haack_profile

print("=== Von Kármán (馮·卡門) 理論範例 ===\n")

# ========== 範例 1: Von Kármán 頭錐設計 ==========
print("1) Von Kármán 頭錐（最小波阻）")
L, R_max = 2.0, 0.5  # m
x, r = create_von_karman_nose_profile(L, R_max, n=0.75, n_points=50)
print(f"頭錐長度 L = {L:.1f} m, 最大半徑 R_max = {R_max:.1f} m")
print(f"生成 {len(x)} 個點，首尾半徑: r[0]={r[0]:.3f} m, r[-1]={r[-1]:.3f} m")

# Sears-Haack Body
x_sh, r_sh = create_sears_haack_profile(L, R_max, n_points=50)
print(f"Sears-Haack Body: 首尾半徑 r[0]={r_sh[0]:.3f} m, r[-1]={r_sh[-1]:.3f} m\n")

# ========== 範例 2: 升力線理論 ==========
print("2) 升力線理論（有限翼）")
AR = 6.0
alpha = math.radians(5.0)
C_L = von_karman.lifting_line_theory(AR, alpha)
print(f"縱橫比 AR = {AR:.1f}, 迎角 α = {math.degrees(alpha):.1f}°")
print(f"升力係數 C_L = {C_L:.3f}\n")

# ========== 範例 3: Kármán-Tsien 可壓縮性修正 ==========
print("3) Kármán-Tsien 可壓縮性修正")
C_p0 = 0.5
M_list = [0.3, 0.6, 0.8, 0.95]
print("M      C_p0    C_p (Kármán-Tsien)")
for M in M_list:
    C_p_kt = von_karman.karman_tsien_compressibility(C_p0, M)
    print(f"{M:.2f}   {C_p0:.3f}   {C_p_kt:.3f}")
print()

# ========== 範例 4: Prandtl-Meyer 展開 ==========
print("4) Prandtl-Meyer 扇形膨脹")
M_list = [1.5, 2.0, 3.0, 5.0]
print("M      ν(M) [deg]")
for M in M_list:
    nu = von_karman.prandtl_meyer_function(M)
    print(f"{M:.1f}   {math.degrees(nu):.2f}")
print()

# ========== 範例 5: Kármán Vortex Street ==========
print("5) Kármán Vortex Street（渦街）")
V, D = 50.0, 0.1  # m/s, m
f = von_karman.karman_vortex_street_frequency(V, D, St=0.2)
print(f"流速 V = {V:.0f} m/s, 直徑 D = {D:.1f} m")
print(f"渦街頻率 f = {f:.2f} Hz")
print(f"Strouhal 數 St = {von_karman.strouhal_number(f, D, V):.3f}\n")

# ========== 範例 6: 臨界質量流率 ==========
print("6) 臨界質量流率（卡門校正）")
C_d, A_star = 0.98, 0.005  # m^2
p0, gamma, R, T0 = 2e6, 1.2, 350.0, 2800.0  # Pa, J/kg/K, K
mdot_crit = von_karman.critical_mass_flow_rate(C_d, A_star, p0, gamma, R, T0)
print(f"喉部面積 A* = {A_star*10000:.1f} cm²")
print(f"臨界質量流率 ṁ = {mdot_crit:.3f} kg/s\n")

# ========== 範例 7: 結構屈曲 ==========
print("7) Kármán-Donnell 圓柱殼屈曲")
E, nu = 200e9, 0.3  # Pa
t, R = 0.005, 0.5  # m
sigma_cr = von_karman.karman_donnell_buckling(E, nu, t, R)
print(f"殼厚度 t = {t*1000:.1f} mm, 半徑 R = {R:.2f} m")
print(f"屈曲應力 σ_cr = {sigma_cr/1e6:.1f} MPa\n")

# ========== 範例 8: 卡門線 ==========
print("8) 卡門線（Kármán Line）")
h = 120000.0  # m
print(f"卡門線高度 = {von_karman.karman_line_altitude()/1000:.0f} km")
print(f"高度 {h/1000:.0f} km 是否在卡門線以上: {von_karman.is_above_karman_line(h)}\n")

print("=== Tsien (錢學森) 理論範例 ===\n")

# ========== 範例 9: 錢學森彈道三方程 ==========
print("9) 錢學森彈道三方程")
T, alpha, mdot = 2000.0, math.radians(10.0), 0.8  # N, rad, kg/s
V0, gamma0, h0, m0 = 100.0, math.radians(80.0), 0.0, 50.0  # m/s, rad, m, kg
g = 9.81

def L_func(V, h, alpha):
    return 0.5 * 1.2 * V * V * 10.0 * 0.5

def D_func(V, h, alpha):
    return 0.5 * 1.2 * V * V * 10.0 * 0.1

state0 = np.array([V0, gamma0, h0, m0])
dstate = tsien.tsien_trajectory_system(0.0, state0, T, alpha, mdot, L_func, D_func, g)
print(f"初始狀態: V={V0:.0f} m/s, γ={math.degrees(gamma0):.1f}°, h={h0:.0f} m, m={m0:.1f} kg")
print(f"狀態變化率:")
print(f"  dV/dt = {dstate[0]:.2f} m/s²")
print(f"  dγ/dt = {math.degrees(dstate[1]):.3f} °/s")
print(f"  dh/dt = {dstate[2]:.1f} m/s")
print(f"  dm/dt = {dstate[3]:.3f} kg/s\n")

# ========== 範例 10: 工程控制論 ==========
print("10) 工程控制論（狀態空間）")
A = np.array([[-0.1, 0.0], [0.0, -0.2]])
B = np.array([[1.0], [0.5]])
C = np.array([[1.0, 0.0]])
D = np.array([[0.0]])
x = np.array([1.0, 2.0])
u = np.array([0.5])

xdot, y = tsien.state_space_model(A, B, C, D, x, u)
eigenvals = np.linalg.eigvals(A)
print(f"狀態空間模型:")
print(f"  A = {A}")
print(f"  狀態 x = {x}")
print(f"  控制 u = {u}")
print(f"  狀態變化率 ẋ = {xdot}")
print(f"  輸出 y = {y}")
print(f"  特徵值 = {eigenvals}")
print(f"  系統穩定: {np.all(np.real(eigenvals) < 0)}\n")

# ========== 範例 11: 高超音速熱流 ==========
print("11) 高超音速熱流（Kármán-Sutton 型）")
rho_inf, V_inf = 0.01, 5000.0  # kg/m³, m/s
q_dot = tsien.hypersonic_heat_flux(rho_inf, V_inf)
print(f"來流密度 ρ = {rho_inf:.3f} kg/m³, 速度 V = {V_inf/1000:.1f} km/s")
print(f"熱流 q̇ = {q_dot/1000:.2f} kW/m²\n")

# ========== 範例 12: 設計流程框架 ==========
print("12) 航太設計流程框架（Von Kármán + Tsien 方法論）")
from .von_karman_tsien_theory import DesignRequirement

# 定義任務需求
req = DesignRequirement(
    mission_type="satellite",
    delta_v_required=9400.0,
    payload_mass=500.0,
    max_acceleration=50.0,
    reliability_target=0.99
)

# Step 0: 任務需求
targets = design_framework.step0_mission_requirements(req)
print(f"任務目標: Δv = {targets['target_delta_v']/1000:.2f} km/s")

# Step 1: 幾何設計
geom = design_framework.step1_geometry_sizing(nose_type="von_karman", L=10.0, R_max=1.0)
print(f"幾何設計: {geom['type']} 頭錐，長度 {10.0:.1f} m")

# Step 2: 氣動設計
aero = design_framework.step2_aerodynamics(M=0.8, alpha=math.radians(5.0), AR=6.0)
print(f"氣動設計: C_L = {aero['C_L']:.3f}")

# Step 3: 推進設計
prop = design_framework.step3_propulsion(p_c=2e6, A_t=0.005, mdot=0.8, gamma=1.2, R_gas=350.0, T0=2800.0)
print(f"推進設計: 臨界流率 ṁ = {prop['mdot_critical']:.3f} kg/s, 膨脹比 = {prop['A_ratio']:.2f}")

# Step 4: 結構設計
struct = design_framework.step4_structure(E=200e9, nu=0.3, t=0.005, R=0.5)
print(f"結構設計: 屈曲應力 σ_cr = {struct['buckling_stress']/1e6:.1f} MPa")

# Step 5: 軌跡分析
traj = design_framework.step5_trajectory(
    T=2000.0, alpha=math.radians(10.0), mdot=0.8,
    V0=100.0, gamma0=math.radians(80.0), h0=0.0, m0=50.0, g=9.81
)
print(f"軌跡分析: dV/dt = {traj['dV_dt']:.2f} m/s², dh/dt = {traj['dh_dt']:.1f} m/s")

# Step 6: 控制設計
A_ctrl = np.array([[-0.1, 0.0], [0.0, -0.2]])
B_ctrl = np.array([[1.0], [0.5]])
C_ctrl = np.array([[1.0, 0.0]])
D_ctrl = np.array([[0.0]])
x_ctrl = np.array([1.0, 2.0])
u_ctrl = np.array([0.5])
control = design_framework.step6_control(A_ctrl, B_ctrl, C_ctrl, D_ctrl, x_ctrl, u_ctrl)
print(f"控制設計: 系統穩定 = {control['stable']}\n")

# 完整設計循環
print("13) 完整設計循環（迭代優化）")
initial_design = {
    "geometry": {"nose_type": "von_karman", "L": 10.0, "R_max": 1.0},
    "aerodynamics": {"M": 0.8, "alpha": math.radians(5.0), "AR": 6.0},
    "propulsion": {"p_c": 2e6, "A_t": 0.005, "mdot": 0.8, "gamma": 1.2, "R_gas": 350.0, "T0": 2800.0},
    "structure": {"E": 200e9, "nu": 0.3, "t": 0.005, "R": 0.5},
    "trajectory": {"T": 2000.0, "alpha": math.radians(10.0), "mdot": 0.8,
                   "V0": 100.0, "gamma0": math.radians(80.0), "h0": 0.0, "m0": 50.0, "g": 9.81},
    "control": {"A": A_ctrl, "B": B_ctrl, "C": C_ctrl, "D": D_ctrl, "x": x_ctrl, "u": u_ctrl}
}

result = design_framework.design_loop(initial_design, max_iter=3, tolerance=0.01)
print(f"設計循環完成: {result['iterations']} 次迭代")
print(f"最終性能: Δv = {result['results']['performance']['delta_v_achieved']/1000:.2f} km/s")
print(f"可靠性 = {result['results']['performance']['reliability']:.2%}\n")

# ========== 範例 14: 錢學森最優彈道 ==========
print("14) 錢學森最優彈道框架")
state_opt = np.array([200.0, math.radians(30.0), 5000.0, 800.0])
optimal = tsien.qian_trajectory_optimal_control(
    state_opt, T_max=50000.0, alpha=0.1,
    L_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.5,
    D_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.1,
    g=9.81, objective="max_range"
)
print(f"最優彈道策略: {optimal['strategy']}, 最佳攻角 = {math.degrees(optimal['alpha_optimal']):.2f}°\n")

# ========== 範例 15: 最長射程彈道 ==========
print("15) 錢學森最長射程彈道（分段控制）")
max_range = tsien.qian_maximum_range_trajectory(
    V0=0.0, gamma0=math.radians(45.0), h0=0.0, m0=1000.0,
    T=50000.0,
    L_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.5,
    D_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.1,
    g=9.81, t_end=50.0, dt=0.1
)
print(f"總射程 = {max_range['total_range']/1000:.2f} km")
print(f"飛行時間 = {max_range['final_time']:.1f} s")
print(f"軌跡點數 = {len(max_range['trajectory'])}\n")

# ========== 範例 16: 最小燃料彈道 ==========
print("16) 錢學森最小燃料彈道")
min_fuel = tsien.qian_minimum_fuel_trajectory(
    V0=100.0, gamma0=math.radians(80.0), h0=0.0, m0=1000.0,
    T_max=50000.0, mdot_max=10.0,
    L_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.5,
    D_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.1,
    g=9.81, target_h=50000.0, target_V=2000.0
)
print(f"燃料消耗 = {min_fuel['fuel_consumed']:.1f} kg")
print(f"到達目標時間 = {min_fuel['time_to_target']:.1f} s\n")

# ========== 範例 17: 導彈飛行力學 ==========
print("17) 導彈飛行力學（穩定性與控制）")
stab_long = tsien.missile_stability_longitudinal(-0.05)
stab_dir = tsien.missile_stability_directional(0.1)
stab_roll = tsien.missile_stability_roll(-0.02)
print(f"縱向穩定: {stab_long}, 方向穩定: {stab_dir}, 滾轉穩定: {stab_roll}")

M_delta = tsien.control_moment_effectiveness(0.1, 50000.0, 10.0, 1.0, math.radians(5.0))
print(f"控制面力矩 M_delta = {M_delta/1000:.2f} kN*m")

a_guidance = tsien.proportional_navigation_guidance(500.0, 400.0, 0.1, N=3.0)
print(f"比例導引加速度 a_cmd = {a_guidance:.2f} m/s²\n")

# ========== 範例 18: 高超音速與高焓 ==========
print("18) 高超音速與高焓氣流")
h_static = 1e6  # J/kg
V_hyp = 5000.0  # m/s
h_total = tsien.high_enthalpy_flow_total_enthalpy(h_static, V_hyp)
print(f"總焓 h_t = {h_total/1e6:.2f} MJ/kg")

species = np.array([0.7, 0.2, 0.1])  # N2, O2, O
reaction_rates = np.array([0.01, 0.02, 0.005])
d_species = tsien.hypersonic_chemical_reaction_effect(0.01, 3000.0, species, reaction_rates)
print(f"化學反應效應: d_species = {d_species}\n")

# ========== 範例 19: 工程控制論系統分解 ==========
print("19) 工程控制論：系統分解")
req = {"total_mass": 1000.0, "total_power": 5000.0}
subsystems = ["propulsion", "aerodynamics", "structure", "control"]
decomposed = tsien.system_decomposition(req, subsystems)
print("子系統需求分解:")
for sub, specs in decomposed.items():
    print(f"  {sub}: 質量預算 = {specs['mass_budget']:.1f} kg, 功率預算 = {specs['power_budget']:.1f} W")

# 需求轉換
mission_req = {"range": 1000.0, "max_g": 5.0, "reliability": 0.99, "payload": 100.0}
specs = tsien.requirement_to_specification(mission_req)
print(f"\n技術指標: Δv = {specs['delta_v']/1000:.2f} km/s, 最大加速度 = {specs['max_acceleration']:.1f} m/s²\n")

# ========== 範例 20: 軌跡最佳化 ==========
print("20) 軌跡最佳化框架")
state_hist = [{"V": 100.0, "gamma": 0.5}, {"V": 200.0, "gamma": 0.3}]
control_hist = [{"mdot": 0.8}, {"mdot": 0.6}]
cost_fuel = tsien.trajectory_optimization_cost(state_hist, control_hist, "min_fuel")
cost_range = tsien.trajectory_optimization_cost(state_hist, control_hist, "max_range")
print(f"最小燃料成本 = {cost_fuel:.3f}")
print(f"最大射程成本 = {cost_range:.3f}")

# Pontryagin Hamiltonian
lambda_vec = np.array([1.0, 2.0, 3.0, 4.0])
def dyn_func(s, u):
    return np.array([s[0]*0.1, s[1]*0.1, s[2]*0.1, -u[0]])
def L_func(s, u):
    return 0.5 * u[0] * u[0]
H = tsien.pontryagin_hamiltonian(state0, np.array([0.5]), lambda_vec, dyn_func, L_func)
print(f"Pontryagin Hamiltonian H = {H:.3f}\n")

# ========== 範例 21: 爆炸波理論 ==========
print("21) 爆炸波理論（Taylor-Sedov）")
E_blast = 1e9  # J
rho0 = 1.2  # kg/m³
t = 0.01  # s
R_blast = tsien.taylor_sedov_blast_wave_radius(E_blast, rho0, t)
print(f"爆炸波半徑 R = {R_blast:.2f} m")

p_ratio = tsien.blast_wave_pressure_ratio(5.0, R_blast)
print(f"壓力比 p/p0 = {p_ratio:.2f}\n")

# ========== 範例 22: 火箭設計基本方程 ==========
print("22) 火箭設計基本方程（錢學森框架）")
m_total = tsien.qian_mass_budget_equation(300.0, 600.0, 100.0)
print(f"總質量 m = {m_total:.0f} kg (結構+推進劑+載荷)")

T_array = np.array([50000.0, 48000.0, 45000.0])
D_array = np.array([5000.0, 6000.0, 7000.0])
m_array = np.array([1000.0, 950.0, 900.0])
t_array = np.array([0.0, 1.0, 2.0])
delta_v_int = tsien.qian_delta_v_integral(T_array, D_array, m_array, t_array)
print(f"Δv (積分) = {delta_v_int:.1f} m/s")

eps_opt = tsien.qian_optimal_expansion_ratio(2e6, 10000.0, gamma=1.2)
print(f"最佳膨脹比 = {eps_opt:.2f}\n")

# ========== 範例 23: 完整系統工程循環 ==========
print("23) 錢學森工程控制論：完整系統工程循環")
from .von_karman_tsien_theory import DesignRequirement

req_full = DesignRequirement(
    mission_type="missile",
    delta_v_required=5000.0,
    payload_mass=100.0,
    max_acceleration=50.0,
    reliability_target=0.99
)

sys_cycle = design_framework.tsien_system_engineering_cycle(req_full)
print("系統工程循環結果:")
print(f"  技術指標: Δv = {sys_cycle['specifications']['delta_v']/1000:.2f} km/s")
print(f"  子系統數: {len(sys_cycle['decomposed_requirements'])}")
print(f"  測試結果: Δv_achieved = {sys_cycle['test_results']['delta_v_achieved']/1000:.2f} km/s")
print(f"  修正建議: {sys_cycle['corrections']}\n")

# ========== 範例 24: 軌跡最佳化框架 ==========
print("24) 錢學森軌跡最佳化框架")
initial = np.array([0.0, math.radians(45.0), 0.0, 1000.0])
target = np.array([2000.0, 0.0, 50000.0, 800.0])
opt_result = design_framework.tsien_trajectory_optimization(
    initial, target, T_max=50000.0, mdot_max=10.0,
    L_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.5,
    D_func=lambda V, h, a: 0.5 * 1.2 * V * V * 10.0 * 0.1,
    g=9.81, objective="min_fuel", method="heuristic"
)
print(f"最佳化結果: 燃料消耗 = {opt_result.get('fuel_consumed', 0):.1f} kg\n")

# ========== 範例 25: 完整導彈設計框架 ==========
print("25) 錢學森導彈設計框架（完整流程）")
missile_design = design_framework.tsien_missile_design_framework(
    mission_range=1000.0, payload=100.0, target_speed=2000.0
)
print("導彈設計結果:")
print(f"  射程 = {missile_design['trajectory']['total_range']/1000:.2f} km")
print(f"  縱向穩定: {missile_design['stability']['longitudinal']}")
print(f"  控制力矩 = {missile_design['control_moment']/1000:.2f} kN*m")
print(f"  導引加速度 = {missile_design['guidance_acceleration']:.2f} m/s²\n")

print("=== 所有範例完成 ===")
