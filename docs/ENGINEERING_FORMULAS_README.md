# 工程級公式庫說明

本模組已整合完整的**航太/火箭設計工程公式庫**，可直接用於設計計算器與模擬器。

## 使用方式

```python
from aerospace_sim import eng_formulas

# 計算動壓
q = eng_formulas.dynamic_pressure(rho=1.2, V=300.0)

# 計算推力
F = eng_formulas.thrust_equation(mdot=0.8, v_e=3000.0, p_e=50000, p_a=10000, A_e=0.01)
```

## 公式分類

### 1) 大氣/環境
- `dynamic_pressure(rho, V)` - 動壓: q = 0.5 * ρ * V²
- `dynamic_pressure_load(q, S, C)` - 動壓載荷
- `gust_alpha_increment(w_g, V)` - 陣風等效迎角增量
- `gust_lift_increment(q, S, C_La, delta_alpha)` - 陣風升力增量
- `reynolds(rho, V, L, mu)` - 雷諾數

### 2) 氣動
- `lift_force(q, S, C_L)` - 升力
- `drag_force(q, S, C_D)` - 阻力
- `moment(q, S, c, C_M)` - 力矩
- `drag_polar(C_D0, k, C_L)` - 阻力極線: C_D = C_D0 + k*C_L²
- `lift_linearized(C_L0, C_La, alpha)` - 升力線性化
- `static_margin(x_NP, x_CG, c)` - 靜穩定裕度
- `pressure_coefficient(p, p_inf, rho_inf, V_inf)` - 壓力係數

### 3) 可壓縮流
- `normal_shock_pressure_ratio(M1, gamma)` - 正激波壓力比
- `normal_shock_density_ratio(M1, gamma)` - 正激波密度比
- `normal_shock_mach2(M1, gamma)` - 正激波後馬赫數
- `isentropic_temperature_ratio(M, gamma)` - 等熵總溫比
- `isentropic_pressure_ratio(M, gamma)` - 等熵總壓比
- `prandtl_glauert_correction(C_p0, M_inf)` - Prandtl-Glauert 壓縮性修正

### 4) 熱環境/熱傳
- `radiation_heat_flux(eps, sigma, T_w, T_env)` - 輻射熱通量
- `convective_heat_flux(h, T_aw, T_w)` - 對流熱通量
- `nusselt_number(h, L, k_f)` - Nusselt 數
- `nusselt_correlation(Re, Pr, C, m, n)` - Nusselt 關聯式
- `heat_conduction_1d(k, dT_dx)` - 1D 導熱
- `stagnation_temperature(T, M, gamma)` - 停滯溫度

### 5) 結構/材料
- `stress_axial(F, A)` - 軸向應力
- `stress_bending(M, y, I)` - 彎曲應力
- `stress_shear(T, r, J)` - 剪應力
- `stress_thin_cylinder_hoop(p, r, t)` - 薄壁圓筒環向應力
- `stress_thin_cylinder_axial(p, r, t)` - 薄壁圓筒軸向應力
- `von_mises_stress(sigma1, sigma2, sigma3)` - von Mises 等效應力
- `euler_buckling_load(E, I, L, K)` - Euler 柱屈曲載荷
- `miner_damage(n_i, N_i)` - Miner 累積損傷
- `paris_erdogan_da_dN(C, delta_K, m)` - Paris-Erdogan 裂紋成長率
- `stress_intensity_factor(beta, delta_sigma, a)` - 應力強度因子
- `margin_of_safety(allowable, actual)` - 安全裕度
- `natural_frequency(k, m)` - 自然頻率
- `damping_ratio(c, k, m)` - 阻尼比

### 6) 飛行力學
- `velocity_rate_3dof(T, D, m, g, gamma)` - 3DoF 速度變化率
- `flight_path_rate_3dof(L, m, g, gamma, V)` - 3DoF 航跡角變化率
- `turn_radius(V, g, n)` - 轉彎半徑

