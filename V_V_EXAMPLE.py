# -*- coding: utf-8 -*-
"""
V&V 與工程化改進使用範例
展示驗算、驗證、不確定度分析、事件系統等
"""

import numpy as np
import math
import logging
from verification_validation import (
    conservation, convergence, unit_test, model_applicability, 
    reference_cases, uncertainty, sensitivity, confidence
)
from event_system import event_detector, mode_switcher, adaptive_integrator, EventType
from coordinate_time_system import coord_manager, consistency_checker
from data_contract import aero_data_manager, AeroCoefficientSchema
from tps_materials import tps_material_lib, tps_failure
from load_cases import load_case_manager
from engineering_tools import sim_logger, api_contract, traceability, unit_system

print("=== V&V 與工程化改進範例 ===\n")

# ========== 範例 1: 守恆檢查 ==========
print("1) 守恆檢查（Verification）")
# 兩體軌道能量守恆
r0 = np.array([6371000.0 + 400000.0, 0.0, 0.0])
v0 = np.array([0.0, 7667.0, 0.0])  # 圓軌道速度
m0 = 1000.0
mu = 3.986004418e14

# 模擬後（簡化：假設無外力）
r_current = r0 * 1.01  # 軌道變化
v_current = v0 * 0.99
m_current = m0

energy_check = conservation.energy_conservation_no_thrust(
    r_current, v_current, m_current, mu, r0, v0, m0
)
print(f"能量守恆檢查:")
print(f"  相對誤差: {energy_check['relative_error']:.2e}")
print(f"  守恆: {energy_check['conserved']}")

angular_check = conservation.angular_momentum_conservation_no_torque(
    r_current, v_current, m_current, r0, v0, m0
)
print(f"角動量守恆檢查:")
print(f"  相對誤差: {angular_check['relative_error']:.2e}")
print(f"  守恆: {angular_check['conserved']}\n")

# ========== 範例 2: 收斂性測試 ==========
print("2) 收斂性測試")
def simple_dynamics(t, x, a=1.0):
    return np.array([a * x[0], -0.1 * x[1]])

x0 = np.array([1.0, 1.0])
dt_list = [0.1, 0.05, 0.01]
conv_result = convergence.run_convergence_test(
    simple_dynamics, x0, t_end=1.0, dt_list=dt_list
)
print(f"不同步長終端狀態:")
for dt, result in conv_result.items():
    if isinstance(dt, float):
        print(f"  dt={dt:.3f}: x = {result['final_state']}")
print(f"收斂誤差: {conv_result.get('convergence_error', 0):.2e}\n")

# ========== 範例 3: 模型適用範圍 ==========
print("3) 模型適用範圍檢查")
isa_applicability = model_applicability
isa_applicability.M_max = 5.0
isa_applicability.h_max = 86000.0

check = isa_applicability.check(M=2.0, h=50000.0, T=250.0, alpha=math.radians(5.0), Re=1e6)
print(f"ISA 模型適用性:")
print(f"  在範圍內: {check['in_range']}")
print(f"  接近邊界: {check['near_boundary']}")
print(f"  警告: {check['warnings']}\n")

# ========== 範例 4: 不確定度傳播 ==========
print("4) 不確定度傳播（Monte Carlo）")
from verification_validation import UncertaintyDistribution

def thrust_calc(mdot, v_e, p_e, p_a, A_e):
    return mdot * v_e + (p_e - p_a) * A_e

uncertain_inputs = {
    "mdot": UncertaintyDistribution("mdot", mean=0.8, std=0.05, distribution_type="gaussian"),
    "v_e": UncertaintyDistribution("v_e", mean=3000.0, std=50.0, distribution_type="gaussian"),
    "p_e": UncertaintyDistribution("p_e", mean=50000.0, std=5000.0, distribution_type="gaussian")
}

fixed_inputs = {"p_a": 10000.0, "A_e": 0.01}

mc_result = uncertainty.monte_carlo_analysis(
    thrust_calc, uncertain_inputs, n_samples=1000, fixed_inputs=fixed_inputs
)
print(f"推力不確定度分析 (n=1000):")
print(f"  均值: {mc_result['mean']/1000:.2f} kN")
print(f"  標準差: {mc_result['std']/1000:.2f} kN")
print(f"  P10: {mc_result['p10']/1000:.2f} kN")
print(f"  P50: {mc_result['p50']/1000:.2f} kN")
print(f"  P90: {mc_result['p90']/1000:.2f} kN\n")

# ========== 範例 5: 敏感度分析 ==========
print("5) 敏感度分析")
base_inputs = {"mdot": 0.8, "v_e": 3000.0, "p_e": 50000.0, "p_a": 10000.0, "A_e": 0.01}
perturbations = {"mdot": 0.01, "v_e": 10.0, "p_e": 1000.0}

