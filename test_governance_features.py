# -*- coding: utf-8 -*-
"""
測試治理與外部驗證功能
"""

import numpy as np
import math
from requirements_traceability import rtm, Requirement, RequirementType, VerificationCase, VerificationMethod
from external_validation import external_validation, calibration_layer, model_uncertainty_manager, ModelFormUncertainty
from event_system import event_detector, EventType
from reproducibility import regression_test, RegressionGate, reproducibility_pack, SimulationConfig
from documentation_sanitizer import doc_sanitizer
from verification_validation import UncertaintyDistribution, UncertaintyPropagation

print("=== 治理與外部驗證功能測試 ===\n")

# ========== 測試 1: RTM（需求可追溯矩陣）==========
print("1) RTM 測試")

# 添加需求
req1 = Requirement(
    req_id="REQ-001",
    req_type=RequirementType.PERFORMANCE,
    description="最大動壓不超過 50 kPa",
    source="任務需求文檔",
    priority="high"
)
rtm.add_requirement(req1)

req2 = Requirement(
    req_id="REQ-002",
    req_type=RequirementType.SAFETY,
    description="表面溫度不超過 1500 K",
    source="安全規範",
    priority="high"
)
rtm.add_requirement(req2)

# 添加驗證案例
case1 = VerificationCase(
    case_id="VV-001",
    req_ids=["REQ-001"],
    verification_method=VerificationMethod.TEST,
    threshold=50000.0,
    result={"max_q": 48000.0},
    passed=True,
    artifacts=["V_V_Report_v1.0.json"]
)
rtm.add_verification_case(case1)

case2 = VerificationCase(
    case_id="VV-002",
    req_ids=["REQ-002"],
    verification_method=VerificationMethod.ANALYSIS,
    threshold=1500.0,
    result={"T_w": 1450.0},
    passed=True,
    artifacts=["thermal_analysis.json"]
)
rtm.add_verification_case(case2)

# 生成 RTM 報告
coverage = rtm.get_coverage()
print(f"  需求覆蓋率: {coverage['coverage_percentage']:.1f}%")
print(f"  已覆蓋需求: {coverage['covered_requirements']}/{coverage['total_requirements']}")
print(f"  未覆蓋需求: {coverage['uncovered_requirements']}\n")

# ========== 測試 2: 外部 Validation ==========
print("2) 外部 Validation 測試")

# ISA 基準
isa_benchmark = external_validation.isa_standard_1976()
print(f"  ISA 基準: {isa_benchmark.name}")
print(f"  來源: {isa_benchmark.source}")
print(f"  數據點數: {len(isa_benchmark.data_points)}")

# 簡化 ISA 函數（用於測試）
def test_isa_func(h):
    if h < 11000:
        T = 288.15 - 0.0065 * h
        p = 101325 * (T / 288.15) ** 5.256
        rho = 1.225 * (T / 288.15) ** 4.256
    else:
        T = 216.65
        p = 22632 * np.exp(-0.000157 * (h - 11000))
        rho = 0.3639 * np.exp(-0.000157 * (h - 11000))
    return {"T": T, "p": p, "rho": rho}

# 比對
comparison = external_validation.compare_with_benchmark(
    test_isa_func, isa_benchmark, "T"
)
print(f"  最大相對誤差: {comparison.get('max_relative_error', 0):.4f}")
print(f"  RMSE: {comparison.get('rmse', 0):.2f}")
print(f"  驗證通過: {comparison.get('validation_passed', False)}\n")

# ========== 測試 3: 校準層 ==========
print("3) 校準層測試")

# 模擬校準數據
train_data = np.array([0.3, 0.31, 0.29, 0.32, 0.3])
validation_data = np.array([0.31, 0.30, 0.32])
pred_train = np.array([0.305, 0.315, 0.295, 0.325, 0.305])
pred_val = np.array([0.315, 0.305, 0.335])  # 故意讓 validation 誤差稍大