### 7) 推進（化學/電/核）
- `thrust_equation(mdot, v_e, p_e, p_a, A_e)` - 推力方程
- `specific_impulse(F, mdot, g0)` - 比衝
- `total_impulse(F_t, t)` - 總衝量（數值積分）
- `delta_v_rocket_equation(I_sp, g0, m0, mf)` - 火箭方程 Δv
- `area_ratio_from_mach(M, gamma)` - 面積比-馬赫數關係
- `characteristic_velocity(p_c, A_t, mdot)` - 特徵速度 c*
- `thrust_coefficient(F, p_c, A_t)` - 推力係數 C_F
- `gravity_loss(g, gamma, t)` - 重力損失（數值積分）

### 7.1) 推進進階（推力係數、等效速度、多級火箭）
- `thrust_coefficient_ideal(p_e, p_c, p_a, A_e, A_t, gamma)` - 理想推力係數（完整公式）
- `thrust_from_coefficient(c_F, p_c, A_t)` - 由推力係數計算推力
- `equivalent_exhaust_velocity(v_e, p_e, p_a, A_e, mdot)` - 等效排氣速度
- `specific_impulse_from_equivalent(V_eq, g0)` - 由等效速度計算比衝
- `thrust_to_weight_ratio(F, m, g0)` - 推重比
- `multi_stage_delta_v(v_e_list, m0_list, mf_list)` - 多級火箭總 Δv
- `payload_ratio(m_payload, m0)` - 有效載荷比
- `payload_ratio_from_delta_v(delta_v, v_e)` - 由 Δv 計算有效載荷比
- `initial_mass_from_delta_v(mf, delta_v, v_e)` - 由 Δv 反解起始質量
- `propellant_mass_from_delta_v(m0, delta_v, v_e)` - 由 Δv 計算推進劑質量
- `instantaneous_acceleration(F, D, m, g)` - 瞬時加速度
- `specific_impulse_altitude_dependent(F_h, mdot, g0)` - 高度相關比衝

### 7.2) 推進熱力學進階
- `exhaust_velocity_isentropic(c_p, T_c, p_e, p_c, gamma)` - 等熵出口流速
- `mixed_gas_cp(n_moles, cp_values)` - 混合氣體定壓比熱
- `mixed_gas_gamma(C_p_mix, R)` - 混合氣體比熱比
- `propulsion_efficiency(I_sp_actual, I_sp_ideal)` - 推進效率
- `nozzle_efficiency(v_e_actual, v_e_ideal)` - 噴管效率
- `combustion_efficiency(c_star_actual, c_star_ideal)` - 燃燒效率

### 7.3) 燃燒化學與混合比
- `oxidizer_fuel_ratio(m_ox, m_f)` - 混合比 O/F
- `reaction_enthalpy_change(nu_i, h_f0_i)` - 反應焓變
- `mass_flow_from_density(rho_e, v_e, A_e)` - 由密度計算質量流率

### 8) 電推進
- `kinetic_power(mdot, v_e)` - 動能功率
- `electric_thrust_from_power(eta, P_in, v_e)` - 電推進推力
- `exhaust_velocity_ion(q, V_acc, m_i)` - 離子推進排氣速度
- `propellant_mass_electric(m_d, delta_v, I_sp, g0)` - 電推進推進劑質量
- `pulse_impulse_bit(I_b, f)` - 脈衝平均推力

### 8.1) 電推進進階
- `electric_propulsion_thrust(eta_T, mdot, v_e)` - 電推進總推力（含效率）
- `electric_propulsion_efficiency(eta_e, eta_m, eta_c)` - 電推進總效率分解
- `electric_thermal_exhaust_velocity(c_p, T_e, T_a)` - 電熱式排氣速度
- `electromagnetic_thrust_approx(B, mu_0, A)` - 電磁式推力近似
- `pulsed_inductive_thrust(E_p, v_e, delta_t)` - 脈衝感應推進器推力
- `pulsed_inductive_avg_thrust(F_pulse, f)` - 脈衝感應平均推力
- `pulse_impulse_bit_integral(F_t, t)` - 脈衝衝量位元（積分）
- `pulse_specific_impulse(I_b, m_b, g0)` - 脈衝比衝

