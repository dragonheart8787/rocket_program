# -*- coding: utf-8 -*-
"""
V&V 報告生成器：標準格式（Case ID / Input Hash / Model Version / Metric / Threshold / Result / Plot）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import json
import hashlib
from datetime import datetime
import numpy as np


@dataclass
class VVTestCase:
    """V&V 測試案例（強制 metric_value / threshold / pass_bool / artifact_path；缺一則 status=ERROR）"""
    case_id: str
    case_name: str
    description: str
    input_hash: str
    model_version: str
    metric: str
    threshold: float
    result: Dict[str, Any]
    passed: bool
    metric_value: Optional[float] = None  # 用於 pass 判定的數值；缺失→ERROR
    plot_path: Optional[str] = None
    notes: str = ""

    def to_dict(self, artifact_path: Optional[str] = None) -> dict:
        d = {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "description": self.description,
            "input_hash": self.input_hash,
            "model_version": self.model_version,
            "metric": self.metric,
            "threshold": self.threshold,
            "metric_value": self.metric_value,
            "result": self.result,
            "passed": bool(self.passed),
            "plot_path": self.plot_path,
            "notes": self.notes,
            "artifact_path": artifact_path or "",
        }
        # 缺 metric_value / threshold / passed 任一→ERROR；artifact_path 可為空
        ok = (self.metric_value is not None and self.threshold is not None)
        if not ok:
            d["status"] = "ERROR"
        else:
            d["status"] = "PASS" if self.passed else "FAIL"
        return d


class VVReportGenerator:
    """V&V 報告生成器"""

    def __init__(self):
        self.test_cases: List[VVTestCase] = []
        self.report_version: str = "1.0"
        self.report_date: str = datetime.now().isoformat()

    def clear(self):
        """清空測試案例（供重新生成使用）"""
        self.test_cases = []

    def add_test_case(self, case_id: str, case_name: str, description: str,
                     inputs: Dict, model_version: str, metric: str,
                     threshold: float, result: Dict, passed: bool,
                     metric_value: Optional[float] = None,
                     plot_path: Optional[str] = None, notes: str = ""):
        """添加測試案例。metric_value 缺則 status=ERROR（SAP 視同 FAIL）。"""
        input_str = json.dumps(inputs, sort_keys=True, default=str)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        self.test_cases.append(VVTestCase(
            case_id=case_id, case_name=case_name, description=description,
            input_hash=input_hash, model_version=model_version, metric=metric,
            threshold=threshold, result=result, passed=bool(passed),
            metric_value=metric_value, plot_path=plot_path, notes=notes
        ))

    def generate_report(self, output_file: str = "V_V_Report_v1.0.json") -> Dict:
        """生成 V&V 報告。status=ERROR 視同 FAIL 計入 n_failed。"""
        cases = [tc.to_dict(artifact_path=output_file) for tc in self.test_cases]
        n_pass = sum(1 for c in cases if c.get("status") == "PASS")
        n_fail = sum(1 for c in cases if c.get("status") in ("FAIL", "ERROR"))
        report = {
            "report_version": self.report_version,
            "report_date": self.report_date,
            "n_test_cases": len(self.test_cases),
            "n_passed": n_pass,
            "n_failed": n_fail,
            "n_error": sum(1 for c in cases if c.get("status") == "ERROR"),
            "test_cases": cases,
        }
        
        # 保存 JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str, ensure_ascii=False)
        
        # 生成 Markdown 摘要
        md_file = output_file.replace('.json', '.md')
        self._generate_markdown(md_file, report)
        
        return report

    def _generate_markdown(self, output_file: str, report: Dict):
        """生成 Markdown 報告"""
        md_content = f"""# V&V Report v{self.report_version}

**報告日期**: {self.report_date}

## 摘要

- 總測試案例數: {report['n_test_cases']}
- 通過: {report['n_passed']}
- 失敗: {report['n_failed']}
- 通過率: {report['n_passed'] / max(report['n_test_cases'], 1) * 100:.1f}%

## 測試案例

"""
        for i, tc in enumerate(self.test_cases, 1):
            status = "✅ PASS" if tc.passed else "❌ FAIL"
            md_content += f"""### {i}. {tc.case_name} ({tc.case_id})

**描述**: {tc.description}

**狀態**: {status}

**輸入 Hash**: `{tc.input_hash}`

**模型版本**: {tc.model_version}

**指標**: {tc.metric}

**門檻**: {tc.threshold}

**結果**:
```json
{json.dumps(tc.result, indent=2, default=str)}
```

"""
            if tc.plot_path:
                md_content += f"**圖表**: {tc.plot_path}\n\n"
            if tc.notes:
                md_content += f"**備註**: {tc.notes}\n\n"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)


# 實例化
vv_report_generator = VVReportGenerator()
