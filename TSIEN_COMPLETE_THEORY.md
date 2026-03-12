# 錢學森（Tsien Hsue-shen）完整理論架構

本文件完整整理錢學森在航太工程領域的所有核心貢獻，並說明如何在設計器中應用。

---

## 一、錢學森彈道（Qian Xuesen Trajectory）

### 1.1 定義與核心精神

**錢學森彈道**不是單一公式，而是一套**導彈飛行軌跡設計方法論**，包含：

- **三大微分方程**（飛行三方程）
- **最優控制策略**（最長射程、最小燃料）
- **分段控制方法**（初期、中段、末段）

### 1.2 三大方程式

```
dV/dt = (T*cos(α) - D)/m - g*sin(γ)    [速度方程]
dγ/dt = (T*sin(α) + L)/(m*V) - (g*cos(γ))/V  [航跡角方程]
dh/dt = V*sin(γ)                       [高度方程]
dm/dt = -ṁ_fuel                        [質量方程]
```

### 1.3 最長射程彈道（Classical Qian Trajectory）

**策略**：
1. **初期**：小攻角快速增速
2. **中段**：零升力、遠距滑翔
3. **末段**：再調整攻角控制末端撞擊條件

這是 MLRS、巡弋飛彈、先進導彈軌跡設計的基礎。

### 1.4 最小燃料彈道（Minimum-Energy Trajectory）

**目標**：`min ∫ ṁ dt`

在氣動阻力、重力、推力限制下的最佳軌跡。這是今日再入軌跡、火箭爬升軌跡、導彈脫離軌跡的數學基礎。

---

## 二、錢學森主要貢獻分類總表

### (A) 火箭與導彈推進

1. **推進與噴管理論**
   - 等熵關係
   - 噴管面積-馬赫數方程
   - 推力公式
   - 噴管最佳膨脹比
   - 低壓環境下的推力損失修正

2. **火箭設計基本方程**
   - 質量預算：`m = m_s + m_p + m_pl`
   - Δv 積分：`Δv = ∫ (T-D)/m dt`

### (B) 導彈飛行力學

1. **錢學森三方程**（飛行微分方程）
2. **導彈穩定性**：縱向、方向、滾轉
3. **控制力矩**：控制面效能計算
4. **導引律**：比例導引（初期形式）
5. **高超音速飛行框架**：含熱流估算

### (C) 空氣動力學與高溫氣體

1. **邊界層理論**（與 Von Kármán 合作）
   - 壓縮性邊界層
   - 激波-邊界層干擾
   - 高焓氣流
   - 音爆與激波系統

2. **Hypersonic Aerodynamics**
   - 再入熱流公式框架
   - 高焓化學反應氣體模型
   - 熱傳與氣動耦合

### (D) 控制理論

1. **多變量控制**
2. **回授控制的工程方法論**
3. **飛行穩定控制**
4. **火箭姿態控制方程**
5. **最佳控制概念雛形**（Pontryagin 之前）

### (E) 工程控制論（Cybernetics in Engineering）

1. **大系統分解方法**
2. **工程設計循環**：需求 → 系統 → 分系統 → 測試 → 修正
3. **需求轉換**：任務需求 → 技術指標
4. **閉環回饋**：設計循環的自動修正

這套方法後來變成航太業標準流程（NASA Systems Engineering Handbook）。

### (F) 熱力學 / 高焓氣體 / 爆炸波

1. **衝擊波理論**
2. **真空射流**
3. **高溫燃燒**
4. **化學非平衡氣體**
5. **爆炸波結構**（Taylor-Sedov）

### (G) 工程數學

1. **區域函數法**
2. **複雜邊界條件下的偏微分方程**
3. **線性與非線性系統分析**

---

## 三、在設計器中的應用

### 3.1 錢學森控制論（Systems Engineering）

**實現**：
- 任務分解
- 需求轉換成技術指標
- 子系統架構
- 設計 → 模擬 → 測試 → 修正的閉環架構

**方法**：
```python
# 系統分解
decomposed = tsien.system_decomposition(requirements, subsystems)

# 需求轉換
specs = tsien.requirement_to_specification(mission_req)

# 設計循環回饋
corrections = tsien.design_cycle_feedback(current_design, test_results, requirements)
```

### 3.2 錢學森彈道 + 軌跡最佳化

**實現**：
- 三方程積分
- Δv 消耗計算
- 氣動阻力整合
- 推力曲線最佳化

**方法**：
```python
# 最長射程彈道
max_range = tsien.qian_maximum_range_trajectory(V0, gamma0, h0, m0, T, L_func, D_func, g, t_end, dt)

# 最小燃料彈道
min_fuel = tsien.qian_minimum_fuel_trajectory(V0, gamma0, h0, m0, T_max, mdot_max, L_func, D_func, g, target_h, target_V)

# 軌跡最佳化
opt_result = design_framework.tsien_trajectory_optimization(initial_state, target_state, T_max, mdot_max, L_func, D_func, g)
```

