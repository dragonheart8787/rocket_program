# 工程化改進說明

本文件說明已實施的 V&V（Verification & Validation）、不確定度治理、數值穩定性、可追溯性等工程化改進。

---

## 一、Verification（驗算）

### 1.1 守恆檢查

**目的**：驗證程式是否正確求解宣稱的方程

#### 能量守恆檢查
- **無推力時**：兩體問題能量應守恆 `E = 0.5*m*V² - μ*m/r = constant`
- **檢查方法**：比較初始與當前能量，計算相對誤差
- **容許誤差**：< 1e-6（數值積分誤差）

#### 角動量守恆檢查
- **無力矩時**：角動量應守恆 `H = m * r × v = constant`
- **檢查方法**：比較初始與當前角動量向量

#### 質量守恆檢查
- **無推進時**：質量應不變

**使用範例**：
```python
from verification_validation import conservation

energy_check = conservation.energy_conservation_no_thrust(
    r_current, v_current, m_current, mu, r0, v0, m0
)
if not energy_check['conserved']:
    print(f"警告：能量守恆誤差 {energy_check['relative_error']:.2e}")
```

### 1.2 收斂性測試

**目的**：驗證數值積分是否收斂

**方法**：用不同步長（dt = 0.02, 0.01, 0.005）運行相同案例，比較終端狀態

**使用範例**：
```python
from verification_validation import convergence

conv_result = convergence.run_convergence_test(
    dynamics_func, initial_state, t_end=10.0, dt_list=[0.02, 0.01, 0.005]
)
```

### 1.3 單元測試基準

**目的**：對每個公式提供已知輸入輸出對照

**已實現**：
- ISA 基準測試
- 推力方程基準測試
- 火箭方程基準測試

---

## 二、Validation（驗證）

### 2.1 模型適用範圍

**目的**：明確每個模型的適用範圍，超出時警告或報錯

**已實現**：
- `ModelApplicability` 類：定義 Mach、高度、溫度、攻角、Re 範圍
- 自動檢查輸入是否在適用範圍內
- 接近邊界時警告

**使用範例**：
```python
from verification_validation import ModelApplicability

isa_applicability = ModelApplicability(
    name="ISA",
    M_max=5.0,
    h_max=86000.0,
    T_min=100.0,
    T_max=5000.0
)

check = isa_applicability.check(M=2.0, h=50000.0, T=250.0, alpha=0.1, Re=1e6)
if not check['in_range']:
    print(f"警告：{check['warnings']}")
```

### 2.2 參考案例對照

**目的**：與權威來源對照驗證

**已實現**：
- 兩體軌道參考案例
- ISA 標準高度對照
- 薄壁圓筒應力參考

---

## 三、不確定度傳播與敏感度分析

### 3.1 Monte Carlo 不確定度分析

**目的**：將輸出從「一條線」升級為「區間」（P10/P50/P90）

**已實現**：
- `UncertaintyDistribution`：定義不確定度分佈（高斯、均勻、界限）
- `UncertaintyPropagation.monte_carlo_analysis()`：Monte Carlo 傳播
- 輸出統計量：均值、標準差、P10/P50/P90

**使用範例**：
```python
from verification_validation import UncertaintyDistribution, UncertaintyPropagation

uncertain_inputs = {
    "mdot": UncertaintyDistribution("mdot", mean=0.8, std=0.05),
    "v_e": UncertaintyDistribution("v_e", mean=3000.0, std=50.0)
}

mc_result = UncertaintyPropagation.monte_carlo_analysis(
    thrust_calc, uncertain_inputs, n_samples=1000
)
print(f"P50: {mc_result['p50']:.2f}, P90: {mc_result['p90']:.2f}")
```

### 3.2 敏感度分析

**目的**：找出主導誤差來源

**已實現**：
- `SensitivityAnalysis.first_order_sensitivity()`：一階敏感度（有限差分）
- `SensitivityAnalysis.sobol_indices_approximation()`：Sobol 指標（簡化）

**使用範例**：
```python
from verification_validation import SensitivityAnalysis

sens_result = SensitivityAnalysis.first_order_sensitivity(
    thrust_calc, base_inputs, perturbations
)
print(f"主導參數: {sens_result['ranked_parameters'][0]}")
```