### 9) 核熱推進
- `nuclear_thermal_power(mdot, c_p, T_hot, T_in)` - 核熱功率

### 9.1) 核熱推進進階
- `nuclear_thermal_exhaust_velocity(gamma, R, T_h)` - 核熱推進排氣速度
- `nuclear_electric_power(eta_gen, P_nuclear)` - 核電推進功率
- `nuclear_pulse_thrust_power(F, v_e)` - 核脈衝推力與功率
- `nuclear_pulse_isp_proportional(E_pulse, mdot_p, g0, C)` - 核脈衝比衝

### 10) 核脈衝/外部脈衝
- `nuclear_pulse_isp(C_0, V_e, g0)` - 核脈衝比衝

### 11) 渦輪泵/流體機械
- `pump_power(delta_p, V_dot, eta_pump)` - 泵功率
- `volume_flow_rate(mdot, rho)` - 體積流率
- `darcy_weisbach_pressure_drop(f, L, D, rho, V)` - Darcy-Weisbach 壓降

### 12) 控制/導航
- `pid_control(Kp, Ki, Kd, e, e_int, e_dot)` - PID 控制
- `state_space_output(A, B, C, D, x, u)` - 狀態空間輸出
- `lqr_gain(A, B, Q, R)` - LQR 增益（需 scipy）

### 13) 系統工程
- `tolerance_rss(tolerances)` - RSS 公差堆疊
- `reliability_series(reliabilities)` - 串聯可靠度
- `reliability_parallel(reliabilities)` - 並聯可靠度
- `thermal_expansion(alpha, L, delta_T)` - 熱膨脹
- `mass_budget(m_dry, m_prop, m_payload)` - 質量預算

### 14) 6-DoF 動力學擴充
- `mass_rate_change(mdot_fuel)` - 質量變化率
- `center_of_gravity_position(r_positions, dm, m_total)` - 重心位置

### 15) 最優控制與軌跡最佳化
- `hamiltonian(lambda_vec, f_xu, L)` - Hamiltonian
- `low_thrust_cost_function(u_t, t)` - 低推力成本函數（L1 範數）

### 16) 多學科設計優化 (MDO)
- `mdo_objective_function(x, weights, objectives)` - MDO 目標函數
- `mdo_constraint_violation(g)` - MDO 約束違反量

### 17) 燃料燃燒與 regression rate
- `hybrid_regression_rate(a, G, n)` - 混合火箭 regression rate
- `mass_consumption_rate(rho_fuel, r_dot, A_burn)` - 質量消耗率

### 18) 能量分析
- `kinetic_energy(m, v)` - 動能
- `kinetic_power_from_thrust(F, v_e)` - 推力動能功率
- `energy_conservation_ideal(mdot, v_e, P_source)` - 理想能量守恆
- `total_enthalpy_balance(mdot_e, h_t, V_e, mdot_f, delta_H_r)` - 總焓平衡

## 範例

完整使用範例請參考 `engineering_formulas_example.py`。

## 參考文獻

公式來源主要基於：
- NASA 技術報告與手冊
- 標準工程手冊（Anderson, Sutton-Graves, etc.）
- 公開學術文獻

### 24) 特徵速度理論公式
- `characteristic_velocity_theoretical(gamma, R, T_c)` - 特徵速度理論值
- `isp_from_cf_cstar(c_F, c_star, g0)` - 比衝與推力係數、特徵速度關係

