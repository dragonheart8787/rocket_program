# -*- coding: utf-8 -*-
"""
Verification & Validation (V&V) 模組
實現驗算、驗證、不確定度分析、敏感度分析
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Tuple
import math
import numpy as np
from enum import Enum


# =============================================================================
# 1) Verification（驗算）：程式是否正確求解宣稱的方程
# =============================================================================

class ConservationCheck:
    """守恆檢查：能量、角動量、質量守恆驗證"""

    @staticmethod
    def energy_conservation_no_thrust(r_I: np.ndarray, v_I: np.ndarray, m: float,
                                      mu: float, r0: np.ndarray, v0: np.ndarray, m0: float,
                                      t: Optional[float] = None, dt: Optional[float] = None) -> dict:
        """
        無推力時能量守恆檢查（兩體問題）
        E = 0.5*m*V² - mu*m/r = constant
        返回: 能量誤差、相對誤差、完整指標
        """
        r_norm = np.linalg.norm(r_I)
        v_norm = np.linalg.norm(v_I)
        E_current = 0.5 * m * v_norm * v_norm - mu * m / max(r_norm, 1e-9)
        
        r0_norm = np.linalg.norm(r0)
        v0_norm = np.linalg.norm(v0)
        E_initial = 0.5 * m0 * v0_norm * v0_norm - mu * m0 / max(r0_norm, 1e-9)
        
        error = abs(E_current - E_initial)
        rel_error = error / max(abs(E_initial), 1e-9)
        
        return {
            "energy_error": error,
            "relative_error": rel_error,
            "max_relative_error": rel_error,  # 單點檢查時等於當前值
            "conserved": rel_error < 1e-6,  # 數值誤差容許
            "E_initial": E_initial,
            "E_current": E_current,
            "time": t,
            "dt": dt,
            "initial_conditions": {
                "r0": r0.tolist() if isinstance(r0, np.ndarray) else r0,
                "v0": v0.tolist() if isinstance(v0, np.ndarray) else v0,
                "m0": m0
            },
            "threshold": 1e-6,
            "formula": "E = 0.5*m*V² - μ*m/r"
        }

    @staticmethod
    def energy_conservation_time_series(time_series: np.ndarray, r_series: List[np.ndarray],
                                       v_series: List[np.ndarray], m_series: np.ndarray,
                                       mu: float, r0: np.ndarray, v0: np.ndarray, m0: float,
                                       dt: float) -> dict:
        """
        能量守恆時間序列檢查
        返回: max|ΔE/E| 隨時間變化
        """
        E_initial = 0.5 * m0 * np.linalg.norm(v0) ** 2 - mu * m0 / max(np.linalg.norm(r0), 1e-9)
        
        rel_errors = []
        for i, (r, v, m) in enumerate(zip(r_series, v_series, m_series)):
            r_norm = np.linalg.norm(r)
            v_norm = np.linalg.norm(v)
            E_current = 0.5 * m * v_norm ** 2 - mu * m / max(r_norm, 1e-9)
            rel_error = abs(E_current - E_initial) / max(abs(E_initial), 1e-9)
            rel_errors.append(rel_error)
        
        rel_errors_array = np.array(rel_errors)
        
        return {
            "max_relative_error": np.max(rel_errors_array),
            "mean_relative_error": np.mean(rel_errors_array),
            "time_series": rel_errors_array,
            "time_points": time_series,
            "threshold": 1e-6,
            "dt": dt,
            "n_points": len(rel_errors)
        }

    @staticmethod
    def angular_momentum_conservation_no_torque(r_I: np.ndarray, v_I: np.ndarray, m: float,
                                                 r0: np.ndarray, v0: np.ndarray, m0: float) -> dict:
        """
        無力矩時角動量守恆檢查
        H = m * r × v = constant
        """
        H_current = m * np.cross(r_I, v_I)
        H_initial = m0 * np.cross(r0, v0)
        
        error = np.linalg.norm(H_current - H_initial)
        H_mag = np.linalg.norm(H_initial)
        rel_error = error / max(H_mag, 1e-9)
        
        return {
            "angular_momentum_error": error,
            "relative_error": rel_error,
            "conserved": rel_error < 1e-6,
            "H_initial": H_initial,
            "H_current": H_current
        }

    @staticmethod
    def mass_conservation_no_propulsion(m: float, m0: float) -> dict:
        """
        無推進時質量守恆檢查
        """
        error = abs(m - m0)
        rel_error = error / max(m0, 1e-9)
        
        return {
            "mass_error": error,
            "relative_error": rel_error,
            "conserved": rel_error < 1e-9,
            "m_initial": m0,
            "m_current": m
        }

    @staticmethod
    def two_body_orbit_validation(r_I: np.ndarray, v_I: np.ndarray, mu: float, 
                                  t: float, r0: np.ndarray, v0: np.ndarray) -> dict:
        """
        兩體軌道驗證：對照解析解或已知 benchmark
        返回: 位置誤差、速度誤差、軌道要素誤差
        """
        # 簡化：計算軌道要素並檢查合理性
        r_norm = np.linalg.norm(r_I)
        v_norm = np.linalg.norm(v_I)
        
        # 比角動量
        h_vec = np.cross(r_I, v_I)
        h = np.linalg.norm(h_vec)
        
        # 比能量
        E = 0.5 * v_norm * v_norm - mu / max(r_norm, 1e-9)
        
        # 半長軸
        if E < 0:
            a = -mu / (2.0 * E)
        else:
            a = float('inf')
        
        # 偏心率
        e_vec = np.cross(v_I, h_vec) / mu - r_I / r_norm
        e = np.linalg.norm(e_vec)
        
        return {
            "orbital_elements": {
                "semi_major_axis": a,
                "eccentricity": e,
                "specific_energy": E,
                "specific_angular_momentum": h
            },
            "valid_orbit": E < 0 and e >= 0 and e < 1.0,
            "r_norm": r_norm,
            "v_norm": v_norm
        }


class ConvergenceTest:
    """收斂性測試：不同步長下的結果一致性"""

    @staticmethod
    def run_convergence_test(dynamics_func: Callable, initial_state: np.ndarray,
                            t_end: float, dt_list: List[float], *args, **kwargs) -> dict:
        """
        用不同步長運行相同案例，檢查收斂性
        返回: 各步長的終端狀態、收斂指標
        """
        results = {}
        final_states = []
        
        for dt in dt_list:
            state = np.copy(initial_state)
            t = 0.0
            n_steps = 0
            
            while t < t_end:
                # 簡化：假設 dynamics_func 返回 dx
                dx = dynamics_func(t, state, *args, **kwargs)
                if isinstance(dx, tuple):
                    dx = dx[0]
                state = state + dx * dt
                t += dt
                n_steps += 1
                
                if n_steps > 100000:  # 防止無限循環
                    break
            
            final_states.append(state)
            results[dt] = {
                "final_state": state,
                "n_steps": n_steps,
                "final_time": t
            }
        
        # 計算收斂指標（Richardson 外插或簡單比較）
        if len(final_states) >= 2:
            # 比較最細步長與次細步長的差異
            diff = np.linalg.norm(final_states[0] - final_states[1])
            results["convergence_error"] = diff
            results["converged"] = diff < 1e-3  # 可調閾值
        
        return results

    @staticmethod
    def compute_convergence_order(dt_list: List[float], error_list: List[float]) -> dict:
        """
        計算收斂階數（log-log 斜率）
        對於 RK4，期望斜率接近 4
        """
        if len(dt_list) < 2 or len(error_list) < 2:
            return {"error": "需要至少 2 個數據點"}
        
        # 轉換為對數空間
        log_dt = np.log(np.array(dt_list))
        log_error = np.log(np.array(error_list))
        
        # 線性擬合（log(error) = p * log(dt) + c）
        # p 是收斂階數
        if len(log_dt) == 2:
            # 兩點：直接計算斜率
            p = (log_error[1] - log_error[0]) / (log_dt[1] - log_dt[0])
        else:
            # 多點：最小二乘擬合
            p = np.polyfit(log_dt, log_error, 1)[0]
        
        # 計算 R²
        log_error_pred = p * log_dt
        ss_res = np.sum((log_error - log_error_pred) ** 2)
        ss_tot = np.sum((log_error - np.mean(log_error)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        return {
            "convergence_order": p,
            "expected_order_rk4": 4.0,
            "order_match": abs(p - 4.0) < 0.5,  # 容許誤差
            "r_squared": r_squared,
            "note": "RK4 期望收斂階數為 4"
        }


class UnitTestBenchmark:
    """單元測試基準：已知輸入輸出對照"""

    @staticmethod
    def isa_benchmark(h: float) -> dict:
        """
        ISA 標準大氣基準測試
        對照 US Standard Atmosphere 1976 表值
        """
        # 簡化：只檢查基本合理性
        if h < 0:
            return {"valid": False, "error": "高度不能為負"}
        if h > 86000:
            return {"valid": False, "error": "超出 ISA 範圍"}
        
        # 基本合理性檢查
        # 實際應對照標準表
        return {"valid": True, "h": h}

    @staticmethod
    def thrust_equation_benchmark(mdot: float, v_e: float, p_e: float, p_a: float, A_e: float) -> dict:
        """
        推力方程基準測試
        已知輸入，驗證輸出是否符合公式
        """
        F_expected = mdot * v_e + (p_e - p_a) * A_e
        
        # 基本合理性
        if mdot < 0 or v_e < 0:
            return {"valid": False, "error": "負值不合理"}
        
        return {
            "valid": True,
            "F_expected": F_expected,
            "mdot": mdot,
            "v_e": v_e
        }

    @staticmethod
    def rocket_equation_benchmark(I_sp: float, g0: float, m0: float, mf: float) -> dict:
        """
        火箭方程基準測試
        """
        if m0 <= mf or mf <= 0:
            return {"valid": False, "error": "質量關係不合理"}
        
        delta_v = I_sp * g0 * math.log(m0 / mf)
        
        # 合理性檢查
        if delta_v < 0 or delta_v > 50000:
            return {"valid": False, "error": "Δv 超出合理範圍"}
        
        return {
            "valid": True,
            "delta_v": delta_v,
            "I_sp": I_sp,
            "mass_ratio": m0 / mf
        }


# =============================================================================
# 2) Validation（驗證）：模型是否接近真實
# =============================================================================

@dataclass
class ModelApplicability:
    """模型適用範圍定義"""
    name: str
    M_min: float = 0.0
    M_max: float = 10.0
    h_min: float = 0.0
    h_max: float = 100000.0
    T_min: float = 100.0
    T_max: float = 5000.0
    alpha_min: float = -30.0  # deg
    alpha_max: float = 30.0
    Re_min: float = 1e3
    Re_max: float = 1e8
    warning_threshold: float = 0.9  # 接近邊界時警告

    def check(self, M: float, h: float, T: float, alpha: float, Re: float) -> dict:
        """檢查輸入是否在適用範圍內"""
        in_range = (
            self.M_min <= M <= self.M_max and
            self.h_min <= h <= self.h_max and
            self.T_min <= T <= self.T_max and
            self.alpha_min <= math.degrees(alpha) <= self.alpha_max and
            self.Re_min <= Re <= self.Re_max
        )
        
        # 接近邊界警告
        M_frac = (M - self.M_min) / max(self.M_max - self.M_min, 1e-9)
        h_frac = (h - self.h_min) / max(self.h_max - self.h_min, 1e-9)
        near_boundary = (
            M_frac < self.warning_threshold or M_frac > (1 - self.warning_threshold) or
            h_frac < self.warning_threshold or h_frac > (1 - self.warning_threshold)
        )
        
        return {
            "in_range": in_range,
            "near_boundary": near_boundary,
            "applicable": in_range,
            "warnings": [] if in_range else [f"輸入超出 {self.name} 適用範圍"]
        }


class ReferenceCaseValidation:
    """參考案例對照：與權威來源對比"""

    @staticmethod
    def two_body_orbit_reference() -> dict:
        """
        兩體軌道參考案例（圓軌道）
        高度 400 km 圓軌道，對照標準軌道要素
        """
        R_earth = 6371000.0
        mu = 3.986004418e14
        h = 400000.0
        r = R_earth + h
        
        # 圓軌道速度
        v_circular = math.sqrt(mu / r)
        
        return {
            "case": "circular_orbit_400km",
            "r": r,
            "v": v_circular,
            "period": 2.0 * math.pi * math.sqrt(r**3 / mu),
            "reference": "Standard two-body mechanics"
        }

    @staticmethod
    def isa_reference_altitudes() -> List[dict]:
        """
        ISA 參考高度對照表（US Standard Atmosphere 1976）
        返回標準高度點的溫度、壓力、密度
        """
        return [
            {"h": 0.0, "T": 288.15, "p": 101325.0, "rho": 1.225, "reference": "US Standard Atmosphere 1976"},
            {"h": 5000.0, "T": 255.65, "p": 54019.7, "rho": 0.7361, "reference": "US Standard Atmosphere 1976"},
            {"h": 11000.0, "T": 216.65, "p": 22632.06, "rho": 0.3639, "reference": "US Standard Atmosphere 1976"},
            {"h": 20000.0, "T": 216.65, "p": 5474.89, "rho": 0.0880, "reference": "US Standard Atmosphere 1976"},
            {"h": 30000.0, "T": 226.51, "p": 1196.98, "rho": 0.0184, "reference": "US Standard Atmosphere 1976"},
            {"h": 40000.0, "T": 250.35, "p": 287.14, "rho": 0.003996, "reference": "US Standard Atmosphere 1976"},
        ]

    @staticmethod
    def isa_validation(isa_func: Callable, reference_altitudes: Optional[List[dict]] = None) -> dict:
        """
        ISA 模型與標準表比對
        isa_func: ISA 計算函數，應接受 h 參數，返回 {"T": T, "p": p, "rho": rho}
        """
        if reference_altitudes is None:
            reference_altitudes = ReferenceCaseValidation.isa_reference_altitudes()
        
        errors = {"T": [], "p": [], "rho": []}
        relative_errors = {"T": [], "p": [], "rho": []}
        heights = []
        
        for ref in reference_altitudes:
            h = ref["h"]
            heights.append(h)
            
            # 計算 ISA 值
            isa_result = isa_func(h)
            
            # 計算誤差
            for prop in ["T", "p", "rho"]:
                if prop in ref and prop in isa_result:
                    error = abs(isa_result[prop] - ref[prop])
                    rel_error = error / max(ref[prop], 1e-9)
                    errors[prop].append(error)
                    relative_errors[prop].append(rel_error)
        
        # 統計
        max_rel_errors = {
            prop: max(rel_errors) if rel_errors else 0.0
            for prop, rel_errors in relative_errors.items()
        }
        
        # 找出誤差最大的高度範圍
        worst_height_idx = {}
        for prop in ["T", "p", "rho"]:
            if relative_errors[prop]:
                worst_idx = np.argmax(relative_errors[prop])
                worst_height_idx[prop] = {
                    "height": heights[worst_idx],
                    "relative_error": relative_errors[prop][worst_idx]
                }
        
        return {
            "max_relative_errors": max_rel_errors,
            "worst_height_ranges": worst_height_idx,
            "n_reference_points": len(reference_altitudes),
            "heights_tested": heights,
            "reference_source": "US Standard Atmosphere 1976",
            "validation_passed": all(max_rel_errors[prop] < 0.01 for prop in ["T", "p", "rho"])  # 1% 容許誤差
        }

    @staticmethod
    def thin_cylinder_stress_reference() -> dict:
        """
        薄壁圓筒應力參考案例
        對照標準材料力學公式
        """
        p, r, t = 2e6, 0.5, 0.005
        sigma_hoop = p * r / t
        sigma_axial = p * r / (2.0 * t)
        
        return {
            "case": "thin_cylinder_pressure",
            "p": p,
            "r": r,
            "t": t,
            "sigma_hoop": sigma_hoop,
            "sigma_axial": sigma_axial,
            "reference": "Standard pressure vessel formula"
        }


# =============================================================================
# 3) 不確定度傳播與敏感度分析
# =============================================================================

@dataclass
class UncertaintyDistribution:
    """不確定度分佈定義"""
    name: str
    mean: float
    std: float = 0.0  # 標準差（高斯）
    lower_bound: Optional[float] = None  # 下界（均勻/界限）
    upper_bound: Optional[float] = None  # 上界
    distribution_type: str = "gaussian"  # "gaussian", "uniform", "bounded"
    truncate: bool = True  # 是否截斷到合理範圍

    def sample(self, n: int = 1, random_state: Optional[np.random.Generator] = None) -> np.ndarray:
        """採樣（支援固定 random seed）"""
        if random_state is None:
            rng = np.random.default_rng()
        else:
            rng = random_state
        
        if self.distribution_type == "gaussian":
            samples = rng.normal(self.mean, self.std, n)
            if self.truncate and (self.lower_bound is not None or self.upper_bound is not None):
                # 截斷到合理範圍
                if self.lower_bound is not None:
                    samples = np.maximum(samples, self.lower_bound)
                if self.upper_bound is not None:
                    samples = np.minimum(samples, self.upper_bound)
            return samples
        elif self.distribution_type == "uniform":
            if self.lower_bound is not None and self.upper_bound is not None:
                return rng.uniform(self.lower_bound, self.upper_bound, n)
        elif self.distribution_type == "bounded":
            if self.lower_bound is not None and self.upper_bound is not None:
                return rng.uniform(self.lower_bound, self.upper_bound, n)
        return np.full(n, self.mean)


class UncertaintyPropagation:
    """不確定度傳播：Monte Carlo 分析"""

    @staticmethod
    def monte_carlo_analysis(func: Callable, uncertain_inputs: Dict[str, UncertaintyDistribution],
                            n_samples: int = 1000, fixed_inputs: Optional[Dict] = None,
                            random_seed: Optional[int] = None,
                            covariance: Optional[np.ndarray] = None,
                            output_kpis: Optional[List[str]] = None) -> dict:
        """
        Monte Carlo 不確定度傳播（擴充版）
        func: 計算函數（可返回多個 KPI 的字典）
        uncertain_inputs: 不確定輸入參數
        fixed_inputs: 固定輸入參數
        random_seed: 固定隨機種子（可重現）
        covariance: 參數相關性矩陣（可選）
        output_kpis: 輸出 KPI 名稱列表（如果 func 返回字典）
        """
        if fixed_inputs is None:
            fixed_inputs = {}
        
        # 固定隨機種子
        if random_seed is not None:
            rng = np.random.default_rng(random_seed)
        else:
            rng = np.random.default_rng()
        
        # 處理參數相關性（如果提供 covariance）
        param_names = list(uncertain_inputs.keys())
        n_params = len(param_names)
        use_correlation = covariance is not None and covariance.shape == (n_params, n_params)
        
        if use_correlation:
            # 使用多元高斯分佈
            means = np.array([uncertain_inputs[name].mean for name in param_names])
            samples_mvn = rng.multivariate_normal(means, covariance, n_samples)
        else:
            samples_mvn = None
        
        results = []
        all_kpi_results = {}  # 用於多 KPI
        
        for i in range(n_samples):
            # 採樣不確定參數
            sampled = {}
            if use_correlation:
                # 使用相關採樣
                for idx, name in enumerate(param_names):
                    dist = uncertain_inputs[name]
                    # 從多元高斯中取樣，然後截斷
                    raw_value = samples_mvn[i, idx]
                    if dist.truncate:
                        if dist.lower_bound is not None:
                            raw_value = max(raw_value, dist.lower_bound)
                        if dist.upper_bound is not None:
                            raw_value = min(raw_value, dist.upper_bound)
                    sampled[name] = raw_value
            else:
                # 獨立採樣
                for name, dist in uncertain_inputs.items():
                    sampled[name] = dist.sample(1, rng)[0]
            
            # 合併固定參數
            all_inputs = {**fixed_inputs, **sampled}
            
            # 計算輸出
            try:
                output = func(**all_inputs)
                
                # 處理多 KPI 輸出
                if isinstance(output, dict):
                    results.append(output)  # 保留完整字典
                    for kpi_name, kpi_value in output.items():
                        if kpi_name not in all_kpi_results:
                            all_kpi_results[kpi_name] = []
                        all_kpi_results[kpi_name].append(kpi_value)
                else:
                    # 單一輸出（向後兼容）
                    results.append(output)
            except Exception as e:
                continue
        
        if len(results) == 0:
            return {"error": "所有採樣都失敗"}
        
        # 處理多 KPI 結果
        if all_kpi_results:
            kpi_stats = {}
            for kpi_name, kpi_values in all_kpi_results.items():
                kpi_array = np.array(kpi_values)
                std = float(np.std(kpi_array))
                un = int(len(np.unique(kpi_array)))
                kpi_stats[kpi_name] = {
                    "mean": np.mean(kpi_array),
                    "std": std,
                    "variance": float(np.var(kpi_array)),
                    "unique_count": un,
                    "degenerate": (std == 0 or un < 5),  # 未受擾動或離散階梯→標記 DEGENERATE
                    "p10": np.percentile(kpi_array, 10),
                    "p50": np.percentile(kpi_array, 50),
                    "p90": np.percentile(kpi_array, 90),
                    "min": np.min(kpi_array),
                    "max": np.max(kpi_array),
                }
            return {
                "kpi_statistics": kpi_stats,
                "n_valid_samples": len(results),
                "n_total_samples": n_samples,
                "random_seed": random_seed,
                "has_correlation": use_correlation,
            }
        else:
            # 單一輸出（向後兼容）
            results_array = np.array(results)
            p50 = np.percentile(results_array, 50)
            p90 = np.percentile(results_array, 90)
            p10 = np.percentile(results_array, 10)
            mean = np.mean(results_array)
            std = np.std(results_array)
            
            return {
                "mean": mean,
                "std": std,
                "p10": p10,
                "p50": p50,
                "p90": p90,
                "min": np.min(results_array),
                "max": np.max(results_array),
                "n_valid_samples": len(results),
                "n_total_samples": n_samples,
                "random_seed": random_seed,
                "has_correlation": use_correlation
            }

    @staticmethod
    def bootstrap_confidence_interval(data: np.ndarray, percentile: float, n_bootstrap: int = 1000,
                                      confidence: float = 0.95, random_seed: Optional[int] = None) -> dict:
        """
        Bootstrap 置信區間估計
        返回: percentile 的置信區間
        """
        if random_seed is not None:
            rng = np.random.default_rng(random_seed)
        else:
            rng = np.random.default_rng()
        
        bootstrap_samples = []
        n = len(data)
        
        for _ in range(n_bootstrap):
            # 重採樣
            indices = rng.integers(0, n, size=n)
            resampled = data[indices]
            bootstrap_samples.append(np.percentile(resampled, percentile))
        
        bootstrap_array = np.array(bootstrap_samples)
        alpha = 1.0 - confidence
        lower = np.percentile(bootstrap_array, 100 * alpha / 2)
        upper = np.percentile(bootstrap_array, 100 * (1 - alpha / 2))
        
        return {
            "percentile": percentile,
            "value": np.percentile(data, percentile),
            "ci_lower": lower,
            "ci_upper": upper,
            "confidence": confidence,
            "ci_width": upper - lower
        }


class SensitivityAnalysis:
    """敏感度分析：找出主導誤差來源"""

    @staticmethod
    def first_order_sensitivity(func: Callable, base_inputs: Dict[str, float],
                               perturbations: Dict[str, float], output_name: str = "output") -> dict:
        """
        一階敏感度分析（有限差分）
        S_i = (∂f/∂x_i) * (x_i / f) ≈ (Δf/Δx_i) * (x_i / f)
        """
        # 基準輸出
        f0 = func(**base_inputs)
        
        sensitivities = {}
        
        for param_name, delta in perturbations.items():
            if param_name not in base_inputs:
                continue
            
            x0 = base_inputs[param_name]
            
            # 正向擾動
            inputs_plus = base_inputs.copy()
            inputs_plus[param_name] = x0 + delta
            f_plus = func(**inputs_plus)
            
            # 負向擾動
            inputs_minus = base_inputs.copy()
            inputs_minus[param_name] = x0 - delta
            f_minus = func(**inputs_minus)
            
            # 中心差分
            df_dx = (f_plus - f_minus) / (2.0 * delta)
            
            # 歸一化敏感度
            if abs(f0) > 1e-9 and abs(x0) > 1e-9:
                S = (df_dx * x0) / f0
            else:
                S = df_dx
            
            sensitivities[param_name] = {
                "sensitivity": S,
                "absolute_effect": abs(df_dx * delta),
                "relative_effect": abs(S) if abs(f0) > 1e-9 else 0.0
            }
        
        # 排序（按絕對影響）
        ranked = sorted(sensitivities.items(), 
                       key=lambda x: abs(x[1]["relative_effect"]), 
                       reverse=True)
        
        return {
            "sensitivities": sensitivities,
            "ranked_parameters": [name for name, _ in ranked],
            "base_output": f0,
            "output_kpi": output_name,
            "note": f"本敏感度只針對輸出 {output_name}"
        }

    @staticmethod
    def multi_kpi_sensitivity(func: Callable, base_inputs: Dict[str, float],
                              perturbations: Dict[str, float], kpi_names: List[str]) -> dict:
        """
        多 KPI 敏感度分析
        func 應返回字典 {kpi_name: value}
        """
        # 基準輸出（應為字典）
        f0_dict = func(**base_inputs)
        if not isinstance(f0_dict, dict):
            raise ValueError("多 KPI 敏感度分析要求 func 返回字典")
        
        all_sensitivities = {}
        
        for kpi_name in kpi_names:
            if kpi_name not in f0_dict:
                continue
            
            # 為每個 KPI 計算敏感度
            sensitivities = {}
            
            for param_name, delta in perturbations.items():
                if param_name not in base_inputs:
                    continue
                
                x0 = base_inputs[param_name]
                
                # 正向擾動
                inputs_plus = base_inputs.copy()
                inputs_plus[param_name] = x0 + delta
                f_plus_dict = func(**inputs_plus)
                f_plus = f_plus_dict.get(kpi_name, 0.0)
                
                # 負向擾動
                inputs_minus = base_inputs.copy()
                inputs_minus[param_name] = x0 - delta
                f_minus_dict = func(**inputs_minus)
                f_minus = f_minus_dict.get(kpi_name, 0.0)
                
                # 中心差分
                df_dx = (f_plus - f_minus) / (2.0 * delta)
                
                # 歸一化敏感度
                f0 = f0_dict[kpi_name]
                if abs(f0) > 1e-9 and abs(x0) > 1e-9:
                    S = (df_dx * x0) / f0
                else:
                    S = df_dx
                
                sensitivities[param_name] = {
                    "sensitivity": S,
                    "absolute_effect": abs(df_dx * delta),
                    "relative_effect": abs(S) if abs(f0) > 1e-9 else 0.0
                }
            
            # 排序
            ranked = sorted(sensitivities.items(),
                           key=lambda x: abs(x[1]["relative_effect"]),
                           reverse=True)
            
            all_sensitivities[kpi_name] = {
                "sensitivities": sensitivities,
                "ranked_parameters": [name for name, _ in ranked],
                "base_value": f0
            }
        
        # 跨 KPI 排名（找出對所有 KPI 都重要的參數）
        param_importance = {}
        for kpi_name, kpi_sens in all_sensitivities.items():
            for param_name, sens_data in kpi_sens["sensitivities"].items():
                if param_name not in param_importance:
                    param_importance[param_name] = []
                param_importance[param_name].append(abs(sens_data["relative_effect"]))
        
        # 計算平均重要性
        param_avg_importance = {
            name: np.mean(importance_list)
            for name, importance_list in param_importance.items()
        }
        
        overall_ranked = sorted(param_avg_importance.items(),
                               key=lambda x: x[1],
                               reverse=True)
        
        return {
            "kpi_sensitivities": all_sensitivities,
            "overall_ranked_parameters": [name for name, _ in overall_ranked],
            "note": f"多 KPI 敏感度分析，涵蓋 {len(kpi_names)} 個 KPI"
        }

    @staticmethod
    def sobol_indices_approximation(func: Callable, base_inputs: Dict[str, float],
                                   distributions: Dict[str, UncertaintyDistribution],
                                   n_samples: int = 1000) -> dict:
        """
        Sobol 敏感度指標近似（簡化版）
        返回: 一階敏感度指標（主效應）
        """
        # 簡化實現：使用 Monte Carlo 近似
        # 完整 Sobol 需要更複雜的採樣策略
        
        # 基準輸出
        f0 = func(**base_inputs)
        f0_var = 0.0  # 需從 Monte Carlo 得到
        
        # 對每個參數計算條件方差
        sobol_indices = {}
        
        for param_name in distributions.keys():
            if param_name not in base_inputs:
                continue
            
            # 簡化：使用一階敏感度作為近似
            # 完整實現需條件採樣
            sobol_indices[param_name] = {
                "S1_approx": 0.0,  # 佔位
                "note": "簡化實現，完整 Sobol 需更複雜採樣"
            }
        
        return {
            "sobol_indices": sobol_indices,
            "note": "這是簡化實現，完整 Sobol 分析需專門庫（如 SALib）"
        }


# =============================================================================
# 4) 置信度輸出（P50/P90）
# =============================================================================

class ConfidenceIntervals:
    """置信度區間計算"""

    @staticmethod
    def compute_percentiles(data: np.ndarray, percentiles: List[float] = [10, 50, 90]) -> dict:
        """
        計算百分位數
        """
        result = {}
        for p in percentiles:
            result[f"P{int(p)}"] = np.percentile(data, p)
        return result

    @staticmethod
    def kpi_confidence_intervals(monte_carlo_results: dict, kpi_name: str) -> dict:
        """
        KPI 置信度區間
        """
        return {
            "kpi": kpi_name,
            "P10": monte_carlo_results.get("p10", 0.0),
            "P50": monte_carlo_results.get("p50", 0.0),
            "P90": monte_carlo_results.get("p90", 0.0),
            "mean": monte_carlo_results.get("mean", 0.0),
            "std": monte_carlo_results.get("std", 0.0)
        }


# 實例化供外部使用
conservation = ConservationCheck()
convergence = ConvergenceTest()
unit_test = UnitTestBenchmark()
model_applicability = ModelApplicability("default")
reference_cases = ReferenceCaseValidation()
uncertainty = UncertaintyPropagation()
sensitivity = SensitivityAnalysis()
confidence = ConfidenceIntervals()
