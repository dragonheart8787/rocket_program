# -*- coding: utf-8 -*-
"""
整合工程報告生成器
彙整設計報告、V&V、UQ、載荷案例、可重現性於單一報告
"""
from __future__ import annotations
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Any


def generate_comprehensive_report(state=None, output_path: str = "整合工程報告.md") -> str:
    """
    生成整合工程報告
    state: DesignState（可選，若無則從檔案讀取）
    """
    lines = [
        "# 火箭設計系統 - 整合工程報告",
        "",
        f"**報告日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 1. 執行摘要",
        "",
        "本報告整合火箭設計系統之完整輸出，包含：",
        "- 任務規劃與多級設計",
        "- 推進系統、結構、熱力、GNC 分析",
        "- 驗證與確認（V&V）",
        "- 不確定度與敏感度分析（UQ）",
        "- 載荷案例與裕度",
        "- 可重現性規格",
        "",
        "---",
        "",
    ]

    # 2. 設計結果摘要
    lines.append("## 2. 設計結果摘要")
    lines.append("")
    if state:
        cfg = state.config
        lines.append(f"- **專案名稱**: {cfg.name}")
        if state.mission:
            dv = state.mission["delta_v_budget"]
            stg = state.mission["staging"]
            lines.append(f"- **目標軌道**: {dv.orbit_type.value} {dv.target_altitude_km:.0f} km")
            lines.append(f"- **總質量**: {stg.total_mass_kg:.0f} kg")
            lines.append(f"- **ΔV 預算**: {dv.dv_total_m_s:.0f} m/s")
        if state.propulsion:
            p = state.propulsion
            lines.append(f"- **真空推力**: {p.F_vac_N/1000:.1f} kN")
            lines.append(f"- **真空比衝**: {p.I_sp_vac_s:.1f} s")
        if state.structural:
            s = state.structural
            lines.append(f"- **結構安全裕度**: 屈服 {s.min_MS_yield:.2f} / 屈曲 {s.min_MS_buckling:.2f}")
        if state.thermal:
            t = state.thermal
            lines.append(f"- **熱裕度**: {t.thermal_margin_K:.0f} K")
        if state.gnc:
            g = state.gnc
            lines.append(f"- **最大動壓**: {g.max_q_Pa/1000:.1f} kPa")
            lines.append(f"- **入軌**: {'達成' if g.is_orbit_achieved else '未達成'}")
    else:
        design_summary_path = Path("full_design_output/design_summary.json")
        if design_summary_path.exists():
            with open(design_summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
            lines.append(f"- **專案名稱**: {summary.get('name', 'N/A')}")
            for k, v in summary.items():
                if k != "name" and isinstance(v, dict):
                    lines.append(f"- **{k}**: {json.dumps(v, ensure_ascii=False)[:100]}...")
        else:
            lines.append("- 設計結果未找到（請先執行 rocket_design_example.py）")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. V&V 報告摘要
    lines.append("## 3. 驗證與確認（V&V）")
    lines.append("")
    vv_path = Path("V_V_Report_v1.0.json")
    if vv_path.exists():
        with open(vv_path, "r", encoding="utf-8") as f:
            vv = json.load(f)
        n_pass = vv.get("n_passed", 0)
        n_fail = vv.get("n_failed", 0)
        n_total = vv.get("n_test_cases", 0)
        lines.append(f"- **總案例數**: {n_total}")
        lines.append(f"- **通過**: {n_pass}")
        lines.append(f"- **失敗**: {n_fail}")
        lines.append(f"- **通過率**: {n_pass/max(n_total,1)*100:.1f}%")
        lines.append("")
        lines.append("### 測試案例列表")
        lines.append("")
        lines.append("| Case ID | 名稱 | 狀態 | 指標 | 門檻 |")
        lines.append("|---------|------|------|------|------|")
        for tc in vv.get("test_cases", []):
            status = "✅ PASS" if tc.get("status") == "PASS" else "❌ FAIL"
            lines.append(f"| {tc.get('case_id','')} | {tc.get('case_name','')} | {status} | {tc.get('metric','')} | {tc.get('threshold','')} |")
    else:
        lines.append("- V&V 報告未找到（請先執行 generate_engineering_reports.py）")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 4. UQ 與敏感度摘要
    lines.append("## 4. 不確定度與敏感度分析")
    lines.append("")
    uq_path = Path("UQ_Sensitivity_Report_v1.0.json")
    if uq_path.exists():
        with open(uq_path, "r", encoding="utf-8") as f:
            uq = json.load(f)
        mc = uq.get("monte_carlo", {})
        lines.append(f"- **Monte Carlo 樣本數**: {mc.get('n_samples', 'N/A')}")
        lines.append(f"- **隨機種子**: {mc.get('random_seed', 'N/A')}")
        lines.append("")
        lines.append("### KPI 統計（P10 / P50 / P90）")
        lines.append("")
        kpi_stats = mc.get("kpi_statistics", {})
        if kpi_stats:
            lines.append("| KPI | 均值 | 標準差 | P10 | P50 | P90 |")
            lines.append("|-----|------|--------|-----|-----|-----|")
            for kpi, stats in kpi_stats.items():
                lines.append(f"| {kpi} | {stats.get('mean',0):.2f} | {stats.get('std',0):.2f} | {stats.get('p10',0):.2f} | {stats.get('p50',0):.2f} | {stats.get('p90',0):.2f} |")
        lines.append("")
        lines.append("### 敏感度排名（整體）")
        sens = uq.get("sensitivity_analysis", {})
        ranked = sens.get("overall_ranked_parameters", [])
        if ranked:
            lines.append(", ".join(ranked))
    else:
        lines.append("- UQ 報告未找到")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 5. 載荷案例
    lines.append("## 5. 載荷案例")
    lines.append("")
    lines.append("標準載荷案例：max_q（動壓）、max_load_factor（過載）、max_bending（彎矩）、thermal_gradient（熱梯度）")
    lines.append("")
    lines.append("載荷案例管理器支援：")
    lines.append("- 裕度計算與瓶頸識別")
    lines.append("- 自動閉環設計建議（propose_design_changes）")
    lines.append("- 迭代優化（iterative_optimization）")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 6. 可重現性
    lines.append("## 6. 可重現性")
    lines.append("")
    repro_path = Path("reproducible_pack")
    if repro_path.exists():
        lines.append(f"- **可重現包目錄**: {repro_path}/")
        config_path = repro_path / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            lines.append(f"- **配置 Hash**: {cfg.get('config_hash', 'N/A')}")
            lines.append(f"- **隨機種子**: {cfg.get('random_seed', 'N/A')}")
    else:
        lines.append("- 可重現包未找到")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 7. 輸出檔案清單
    lines.append("## 7. 輸出檔案清單")
    lines.append("")
    lines.append("| 檔案 | 說明 |")
    lines.append("|------|------|")
    lines.append("| full_design_output/design_summary.json | 設計摘要 |")
    lines.append("| full_design_output/Design_Report.md | 設計報告 |")
    lines.append("| V_V_Report_v1.0.json | V&V 報告（JSON） |")
    lines.append("| V_V_Report_v1.0.md | V&V 報告（Markdown） |")
    lines.append("| UQ_Sensitivity_Report_v1.0.json | UQ 與敏感度報告 |")
    lines.append("| reproducible_pack/ | 可重現執行包 |")
    lines.append("| Reproducible_Run_Pack_Spec_v1.0.md | 可重現規格說明 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本報告由 generate_comprehensive_report 自動產生。*")
    lines.append("")

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