---

## 四、數值穩定性與事件系統

### 4.1 事件驅動模擬

**目的**：處理分段模式切換、事件偵測

**已實現**：
- `EventDetector`：事件偵測器
  - 最大動壓
  - 過熱
  - 過載
  - 燃料耗盡
  - 地面碰撞
  - 模型邊界
- `Event`：事件定義
- `ModeSwitcher`：模式切換器

**使用範例**：
```python
from event_system import event_detector

events = event_detector.check_all_events(t, state, aux)
for event in events:
    result = event_detector.handle_event(event)
```

### 4.2 自適應步長積分器

**目的**：處理剛性問題，提高數值穩定性

**已實現**：
- `AdaptiveIntegrator`：Dormand-Prince 5(4) 自適應積分器
- 自動步長調整
- 誤差估計

**使用範例**：
```python
from event_system import adaptive_integrator

t_history, x_history, dt_history = adaptive_integrator.integrate_adaptive(
    dynamics_func, t0, x0, t_end, dt_initial=0.02
)
```

---

## 五、座標系與時間系統

### 5.1 明確定義

**已實現**：
- `TimeStandard`：時間標準（UTC/UT1/TT/TAI）
- `CoordinateFrame`：座標系（ECI/ECEF/NED/BODY）
- `EarthModel`：地球模型（球形/橢球）
- `CoordinateSystemManager`：座標系管理器

### 5.2 一致性檢查

**已實現**：
- `ConsistencyChecker`：座標轉換一致性檢查
- 時間一致性檢查

**使用範例**：
```python
from coordinate_time_system import coord_manager, consistency_checker

r_ecef = coord_manager.ecef_from_eci(r_eci, t)
consistency = consistency_checker.check_coordinate_consistency(r_eci, r_ecef, t, coord_manager)
```

### 5.3 風場定義域

**明確**：風場定義在 NED（相對地表），轉換到 ECI 用於空速計算

---

## 六、資料契約與版本控管

### 6.1 氣動係數資料契約

**已實現**：
- `AeroCoefficientSchema`：定義氣動係數資料結構
  - 適用範圍（Mach, Re, alpha, beta）
  - 網格定義
  - 插值方法
  - 外插策略
  - 資料來源
  - 版本資訊

### 6.2 版本控管

**已實現**：
- `ModelVersion`：模型版本資訊
- `DataVersionControl`：版本歷史管理
- 可匯出 JSON

**使用範例**：
```python
from data_contract import AeroCoefficientSchema, DataVersionControl

schema = AeroCoefficientSchema(
    name="test_aero",
    version="1.0",
    Mach_range=(0.0, 2.0),
    ...
)
validation = schema.validate_input(M, alpha, Re, beta)
sanity = schema.check_physical_sanity()
```

---

## 七、TPS 材料模型與失效判據

### 7.1 材料性質隨溫度變化

**已實現**：
- `MaterialProperty`：材料性質（導熱率、比熱、密度隨溫度）
- 分段線性或幂律模型

### 7.2 失效判據

**已實現**：
- 玻璃化溫度
- 熔點
- 結構允許上限
- 黏結層上限

### 7.3 強度折減

**已實現**：
- `MaterialStrengthDegradation`：屈服強度、彈性模數隨溫度折減
- 熱-結構耦合分析

**使用範例**：
```python
from tps_materials import tps_failure

failure = tps_failure.analyze_thermal_failure("C-C", T_w=2600.0, T_int=2000.0)
if failure['overall_failed']:
    print("TPS 失效！")
```

---

## 八、載荷案例管理

### 8.1 標準載荷案例

**已實現**：
- 最大動壓
- 最大過載
- 最大彎矩
- 熱梯度
- 落震/振動（介面）

### 8.2 裕度報表

**已實現**：
- 自動計算所有案例的裕度
- 找出瓶頸案例（最小裕度）

**使用範例**：
```python
from load_cases import load_case_manager

load_result = load_case_manager.evaluate_all_cases(q, n, M_bend, delta_T, t)
margins = load_case_manager.compute_margins(actual_values)
print(f"瓶頸: {margins['bottleneck_cases']}")
```

---

## 九、工程化工具