sens_result = sensitivity.first_order_sensitivity(
    thrust_calc, base_inputs, perturbations
)
print(f"一階敏感度:")
for param, sens in sens_result["sensitivities"].items():
    print(f"  {param}: S = {sens['sensitivity']:.3f}, 相對影響 = {sens['relative_effect']:.1%}")
print(f"主導參數: {sens_result['ranked_parameters'][0]}\n")

# ========== 範例 6: 事件系統 ==========
print("6) 事件偵測與處理")
# 註冊事件處理器
def handle_max_q(event):
    print(f"  事件: 最大動壓 {event.data['q']/1000:.1f} kPa")
    return {"action": "reduce_throttle", "throttle": 0.5}

event_detector.register_handler(EventType.MAX_DYNAMIC_PRESSURE, handle_max_q)

# 模擬事件偵測
state = np.array([100.0, 0.0, 5000.0, 50.0])  # V, gamma, h, m
aux = {"q_dynamic": 55000.0, "T_w": 1200.0, "load_factor": 8.0, "altitude": 5000.0, "Mach": 0.8}

events = event_detector.check_all_events(10.0, state, aux)
print(f"偵測到 {len(events)} 個事件:")
for event in events:
    print(f"  {event.event_type.value} at t={event.time:.1f}s")
    result = event_detector.handle_event(event)
    print(f"    處理: {result}\n")

# ========== 範例 7: 座標系一致性 ==========
print("7) 座標系一致性檢查")
r_eci = np.array([6771000.0, 0.0, 0.0])
t = 100.0
r_ecef = coord_manager.ecef_from_eci(r_eci, t)
r_eci_back = coord_manager.eci_from_ecef(r_ecef, t)

consistency = consistency_checker.check_coordinate_consistency(r_eci, r_ecef, t, coord_manager)
print(f"座標轉換一致性:")
print(f"  一致: {consistency['consistent']}")
print(f"  相對誤差: {consistency['relative_error']:.2e}\n")

# ========== 範例 8: 資料契約 ==========
print("8) 氣動係數資料契約")
schema = AeroCoefficientSchema(
    name="test_aero",
    version="1.0",
    Mach_range=(0.0, 2.0),
    Re_range=(1e5, 1e7),
    alpha_range=(-10.0, 20.0),
    beta_range=(-5.0, 5.0),
    grid_Mach=np.array([0.0, 0.5, 1.0, 1.5, 2.0]),
    grid_alpha=np.array([-10.0, 0.0, 10.0, 20.0]),
    C_L_table=np.zeros((4, 5)),
    C_D_table=np.ones((4, 5)) * 0.1,
    C_m_table=np.zeros((4, 5)),
    extrapolation_strategy="clamp",
    source="placeholder"
)

validation = schema.validate_input(M=1.5, alpha=math.radians(15.0), Re=5e6, beta=0.0)
print(f"資料契約驗證:")
print(f"  有效: {validation['valid']}")
print(f"  錯誤: {validation['errors']}")

sanity = schema.check_physical_sanity()
print(f"物理合理性: {sanity['sane']}, 問題: {sanity['issues']}\n")

# ========== 範例 9: TPS 材料與失效 ==========
print("9) TPS 材料失效分析")
material = tps_material_lib.get_material("C-C")
if material:
    failure = material.check_failure(T=2600.0)
    print(f"材料失效檢查 (T=2600 K):")
    print(f"  失效: {failure['failed']}")
    print(f"  問題: {failure['failures']}")
    print(f"  警告: {failure['warnings']}\n")

# ========== 範例 10: 載荷案例 ==========
print("10) 載荷案例管理")
load_result = load_case_manager.evaluate_all_cases(
    q=55000.0, n=12.0, M_bend=12000.0, delta_T=600.0, t=15.0
)
print(f"載荷案例評估:")
print(f"  違反案例數: {sum(1 for r in load_result['all_cases'].values() if r['violated'])}")
for name, result in load_result['all_cases'].items():
    if result['violated']:
        print(f"  {name}: {result['violations']}")

margins = load_case_manager.compute_margins({
    "q": 45000.0, "n": 8.0, "M_bend": 8000.0, "delta_T": 400.0
})
print(f"\n裕度分析:")
print(f"  最小裕度: {margins['min_margin']:.2f}")
print(f"  瓶頸案例: {margins['bottleneck_cases']}\n")

# ========== 範例 11: 日誌與可追溯性 ==========
print("11) 日誌與可追溯性")
sim_logger.log_simulation_start("test_001", {"delta_v": 9400.0, "payload": 500.0})
sim_logger.log_event("propulsion", "推進系統啟動", logging.INFO)
sim_logger.log_event("warning", "接近最大動壓", logging.WARNING)

traceability.record_decision(
    "選擇化學推進",
    "滿足 Δv 需求且技術成熟",
    {"I_sp": 300.0, "thrust": 2000.0}
)
traceability.record_requirement(
    "REQ-001",
    "Δv ≥ 9.4 km/s",
    "任務需求文檔"
)

print("日誌與可追溯性記錄完成\n")

print("=== 所有 V&V 範例完成 ===")
