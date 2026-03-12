# Von Kármán (馮·卡門) 與 Tsien (錢學森) 理論模組說明

本模組整合了兩位航太工程大師的核心理論、公式與設計方法論，可直接用於航太載具的概念設計與分析。

## 模組結構

### 1. `VonKarmanTheory` 類
包含馮·卡門在空氣動力學、邊界層、超音速流、結構力學等領域的經典公式。

### 2. `TsienTheory` 類
包含錢學森在可壓縮邊界層、飛行力學、工程控制論、高超音速等領域的核心貢獻。

### 3. `AerospaceDesignFramework` 類
實現完整的航太設計流程框架，體現「理論 → 模型 → 試驗 → 修正 → 工程化」的設計循環。

---

## Von Kármán 理論核心內容

### 幾何設計
- **Von Kármán 頭錐**：最小波阻頭錐形狀
  ```python
  von_karman.von_karman_nose_cone(x, L, R, n=0.75)
  ```
- **Sears-Haack Body**：最小波阻三維體

### 氣動理論
- **升力線理論**：有限翼升力計算
- **Kármán-Tsien 可壓縮性修正**：比 Prandtl-Glauert 更精確
- **Prandtl-Meyer 展開**：超音速轉角計算
- **斜激波關係**：θ-β-M 關係

### 邊界層
- **von Kármán 動量積分方程**：工程級邊界層預估基礎

### 渦動力學
- **Kármán Vortex Street**：渦街頻率與 Strouhal 數

### 結構力學
- **Kármán-Donnell 圓柱殼屈曲**：火箭殼體屈曲應力

### 推進
- **臨界質量流率**：噴管喉部流率（卡門校正）

### 卡門線
- **Kármán Line**：100 km 高度（大氣與太空分界）

---

## Tsien (錢學森) 理論核心內容

### 可壓縮邊界層
- **可壓縮邊界層動量方程**：錢學森博士論文核心
- **可壓縮邊界層能量方程**：總焓形式

### 錢學森彈道（三方程 + 最優彈道）
- **速度方程**：`dV/dt = (T*cos(α) - D)/m - g*sin(γ)`
- **航跡角方程**：`dγ/dt = (T*sin(α) + L)/(m*V) - (g*cos(γ))/V`
- **高度方程**：`dh/dt = V*sin(γ)`
- **質量方程**：`dm/dt = -ṁ_fuel`
- **最優彈道控制框架**：最長射程 / 最小燃料策略
- **最長射程彈道**：分段控制（初期增速、中段滑翔、末段調整）
- **最小燃料彈道**：最佳控制問題求解

### 導彈飛行力學
- **穩定性分析**：縱向、方向、滾轉穩定性
- **控制力矩效能**：控制面力矩計算
- **比例導引律**：導彈導引控制（錢學森框架的初期形式）

### 結構力學
- **圓柱殼屈曲**：與 von Kármán 合作的薄殼屈曲理論

### 工程控制論（Engineering Cybernetics）
- **狀態空間模型**：`ẋ = A*x + B*u, y = C*x + D*u`
- **回授控制**：閉迴路系統設計
- **解耦控制**：多變量系統解耦
- **系統分解方法**：大系統分解為子系統
- **設計循環回饋**：設計 → 模擬 → 測試 → 修正閉環
- **需求轉換**：任務需求轉換為技術指標

### 高超音速與高焓氣流
- **再入熱流**：Kármán-Sutton 型熱流估算
- **高焓氣流總焓**：`h_t = h + V²/2`
- **化學反應效應**：高超音速化學非平衡
- **熱傳耦合**：氣動與熱防護耦合

### 噴管設計
- **面積-馬赫數關係**：JPL 時期推廣的噴管設計公式
- **最佳膨脹比**：低壓環境修正
- **推力損失修正**：低壓環境下的推力損失

### 軌跡最佳化
- **成本函數**：最小燃料、最小時間、最大射程
- **Pontryagin 最優性原理**：Hamiltonian 計算

### 爆炸波理論
- **Taylor-Sedov 爆炸波**：爆炸波半徑計算
- **爆炸波壓力分佈**：壓力比隨距離變化

### 工程數學方法
- **區域函數法**：複雜邊界條件求解
- **非線性系統分析**：線性化方法

