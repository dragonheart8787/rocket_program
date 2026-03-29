# -*- coding: utf-8 -*-
"""
載荷案例管理：最大動壓、最大過載、最大彎矩、熱梯度等
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import numpy as np
from enum import Enum


class LoadCaseType(Enum):
    """載荷案例類型"""
    MAX_Q = "max_dynamic_pressure"
    MAX_LOAD_FACTOR = "max_load_factor"
    MAX_BENDING = "max_bending_moment"
    THERMAL_GRADIENT = "thermal_gradient"
    LANDING_IMPACT = "landing_impact"
    VIBRATION = "vibration"
    COMBINED = "combined"


@dataclass
class LoadCase:
    """載荷案例定義"""
    name: str
    case_type: LoadCaseType
    description: str = ""
    # 載荷參數
    q_max: Optional[float] = None  # Pa
    n_max: Optional[float] = None  # g
    M_bend_max: Optional[float] = None  # N*m
    delta_T_max: Optional[float] = None  # K
    # 時間點或條件
    time: Optional[float] = None
    condition: Optional[str] = None  # "ascent", "descent", "max_q", etc.
    # 安全係數
    safety_factor: float = 1.5
    # 結果
    occurred: bool = False
    max_value: float = 0.0
    margin_of_safety: Optional[float] = None

    def check_condition(self, q: float, n: float, M_bend: float, delta_T: float) -> Dict:
        """檢查載荷條件"""
        violations = []
        
        if self.q_max and q > self.q_max:
            violations.append(f"動壓 {q/1000:.1f} kPa > 限制 {self.q_max/1000:.1f} kPa")
        
        if self.n_max and n > self.n_max:
            violations.append(f"過載 {n:.1f} g > 限制 {self.n_max:.1f} g")
        
        if self.M_bend_max and M_bend > self.M_bend_max:
            violations.append(f"彎矩 {M_bend/1000:.1f} kN*m > 限制 {self.M_bend_max/1000:.1f} kN*m")
        
        if self.delta_T_max and delta_T > self.delta_T_max:
            violations.append(f"熱梯度 {delta_T:.1f} K > 限制 {self.delta_T_max:.1f} K")
        
        return {
            "violated": len(violations) > 0,
            "violations": violations,
            "current_values": {
                "q": q, "n": n, "M_bend": M_bend, "delta_T": delta_T
            }
        }


class LoadCaseManager:
    """載荷案例管理器"""

    def __init__(self):
        self.load_cases: Dict[str, LoadCase] = {}
        self.history: List[Dict] = []

    def register_load_case(self, case: LoadCase):
        """註冊載荷案例"""
        self.load_cases[case.name] = case

    def create_standard_cases(self):
        """創建標準載荷案例"""
        # 最大動壓
        max_q = LoadCase(
            name="max_q",
            case_type=LoadCaseType.MAX_Q,
            description="最大動壓載荷",
            q_max=50000.0,  # Pa
            condition="ascent",
            safety_factor=1.5
        )
        self.register_load_case(max_q)
        
        # 最大過載
        max_n = LoadCase(
            name="max_load_factor",
            case_type=LoadCaseType.MAX_LOAD_FACTOR,
            description="最大過載",
            n_max=10.0,  # g
            condition="ascent",
            safety_factor=1.5
        )
        self.register_load_case(max_n)
        
        # 最大彎矩
        max_bend = LoadCase(
            name="max_bending",
            case_type=LoadCaseType.MAX_BENDING,
            description="最大彎矩",
            M_bend_max=10000.0,  # N*m
            condition="ascent",
            safety_factor=2.0
        )
        self.register_load_case(max_bend)
        
        # 熱梯度
        thermal = LoadCase(
            name="thermal_gradient",
            case_type=LoadCaseType.THERMAL_GRADIENT,
            description="最大熱梯度",
            delta_T_max=500.0,  # K
            condition="reentry",
            safety_factor=1.2
        )
        self.register_load_case(thermal)

    def evaluate_all_cases(self, q: float, n: float, M_bend: float, delta_T: float, t: float) -> Dict:
        """評估所有載荷案例"""
        results = {}
        any_violation = False
        
        for name, case in self.load_cases.items():
            check = case.check_condition(q, n, M_bend, delta_T)
            results[name] = check
            
            if check["violated"]:
                any_violation = True
                case.occurred = True
                # 更新最大值
                if case.q_max:
                    case.max_value = max(case.max_value, q)
                if case.n_max:
                    case.max_value = max(case.max_value, n)
                if case.M_bend_max:
                    case.max_value = max(case.max_value, M_bend)
        
        self.history.append({
            "time": t,
            "results": results,
            "any_violation": any_violation
        })
        
        return {
            "all_cases": results,
            "any_violation": any_violation,
            "time": t
        }

    def compute_margins(self, actual_values: Dict[str, float]) -> Dict:
        """計算所有案例的裕度"""
        margins = {}
        
        for name, case in self.load_cases.items():
            if case.q_max:
                MS = (case.q_max / max(actual_values.get("q", 1e-9), 1e-9)) - 1.0
                margins[name] = {"MS": MS, "type": "q"}
            elif case.n_max:
                MS = (case.n_max / max(actual_values.get("n", 1e-9), 1e-9)) - 1.0
                margins[name] = {"MS": MS, "type": "n"}
            elif case.M_bend_max:
                MS = (case.M_bend_max / max(actual_values.get("M_bend", 1e-9), 1e-9)) - 1.0
                margins[name] = {"MS": MS, "type": "M_bend"}
            elif case.delta_T_max:
                MS = (case.delta_T_max / max(actual_values.get("delta_T", 1e-9), 1e-9)) - 1.0
                margins[name] = {"MS": MS, "type": "delta_T"}
        
        # 找出最小裕度（瓶頸）
        min_margin = min([m["MS"] for m in margins.values()], default=0.0)
        bottleneck = [name for name, m in margins.items() if m["MS"] == min_margin]
        
        return {
            "margins": margins,
            "min_margin": min_margin,
            "bottleneck_cases": bottleneck
        }

    def generate_report(self) -> Dict:
        """生成載荷案例報表"""
        report = {
            "load_cases": {},
            "summary": {
                "total_cases": len(self.load_cases),
                "cases_occurred": sum(1 for c in self.load_cases.values() if c.occurred),
                "total_violations": sum(1 for h in self.history if h.get("any_violation", False))
            }
        }
        
        for name, case in self.load_cases.items():
            report["load_cases"][name] = {
                "type": case.case_type.value,
                "occurred": case.occurred,
                "max_value": case.max_value,
                "margin_of_safety": case.margin_of_safety
            }
        
        return report

    def propose_design_changes(self, violations: Dict[str, Dict]) -> Dict:
        """
        自動閉環設計：提出可行改動
        返回: 設計改動建議、trade-off 分析
        """
        proposals = []
        trade_offs = []
        
        for case_name, violation_data in violations.items():
            case = self.load_cases.get(case_name)
            if not case:
                continue
            
            if case.case_type == LoadCaseType.MAX_Q:
                # 降低 max-q 的建議
                proposals.append({
                    "case": case_name,
                    "problem": "動壓超限",
                    "suggestions": [
                        "調整節流曲線（降低上升段推力）",
                        "改變爬升剖面（更陡峭的軌跡）",
                        "降低外形阻力係數（優化氣動外形）",
                        "增加結構強度（允許更高動壓）"
                    ],
                    "trade_off": {
                        "降低節流": {"pro": "降低動壓", "con": "可能增加重力損失"},
                        "改變軌跡": {"pro": "降低動壓", "con": "可能增加燃料消耗"},
                        "優化外形": {"pro": "降低阻力", "con": "可能增加設計複雜度"},
                        "增加強度": {"pro": "允許更高動壓", "con": "增加質量"}
                    }
                })
            
            elif case.case_type == LoadCaseType.MAX_LOAD_FACTOR:
                proposals.append({
                    "case": case_name,
                    "problem": "過載超限",
                    "suggestions": [
                        "降低加速度（調整推力）",
                        "增加結構強度",
                        "優化軌跡（減少轉彎率）"
                    ],
                    "trade_off": {
                        "降低推力": {"pro": "降低過載", "con": "可能增加飛行時間"},
                        "增加強度": {"pro": "允許更高過載", "con": "增加質量"}
                    }
                })
            
            elif case.case_type == LoadCaseType.MAX_BENDING:
                proposals.append({
                    "case": case_name,
                    "problem": "彎矩超限",
                    "suggestions": [
                        "增加結構厚度",
                        "改變材料（更高強度）",
                        "優化載荷分佈",
                        "增加結構支撐"
                    ],
                    "trade_off": {
                        "增加厚度": {"pro": "降低應力", "con": "增加質量"},
                        "改變材料": {"pro": "更高強度", "con": "可能增加成本"}
                    }
                })
            
            elif case.case_type == LoadCaseType.THERMAL_GRADIENT:
                proposals.append({
                    "case": case_name,
                    "problem": "熱梯度超限",
                    "suggestions": [
                        "增加 TPS 厚度",
                        "改變 TPS 材料（更高導熱）",
                        "優化熱防護佈局",
                        "降低再入速度/角度"
                    ],
                    "trade_off": {
                        "增加 TPS": {"pro": "降低熱梯度", "con": "增加質量"},
                        "改變材料": {"pro": "更好熱性能", "con": "可能增加成本"},
                        "降低速度": {"pro": "降低熱載荷", "con": "可能增加燃料"}
                    }
                })
        
        return {
            "proposals": proposals,
            "n_proposals": len(proposals),
            "note": "概念級設計建議，需詳細分析驗證"
        }

    def iterative_optimization(self, initial_values: Dict[str, float],
                              objective: str = "minimize_mass",
                              max_iterations: int = 10) -> Dict:
        """
        迭代優化（簡化版）
        目標：最小化質量、最大化裕度、最小化熱峰值等
        """
        current_values = initial_values.copy()
        iteration_history = []
        
        for iteration in range(max_iterations):
            # 評估當前載荷案例
            margins = self.compute_margins(current_values)
            min_margin = margins["min_margin"]
            bottleneck = margins["bottleneck_cases"][0] if margins["bottleneck_cases"] else None
            
            iteration_history.append({
                "iteration": iteration,
                "min_margin": min_margin,
                "bottleneck": bottleneck,
                "values": current_values.copy()
            })
            
            # 如果所有裕度都足夠，停止
            if min_margin > 0.2:  # 20% 裕度
                break
            
            # 根據瓶頸提出改動（簡化：只調整數值）
            if bottleneck:
                case = self.load_cases.get(bottleneck)
                if case and case.q_max:
                    # 簡化：降低當前值 10%
                    current_values["q"] *= 0.9
                elif case and case.n_max:
                    current_values["n"] *= 0.9
                elif case and case.M_bend_max:
                    current_values["M_bend"] *= 0.9
                elif case and case.delta_T_max:
                    current_values["delta_T"] *= 0.9
        
        return {
            "final_values": current_values,
            "final_margins": self.compute_margins(current_values),
            "iteration_history": iteration_history,
            "converged": iteration_history[-1]["min_margin"] > 0.2 if iteration_history else False,
            "n_iterations": len(iteration_history)
        }


# 實例化
load_case_manager = LoadCaseManager()
load_case_manager.create_standard_cases()
