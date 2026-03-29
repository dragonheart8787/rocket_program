# -*- coding: utf-8 -*-
"""
需求可追溯矩陣（RTM）：需求 → 測試 → 證據
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum
from pathlib import Path
import json
from datetime import datetime

# 合規門檻常數（REQ-001 max_q ≤ 50 kPa）
REQ001_MAX_Q_PA = 50000.0
UQ_REQ001_CASE_ID = "UQ-REQ-001"


def _to_bool(x: Any) -> Optional[bool]:
    """將 JSON/字串轉為 bool；無法解析時回傳 None。"""
    if x is True:
        return True
    if x is False or x == "False" or (isinstance(x, str) and x.lower() == "false"):
        return False
    if x == "True" or (isinstance(x, str) and x.lower() == "true"):
        return True
    return None


class RequirementType(Enum):
    """需求類型"""
    FUNCTIONAL = "functional"  # 功能需求
    PERFORMANCE = "performance"  # 性能需求
    SAFETY = "safety"  # 安全需求
    APPLICABILITY = "applicability"  # 適用域需求
    OUTPUT_FORMAT = "output_format"  # 輸出格式需求


class VerificationMethod(Enum):
    """驗證方式"""
    ANALYSIS = "analysis"  # 分析
    TEST = "test"  # 測試
    INSPECTION = "inspection"  # 檢查
    DEMONSTRATION = "demonstration"  # 演示


@dataclass
class Requirement:
    """需求定義。threshold / threshold_unit 用於合規判定（如 REQ-001 max_q Pa）。"""
    req_id: str
    req_type: RequirementType
    description: str
    source: str
    priority: str = "medium"
    applicable_range: Optional[Dict] = None
    threshold: Optional[float] = None   # 合規門檻（與 threshold_unit 同用）
    threshold_unit: Optional[str] = None  # 如 "Pa", "K"
    notes: str = ""


@dataclass
class VerificationCase:
    """驗證案例。threshold_unit 與門檻同用，避免單位混用。"""
    case_id: str
    req_ids: List[str]
    verification_method: VerificationMethod
    threshold: float
    result: Optional[Dict] = None
    passed: Optional[bool] = None
    threshold_unit: Optional[str] = None  # 如 "Pa", "K"
    artifacts: List[str] = field(default_factory=list)
    notes: str = ""


class RequirementsTraceabilityMatrix:
    """需求可追溯矩陣"""

    def __init__(self):
        self.requirements: Dict[str, Requirement] = {}
        self.verification_cases: Dict[str, VerificationCase] = {}
        self.traceability: Dict[str, List[str]] = {}  # req_id -> [case_ids]

    def add_requirement(self, req: Requirement):
        """添加需求"""
        self.requirements[req.req_id] = req
        self.traceability[req.req_id] = []

    def add_verification_case(self, case: VerificationCase):
        """添加驗證案例"""
        self.verification_cases[case.case_id] = case
        
        # 建立追溯關係
        for req_id in case.req_ids:
            if req_id in self.traceability:
                if case.case_id not in self.traceability[req_id]:
                    self.traceability[req_id].append(case.case_id)

    def link_requirement_to_case(self, req_id: str, case_id: str):
        """手動連結需求與測試案例"""
        if req_id not in self.requirements:
            raise ValueError(f"需求 {req_id} 不存在")
        if case_id not in self.verification_cases:
            raise ValueError(f"測試案例 {case_id} 不存在")
        
        if req_id not in self.traceability:
            self.traceability[req_id] = []
        
        if case_id not in self.traceability[req_id]:
            self.traceability[req_id].append(case_id)
        
        # 同時更新驗證案例
        if req_id not in self.verification_cases[case_id].req_ids:
            self.verification_cases[case_id].req_ids.append(req_id)

    def get_coverage(self) -> Dict:
        """獲取覆蓋率統計"""
        total_reqs = len(self.requirements)
        covered_reqs = sum(1 for req_id, case_ids in self.traceability.items() if len(case_ids) > 0)
        coverage = covered_reqs / max(total_reqs, 1) * 100
        
        return {
            "total_requirements": total_reqs,
            "covered_requirements": covered_reqs,
            "coverage_percentage": coverage,
            "uncovered_requirements": [
                req_id for req_id, case_ids in self.traceability.items() if len(case_ids) == 0
            ]
        }

    def generate_rtm_report(self, output_file: str = "RTM_Report_v1.0.json",
                            artifacts_base: Optional[Path] = None) -> Dict:
        """生成 RTM 報告。artifacts_base：專案根，用於讀 V_V_Report、UQ 以解析 passed/compliance。"""
        base = Path(artifacts_base) if artifacts_base else Path(output_file).parent.parent

        # 從 artifact 解析 passed
        vv = {}
        try:
            vv_path = base / "V_V_Report_v1.0.json"
            if vv_path.is_file():
                vv = json.loads(vv_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        vv_cases = {c["case_id"]: c for c in vv.get("test_cases", [])} if vv else {}

        uq = {}
        try:
            uq_path = base / "UQ_Sensitivity_Report_v1.0.json"
            if uq_path.is_file():
                uq = json.loads(uq_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        uq_mc = (uq.get("monte_carlo") or {}).get("kpi_statistics") or {}

        def _resolve_passed(case_id: str, case: VerificationCase, arts: List[str]) -> Optional[bool]:
            if "UQ_Sensitivity_Report" in str(arts) and case_id == UQ_REQ001_CASE_ID:
                p90 = (uq_mc.get("max_q") or {}).get("p90")
                if p90 is not None:
                    return float(p90) <= REQ001_MAX_Q_PA
                return None
            if "UQ_Sensitivity_Report" in str(arts) and case_id == "VV-UQ":
                # REQ-004：KPI 輸出 P10/P50/P90 → 有任一 KPI 含 p10/p50/p90 即視為通過
                for kpi_stats in (uq_mc or {}).values():
                    if isinstance(kpi_stats, dict) and "p10" in kpi_stats and "p50" in kpi_stats and "p90" in kpi_stats:
                        return True
                return None
            c = vv_cases.get(case_id)
            if not c:
                return case.passed
            if c.get("status") == "ERROR":
                return False
            return _to_bool(c.get("passed"))

        case_passed = {}
        for cid, c in self.verification_cases.items():
            p = _resolve_passed(cid, c, c.artifacts)
            case_passed[cid] = p

        def _compliance(req_id: str) -> str:
            ids = self.traceability.get(req_id, [])
            if req_id == "REQ-001" and UQ_REQ001_CASE_ID in ids:
                ids = [UQ_REQ001_CASE_ID]
            resolved = [case_passed.get(i) for i in ids]
            if not resolved:
                return "not_evaluated"
            if any(r is False for r in resolved):
                return "failed"
            if all(r is True for r in resolved):
                return "passed"
            return "not_evaluated"

        rtm_data = {
            "report_version": "1.0",
            "report_date": datetime.now().isoformat(),
            "requirements": {
                req_id: {
                    "req_id": req.req_id,
                    "type": req.req_type.value,
                    "description": req.description,
                    "source": req.source,
                    "priority": req.priority,
                    "applicable_range": req.applicable_range,
                    "threshold": req.threshold,
                    "threshold_unit": req.threshold_unit,
                    "verification_cases": self.traceability.get(req_id, []),
                    "verification_status": "covered" if len(self.traceability.get(req_id, [])) > 0 else "uncovered",
                    "compliance_status": _compliance(req_id),
                }
                for req_id, req in self.requirements.items()
            },
            "verification_cases": {
                case_id: {
                    "case_id": case.case_id,
                    "req_ids": case.req_ids,
                    "verification_method": case.verification_method.value,
                    "threshold": case.threshold,
                    "threshold_unit": case.threshold_unit,
                    "passed": case_passed.get(case_id, case.passed),
                    "artifacts": case.artifacts,
                    "notes": case.notes,
                }
                for case_id, case in self.verification_cases.items()
            },
            "coverage": self.get_coverage(),
            "note": "compliance_status=passed 表門檻達標；covered 僅表有對應案例。"
        }
        
        # 保存 JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(rtm_data, f, indent=2, default=str, ensure_ascii=False)
        
        # 生成 Markdown
        md_file = output_file.replace('.json', '.md')
        self._generate_rtm_markdown(md_file, rtm_data)
        
        return rtm_data

    def _generate_rtm_markdown(self, output_file: str, rtm_data: Dict):
        """生成 RTM Markdown 報告"""
        md_content = f"""# Requirements Traceability Matrix (RTM) v1.0