calibration_report = calibration_layer.calibration_report(
    "C_D", train_data, validation_data, pred_train, pred_val
)
print(f"  參數: {calibration_report['parameter']}")
print(f"  Train RMSE: {calibration_report['rmse_train']:.4f}")
print(f"  Validation RMSE: {calibration_report['rmse_validation']:.4f}")
print(f"  過擬合風險: {calibration_report['overfitting_risk']:.4f}")
print(f"  過擬合檢測: {calibration_report['overfitting_detected']}\n")

# ========== 測試 4: 模型不確定度 ==========
print("4) 模型不確定度測試")

uncertainty = ModelFormUncertainty(
    model_name="heating_model",
    uncertainty_type="additive",
    epsilon_model=0.1,
    applicable_range={"M_min": 5.0, "M_max": 10.0}
)
model_uncertainty_manager.register_model_uncertainty(uncertainty)

result = model_uncertainty_manager.apply_uncertainty("heating_model", 1000.0, {"M": 7.0})
print(f"  模型: heating_model")
print(f"  基礎輸出: {result['base_output']}")
print(f"  修正輸出: {result['output']}")
print(f"  誤差類型: {result['uncertainty_type']}\n")

# ========== 測試 5: 事件系統 Zeno/抖動 ==========
print("5) 事件系統 Zeno/抖動測試")

# 模擬事件歷史（抖動）
from event_system import Event
event_history = [
    Event(EventType.MAX_DYNAMIC_PRESSURE, 10.0, np.array([1.0]), {"q": 51000.0}),
    Event(EventType.MAX_DYNAMIC_PRESSURE, 10.05, np.array([1.0]), {"q": 50500.0}),
    Event(EventType.MAX_DYNAMIC_PRESSURE, 10.08, np.array([1.0]), {"q": 50800.0}),
]

zeno_result = event_detector.detect_zeno_events(event_history, time_window=0.1)
print(f"  Zeno 事件數: {zeno_result['n_zeno']}")
if zeno_result['n_zeno'] > 0:
    print(f"  建議: {zeno_result['recommendations']}\n")

# 事件回溯
def test_event_func(t, state):
    # 簡化：在 t=10.0 時觸發事件
    return {"triggered": abs(t - 10.0) < 0.01}

root_finding = event_detector.event_root_finding(
    test_event_func, 9.5, 10.5,
    np.array([1.0]), np.array([1.0]),
    tolerance=1e-6
)
print(f"  事件時間: {root_finding['event_time']:.6f}")
print(f"  容差達成: {root_finding['tolerance_achieved']}\n")

# ========== 測試 6: 回歸測試分層閘門 ==========
print("6) 回歸測試分層閘門測試")

# 設置硬約束
regression_test.set_baseline("coordinate_transform_error", 0.0, "v1.0")
regression_test.set_tolerance(
    "coordinate_transform_error",
    absolute_tol=1e-9,
    gate_type=RegressionGate.HARD_INVARIANT
)

# 設置軟約束
regression_test.set_baseline("max_q", 50000.0, "v1.0")
regression_test.set_tolerance(
    "max_q",
    relative_tol=0.05,
    gate_type=RegressionGate.SOFT_KPI
)

# 設置預期變動
regression_test.set_baseline("C_D", 0.3, "v1.0")
regression_test.set_tolerance(
    "C_D",
    relative_tol=0.1,
    allow_change=True,
    gate_type=RegressionGate.MODEL_UPDATE_EXPECTED
)

# 檢查回歸
current_kpis = {
    "coordinate_transform_error": 1e-10,  # 硬約束：通過
    "max_q": 51000.0,  # 軟約束：超過 5%，失敗
    "C_D": 0.32  # 預期變動：在 10% 內，通過但需說明
}

