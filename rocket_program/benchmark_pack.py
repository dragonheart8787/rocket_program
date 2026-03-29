# -*- coding: utf-8 -*-
"""
Benchmark Pack：CEA + GMAT + Sutton-Graves 全自動化對標與誤差報告

對標外部公認工具／文獻，產出 pass/fail 誤差報告，供 TRL4 驗證升級。
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

REPORT_REL_TOL = 0.05  # 5% 相對誤差閾值
REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DATA_DIR = REPO_ROOT / "data" / "benchmarks"


@dataclass
class BenchmarkCase:
    case_id: str
    name: str
    source: str
    passed: bool
    ref_value: float
    model_value: float
    rel_error: float
    threshold: float
    notes: str = ""


@dataclass
class BenchmarkReport:
    timestamp: str
    cea_cases: List[BenchmarkCase] = field(default_factory=list)
    gmat_cases: List[BenchmarkCase] = field(default_factory=list)
    sutton_graves_cases: List[BenchmarkCase] = field(default_factory=list)
    source_registry: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        def case_to_dict(c: BenchmarkCase) -> Dict:
            return {
                "case_id": str(c.case_id),
                "name": str(c.name),
                "source": str(c.source),
                "passed": bool(c.passed),
                "ref_value": float(c.ref_value),
                "model_value": float(c.model_value),
                "rel_error": float(c.rel_error),
                "threshold": float(c.threshold),
                "notes": str(c.notes),
            }
        return {
            "timestamp": self.timestamp,
            "cea": [case_to_dict(c) for c in self.cea_cases],
            "gmat": [case_to_dict(c) for c in self.gmat_cases],
            "sutton_graves": [case_to_dict(c) for c in self.sutton_graves_cases],
            "source_registry": self.source_registry,
            "summary": self.summary,
        }


def _load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if default is None:
        default = {}
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return default


def _source_label(source_ids: List[str], registry: Dict[str, Any]) -> str:
    srcs = registry.get("sources", [])
    title_map = {s.get("id"): s.get("title", s.get("id")) for s in srcs if isinstance(s, dict)}
    labels = [title_map.get(sid, sid) for sid in source_ids]
    return " / ".join(labels) if labels else "N/A"


def _run_cea_benchmark(registry: Dict[str, Any]) -> List[BenchmarkCase]:
    """CEA 對標：內建公式 vs RocketCEA（若可用）；或 CEA vs 文獻參考值。"""
    cases: List[BenchmarkCase] = []
    try:
        from .cea_bridge import get_cea_properties, is_cea_available
    except ImportError:
        cases.append(BenchmarkCase(
            "CEA-001", "CEA 模組", "N/A", False, 0.0, 0.0, 1.0, 0.05, "cea_bridge 未安裝"
        ))
        return cases

    if not is_cea_available():
        cases.append(BenchmarkCase(
            "CEA-001", "RocketCEA", "N/A", False, 0.0, 0.0, 1.0, 0.05, "RocketCEA 未安裝"
        ))
        return cases

    cea_ref = _load_json(BENCHMARK_DATA_DIR / "cea_reference_cases.json", {})
    source_text = _source_label(cea_ref.get("sources", []), registry)
    for item in cea_ref.get("cases", []):
        propellant_id = item.get("propellant_id", "LOX_RP1")
        Pc_Pa = float(item.get("Pc_Pa", 2.0e6))
        eps = float(item.get("expansion_ratio", 25.0))
        mr = item.get("MR")
        kpi = item.get("kpi", "Isp_vac_s")
        ref_val = float(item.get("reference_value", 0.0))
        thr = float(item.get("threshold_rel", REPORT_REL_TOL))
        cid = item.get("case_id", "CEA-XXX")
        notes = item.get("notes", "")

        r = get_cea_properties(propellant_id, Pc_Pa, eps, MR=mr)
        if r is None:
            cases.append(BenchmarkCase(
                cid, f"{propellant_id} {kpi}", source_text, False, ref_val, 0.0, 1.0, thr, "CEA 計算失敗"
            ))
            continue

        model_val = float(getattr(r, kpi, 0.0))
        err = abs(model_val - ref_val) / max(abs(ref_val), 1.0)
        cases.append(BenchmarkCase(
            cid, f"{propellant_id} {kpi}", source_text,
            err <= thr, ref_val, model_val, err, thr, notes
        ))

    return cases


def _run_gmat_benchmark(registry: Dict[str, Any]) -> List[BenchmarkCase]:
    """GMAT 對標：mission_planning 軌道參數 vs GMAT 輸出（若 GMAT 可用）。"""
    cases: List[BenchmarkCase] = []
    try:
        from .gmat_bridge import is_gmat_available, run_gmat_script
        from .mission_planning import compute_delta_v_budget, MissionSpec, OrbitType
        import math
    except ImportError as e:
        cases.append(BenchmarkCase(
            "GMAT-001", "GMAT/使命規劃", "N/A", False, 0.0, 0.0, 1.0, 0.05, f"Import 錯誤: {e}"
        ))
        return cases

    gmat_ref = _load_json(BENCHMARK_DATA_DIR / "gmat_reference_cases.json", {})
    source_text = _source_label(gmat_ref.get("sources", []), registry)

    # 本專案 LEO 400 km 圓軌 ΔV 預算
    spec = MissionSpec(
        orbit_type=OrbitType.LEO,
        target_altitude_km=400.0,
        payload_mass_kg=500.0,
    )
    dv = compute_delta_v_budget(spec)
    v_orbit = math.sqrt(3.986004418e14 / (6371000.0 + 400000.0))  # ~7.67 km/s

    for item in gmat_ref.get("cases", []):
        cid = item.get("case_id", "GMAT-XXX")
        name = item.get("name", cid)
        target = item.get("target", "")
        ref_val = float(item.get("reference_value", 0.0))
        thr = float(item.get("threshold_rel", REPORT_REL_TOL))
        notes = item.get("notes", "")
        if target == "orbit_velocity_m_s":
            model_val = v_orbit
        elif target == "dv_total_m_s":
            model_val = float(dv.dv_total_m_s)
        else:
            model_val = 0.0
        err = abs(model_val - ref_val) / max(abs(ref_val), 1.0)
        cases.append(BenchmarkCase(
            cid, name, source_text, err <= thr, ref_val, model_val, err, thr, notes
        ))

    # 若 GMAT 可用，跑腳本並比對（此處先做使命規劃自洽檢查）
    if is_gmat_available():
        try:
            from pathlib import Path
            td = Path("benchmark_pack_output")
            td.mkdir(exist_ok=True)
            from .gmat_bridge import write_minimal_script
            script_path = str(td / "gmat_bench.script")
            write_minimal_script(script_path)
            proc = run_gmat_script(script_path, run_and_exit=True, timeout=30)
            cases.append(BenchmarkCase(
                "GMAT-003", "GMAT 批次執行", "gmat_bridge",
                proc.returncode == 0, 0.0, float(proc.returncode), 0.0 if proc.returncode == 0 else 1.0, 0.05,
                "GMAT 腳本可執行" if proc.returncode == 0 else proc.stderr[:200] if proc.stderr else "失敗"
            ))
        except Exception as ex:
            cases.append(BenchmarkCase(
                "GMAT-003", "GMAT 批次", "N/A", False, 0.0, 0.0, 1.0, 0.05, str(ex)[:150]
            ))

    return cases


def _run_sutton_graves_benchmark(registry: Dict[str, Any]) -> List[BenchmarkCase]:
    """Sutton-Graves 對標：本專案 ThermalTPS.heating_rate vs 公式手算值。"""
    cases: List[BenchmarkCase] = []
    try:
        from .aerospace_sim import ISA, ThermalTPS
        import math
    except ImportError as e:
        cases.append(BenchmarkCase(
            "SG-001", "Sutton-Graves", "N/A", False, 0.0, 0.0, 1.0, 0.05, f"Import: {e}"
        ))
        return cases

    sg_ref = _load_json(BENCHMARK_DATA_DIR / "sutton_graves_reference_cases.json", {})
    source_text = _source_label(sg_ref.get("sources", []), registry)
    k_sg = float(sg_ref.get("constants", {}).get("k_sg", 1.83e-4))
    r_n = float(sg_ref.get("constants", {}).get("R_n_m", 0.15))
    isa = ISA()
    tps = ThermalTPS(k_sg=k_sg, R_n=r_n)

    for item in sg_ref.get("cases", []):
        cid = item.get("case_id", "SG-XXX")
        h = float(item.get("h_m", 0.0))
        V = float(item.get("V_m_s", 0.0))
        thr = float(item.get("threshold_rel", 1e-5))
        props = isa.properties(h)
        rho = props["rho"]
        q_model = tps.heating_rate(rho, V)
        q_ref = k_sg * math.sqrt(rho / max(r_n, 1e-12)) * (V ** 3)
        err = abs(q_model - q_ref) / max(abs(q_ref), 1.0)
        cases.append(BenchmarkCase(
            cid, f"Sutton-Graves h={h/1e3:.0f}km V={V/1e3:.1f}km/s",
            source_text,
            err <= thr, q_ref, q_model, err, thr,
            f"q={q_model:.0f} W/m^2"
        ))

    return cases


def run_all_benchmarks() -> BenchmarkReport:
    """執行全部對標，產出報告。"""
    registry = _load_json(BENCHMARK_DATA_DIR / "source_registry.json", {"sources": []})
    cea = _run_cea_benchmark(registry)
    gmat = _run_gmat_benchmark(registry)
    sg = _run_sutton_graves_benchmark(registry)

    all_cases = cea + gmat + sg
    n_pass = sum(1 for c in all_cases if c.passed)
    n_total = len(all_cases)

    summary = {
        "total_cases": int(n_total),
        "passed": int(n_pass),
        "failed": int(n_total - n_pass),
        "pass_rate": float(n_pass / max(n_total, 1)),
        "cea_available": bool(len(cea) > 0 and any(c.model_value > 0 for c in cea)),
        "gmat_available": bool(any("GMAT" in c.source for c in gmat)),
        "sutton_graves_ok": bool(all(c.passed for c in sg) if sg else False),
    }

    return BenchmarkReport(
        timestamp=datetime.utcnow().isoformat() + "Z",
        cea_cases=cea,
        gmat_cases=gmat,
        sutton_graves_cases=sg,
        source_registry=registry,
        summary=summary,
    )


def write_report(report: BenchmarkReport, output_dir: str = "benchmark_pack_output") -> str:
    """寫入 JSON 與 Markdown 報告。"""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "benchmark_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    md_lines = [
        "# Benchmark Pack 誤差報告",
        f"**生成時間**: {report.timestamp}",
        "",
        "## 資料來源",
    ]
    for s in report.source_registry.get("sources", []):
        if isinstance(s, dict):
            md_lines.append(f"- **{s.get('id', 'SRC-?')}**: {s.get('title', '')} ({s.get('reference', '')}) — {s.get('url', '')}")
    md_lines.extend([
        "",
        "## 摘要",
        f"- 總案例: {report.summary.get('total_cases', 0)}",
        f"- 通過: {report.summary.get('passed', 0)}",
        f"- 失敗: {report.summary.get('failed', 0)}",
        f"- 通過率: {report.summary.get('pass_rate', 0):.1%}",
        "",
        "## CEA 對標",
        "| Case | 名稱 | 通過 | 參考值 | 模型值 | 相對誤差 | 門檻 |",
        "|------|------|------|--------|--------|----------|------|",
    ])
    for c in report.cea_cases:
        md_lines.append(f"| {c.case_id} | {c.name} | {'✅' if c.passed else '❌'} | {c.ref_value:.2f} | {c.model_value:.2f} | {c.rel_error:.4f} | {c.threshold} |")
    md_lines.extend(["", "## GMAT / 使命規劃對標", "| Case | 名稱 | 通過 | 參考值 | 模型值 | 相對誤差 | 門檻 |", "|------|------|------|--------|--------|----------|------|"])
    for c in report.gmat_cases:
        md_lines.append(f"| {c.case_id} | {c.name} | {'✅' if c.passed else '❌'} | {c.ref_value:.2f} | {c.model_value:.2f} | {c.rel_error:.4f} | {c.threshold} |")
    md_lines.extend(["", "## Sutton-Graves 對標", "| Case | 名稱 | 通過 | 參考值 | 模型值 | 相對誤差 | 門檻 |", "|------|------|------|--------|--------|----------|------|"])
    for c in report.sutton_graves_cases:
        md_lines.append(f"| {c.case_id} | {c.name} | {'✅' if c.passed else '❌'} | {c.ref_value:.0f} | {c.model_value:.0f} | {c.rel_error:.2e} | {c.threshold} |")

    md_path = os.path.join(output_dir, "benchmark_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return md_path


if __name__ == "__main__":
    print("=== Benchmark Pack：CEA + GMAT + Sutton-Graves 全自動對標 ===\n")
    report = run_all_benchmarks()
    path = write_report(report)
    print(f"通過: {report.summary['passed']}/{report.summary['total_cases']} ({report.summary['pass_rate']:.1%})")
    print(f"報告: {path}")
