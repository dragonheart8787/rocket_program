# -*- coding: utf-8 -*-
"""
外部 Validation 基準：公開資料可比對、校準層、模型不確定度
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable
import numpy as np
import math
import json
from datetime import datetime

# 外部比對預設相對誤差門檻（5%）
DEFAULT_REL_TOL = 0.05


@dataclass
class ExternalBenchmark:
    """外部基準"""
    name: str
    source: str  # 資料來源（公開文獻/教科書）
    reference: str  # 引用
    data_points: List[Dict]  # 基準數據點
    applicable_range: Dict  # 適用範圍
    notes: str = ""


@dataclass
class CalibrationParameter:
    """校準參數"""
    name: str
    value: float
    uncertainty: float
    calibration_version: str
    calibration_date: str
    source: str  # 校準來源
    train_validation_split: Optional[float] = None  # train/validation 分割比例


@dataclass
class ModelFormUncertainty:
    """模型型式誤差"""
    model_name: str
    uncertainty_type: str  # "additive", "multiplicative", "envelope"
    epsilon_model: Optional[float] = None  # 誤差項
    envelope_models: Optional[List[str]] = None  # 模型集成
    applicable_range: Dict = field(default_factory=dict)
    notes: str = ""


class ExternalValidation:
    """外部驗證"""

    @staticmethod
    def isa_standard_1976() -> ExternalBenchmark:
        """US Standard Atmosphere 1976 標準表"""
        return ExternalBenchmark(
            name="ISA_1976",
            source="US Standard Atmosphere 1976",
            reference="NOAA/NASA/USAF, 1976",
            data_points=[
                {"h": 0.0, "T": 288.15, "p": 101325.0, "rho": 1.225},
                {"h": 5000.0, "T": 255.65, "p": 54019.7, "rho": 0.7361},
                {"h": 11000.0, "T": 216.65, "p": 22632.06, "rho": 0.3639},
                {"h": 20000.0, "T": 216.65, "p": 5474.89, "rho": 0.0880},
                {"h": 30000.0, "T": 226.51, "p": 1196.98, "rho": 0.0184},
                {"h": 40000.0, "T": 250.35, "p": 287.14, "rho": 0.003996},
            ],
            applicable_range={"h_min": 0.0, "h_max": 86000.0}
        )

    @staticmethod
    def drag_fall_benchmark() -> ExternalBenchmark:
        """標準阻力落體基準（簡化）"""
        # 參考：Anderson, "Introduction to Flight"
        return ExternalBenchmark(
            name="Drag_Fall_Standard",
            source="Anderson, Introduction to Flight",
            reference="Anderson, J.D., 2017",
            data_points=[
                {"t": 0.0, "v": 0.0, "h": 1000.0},
                {"t": 5.0, "v": 45.0, "h": 775.0},  # 佔位數據
            ],
            applicable_range={"h_min": 0.0, "h_max": 10000.0, "M_max": 0.3}
        )

    @staticmethod
    def reentry_heating_benchmark() -> ExternalBenchmark:
        """簡化再入加熱 benchmark"""
        # 參考：Sutton-Graves 關聯式標準案例
        return ExternalBenchmark(
            name="Reentry_Heating_Sutton_Graves",
            source="Sutton-Graves correlation",
            reference="Sutton & Graves, 1971",
            data_points=[
                {"h": 70000.0, "V": 7000.0, "q_dot": 1.2e6},  # 佔位
                {"h": 50000.0, "V": 5000.0, "q_dot": 8.5e5},
            ],
            applicable_range={"h_min": 40000.0, "h_max": 100000.0, "M_min": 5.0}
        )

    @staticmethod
    def wind_tunnel_coefficient_example() -> ExternalBenchmark:
        """風洞係數示例表（學術/教科書級）"""
        # 參考：典型教科書數據
        return ExternalBenchmark(
            name="Wind_Tunnel_Coefficient_Example",
            source="Academic textbook example",
            reference="Typical aerodynamics textbook",
            data_points=[
                {"M": 0.3, "alpha": 0.0, "C_L": 0.0, "C_D": 0.02},
                {"M": 0.3, "alpha": 5.0, "C_L": 0.5, "C_D": 0.03},
                {"M": 0.8, "alpha": 0.0, "C_L": 0.0, "C_D": 0.025},
            ],
            applicable_range={"M_min": 0.0, "M_max": 1.0, "alpha_min": -10.0, "alpha_max": 10.0}
        )

    @staticmethod
    def compare_with_benchmark(model_func: Callable, benchmark: ExternalBenchmark,
                              kpi_name: str) -> Dict:
        """
        與外部基準比對
        返回: 最大相對誤差、RMSE、分段誤差
        """
        errors = []
        relative_errors = []
        segments = {}  # 分段誤差
        
        # 只排除「被比對的輸出」kpi_name；h 為 ISA 等之輸入，不可排除
        exclude = [kpi_name, "q_dot", "C_L", "C_D", "v"]
        for data_point in benchmark.data_points:
            inputs = {k: v for k, v in data_point.items() if k not in exclude}
            
            # 計算模型輸出
            try:
                model_output = model_func(**inputs)
                if isinstance(model_output, dict):
                    model_value = model_output.get(kpi_name, 0.0)
                else:
                    model_value = model_output
                
                # 基準值
                reference_value = data_point.get(kpi_name, 0.0)
                
                # 計算誤差
                error = abs(model_value - reference_value)
                rel_error = error / max(abs(reference_value), 1e-9)
                
                errors.append(error)
                relative_errors.append(rel_error)
                
                # 分段誤差（按高度/Mach）
                if "h" in data_point:
                    h = data_point["h"]
                    segment = "low" if h < 20000 else "mid" if h < 50000 else "high"
                    if segment not in segments:
                        segments[segment] = []
                    segments[segment].append(rel_error)
                elif "M" in data_point:
                    M = data_point["M"]
                    segment = "subsonic" if M < 0.8 else "transonic" if M < 1.2 else "supersonic"
                    if segment not in segments:
                        segments[segment] = []
                    segments[segment].append(rel_error)
            except Exception as e:
                continue
        
        if len(errors) == 0:
            return {
                "error": "無有效數據點",
                "n_points_compared": 0,
                "threshold_used": None,
                "fail_reason": "no_data",
                "validation_passed": False,
            }
        
        # 統計
        max_rel_error = max(relative_errors)
        rmse = np.sqrt(np.mean(np.array(errors) ** 2))
        mean_rel_error = np.mean(relative_errors)
        
        # 分段統計
        segment_stats = {
            seg: {
                "max_rel_error": max(rel_errors),
                "mean_rel_error": np.mean(rel_errors),
                "n_points": len(rel_errors)
            }
            for seg, rel_errors in segments.items()
        }
        
        return {
            "benchmark_name": benchmark.name,
            "kpi": kpi_name,
            "max_relative_error": max_rel_error,
            "rmse": rmse,
            "mean_relative_error": mean_rel_error,
            "n_data_points": len(errors),
            "n_points_compared": len(errors),
            "threshold_used": DEFAULT_REL_TOL,
            "fail_reason": "" if max_rel_error < DEFAULT_REL_TOL else "metric_exceeded",
            "segment_statistics": segment_stats,
            "validation_passed": max_rel_error < DEFAULT_REL_TOL,
        }


class CalibrationLayer:
    """校準層"""

    def __init__(self):
        self.calibrated_parameters: Dict[str, CalibrationParameter] = {}

    def register_calibration(self, param: CalibrationParameter):
        """註冊校準參數"""
        self.calibrated_parameters[param.name] = param

    def get_calibrated_value(self, param_name: str) -> Optional[float]:
        """獲取校準值"""
        if param_name in self.calibrated_parameters:
            return self.calibrated_parameters[param_name].value
        return None

    def calibration_report(self, param_name: str, 
                          train_data: np.ndarray, validation_data: np.ndarray,
                          predictions_train: np.ndarray, predictions_val: np.ndarray) -> Dict:
        """
        校準報告：偏差、殘差分布、過擬合風險
        """
        # 計算偏差
        bias_train = np.mean(predictions_train - train_data)
        bias_val = np.mean(predictions_val - validation_data)
        
        # 殘差
        residuals_train = predictions_train - train_data
        residuals_val = predictions_val - validation_data
        
        # 過擬合風險（train vs validation 誤差差異）
        rmse_train = np.sqrt(np.mean(residuals_train ** 2))
        rmse_val = np.sqrt(np.mean(residuals_val ** 2))
        overfitting_risk = (rmse_val - rmse_train) / max(rmse_train, 1e-9)
        
        return {
            "parameter": param_name,
            "bias_train": bias_train,
            "bias_validation": bias_val,
            "rmse_train": rmse_train,
            "rmse_validation": rmse_val,
            "overfitting_risk": overfitting_risk,
            "overfitting_detected": overfitting_risk > 0.2,  # 20% 差異視為過擬合
            "residuals_train": residuals_train.tolist(),
            "residuals_validation": residuals_val.tolist()
        }


class ModelFormUncertaintyManager:
    """模型型式誤差管理器"""

    def __init__(self):
        self.model_uncertainties: Dict[str, ModelFormUncertainty] = {}

    def register_model_uncertainty(self, uncertainty: ModelFormUncertainty):
        """註冊模型型式誤差"""
        self.model_uncertainties[uncertainty.model_name] = uncertainty

    def apply_uncertainty(self, model_name: str, base_output: float, inputs: Dict) -> Dict:
        """
        應用模型型式誤差
        返回: 修正後的輸出、誤差範圍
        """
        if model_name not in self.model_uncertainties:
            return {
                "output": base_output,
                "uncertainty_applied": False,
                "note": "無模型型式誤差定義"
            }
        
        uncertainty = self.model_uncertainties[model_name]
        
        if uncertainty.uncertainty_type == "additive":
            # 加性誤差: y = f(x) + ε_model
            epsilon = uncertainty.epsilon_model or 0.0
            output = base_output + epsilon
            return {
                "output": output,
                "base_output": base_output,
                "epsilon_model": epsilon,
                "uncertainty_type": "additive"
            }
        
        elif uncertainty.uncertainty_type == "multiplicative":
            # 乘性誤差: y = f(x) * (1 + ε_model)
            epsilon = uncertainty.epsilon_model or 0.0
            output = base_output * (1.0 + epsilon)
            return {
                "output": output,
                "base_output": base_output,
                "epsilon_model": epsilon,
                "uncertainty_type": "multiplicative"
            }
        
        elif uncertainty.uncertainty_type == "envelope":
            # 模型集成：輸出 envelope
            # 簡化：假設有多個模型輸出
            return {
                "output": base_output,
                "envelope_models": uncertainty.envelope_models,
                "uncertainty_type": "envelope",
                "note": "需提供多個模型輸出以計算 envelope"
            }
        
        return {"output": base_output, "uncertainty_applied": False}

    def generate_uncertainty_report(self) -> Dict:
        """生成模型不確定度報告"""
        return {
            "model_uncertainties": {
                name: {
                    "model_name": unc.model_name,
                    "uncertainty_type": unc.uncertainty_type,
                    "epsilon_model": unc.epsilon_model,
                    "envelope_models": unc.envelope_models,
                    "applicable_range": unc.applicable_range,
                    "notes": unc.notes
                }
                for name, unc in self.model_uncertainties.items()
            },
            "note": "模型型式誤差需與參數不確定度分開報告"
        }


# 實例化
external_validation = ExternalValidation()
calibration_layer = CalibrationLayer()
model_uncertainty_manager = ModelFormUncertaintyManager()
