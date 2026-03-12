# -*- coding: utf-8 -*-
"""
TRL4 升級腳本：一鍵執行 Benchmark Pack + 氣動升級檢查 + AI Surrogate 管線示範

對應工程審查建議三動作：
1. Benchmark Pack：CEA + GMAT + Sutton-Graves 全自動對標
2. 氣動升級：可插拔來源、覆蓋率檢查
3. AI Surrogate：氣動代理、fail-closed、Pareto 前緣
"""

from __future__ import annotations
import os
import numpy as np
from pathlib import Path


def main():
    print("=" * 70)
    print("  TRL4 升級：Benchmark Pack + 氣動升級 + AI Surrogate + Real Aero V&V")
    print("=" * 70)

    # 1) Benchmark Pack
    print("\n[1/3] Benchmark Pack（CEA + GMAT + Sutton-Graves）...")
    try:
        from benchmark_pack import run_all_benchmarks, write_report
        report = run_all_benchmarks()
        out_dir = "benchmark_pack_output"
        path = write_report(report, out_dir)
        print(f"      通過: {report.summary['passed']}/{report.summary['total_cases']} ({report.summary['pass_rate']:.1%})")
        print(f"      報告: {path}")
    except Exception as e:
        print(f"      錯誤: {e}")

    # 2) 氣動升級
    print("\n[2/3] 氣動升級（可插拔來源、覆蓋率檢查）...")
    try:
        from aero_upgrade import (
            get_pluggable_aero,
            check_coverage,
            DesignSpace,
            aero_source_to_table,
        )
        import math

        source = get_pluggable_aero(source="placeholder", uncertainty={"C_L": 0.05, "C_D": 0.10})
        c = source.coeffs(0.0, 0.0, 0.8, 1e6)
        print(f"      C_L(M=0.8,α=0): {c['C_L']:.4f}, C_D: {c['C_D']:.4f}")

        if hasattr(source, "coeffs_with_uncertainty"):
            cu = source.coeffs_with_uncertainty(0.0, 0.0, 0.8, 1e6)
            print(f"      C_L 不確定度: {cu.get('C_L', (0, None))}")

        space = DesignSpace(M_min=0.3, M_max=1.5, alpha_min_deg=-5.0, alpha_max_deg=15.0)
        alpha_deg = np.array([0.0, 5.0, 10.0, 15.0])
        M = np.array([0.3, 0.6, 0.9, 1.2, 1.5])
        cov = check_coverage(alpha_deg, M, space, n_sample=100)
        print(f"      覆蓋率: {cov['covered_ratio']:.1%} (ok={cov['coverage_ok']})")

        # 轉成 AeroTable 供 aerospace_sim 使用
        tbl = aero_source_to_table(source, alpha_deg, M, Re_ref=1e6)
        if tbl is not None:
            print(f"      AeroTable 已生成: alpha x M = {len(alpha_deg)} x {len(M)}")
    except Exception as e:
        print(f"      錯誤: {e}")

    # 3) AI Surrogate 管線
    print("\n[3/4] AI Surrogate 管線（氣動代理、fail-closed、Pareto）...")
    try:
        from ai_surrogate_pipeline import (
            latin_hypercube_sample,
            SimpleGP,
            build_aero_surrogate,
            pareto_front_2d,
            ood_distance_to_nearest,
        )

        # 模擬 truth：簡單公式
        def truth_cl(x):
            M, a, logRe = x[:, 0], x[:, 1], x[:, 2]
            return 0.08 * a * (1.0 - 0.05 * (M - 0.5))
        def truth_cd(x):
            M, a = x[:, 0], x[:, 1]
            return 0.02 + 0.001 * (a ** 2) * (0.8 + 0.15 * M)

        bounds = [(0.3, 1.5), (-5.0, 15.0), (5.0, 7.0)]  # M, alpha_deg, log10(Re)
        X = latin_hypercube_sample(bounds, 30, seed=42)
        y_cl = truth_cl(X)
        y_cd = truth_cd(X)

        aero_surr = build_aero_surrogate(X, y_cl, y_cd, bounds)
        pred_cl, _ = aero_surr["C_L"]
        pred_cd, _ = aero_surr["C_D"]
        x_test = np.array([[0.8, 5.0, 6.0]])
        print(f"      Surrogate 預測 C_L: {pred_cl(x_test)[0]:.4f}, C_D: {pred_cd(x_test)[0]:.4f}")
        print(f"      Truth C_L: {truth_cl(x_test)[0]:.4f}, C_D: {truth_cd(x_test)[0]:.4f}")

        # OOD 偵測
        d = ood_distance_to_nearest(x_test, X)
        print(f"      OOD 距離（訓練集）: {d[0]:.4f}")

        # Pareto 前緣
        obj = np.column_stack([y_cl, y_cd])  # 最大化 C_L、最小化 C_D
        obj[:, 0] = -obj[:, 0]  # 轉成最小化
        idx = pareto_front_2d(obj, minimize=(True, True))
        print(f"      Pareto 前緣點數: {len(idx)}/{len(obj)}")
    except Exception as e:
        print(f"      錯誤: {e}")

    # 4) 真實氣動 + 專業工具 + V&V
    print("\n[4/4] 真實氣動係數 + 專業工具 + V&V...")
    try:
        from integrate_real_aero_vv import run_real_aero_vv, write_reports, DEFAULT_CSV
        report = run_real_aero_vv(DEFAULT_CSV)
        paths = write_reports(report, out_dir=Path("benchmark_pack_output"))
        print(f"      SU2 可用: {report['tool_status']['su2_available']}")
        print(f"      OpenFOAM 可用: {report['tool_status']['openfoam_available']}")
        print(f"      覆蓋率通過: {report['acceptance']['coverage_ok']}")
        print(f"      基準驗證 C_L/C_D: {report['acceptance']['cl_validation_passed']}/{report['acceptance']['cd_validation_passed']}")
        print(f"      Overall: {report['acceptance']['overall_passed']}")
        print(f"      報告: {paths['md']}")
    except Exception as e:
        print(f"      錯誤: {e}")

    print("\n" + "=" * 70)
    print("  完成。詳細報告見 benchmark_pack_output/")
    print("=" * 70)


if __name__ == "__main__":
    main()