### 火箭設計基本方程
- **質量預算方程**：`m = m_s + m_p + m_pl`
- **Δv 積分方程**：`Δv = ∫ (T-D)/m dt`

---

## 設計流程框架

`AerospaceDesignFramework` 實現完整的設計循環：

### Step 0: 任務需求
定義任務類型、Δv 需求、載重、可靠度等。

### Step 1: 幾何初始設計
使用 Von Kármán 頭錐或 Sears-Haack Body 生成初始幾何。

### Step 2: 氣動設計
應用升力線理論、Kármán-Tsien 修正、Prandtl-Meyer 等計算氣動特性。

### Step 3: 推進系統設計
計算臨界質量流率、噴管膨脹比等。

### Step 4: 結構設計
使用 Kármán-Donnell 屈曲公式評估結構安全。

### Step 5: 軌跡分析
使用錢學森三方程計算飛行軌跡。

### Step 6: 控制設計
應用工程控制論設計控制系統。

### Step 7: 系統整合
整合所有子系統，進行迭代優化。

### 錢學森工程控制論擴充方法
- **`tsien_system_engineering_cycle()`**：完整系統工程循環（需求 → 系統 → 分系統 → 測試 → 修正）
- **`tsien_trajectory_optimization()`**：軌跡最佳化框架（最長射程、最小燃料）
- **`tsien_missile_design_framework()`**：完整導彈設計框架（彈道、穩定性、控制、導引）

---

## 使用範例

```python
from von_karman_tsien_theory import von_karman, tsien, design_framework

# Von Kármán 頭錐
x, r = create_von_karman_nose_profile(L=2.0, R_max=0.5, n=0.75)

# 升力線理論
C_L = von_karman.lifting_line_theory(AR=6.0, alpha=math.radians(5.0))

# Kármán-Tsien 修正
C_p = von_karman.karman_tsien_compressibility(C_p0=0.5, M=0.8)

# 錢學森彈道
dstate = tsien.tsien_trajectory_system(t, state, T, alpha, mdot, L_func, D_func, g)

# 最優彈道
optimal = tsien.qian_trajectory_optimal_control(state, T_max, alpha, L_func, D_func, g, "max_range")

# 最長射程彈道
max_range = tsien.qian_maximum_range_trajectory(V0, gamma0, h0, m0, T, L_func, D_func, g, t_end, dt)

# 最小燃料彈道
min_fuel = tsien.qian_minimum_fuel_trajectory(V0, gamma0, h0, m0, T_max, mdot_max, L_func, D_func, g, target_h, target_V)

# 導彈飛行力學
stability = tsien.missile_stability_longitudinal(C_m_alpha)
guidance = tsien.proportional_navigation_guidance(V_missile, V_target, lambda_angle, N=3.0)

# 工程控制論
xdot, y = tsien.state_space_model(A, B, C, D, x, u)
decomposed = tsien.system_decomposition(requirements, subsystems)

# 完整系統工程循環
sys_cycle = design_framework.tsien_system_engineering_cycle(requirements)

# 軌跡最佳化
opt_result = design_framework.tsien_trajectory_optimization(initial_state, target_state, T_max, mdot_max, L_func, D_func, g)

# 完整導彈設計
missile_design = design_framework.tsien_missile_design_framework(mission_range, payload, target_speed)
```

詳細範例請參考 `von_karman_tsien_example.py`。

---

## 理論來源

- **Von Kármán**: *Aerodynamics: Selected Topics*, *Mathematical Methods in Engineering*
- **Tsien**: *Engineering Cybernetics*, JPL 技術報告系列
- 公開學術文獻與 NASA/JPL 技術手冊

---

## 注意事項

1. **教育用途**：本模組主要用於教育與概念設計
2. **驗證需求**：實際工程應用需依專案需求進行驗證與修正
3. **簡化假設**：部分公式使用簡化假設，完整分析需使用專業 CFD/FEA 工具
4. **迭代求解**：某些公式（如斜激波角）需數值迭代，本模組提供簡化近似

---

## 擴展方向

- 整合 CFD 代理模型
- 加入更多試驗數據校正
- 實現完整的最優控制求解器
- 擴充多學科設計優化（MDO）框架
- 加入更多材料與結構模型