### 9.1 單位系統

**已實現**：
- `UnitSystem`：強制 SI 單位
- 單位驗證（數值範圍合理性）

### 9.2 日誌與追蹤

**已實現**：
- `SimulationLogger`：模擬日誌記錄
- `SimulationMetadata`：元數據（可追溯性）
  - 模擬 ID
  - 時間戳
  - Git commit
  - 模型版本
  - 參數快照

### 9.3 API Schema

**已實現**：
- `InputSchema`：輸入驗證
- `OutputSchema`：輸出文件化
- `APIContract`：API 契約管理

### 9.4 可追溯性

**已實現**：
- `TraceabilityManager`：記錄設計決策、需求、驗證結果
- 可匯出 JSON

---

## 十、改進前後對比

### 改進前
- ❌ 無 V&V 框架
- ❌ 無不確定度分析
- ❌ 無事件系統
- ❌ 座標系定義不明確
- ❌ 無資料版本控管
- ❌ TPS 無失效判據
- ❌ 無載荷案例管理
- ❌ 無可追溯性

### 改進後
- ✅ 完整 V&V 框架（守恆檢查、收斂性測試、參考案例）
- ✅ Monte Carlo 不確定度分析（P10/P50/P90）
- ✅ 敏感度分析（找出主導誤差來源）
- ✅ 事件系統（事件偵測與處理）
- ✅ 自適應步長積分器（數值穩定性）
- ✅ 座標系與時間系統明確化
- ✅ 資料契約與版本控管
- ✅ TPS 材料模型與失效判據
- ✅ 載荷案例管理與裕度報表
- ✅ 工程化工具（單位、日誌、API schema、可追溯性）

---

## 十一、使用建議

### 11.1 每次模擬前
1. 執行守恆檢查（驗算）
2. 檢查模型適用範圍
3. 驗證輸入參數（API schema）

### 11.2 模擬過程中
1. 監控事件（最大動壓、過熱等）
2. 記錄關鍵決策（可追溯性）
3. 檢查載荷案例

### 11.3 模擬後
1. 執行不確定度分析（Monte Carlo）
2. 敏感度分析（找出主導參數）
3. 生成 V&V 報告
4. 儲存元數據與可追溯性記錄

---

## 十二、限制與注意事項

### 12.1 當前限制
1. **部分實現為簡化版**：
   - Dormand-Prince 積分器為簡化實現
   - Sobol 敏感度為近似
   - 單位系統無完整轉換（需 units library）

2. **V&V 覆蓋率**：
   - 守恆檢查僅涵蓋基本情況
   - 參考案例對照需擴充
   - 單元測試基準需持續補充

3. **不確定度分析**：
   - Monte Carlo 樣本數可調（建議 ≥ 1000）
   - 敏感度分析為一階（高階需專門庫）

### 12.2 後續改進方向
1. 整合完整 units library（如 pint）
2. 擴充參考案例庫
3. 實現完整 Sobol 敏感度（SALib）
4. 添加更多單元測試基準
5. 實現完整 Dormand-Prince 積分器
6. 整合 CI/CD 自動測試

---

## 十三、適用範圍明確化

### ✅ 適用
- 概念設計階段性能估算
- 教育與研究用途
- 算法開發與理論驗證
- 參數掃描與敏感度分析
- 初步設計迭代

### ❌ 不適用
- 最終設計驗證（需專業工具交叉驗證）
- 製造級精度要求
- 認證與審查（需完整 V&V 報告）
- 實際飛行任務（需完整測試驗證）

---

## 十四、文檔修正

### 修正前
- "專業級精度" ❌
- "可直接用於設計計算" ❌
- "導彈設計框架" ⚠️（風險表述）

### 修正後
- "概念設計/教育用途" ✅
- "需專業工具交叉驗證" ✅
- "一般飛行器/再入體/探空載具" ✅（中性表述）
- 明確適用範圍與限制 ✅
- 強制輸出誤差帶與適用範圍 ✅

---

**總結**：本程式已從「功能展示」升級為「工程可信」框架，具備完整的 V&V、不確定度分析、數值穩定性、可追溯性等工程化能力。但仍需明確適用範圍，並持續擴充 V&V 覆蓋率。