### 25) 阻力分解
- `drag_skin_friction(C_f, S_wet, q)` - 皮膚摩擦阻力
- `drag_form(C_D0, S_ref, q)` - 形狀阻力
- `drag_wave(C_D_wave, S_ref, q)` - 波阻力（超音速）
- `drag_induced(k, C_L, S_ref, q)` - 誘導阻力
- `total_drag_decomposed(...)` - 總阻力分解

### 26) 實際 Δv 損失
- `delta_v_drag_loss(D, m, t)` - 阻力損失積分
- `delta_v_gravity_loss(g, gamma, t)` - 重力損失積分
- `delta_v_real(delta_v_ideal, delta_v_drag, delta_v_gravity)` - 實際 Δv

### 27) 質量比與燃料效率
- `mass_ratio(m0, mf)` - 質量比
- `propellant_fraction(m_prop, m0)` - 推進劑分數

### 28) 火箭瞬時質量模型
- `mass_linear_burnout(m0, mf, t, t_b)` - 線性燃燒質量模型
- `velocity_with_gravity(I_sp, g0, m0, m, t)` - 含重力修正的速度

### 29) 推進能量轉換
- `combustion_heat_power(mdot_f, delta_H_r)` - 燃燒熱功率
- `exhaust_kinetic_power(mdot, v_e)` - 排氣動能功率
- `propulsion_energy_efficiency(P_k, Q_comb)` - 推進能量效率

### 30) Oberth 效應
- `oberth_effect_delta_v(mu, r1, r2, v_at_r1)` - Oberth 效應 Δv 增益

### 31) 推重比與起飛性能
- `takeoff_capability(T_W, g0)` - 起飛能力判斷
- `acceleration_from_twr(T_W, g0, D_W)` - 由推重比計算加速度

### 32) 多級火箭質量分配
- `stage_mass_allocation(m0_i, m_i, m_i_plus_1)` - 級間質量分配

### 33) 固體火箭 regression rate
- `solid_regression_rate(a, G, n)` - 固體火箭 regression rate

### 34) 相對論火箭方程
- `relativistic_rocket_equation(v_e, c, m0, mf)` - 相對論火箭方程（極端情況）

### 35) 最大高度估算
- `max_altitude_simplified(g, t_b, I_sp, m0, mf)` - 最大高度估算（簡化）

---

## Von Kármán (馮·卡門) 與 Tsien (錢學森) 理論模組

新增 `von_karman_tsien_theory.py` 模組，包含兩位大師的核心理論：

### Von Kármán 理論
- **幾何設計**：Von Kármán 頭錐、Sears-Haack Body
- **氣動理論**：升力線理論、Kármán-Tsien 可壓縮性修正
- **邊界層**：von Kármán 動量積分方程
- **渦街**：Kármán Vortex Street 頻率
- **超音速**：斜激波、Prandtl-Meyer 展開
- **噴管**：臨界質量流率（卡門校正）
- **結構**：Kármán-Donnell 圓柱殼屈曲
- **卡門線**：100 km 高度定義

### Tsien (錢學森) 理論
- **可壓縮邊界層**：動量與能量方程
- **錢學森彈道**：三方程系統（速度、航跡角、高度、質量）
- **薄殼屈曲**：圓柱殼軸向壓縮屈曲
- **工程控制論**：狀態空間模型、回授控制、解耦控制
- **高超音速**：再入熱流估算
- **噴管設計**：面積-馬赫數關係

### 設計流程框架
`AerospaceDesignFramework` 類實現完整的設計循環：
1. Step 0: 任務需求定義
2. Step 1: 幾何初始設計
3. Step 2: 氣動設計
4. Step 3: 推進系統設計
5. Step 4: 結構設計
6. Step 5: 軌跡分析
7. Step 6: 控制設計
8. Step 7: 系統整合與迭代優化

使用範例請參考 `von_karman_tsien_example.py`。

---

**注意**：本公式庫用於教育與概念設計，實際工程應用需依專案需求進行驗證與修正。
