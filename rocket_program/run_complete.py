# -*- coding: utf-8 -*-
"""
火箭設計系統完整執行腳本
一鍵執行：設計 → 報告 → 工程驗證
"""
from __future__ import annotations
import os
import sys

def main():
    print("=" * 70)
    print("  火箭設計系統 - 完整執行")
    print("=" * 70)

    # 1. 完整設計
    print("\n[1/4] 執行完整設計...")
    from .rocket_design_example import main as design_main
    state = design_main()

    # 2. 工程報告（V&V、UQ、可重現包）
    print("\n[2/4] 生成工程報告...")
    from . import generate_engineering_reports  # noqa: F401 — 匯入時自動執行

    # 3. Benchmark Pack（若存在）
    print("\n[3/4] 執行 Benchmark Pack...")
    try:
        from . import benchmark_pack
        print("  Benchmark Pack 完成")
    except Exception as e:
        print(f"  Benchmark Pack 跳過: {e}")

    # 4. 整合報告
    print("\n[4/4] 生成整合報告...")
    from .generate_comprehensive_report import generate_comprehensive_report
    report_path = generate_comprehensive_report(state)
    print(f"  整合報告: {report_path}")

    print("\n" + "=" * 70)
    print("  執行完成")
    print("=" * 70)
    print("\n輸出目錄:")
    print("  - full_design_output/    設計結果與設計報告")
    print("  - V_V_Report_v1.0.json    驗證與確認報告")
    print("  - UQ_Sensitivity_Report_v1.0.json  不確定度與敏感度報告")
    print("  - reproducible_pack/     可重現執行包")
    print(f"  - {report_path}  整合工程報告")
    print()
    return state


if __name__ == "__main__":
    main()
