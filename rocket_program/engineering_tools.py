# -*- coding: utf-8 -*-
"""
工程化工具：單位系統、日誌、API schema、可追溯性
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import json
import logging
from datetime import datetime
from pathlib import Path
import numpy as np


# =============================================================================
# 1) 單位系統
# =============================================================================

class UnitSystem:
    """強制 SI 單位系統"""
    
    # 基本單位
    LENGTH = "m"
    MASS = "kg"
    TIME = "s"
    FORCE = "N"
    PRESSURE = "Pa"
    TEMPERATURE = "K"
    ENERGY = "J"
    POWER = "W"
    
    @staticmethod
    def validate_units(value: float, expected_unit: str, tolerance: float = 1e-9) -> bool:
        """
        驗證單位合理性（簡化：只檢查數值範圍）
        實際應使用 units library (如 pint)
        """
        # 簡化：只檢查數值範圍合理性
        if expected_unit == UnitSystem.TEMPERATURE:
            return 0.0 < value < 10000.0  # K
        elif expected_unit == UnitSystem.PRESSURE:
            return 0.0 <= value < 1e10  # Pa
        elif expected_unit == UnitSystem.LENGTH:
            return -1e7 < value < 1e7  # m
        elif expected_unit == UnitSystem.MASS:
            return 0.0 < value < 1e6  # kg
        return True

    @staticmethod
    def convert_to_si(value: float, from_unit: str) -> tuple[float, str]:
        """
        轉換到 SI（簡化實現）
        完整實現需 units library
        """
        # 簡化：假設輸入已是 SI
        return value, from_unit


# =============================================================================
# 2) 日誌與追蹤
# =============================================================================

@dataclass
class SimulationMetadata:
    """模擬元數據（可追溯性）"""
    simulation_id: str
    timestamp: str
    git_commit: Optional[str] = None
    model_versions: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_files: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        """轉換為字典"""
        return asdict(self)

    def save(self, filepath: str):
        """儲存元數據"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False, default=str)


class SimulationLogger:
    """模擬日誌記錄器"""

    def __init__(self, log_file: Optional[str] = None, level: int = logging.INFO):
        self.logger = logging.getLogger("aerospace_sim")
        self.logger.setLevel(level)
        
        # 控制台輸出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件輸出
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        self.metadata: Optional[SimulationMetadata] = None

    def log_simulation_start(self, sim_id: str, parameters: Dict):
        """記錄模擬開始"""
        self.metadata = SimulationMetadata(
            simulation_id=sim_id,
            timestamp=datetime.now().isoformat(),
            parameters=parameters
        )
        self.logger.info(f"模擬開始: {sim_id}")
        self.logger.info(f"參數: {json.dumps(parameters, indent=2, default=str)}")

    def log_event(self, event_type: str, message: str, level: int = logging.INFO):
        """記錄事件"""
        if level == logging.INFO:
            self.logger.info(f"[{event_type}] {message}")
        elif level == logging.WARNING:
            self.logger.warning(f"[{event_type}] {message}")
        elif level == logging.ERROR:
            self.logger.error(f"[{event_type}] {message}")

    def log_simulation_end(self, summary: Dict):
        """記錄模擬結束"""
        self.logger.info(f"模擬結束: {self.metadata.simulation_id if self.metadata else 'unknown'}")
        self.logger.info(f"摘要: {json.dumps(summary, indent=2, default=str)}")

    def save_metadata(self, filepath: str):
        """儲存元數據"""
        if self.metadata:
            self.metadata.save(filepath)


# =============================================================================
# 3) API Schema（輸入/輸出契約）
# =============================================================================

@dataclass
class InputSchema:
    """輸入 schema"""
    parameter_name: str
    unit: str
    type: type
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default: Optional[Any] = None
    description: str = ""
    required: bool = True

    def validate(self, value: Any) -> Dict:
        """驗證輸入"""
        errors = []
        
        # 類型檢查
        if not isinstance(value, self.type):
            errors.append(f"{self.parameter_name}: 類型錯誤，期望 {self.type}，得到 {type(value)}")
        
        # 數值範圍檢查
        if isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                errors.append(f"{self.parameter_name}: 值 {value} < 最小值 {self.min_value}")
            if self.max_value is not None and value > self.max_value:
                errors.append(f"{self.parameter_name}: 值 {value} > 最大值 {self.max_value}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


@dataclass
class OutputSchema:
    """輸出 schema"""
    output_name: str
    unit: str
    type: type
    description: str = ""


class APIContract:
    """API 契約管理器"""

    def __init__(self):
        self.input_schemas: Dict[str, List[InputSchema]] = {}
        self.output_schemas: Dict[str, List[OutputSchema]] = {}

    def define_function_contract(self, function_name: str, 
                                 inputs: List[InputSchema],
                                 outputs: List[OutputSchema]):
        """定義函數契約"""
        self.input_schemas[function_name] = inputs
        self.output_schemas[function_name] = outputs

    def validate_inputs(self, function_name: str, **kwargs) -> Dict:
        """驗證函數輸入"""
        if function_name not in self.input_schemas:
            return {"valid": True, "warnings": ["無定義的 schema"]}
        
        all_errors = []
        for schema in self.input_schemas[function_name]:
            if schema.parameter_name in kwargs:
                validation = schema.validate(kwargs[schema.parameter_name])
                if not validation["valid"]:
                    all_errors.extend(validation["errors"])
            elif schema.required:
                all_errors.append(f"缺少必需參數: {schema.parameter_name}")
        
        return {
            "valid": len(all_errors) == 0,
            "errors": all_errors
        }

    def document_outputs(self, function_name: str) -> Dict:
        """文件化輸出"""
        if function_name not in self.output_schemas:
            return {}
        
        docs = {}
        for schema in self.output_schemas[function_name]:
            docs[schema.output_name] = {
                "unit": schema.unit,
                "type": schema.type.__name__,
                "description": schema.description
            }
        return docs


# =============================================================================
# 4) 可追溯性
# =============================================================================

class TraceabilityManager:
    """可追溯性管理器"""

    def __init__(self):
        self.trace_records: List[Dict] = []

    def record_decision(self, decision: str, rationale: str, parameters: Dict):
        """記錄設計決策"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "rationale": rationale,
            "parameters": parameters
        }
        self.trace_records.append(record)

    def record_requirement(self, req_id: str, description: str, source: str):
        """記錄需求"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "type": "requirement",
            "req_id": req_id,
            "description": description,
            "source": source
        }
        self.trace_records.append(record)

    def record_validation(self, test_name: str, result: Dict, reference: str):
        """記錄驗證結果"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "type": "validation",
            "test_name": test_name,
            "result": result,
            "reference": reference
        }
        self.trace_records.append(record)

    def export_traceability(self, filepath: str):
        """匯出可追溯性記錄"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.trace_records, f, indent=2, ensure_ascii=False, default=str)


# 實例化
unit_system = UnitSystem()
sim_logger = SimulationLogger()
api_contract = APIContract()
traceability = TraceabilityManager()