**報告日期**: {rtm_data['report_date']}

## 覆蓋率摘要

- 總需求數: {rtm_data['coverage']['total_requirements']}
- 已覆蓋: {rtm_data['coverage']['covered_requirements']}
- 覆蓋率: {rtm_data['coverage']['coverage_percentage']:.1f}%
- 未覆蓋需求: {len(rtm_data['coverage']['uncovered_requirements'])}

## 需求追溯表

| 需求 ID | 類型 | 描述 | 驗證方式 | 測試案例 | 覆蓋 | 合規 | 產物 |
|---------|------|------|---------|---------|------|------|------|
"""
        for req_id, req_data in rtm_data['requirements'].items():
            case_ids = req_data['verification_cases']
            case_list = ', '.join(case_ids) if case_ids else '無'
            methods = []
            artifacts = []
            for case_id in case_ids:
                if case_id in rtm_data['verification_cases']:
                    case = rtm_data['verification_cases'][case_id]
                    methods.append(case['verification_method'])
                    artifacts.extend(case['artifacts'])
            method_str = ', '.join(set(methods)) if methods else '未定義'
            artifact_str = ', '.join(set(artifacts)) if artifacts else '無'
            cov = "✅ 已覆蓋" if case_ids else "❌ 未覆蓋"
            comp = req_data.get("compliance_status", "")
            comp_s = "✅ 達標" if comp == "passed" else "❌ 未達標" if comp == "failed" else "⏳ 未評估"
            md_content += f"| {req_id} | {req_data['type']} | {req_data['description'][:50]}... | {method_str} | {case_list} | {cov} | {comp_s} | {artifact_str} |\n"
        
        md_content += "\n## 詳細需求（Coverage＝有案例；Compliance＝門檻達標）\n\n"
        for req_id, req_data in rtm_data['requirements'].items():
            th = req_data.get("threshold")
            u = req_data.get("threshold_unit", "")
            th_str = f" {th} {u}" if th is not None and u else ""
            md_content += f"""### {req_id}: {req_data['description']}

**類型**: {req_data['type']}
**來源**: {req_data['source']}
**門檻/單位**: {th_str or '—'}

**驗證案例**:
"""
            for case_id in req_data['verification_cases']:
                if case_id in rtm_data['verification_cases']:
                    case = rtm_data['verification_cases'][case_id]
                    p = case.get('passed')
                    status = "✅ 通過" if p is True else "❌ 失敗" if p is False else "⏳ 待測"
                    md_content += f"- {case_id}: {case['verification_method']} (門檻: {case['threshold']}) - {status}\n"
            
            md_content += "\n"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)


# 實例化
rtm = RequirementsTraceabilityMatrix()