### 3.3 錢學森高超聲速模型

**實現**：
- 高焓氣流計算
- 再入熱流估算
- 熱防護 TPS 估算

**方法**：
```python
# 高焓總焓
h_total = tsien.high_enthalpy_flow_total_enthalpy(h_static, V)

# 化學反應效應
d_species = tsien.hypersonic_chemical_reaction_effect(rho, T, species, reaction_rates)

# 熱傳耦合
dT_dt = tsien.hypersonic_heat_transfer_coupling(q_aero, T_w, k_tps, delta_tps)
```

---

## 四、完整方法列表

### 錢學森彈道與軌跡
- `tsien_trajectory_system()` - 三方程系統
- `qian_trajectory_optimal_control()` - 最優彈道控制框架
- `qian_maximum_range_trajectory()` - 最長射程彈道
- `qian_minimum_fuel_trajectory()` - 最小燃料彈道

### 導彈飛行力學
- `missile_stability_longitudinal()` - 縱向穩定性
- `missile_stability_directional()` - 方向穩定性
- `missile_stability_roll()` - 滾轉穩定性
- `control_moment_effectiveness()` - 控制力矩效能
- `proportional_navigation_guidance()` - 比例導引律

### 工程控制論
- `state_space_model()` - 狀態空間模型
- `feedback_control_loop()` - 回授控制
- `decoupling_control()` - 解耦控制
- `system_decomposition()` - 系統分解
- `design_cycle_feedback()` - 設計循環回饋
- `requirement_to_specification()` - 需求轉換

### 高超音速與高焓
- `hypersonic_heat_flux()` - 再入熱流
- `high_enthalpy_flow_total_enthalpy()` - 高焓總焓
- `hypersonic_chemical_reaction_effect()` - 化學反應效應
- `hypersonic_heat_transfer_coupling()` - 熱傳耦合

### 軌跡最佳化
- `trajectory_optimization_cost()` - 成本函數
- `pontryagin_hamiltonian()` - Pontryagin Hamiltonian

### 爆炸波理論
- `taylor_sedov_blast_wave_radius()` - Taylor-Sedov 爆炸波
- `blast_wave_pressure_ratio()` - 爆炸波壓力比

### 工程數學
- `region_function_method()` - 區域函數法
- `nonlinear_system_analysis()` - 非線性系統分析

### 火箭設計基本方程
- `qian_mass_budget_equation()` - 質量預算
- `qian_delta_v_integral()` - Δv 積分
- `qian_optimal_expansion_ratio()` - 最佳膨脹比
- `qian_thrust_loss_low_pressure()` - 低壓推力損失

### 設計框架擴充
- `tsien_system_engineering_cycle()` - 完整系統工程循環
- `tsien_trajectory_optimization()` - 軌跡最佳化框架
- `tsien_missile_design_framework()` - 完整導彈設計框架

---

## 五、理論來源

- **Engineering Cybernetics**（工程控制論）- 錢學森著
- **JPL 技術報告系列** - 1940-1950 年代
- **Caltech 學術論文** - 可壓縮邊界層、高超音速
- **公開學術文獻** - 導彈飛行力學、軌跡最佳化

---

## 六、應用限制

1. **教育與研究用途**：本理論框架主要用於教育與概念設計
2. **驗證需求**：實際工程應用需依專案需求進行驗證
3. **簡化假設**：部分方法使用簡化假設，完整分析需專業工具
4. **非軍事用途**：限制用於民用教育／研究，不涉及軍事落地

---

## 七、與 Von Kármán 的關聯

| 領域 | Von Kármán | 錢學森 |
|------|------------|--------|
| 邊界層 | 動量積分方程 | 可壓縮邊界層 |
| 結構屈曲 | Kármán-Donnell | 合作研究 |
| 噴管設計 | 基礎理論 | JPL 工程化 |
| 系統工程 | 基礎框架 | 工程控制論（完整方法論） |
| 軌跡最佳化 | 基礎方程 | 三方程 + 最優控制 |

---

## 八、完整設計流程（錢學森方法論）

```
任務需求
    ↓
需求轉換（技術指標）
    ↓
系統分解（子系統需求）
    ↓
子系統設計（幾何、氣動、推進、結構、控制）
    ↓
系統整合
    ↓
軌跡分析（錢學森三方程）
    ↓
軌跡最佳化（最長射程/最小燃料）
    ↓
測試與驗證
    ↓
設計循環回饋（修正）
    ↓
最終設計
```

---

**總計**：錢學森理論模組包含 **30+ 個核心方法**，涵蓋彈道、飛行力學、控制論、系統工程、高超音速等所有領域。