regression_result = regression_test.check_regression(current_kpis, "v1.1")
print(f"  檢查 KPI 數: {regression_result['n_checked']}")
print(f"  通過: {regression_result['n_passed']}")
print(f"  失敗: {regression_result['n_failed']}")
print(f"  硬約束: {regression_result['summary']['hard_invariant']}")
print(f"  軟約束: {regression_result['summary']['soft_kpi']}")
print(f"  預期變動: {regression_result['summary']['model_update_expected']}\n")

# ========== 測試 7: 可重現性包 ==========
print("7) 可重現性包測試")

config = SimulationConfig(
    simulation_id="test_001",
    timestamp="2026-01-26T10:00:00",
    random_seed=42,
    dt=0.01,
    t_end=100.0,
    initial_conditions={"r0": [6771000.0, 0.0, 0.0]},
    parameters={"mu": 3.986004418e14}
)

reproducibility_pack.set_config(config)
reproducibility_pack.register_model_version("aero", "1.0", {"C_D": 0.3}, "CFD")
reproducibility_pack.set_output_summary(
    kpis={"max_q": 50000.0, "fuel_margin": 0.9}
)

print(f"  配置 Hash: {config.compute_hash()}")
print(f"  模型版本數: {len(reproducibility_pack.model_versions)}\n")

# ========== 測試 8: 文件去敏 ==========
print("8) 文件去敏測試")

test_text = "這是一個導彈設計程式，使用比例導引進行攔截。"
sanitized = doc_sanitizer.sanitize_text(test_text, add_disclaimer=False)
print(f"  原文: {test_text}")
print(f"  清理後: {sanitized}\n")

# ========== 測試 9: Monte Carlo 多 KPI ==========
print("9) Monte Carlo 多 KPI 測試")

def multi_kpi_calc(mdot, v_e, C_D, rho, V, S_ref):
    return {
        "thrust": mdot * v_e,
        "max_q": 0.5 * rho * V * V,
        "drag": 0.5 * C_D * rho * V * V * S_ref
    }

uncertain_inputs = {
    "mdot": UncertaintyDistribution("mdot", mean=0.8, std=0.05, lower_bound=0.5, upper_bound=1.0),
    "v_e": UncertaintyDistribution("v_e", mean=3000.0, std=50.0, lower_bound=2800.0, upper_bound=3200.0),
    "C_D": UncertaintyDistribution("C_D", mean=0.3, std=0.02, lower_bound=0.2, upper_bound=0.4)
}

fixed_inputs = {"rho": 1.0, "V": 1000.0, "S_ref": 1.0}

mc_result = UncertaintyPropagation.monte_carlo_analysis(
    multi_kpi_calc, uncertain_inputs, n_samples=100,
    fixed_inputs=fixed_inputs, random_seed=42
)

if "kpi_statistics" in mc_result:
    print(f"  多 KPI 分析完成:")
    for kpi_name, stats in mc_result["kpi_statistics"].items():
        print(f"    {kpi_name}: P50={stats['p50']:.2f}, P90={stats['p90']:.2f}")
    print(f"  隨機種子: {mc_result['random_seed']}\n")

# ========== 測試 10: 同時事件處理 ==========
print("10) 同時事件處理測試")

concurrent_events = [
    Event(EventType.MAX_DYNAMIC_PRESSURE, 10.0, np.array([1.0]), {"q": 55000.0}),
    Event(EventType.OVERHEAT, 10.0, np.array([1.0]), {"T_w": 1600.0}),
    Event(EventType.FUEL_DEPLETED, 10.0, np.array([1.0]), {"m": 0.5}),
]

results = event_detector.handle_concurrent_events(concurrent_events)
print(f"  同時事件數: {len(concurrent_events)}")
print(f"  處理結果數: {len(results)}")
for i, result in enumerate(results):
    print(f"    事件 {i+1}: {result['event_type']}, 優先級: {result['priority']}\n")

print("=== 所有測試完成 ===")
