# -*- coding: utf-8 -*-
"""
火箭完整設計範例：一鍵執行任務規劃 → 推進 → 結構 → 熱力 → GNC → 報告
"""
from rocket_system_driver import RocketSystemConfig, run_full_design, export_design_state
from design_report_generator import generate_design_report
from mission_planning import OrbitType
from propulsion_advanced import PropulsionCycle


def main():
    print("=" * 60)
    print("  火箭完整模組化設計系統")
    print("=" * 60)

    cfg = RocketSystemConfig(
        name="Falcon-EDU",
        orbit_type=OrbitType.LEO,
        target_altitude_km=400.0,
        payload_mass_kg=500.0,
        launch_latitude_deg=28.5,
        n_stages=2,
        stage_isp_s=[300.0, 350.0],
        stage_struct_frac=[0.08, 0.10],
        propulsion_cycle=PropulsionCycle.GAS_GENERATOR,
        propellant_id="LOX_RP1",
        chamber_pressure_MPa=7.0,
        expansion_ratio=25.0,
        gamma=1.22,
        R_gas=378.0,     # LOX/RP-1: M_w ≈ 22, R = 8314/22
        T_c_K=3670.0,    # 典型 LOX/RP-1 燃燒溫度
        nose_type="von_karman",
        nose_length_m=2.0,
        body_radius_m=0.5,
        n_fins=4,
        wall_thickness_m=0.004,
        material_id="Al7075_T6",
        coolant_id="RP1",
        wall_temp_limit_K=900.0,
    )

    print("\n[1/6] 任務規劃...")
    print("[2/6] 推進系統設計...")
    print("[3/6] 外觀生成...")
    print("[4/6] 結構分析...")
    print("[5/6] 熱力分析...")
    print("[6/6] GNC 飛行模擬...")
    print()

    state = run_full_design(cfg)

    # 匯出
    out_dir = "full_design_output"
    export_design_state(state, out_dir)
    report_path = generate_design_report(state, f"{out_dir}/Design_Report.md")

    # 摘要
    print("-" * 60)
    print("  設計結果摘要")
    print("-" * 60)

    if state.mission:
        dv = state.mission["delta_v_budget"]
        stg = state.mission["staging"]
        print(f"  任務 ΔV:       {dv.dv_total_m_s:.0f} m/s")
        print(f"  總質量:        {stg.total_mass_kg:.0f} kg")
        print(f"  載荷比:        {stg.payload_ratio:.4f}")
    if state.propulsion:
        p = state.propulsion
        print(f"  真空推力:      {p.F_vac_N/1000:.1f} kN")
        print(f"  比衝 (vac):    {p.I_sp_vac_s:.1f} s")
        print(f"  循環:          {p.cycle.value}")
        print(f"  燃燒穩定:      {'穩定' if p.stability.is_stable else '不穩定'}")
    if state.structural:
        s = state.structural
        print(f"  屈服安全裕度:  {s.min_MS_yield:.2f}")
        print(f"  屈曲安全裕度:  {s.min_MS_buckling:.2f}")
    if state.thermal:
        t = state.thermal
        print(f"  最高壁溫:      {t.max_wall_temp_K:.0f} K")
        print(f"  熱裕度:        {t.thermal_margin_K:.0f} K")
    if state.gnc:
        g = state.gnc
        print(f"  最終高度:      {g.final_altitude_m/1000:.1f} km")
        print(f"  最終速度:      {g.final_velocity_m_s:.0f} m/s")
        print(f"  最大動壓:      {g.max_q_Pa/1000:.1f} kPa")
        print(f"  入軌:          {'達成' if g.is_orbit_achieved else '未達成'}")

    print(f"\n  輸出: {out_dir}/")
    print(f"  報告: {report_path}")
    print("=" * 60)
    return state


if __name__ == "__main__":
    main()
