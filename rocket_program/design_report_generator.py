# -*- coding: utf-8 -*-
"""
完整設計報告生成器：從 DesignState 產生 Markdown 報告
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Optional
import math


def generate_design_report(state, output_path: str = "Design_Report.md") -> str:
    """從 DesignState 產生完整 Markdown 設計報告。"""
    cfg = state.config
    lines = [
        f"# 火箭完整設計報告：{cfg.name}",
        "",
        f"**產生時間**: {datetime.now().isoformat()}",
        "",
        "---",
        "",
    ]

    # 1) 任務規劃
    lines.append("## 1. 任務規劃")
    lines.append("")
    if state.mission:
        dv = state.mission["delta_v_budget"]
        stg = state.mission["staging"]
        bud = state.mission["mass_budget"]
        win = state.mission["launch_window"]
        lines.append(f"- **軌道類型**: {dv.orbit_type.value}")
        lines.append(f"- **目標高度**: {dv.target_altitude_km:.0f} km")
        lines.append(f"- **有效載荷**: {cfg.payload_mass_kg:.0f} kg")
        lines.append(f"- **ΔV 預算**: {dv.dv_total_m_s:.0f} m/s（理想 {dv.dv_ideal_m_s:.0f} + 重力損 {dv.dv_gravity_loss_m_s:.0f} + 阻力損 {dv.dv_drag_loss_m_s:.0f} + 操控損 {dv.dv_steering_loss_m_s:.0f}）")
        lines.append("")
        lines.append("### 多級設計")
        lines.append("")
        lines.append("| 級別 | 起始質量 (kg) | 推進劑 (kg) | 結構 (kg) | ΔV (m/s) | Isp (s) | 質量比 |")
        lines.append("|------|-------------|-----------|---------|---------|---------|--------|")
        for s in stg.stages:
            lines.append(f"| {s.stage_index} | {s.m0_kg:.0f} | {s.m_prop_kg:.0f} | {s.m_struct_kg:.0f} | {s.dv_m_s:.0f} | {s.isp_s:.0f} | {s.mass_ratio:.2f} |")
        lines.append("")
        lines.append(f"- **總質量**: {stg.total_mass_kg:.0f} kg")
        lines.append(f"- **載荷比**: {stg.payload_ratio:.4f}")
        lines.append("")
        lines.append("### 質量分配")
        lines.append("")
        lines.append(f"| 項目 | 質量 (kg) | 佔比 |")
        lines.append(f"|------|---------|------|")
        lines.append(f"| 推進劑 | {bud.total_propellant_kg:.0f} | {bud.propellant_fraction:.1%} |")
        lines.append(f"| 結構 | {bud.total_structure_kg:.0f} | {bud.structure_fraction:.1%} |")
        lines.append(f"| 載荷 | {bud.payload_mass_kg:.0f} | {bud.payload_fraction:.1%} |")
        lines.append("")
        lines.append(f"### 發射窗口")
        lines.append("")
        lines.append(f"- **發射緯度**: {win.latitude_deg:.1f}°")
        lines.append(f"- **東向速度增量**: {win.eastward_velocity_m_s:.1f} m/s")
        lines.append(f"- **面變換 ΔV**: {win.dv_plane_change_m_s:.1f} m/s")
        lines.append(f"- **發射方位角**: {win.launch_azimuth_deg:.1f}°")
        lines.append(f"- **備註**: {win.note}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2) 推進系統
    lines.append("## 2. 推進系統")
    lines.append("")
    if state.propulsion:
        p = state.propulsion
        lines.append(f"- **循環**: {p.cycle.value}")
        lines.append(f"- **真空推力**: {p.F_vac_N/1000:.1f} kN")
        lines.append(f"- **海平面推力**: {p.F_sea_N/1000:.1f} kN")
        lines.append(f"- **真空比衝**: {p.I_sp_vac_s:.1f} s")
        lines.append(f"- **海平面比衝**: {p.I_sp_sea_s:.1f} s")
        lines.append(f"- **質量流率**: {p.mdot_kg_s:.2f} kg/s")
        lines.append("")
        c = p.chamber
        lines.append("### 燃燒室")
        lines.append(f"- 直徑: {c.D_c_m*1000:.1f} mm，長度: {c.L_c_m*1000:.1f} mm")
        lines.append(f"- 喉部直徑: {c.D_t_m*1000:.1f} mm")
        lines.append(f"- L*: {c.L_star_m:.2f} m，滯留時間: {c.stay_time_ms:.2f} ms")
        lines.append(f"- c*: {c.c_star_m_s:.1f} m/s")
        lines.append("")
        inj = p.injector
        lines.append("### 噴注器")
        lines.append(f"- 元件數: {inj.n_elements}，孔徑: {inj.orifice_diameter_mm:.2f} mm")
        lines.append(f"- 噴射速度: {inj.injection_velocity_m_s:.1f} m/s，噴霧角: {inj.spray_angle_deg:.1f}°")
        lines.append(f"- 壓降比: {inj.pressure_drop_ratio:.0%}，型式: {inj.pattern}")
        lines.append("")
        if p.turbopump:
            tp = p.turbopump
            lines.append("### 渦輪泵")
            lines.append(f"- 泵功率: {tp.pump_power_kW:.1f} kW，轉速: {tp.shaft_speed_rpm:.0f} rpm")
            lines.append(f"- NPSH 裕度: {tp.cavitation_margin:.2f}")
            lines.append(f"- 效率: {tp.efficiency:.0%}")
            lines.append("")
        stab = p.stability
        lines.append("### 燃燒穩定性")
        lines.append(f"- 第一切向模態: {stab.first_tangential_freq_Hz:.0f} Hz")
        lines.append(f"- 第一縱向模態: {stab.first_longitudinal_freq_Hz:.0f} Hz")
        lines.append(f"- Crocco n={stab.crocco_n:.2f}，τ={stab.crocco_tau_ms:.2f} ms")
        lines.append(f"- 穩定性裕度: {stab.stability_margin:.2f}，{'✅ 穩定' if stab.is_stable else '❌ 不穩定'}")
        lines.append("")
        noz = p.nozzle
        lines.append("### 噴管（Rao 80% Bell）")
        lines.append(f"- 膨脹比: {noz.expansion_ratio:.1f}，長度: {noz.L_nozzle_m*1000:.1f} mm")
        lines.append(f"- 入口角: {noz.theta_init_deg:.1f}°，出口角: {noz.theta_exit_deg:.1f}°")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3) 結構
    lines.append("## 3. 結構分析")
    lines.append("")
    if state.structural:
        st = state.structural
        lines.append(f"- **最小屈服安全裕度**: {st.min_MS_yield:.2f}")
        lines.append(f"- **最小屈曲安全裕度**: {st.min_MS_buckling:.2f}")
        lines.append(f"- **臨界截面**: #{st.critical_section_index}")
        lines.append(f"- **結構質量**: {st.total_structural_mass_kg:.1f} kg")
        if st.fatigue:
            f = st.fatigue
            lines.append(f"- **疲勞壽命**: {f.n_cycles_to_failure:.0f} 循環")
            lines.append(f"- **累積損傷**: {f.cumulative_damage:.4f}")
            lines.append(f"- **裂紋成長率**: {f.crack_growth_rate_m_per_cycle:.2e} m/cycle")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 4) 熱力
    lines.append("## 4. 熱力分析")
    lines.append("")
    if state.thermal:
        th = state.thermal
        lines.append(f"- **最高壁溫**: {th.max_wall_temp_K:.0f} K")
        lines.append(f"- **熱裕度**: {th.thermal_margin_K:.0f} K")
        lines.append(f"- **TPS 質量**: {th.tps_mass_kg:.1f} kg")
        if th.regen_cooling:
            rc = th.regen_cooling
            lines.append(f"- **再生冷卻出口溫度**: {rc.coolant_outlet_temp_K:.0f} K")
            lines.append(f"- **總熱負荷**: {rc.total_heat_load_W/1e6:.2f} MW")
            lines.append(f"- **冷卻劑速度**: {rc.coolant_velocity_m_s:.1f} m/s")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 5) GNC
    lines.append("## 5. 導引與飛行模擬")
    lines.append("")
    if state.gnc:
        g = state.gnc
        lines.append(f"- **最終高度**: {g.final_altitude_m/1000:.1f} km")
        lines.append(f"- **最終速度**: {g.final_velocity_m_s:.0f} m/s")
        lines.append(f"- **最終航跡角**: {g.final_gamma_deg:.1f}°")
        lines.append(f"- **最大動壓**: {g.max_q_Pa/1000:.1f} kPa")
        lines.append(f"- **最大加速度**: {g.max_accel_g:.1f} g")
        lines.append(f"- **TVC 最大偏轉**: {g.tvc_max_gimbal_used_deg:.2f}°")
        lines.append(f"- **入軌判定**: {'✅ 達成' if g.is_orbit_achieved else '❌ 未達成'}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 6) 總結
    lines.append("## 6. 設計總結")
    lines.append("")
    ok_items = []
    warn_items = []
    if state.structural and state.structural.min_MS_yield > 0:
        ok_items.append("結構安全裕度 > 0")
    else:
        warn_items.append("結構安全裕度不足")
    if state.thermal and state.thermal.thermal_margin_K > 0:
        ok_items.append(f"熱裕度 {state.thermal.thermal_margin_K:.0f} K")
    else:
        warn_items.append("壁溫超過限制")
    if state.gnc and state.gnc.is_orbit_achieved:
        ok_items.append("GNC 入軌成功")
    else:
        warn_items.append("GNC 未達入軌條件")
    if state.propulsion and state.propulsion.stability.is_stable:
        ok_items.append("燃燒穩定")
    else:
        warn_items.append("燃燒不穩定風險")

    for item in ok_items:
        lines.append(f"- ✅ {item}")
    for item in warn_items:
        lines.append(f"- ⚠ {item}")

    lines.append("")
    lines.append("*本報告由 design_report_generator 自動產生。*")
    lines.append("")

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
