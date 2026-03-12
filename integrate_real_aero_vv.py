# -*- coding: utf-8 -*-
"""
真實氣動係數接入 + 專業工具可用性檢查 + V&V 報告

功能：
1) 支援由 URL 下載或本機讀取氣動係數 CSV
2) 以可插拔來源接入 aero_upgrade（SU2/OpenFOAM 可用性檢查 + CSV fallback）
3) 產生覆蓋率與外部基準（風洞示例）V&V 報告
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import json
import urllib.request
import numpy as np
import math

from aero_upgrade import get_pluggable_aero, check_coverage, DesignSpace
from external_validation import external_validation
from su2_bridge import is_su2_available
from openfoam_bridge import is_openfoam_available


ROOT = Path(__file__).parent
DEFAULT_CSV = ROOT / "data" / "aero" / "real_aero_coeffs_sample.csv"
OUT_DIR = ROOT / "benchmark_pack_output"


def fetch_csv_if_needed(csv_url: Optional[str], out_path: Path) -> Path:
    """若提供 URL，抓取到 out_path；否則直接使用 out_path。"""
    if not csv_url:
        return out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(csv_url, str(out_path))
    return out_path


def make_model_func_for_kpi(aero_source, kpi_name: str):
    """包裝為 external_validation.compare_with_benchmark 需要的 callable。"""
    def _f(M: float, alpha: float):
        c = aero_source.coeffs(math.radians(alpha), 0.0, float(M), 1e6)
        return {kpi_name: float(c.get(kpi_name, 0.0))}
    return _f


def run_real_aero_vv(csv_path: Path) -> Dict[str, Any]:
    # 來源優先策略：若專業工具可用則記錄可用性；本腳本先使用 CSV 作為資料面主來源。
    tool_status = {
        "su2_available": bool(is_su2_available()),
        "openfoam_available": bool(is_openfoam_available()),
        "aero_source_selected": "csv",
    }

    source = get_pluggable_aero(
        source="csv",
        path=str(csv_path),
        uncertainty={"C_L": 0.03, "C_D": 0.05, "C_m": 0.05},
    )

    # 覆蓋率檢查（以概念設計常見包線）
    alpha_deg = np.array([-5.0, 0.0, 5.0, 10.0], dtype=float)
    M = np.array([0.30, 0.80, 1.20], dtype=float)
    coverage = check_coverage(
        alpha_deg=alpha_deg,
        M=M,
        space=DesignSpace(M_min=0.30, M_max=1.20, alpha_min_deg=-5.0, alpha_max_deg=10.0),
        n_sample=200,
        seed=42,
    )

    # 外部基準 V&V（示例基準點）
    bench = external_validation.wind_tunnel_coefficient_example()
    cl_result = external_validation.compare_with_benchmark(
        make_model_func_for_kpi(source, "C_L"), bench, "C_L"
    )
    cd_result = external_validation.compare_with_benchmark(
        make_model_func_for_kpi(source, "C_D"), bench, "C_D"
    )

    vv = {
        "version": "1.0",
        "data_source": str(csv_path),
        "tool_status": tool_status,
        "coverage": coverage,
        "benchmark_validation": {
            "C_L": cl_result,
            "C_D": cd_result,
        },
        "acceptance": {
            "coverage_ok": bool(coverage.get("coverage_ok", False)),
            "cl_validation_passed": bool(cl_result.get("validation_passed", False)),
            "cd_validation_passed": bool(cd_result.get("validation_passed", False)),
        },
    }
    vv["acceptance"]["overall_passed"] = (
        vv["acceptance"]["coverage_ok"]
        and vv["acceptance"]["cl_validation_passed"]
        and vv["acceptance"]["cd_validation_passed"]
    )
    return vv


def write_reports(report: Dict[str, Any], out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "real_aero_vv_report.json"
    md_path = out_dir / "real_aero_vv_report.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md = []
    md.append("# Real Aero + Professional Tools + V&V Report")
    md.append("")
    md.append("## Source")
    md.append(f"- CSV: `{report['data_source']}`")
    md.append(f"- SU2 available: `{report['tool_status']['su2_available']}`")
    md.append(f"- OpenFOAM available: `{report['tool_status']['openfoam_available']}`")
    md.append("")
    md.append("## Coverage")
    cov = report["coverage"]
    md.append(f"- Covered ratio: {cov.get('covered_ratio', 0.0):.1%}")
    md.append(f"- Coverage OK (>=95%): {cov.get('coverage_ok', False)}")
    md.append("")
    md.append("## Benchmark Validation")
    cl = report["benchmark_validation"]["C_L"]
    cd = report["benchmark_validation"]["C_D"]
    md.append(f"- C_L max relative error: {cl.get('max_relative_error', 0.0):.4f}, passed={cl.get('validation_passed', False)}")
    md.append(f"- C_D max relative error: {cd.get('max_relative_error', 0.0):.4f}, passed={cd.get('validation_passed', False)}")
    md.append("")
    md.append("## Acceptance")
    acc = report["acceptance"]
    md.append(f"- coverage_ok: {acc['coverage_ok']}")
    md.append(f"- cl_validation_passed: {acc['cl_validation_passed']}")
    md.append(f"- cd_validation_passed: {acc['cd_validation_passed']}")
    md.append(f"- overall_passed: {acc['overall_passed']}")
    md_path.write_text("\n".join(md), encoding="utf-8")

    return {"json": str(json_path), "md": str(md_path)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Integrate real aero coefficients and run V&V.")
    parser.add_argument("--csv-path", type=str, default=str(DEFAULT_CSV), help="Local CSV path for aerodynamic coefficients.")
    parser.add_argument("--csv-url", type=str, default="", help="Optional URL to download coefficient CSV.")
    args = parser.parse_args()

    local_csv = Path(args.csv_path)
    csv_path = fetch_csv_if_needed(args.csv_url.strip() or None, local_csv)

    report = run_real_aero_vv(csv_path)
    paths = write_reports(report, OUT_DIR)

    print("=== Real Aero + Professional Tools + V&V ===")
    print(f"CSV source: {csv_path}")
    print(f"SU2 available: {report['tool_status']['su2_available']}")
    print(f"OpenFOAM available: {report['tool_status']['openfoam_available']}")
    print(f"Coverage OK: {report['acceptance']['coverage_ok']}")
    print(f"C_L passed: {report['acceptance']['cl_validation_passed']}")
    print(f"C_D passed: {report['acceptance']['cd_validation_passed']}")
    print(f"Overall passed: {report['acceptance']['overall_passed']}")
    print(f"Report JSON: {paths['json']}")
    print(f"Report MD: {paths['md']}")


if __name__ == "__main__":
    main()

