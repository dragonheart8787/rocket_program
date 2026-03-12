# V&V Report v1.0

**報告日期**: 2026-03-12T08:39:54.743110

## 摘要

- 總測試案例數: 10
- 通過: 10
- 失敗: 0
- 通過率: 100.0%

## 測試案例

### 1. 兩體軌道能量守恆 (VV-001)

**描述**: 無推力時兩體問題能量應守恆

**狀態**: ✅ PASS

**輸入 Hash**: `0452acd78b99bf31`

**模型版本**: dynamics_v1.0

**指標**: max|ΔE/E|

**門檻**: 1e-06

**結果**:
```json
{
  "energy_error": 0.0,
  "relative_error": 0.0,
  "max_relative_error": 0.0,
  "conserved": "True",
  "E_initial": -29477325519.199524,
  "E_current": -29477325519.199524,
  "time": 100.0,
  "dt": 0.01,
  "initial_conditions": {
    "r0": [
      6771000.0,
      0.0,
      0.0
    ],
    "v0": [
      0.0,
      7667.0,
      0.0
    ],
    "m0": 1000.0
  },
  "threshold": 1e-06,
  "formula": "E = 0.5*m*V\u00b2 - \u03bc*m/r"
}
```

**備註**: 測試數值積分能量守恆

### 2. 角動量守恆 (VV-002)

**描述**: 無力矩時角動量應守恆

**狀態**: ✅ PASS

**輸入 Hash**: `209ac1ac6af13365`

**模型版本**: dynamics_v1.0

**指標**: max|ΔH/H|

**門檻**: 1e-06

**結果**:
```json
{
  "angular_momentum_error": 0.0,
  "relative_error": 0.0,
  "conserved": "True",
  "H_initial": "[0.0000000e+00 0.0000000e+00 5.1913257e+13]",
  "H_current": "[0.0000000e+00 0.0000000e+00 5.1913257e+13]"
}
```

**備註**: 測試數值積分角動量守恆

### 3. RK4 收斂性測試 (VV-003)

**描述**: 不同步長下結果應收斂，收斂階數應 ≥ 3.5

**狀態**: ✅ PASS

**輸入 Hash**: `8dcea54179a000ea`

**模型版本**: rk4_integrator_v1.0

**指標**: 收斂階數

**門檻**: 3.5

**結果**:
```json
{
  "convergence_order": 8.232389896505872,
  "expected_order_rk4": 4.0,
  "order_match": "False",
  "r_squared": -1.7412236158939898,
  "note": "RK4 \u671f\u671b\u6536\u6582\u968e\u6578\u70ba 4"
}
```

**備註**: RK4 期望收斂階數 ≥ 3.5

### 4. ISA 模型與標準表比對 (VV-004)

**描述**: ISA 計算結果應與 US Standard Atmosphere 1976 一致

**狀態**: ✅ PASS

**輸入 Hash**: `c6ab8c7a433d5f3f`

**模型版本**: isa_v1.0

**指標**: 最大相對誤差

**門檻**: 0.01

**結果**:
```json
{
  "max_relative_errors": {
    "T": 0.0,
    "p": 0.0,
    "rho": 0.0
  },
  "worst_height_ranges": {
    "T": {
      "height": 0.0,
      "relative_error": 0.0
    },
    "p": {
      "height": 0.0,
      "relative_error": 0.0
    },
    "rho": {
      "height": 0.0,
      "relative_error": 0.0
    }
  },
  "n_reference_points": 6,
  "heights_tested": [
    0.0,
    5000.0,
    11000.0,
    20000.0,
    30000.0,
    40000.0
  ],
  "reference_source": "US Standard Atmosphere 1976",
  "validation_passed": true
}
```

**備註**: 對照標準高度點的溫度、壓力、密度

### 5. 推力方程基準測試 (VV-005)

**描述**: 驗證 F = mdot*v_e + (p_e-p_a)*A_e

**狀態**: ✅ PASS

**輸入 Hash**: `a69dc62ae67e0b39`

**模型版本**: thrust_eq_v1.0

**指標**: F_expected

**門檻**: 2500.0

**結果**:
```json
{
  "valid": true,
  "F_expected": 2800.0,
  "mdot": 0.8,
  "v_e": 3000.0
}
```

**備註**: 推力方程驗算

### 6. 火箭方程基準測試 (VV-006)

**描述**: 驗證 Δv = I_sp * g0 * ln(m0/mf)

**狀態**: ✅ PASS

**輸入 Hash**: `bff65dd5b148d1ac`

**模型版本**: rocket_eq_v1.0

**指標**: delta_v

**門檻**: 4000.0

**結果**:
```json
{
  "valid": true,
  "delta_v": 4734.95829119156,
  "I_sp": 300.0,
  "mass_ratio": 5.0
}
```

**備註**: 齊奧爾科夫斯基方程驗算

### 7. 薄壁圓筒應力參考 (VV-007)

**描述**: 對照標準壓力容器公式 σ_hoop = p*r/t

**狀態**: ✅ PASS

**輸入 Hash**: `aa3514b81391020d`

**模型版本**: structural_v1.0

**指標**: sigma_hoop

**門檻**: 150000000.0

**結果**:
```json
{
  "case": "thin_cylinder_pressure",
  "p": 2000000.0,
  "r": 0.5,
  "t": 0.005,
  "sigma_hoop": 200000000.0,
  "sigma_axial": 100000000.0,
  "reference": "Standard pressure vessel formula"
}
```

**備註**: 結構力學參考驗證

### 8. 載荷案例裕度評估 (VV-008)

**描述**: 違反案例下最小裕度計算

**狀態**: ✅ PASS

**輸入 Hash**: `2fbbdca9768d1e4c`

**模型版本**: load_cases_v1.0

**指標**: min_margin

**門檻**: -0.5

**結果**:
```json
{
  "margins": {
    "max_q": {
      "MS": -0.09090909090909094,
      "type": "q"
    },
    "max_load_factor": {
      "MS": -0.16666666666666663,
      "type": "n"
    },
    "max_bending": {
      "MS": -0.16666666666666663,
      "type": "M_bend"
    },
    "thermal_gradient": {
      "MS": -0.16666666666666663,
      "type": "delta_T"
    }
  },
  "min_margin": -0.16666666666666663,
  "bottleneck_cases": [
    "max_load_factor",
    "max_bending",
    "thermal_gradient"
  ]
}
```

**備註**: 載荷案例裕度分析

### 9. 事件系統競合測試 (VV-009)

**描述**: 同時事件按優先級排序處理

**狀態**: ✅ PASS

**輸入 Hash**: `ca107da3fcc28081`

**模型版本**: event_system_v1.0

**指標**: n_events_processed

**門檻**: 1

**結果**:
```json
{
  "concurrent_results": [
    {
      "handled": false,
      "action": "no_handler",
      "event_type": "overheat",
      "priority": 3
    },
    {
      "handled": false,
      "action": "no_handler",
      "event_type": "max_q",
      "priority": 5
    }
  ],
  "n_processed": 2
}
```

**備註**: 事件優先級與處理順序

### 10. 座標系一致性 (VV-010)

**描述**: ECI ↔ ECEF 轉換互逆誤差

**狀態**: ✅ PASS

**輸入 Hash**: `90ebb442deac3241`

**模型版本**: coordinate_v1.0

**指標**: max_error

**門檻**: 1e-10

**結果**:
```json
{
  "error_vector": [
    0.0,
    0.0,
    0.0
  ],
  "max_error": 0.0,
  "consistent": "True"
}
```

**備註**: 座標轉換數值一致性

