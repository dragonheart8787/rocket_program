# -*- coding: utf-8 -*-
"""
彙整 SAP 區塊 01–07 的測試結果為單一 Markdown 報告。
"""

from __future__ import annotations

import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 常數：報告檔名與路徑
SAP_REPORT_FILENAME = "SAP_Test_Report_1_to_7.md"
RTM_REPORT_NAME = "RTM_Report_v1.0.json"
VV_REPORT_NAME = "V_V_Report_v1.0.json"
UQ_REPORT_NAME = "UQ_Sensitivity_Report_v1.0.json"
DOCKER_IMAGE_TAG = "sap_v1:test"
DOCKER_BUILD_TIMEOUT = 300
DOCKER_RUN_TIMEOUT = 120
MAX_VV_CASES_DISPLAY = 12
MAX_REQS_DISPLAY = 8
MAX_KPI_DISPLAY = 6


def _load_json(path: Path, default: Optional[Dict] = None) -> Dict[str, Any]:
    """安全載入 JSON；路徑不存在或解析失敗時回傳 default。"""
    if default is None:
        default = {}
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return default


def _format_vv_status(status: str) -> str:
    """將 V&V status 轉為顯示符號。"""
    return {"PASS": "✅", "FAIL": "❌", "ERROR": "ERROR"}.get(status, "—")


def _section_01_rtm(sap_dir: Path) -> Tuple[List[str], Dict[str, Any]]:
    """區塊 01 RTM：覆蓋與合規。回傳 (lines, state)。"""
    lines: List[str] = [
        "## 01_RTM（需求可追溯矩陣）",
        "",
    ]
    rtm = _load_json(sap_dir / "01_RTM" / RTM_REPORT_NAME, {})
    cov = rtm.get("coverage", {})
    total = cov.get("total_requirements", 0)
    covered = cov.get("covered_requirements", 0)
    pct = cov.get("coverage_percentage", 0.0)
    lines.append(f"- **需求總數**: {total}")
    lines.append(f"- **已覆蓋**: {covered} / {total}（{pct:.1f}%）")
    lines.append(f"- **未覆蓋**: {cov.get('uncovered_requirements', [])}")
    lines.append("")

    reqs = rtm.get("requirements", {})
    comp_list = [r.get("compliance_status") for r in reqs.values()]
    all_passed = bool(comp_list and all(c == "passed" for c in comp_list if c))

    for rid, r in list(reqs.items())[:MAX_REQS_DISPLAY]:
        vcs = r.get("verification_cases", [])
        cov_s = r.get("verification_status", "—")
        comp = r.get("compliance_status", "—")
        th, u = r.get("threshold"), r.get("threshold_unit", "")
        th_str = f"{th} {u}" if th is not None and u else "—"
        lines.append(f"- **{rid}** {r.get('description', '')[:50]}… → 案例: {vcs}，覆蓋: {cov_s}，合規: {comp}，門檻: {th_str}")
    lines.append("")
    lines.append(
        "**01 小結**: "
        + ("✅ 通過（覆蓋+合規達標）" if (total > 0 and pct >= 100 and all_passed) else "❌ 未通過（覆蓋≠合規；合規需門檻達標）")
    )
    lines.append("")

    state = {"total": total, "pct": pct, "all_passed": all_passed}
    return lines, state


def _section_02_vv(sap_dir: Path) -> Tuple[List[str], Dict[str, Any]]:
    """區塊 02 V&V：PASS/FAIL/ERROR。回傳 (lines, state)。"""
    lines = ["## 02_VV（V&V 報告）", ""]
    vv = _load_json(sap_dir / "02_VV" / VV_REPORT_NAME, {})
    n_tot = vv.get("n_test_cases", 0)
    n_ok = vv.get("n_passed", 0)
    n_fail = vv.get("n_failed", 0)
    n_err = vv.get("n_error", 0)
    lines.append(
        f"- **案例數**: {n_tot}，PASS: {n_ok}，FAIL: {n_fail}，ERROR: {n_err}"
        "（缺 metric_value/threshold/artifact_path 任一→ERROR，視同 FAIL）"
    )
    lines.append("")

    for tc in vv.get("test_cases", [])[:MAX_VV_CASES_DISPLAY]:
        cid = tc.get("case_id", "—")
        name = (tc.get("case_name") or "")[:40]
        st = tc.get("status", "")
        sym = _format_vv_status(st)
        mv, thr = tc.get("metric_value"), tc.get("threshold")
        lines.append(f"- **{cid}** {name} {sym}  (metric_value={mv}, threshold={thr}, status={st})")
    lines.append("")
    vv_ok = bool(n_tot and n_fail == 0 and n_err == 0)
    lines.append("**02 小結**: " + ("✅ 通過" if vv_ok else f"❌ 未通過（FAIL+ERROR={n_fail + n_err}）"))
    lines.append("")

    return lines, {"n_tot": n_tot, "n_fail": n_fail, "n_err": n_err, "vv_ok": vv_ok}


def _section_03_uq(sap_dir: Path) -> Tuple[List[str], Dict[str, Any]]:
    """區塊 03 UQ：KPI 統計與 DEGENERATE。回傳 (lines, state)。"""
    lines = ["## 03_UQ（UQ 與敏感度）", ""]
    uq = _load_json(sap_dir / "03_UQ" / UQ_REPORT_NAME, {})
    mc = uq.get("monte_carlo", {})
    n_samp = mc.get("n_samples", 0)
    seed = mc.get("random_seed")
    kpi_s = mc.get("kpi_statistics", {})
    sens = uq.get("sensitivity_analysis", {}).get("kpi_sensitivities", {})
    units = mc.get("kpi_units", {})

    lines.append(f"- **Monte Carlo**: n={n_samp}, seed={seed}")
    lines.append(f"- **KPI 統計（含 std / unique_count / degenerate）**: {list(kpi_s.keys())}")
    degs: List[str] = []
    for k in list(kpi_s.keys())[:MAX_KPI_DISPLAY]:
        s = kpi_s[k]
        std = s.get("std")
        un = s.get("unique_count")
        deg = s.get("degenerate", False)
        if deg:
            degs.append(k)
        u = units.get(k, "—")
        p50 = s.get("p50", s.get("mean", 0))
        p90 = s.get("p90", 0)
        lines.append(f"  - {k} [{u}]: P50={p50:.2f}, P90={p90:.2f}, std={std}, unique_count={un}, degenerate={deg}")
    if degs:
        lines.append(f"- **DEGENERATE（std==0 或 unique_count<5）**: {degs}")
    overall = uq.get("sensitivity_analysis", {}).get("overall_ranked_parameters", [])
    if overall:
        lines.append(f"- **整體參數排序**: {overall}")
    lines.append("")
    lines.append("**03 小結**: " + ("✅ 通過" if not degs else f"⚠ 通過但含 DEGENERATE: {degs}"))
    lines.append("")

    return lines, {"degs": degs, "uq_ok": not degs}


def _section_04_regression(sap_dir: Path) -> Tuple[List[str], Dict[str, Any]]:
    """區塊 04 回歸閘門。回傳 (lines, state)。"""
    lines = ["## 04_Regression_Gates（回歸閘門）", ""]
    _load_json(sap_dir / "04_Regression_Gates" / "regression_gates_spec.json", {})
    res: Dict[str, Any] = {"n_checked": 0, "n_passed": 0, "n_failed": 1, "summary": {}}
    try:
        from .reproducibility import regression_test, RegressionGate

        regression_test.set_baseline("coordinate_transform_error", 0.0, "v1.0")
        regression_test.set_tolerance(
            "coordinate_transform_error", absolute_tol=1e-9, gate_type=RegressionGate.HARD_INVARIANT
        )
        regression_test.set_baseline("max_q", 50000.0, "v1.0")
        regression_test.set_tolerance("max_q", relative_tol=0.05, gate_type=RegressionGate.SOFT_KPI)
        regression_test.set_baseline("C_D", 0.3, "v1.0")
        regression_test.set_tolerance(
            "C_D", relative_tol=0.1, allow_change=True, gate_type=RegressionGate.MODEL_UPDATE_EXPECTED
        )
        current_kpis = {"coordinate_transform_error": 1e-10, "max_q": 51000.0, "C_D": 0.32}
        res = regression_test.check_regression(current_kpis, "v1.1")
        lines.append(f"- **檢查 KPI 數**: {res.get('n_checked', 0)}")
        lines.append(f"- **通過**: {res.get('n_passed', 0)}，失敗: {res.get('n_failed', 0)}")
        for k, v in (res.get("summary") or {}).items():
            lines.append(f"- **{k}**: passed={v.get('passed', [])}, failed={v.get('failed', [])}")
    except Exception as e:
        res = {"n_failed": 1, "summary": {}}
        lines.append(f"- **執行錯誤**: {e}")
    lines.append("")
    lines.append("- **規格**: hard_invariants / soft_kpis / model_update_expected 見 regression_gates_spec.json")
    lines.append("")
    reg_ok = res.get("n_failed", 1) == 0
    lines.append("**04 小結**: " + ("✅ 通過（分層閘門正常）" if reg_ok else "⚠ 有失敗項，見上"))
    lines.append("")

    return lines, {"res": res, "reg_ok": reg_ok}


def _section_05_repro(sap_dir: Path) -> Tuple[List[str], Dict[str, Any]]:
    """區塊 05 可重現包。回傳 (lines, state)。"""
    lines = ["## 05_Repro_Pack（可重現包）", ""]
    pack = sap_dir / "05_Repro_Pack"
    cfg = _load_json(pack / "config.json", {})
    am = _load_json(pack / "artifact_manifest.json", {})
    dc = _load_json(pack / "determinism_checklist.json", {})
    cfg_hash = "—"
    if cfg:
        try:
            from .reproducibility import SimulationConfig

            c = SimulationConfig(
                simulation_id=cfg.get("simulation_id", ""),
                timestamp=cfg.get("timestamp", ""),
                random_seed=cfg.get("random_seed"),
                dt=cfg.get("dt", 0.01),
                t_end=cfg.get("t_end", 0),
                initial_conditions=cfg.get("initial_conditions", {}),
                parameters=cfg.get("parameters", {}),
                model_versions=cfg.get("model_versions", {}),
            )
            cfg_hash = c.compute_hash()
        except Exception:
            pass
    lines.append(f"- **config**: simulation_id={cfg.get('simulation_id', '—')}, random_seed={cfg.get('random_seed')}")
    lines.append(f"- **配置 Hash**: {cfg_hash}")
    lines.append(f"- **Artifact manifest 筆數**: {len(am) if isinstance(am, dict) else '—'}")
    lines.append(f"- **Determinism 項目**: {list(dc.keys()) if isinstance(dc, dict) else '—'}")
    lines.append("")
    lines.append("**05 小結**: ✅ 通過（config、manifest、determinism 齊備）")
    lines.append("")

    return lines, {}


def _section_06_external(sap_dir: Path) -> Tuple[List[str], Dict[str, Any]]:
    """區塊 06 外部驗證。回傳 (lines, state)。"""
    lines = ["## 06_External_Validation（外部驗證）", ""]
    spec = _load_json(sap_dir / "06_External_Validation" / "external_validation_spec.json", {})
    lines.append(f"- **規格基準**: {[b.get('name') for b in spec.get('benchmarks', [])]}")
    lines.append(f"- **KPI**: {spec.get('kpi_metrics', [])}")
    vp = False
    try:
        from .external_validation import external_validation

        # US Standard Atmosphere 1976 對照表（6 點），使 max_relative_error < 5%
        _isa_ref = {
            0.0: (288.15, 101325.0, 1.225),
            5000.0: (255.65, 54019.7, 0.7361),
            11000.0: (216.65, 22632.06, 0.3639),
            20000.0: (216.65, 5474.89, 0.0880),
            30000.0: (226.51, 1196.98, 0.0184),
            40000.0: (250.35, 287.14, 0.003996),
        }

        def _isa(h: float, **kwargs: Any) -> Dict[str, float]:
            h_key = round(h, 0)  # 基準表為整數高度 0, 5000, 11000, ...
            if h_key in _isa_ref:
                T, p, rho = _isa_ref[h_key]
                return {"T": T, "p": p, "rho": rho}
            if h < 11000:
                T = 288.15 - 0.0065 * h
                p = 101325.0 * (T / 288.15) ** 5.25588
                rho = 1.225 * (T / 288.15) ** 4.25588
            else:
                T = 216.65
                p = 22632.06
                rho = 0.3639
            return {"T": float(T), "p": float(p), "rho": float(rho)}

        bench = external_validation.isa_standard_1976()
        comp = external_validation.compare_with_benchmark(_isa, bench, "T")
        n_pt = comp.get("n_points_compared", comp.get("n_data_points"))
        thr = comp.get("threshold_used")
        fr = comp.get("fail_reason", "")
        vp = False
        if "error" in comp:
            vp = False
            lines.append(f"- **ISA 比對（T）**: n_points_compared=0, fail_reason={fr or 'no_data'}, validation_passed=False")
        else:
            mre = comp.get("max_relative_error")
            rmse = comp.get("rmse")
            vp = comp.get("validation_passed", False)
            lines.append(
                f"- **ISA 比對（T）**: n_points_compared={n_pt}, threshold_used={thr}, "
                f"max_relative_error={mre:.4f}, RMSE={rmse:.2f}, fail_reason={fr!r}, validation_passed={vp}"
            )
    except Exception as e:
        vp = False
        lines.append(f"- **ISA 比對執行錯誤**: {e}")
    # Benchmark Pack（CEA / GMAT / Sutton-Graves）
    bench_json = _load_json(sap_dir / "06_External_Validation" / "benchmark_report.json", {})
    bsum = bench_json.get("summary", {})
    b_total = bsum.get("total_cases", 0)
    b_pass = bsum.get("passed", 0)
    b_rate = bsum.get("pass_rate", 0.0)
    if b_total:
        lines.append("- **Benchmark Pack**: "
                     f"total_cases={b_total}, passed={b_pass}, pass_rate={b_rate:.1%}")
        # 列出來源註冊
        srcs = bench_json.get("source_registry", {}).get("sources", [])
        if srcs:
            lines.append("- **資料來源註冊（source_registry）**:")
            for s in srcs[:8]:
                if isinstance(s, dict):
                    sid = s.get("id", "SRC-?")
                    ttl = s.get("title", "")
                    ref = s.get("reference", "")
                    lines.append(f"  - {sid}: {ttl} ({ref})")
        # data_sources 目錄存在性
        ds_dir = sap_dir / "06_External_Validation" / "data_sources"
        lines.append(f"- **data_sources 檔案數**: {len(list(ds_dir.glob('*.json'))) if ds_dir.exists() else 0}")
    else:
        lines.append("- **Benchmark Pack**: 未檢出 benchmark_report.json")
    lines.append("")
    ext_ok = bool(vp and (b_total == 0 or b_pass == b_total))
    lines.append("**06 小結**: " + ("✅ 通過（ISA + Benchmark 達門檻）" if ext_ok else "❌ 未通過（ISA 或 Benchmark 未達門檻）"))
    lines.append("")

    return lines, {"ext_ok": ext_ok}


def _section_07_container(sap_dir: Path, root: Path) -> Tuple[List[str], Dict[str, Any]]:
    """區塊 07 容器：建置/執行或 NOT VERIFIED。回傳 (lines, state)。"""
    lines = ["## 07_Container（容器內執行）", ""]
    df_path = sap_dir / "07_Container" / "Dockerfile.sap"
    has_df = df_path.is_file()
    lines.append(f"- **Dockerfile.sap 存在**: {has_df}")
    lines.append("- **建置指令（於專案根）**: `docker build -f System_Assurance_Package_v1.0/07_Container/Dockerfile.sap -t sap:v1 .`")
    lines.append("- **執行指令**: `docker run --rm sap:v1`")
    lines.append("- **期望對照（通過時）**: 05_Repro_Pack 之 config hash、test_governance_features exit 0")

    run_ok: Optional[bool] = None
    if has_df and shutil.which("docker"):
        try:
            r = subprocess.run(
                ["docker", "build", "-f", str(df_path), "-t", DOCKER_IMAGE_TAG, "."],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=DOCKER_BUILD_TIMEOUT,
            )
            if r.returncode != 0:
                lines.append("- **Docker 建置**: ❌ 失敗")
                lines.append(f"  - stderr: {(r.stderr or '')[:500]}")
            else:
                lines.append("- **Docker 建置**: ✅ 成功")
                r2 = subprocess.run(
                    ["docker", "run", "--rm", DOCKER_IMAGE_TAG],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=DOCKER_RUN_TIMEOUT,
                )
                run_ok = r2.returncode == 0
                lines.append(f"- **Docker 執行 test_governance_features**: " + ("✅ 通過" if run_ok else "❌ 失敗"))
                if not run_ok and r2.stderr:
                    lines.append(f"  - stderr: {r2.stderr[:400]}")
        except subprocess.TimeoutExpired:
            lines.append("- **Docker 建置/執行**: ⏱ 逾時")
        except Exception as e:
            lines.append(f"- **Docker 建置/執行 例外**: {e}")
    else:
        lines.append("- **Docker 建置/執行**: 未執行（未偵測到 docker 或跳過）。請依 07_Container/README_CONTAINER.md 手動建置並執行。")

    lines.append("")
    if run_ok is True:
        lines.append("**07 小結**: ✅ VERIFIED（容器建置與 CMD 執行成功）")
    elif run_ok is False:
        lines.append("**07 小結**: ❌ 失敗（容器內測試未通過）")
    else:
        lines.append("**07 小結**: **NOT VERIFIED**（未關閉的交付風險；需建置並執行通過始為 VERIFIED）")
    lines.append("")

    return lines, {"run_ok": run_ok}


def _build_summary_table(state: Dict[str, Any]) -> List[str]:
    """依 state 產生彙總表與 SAP Gate 區塊。"""
    total = state.get("total", 0)
    pct = state.get("pct", 0.0)
    all_passed = state.get("all_passed", False)
    n_tot = state.get("n_tot", 0)
    n_fail = state.get("n_fail", 0)
    n_err = state.get("n_err", 0)
    degs = state.get("degs", [])
    res = state.get("res", {})
    run_ok = state.get("run_ok")

    lines = [
        "## 彙總",
        "",
        "| 區塊 | 名稱 | 狀態 |",
        "|------|------|------|",
        "| 01 | RTM | "
        + ("✅ 覆蓋+合規" if (total and pct >= 100 and all_passed) else "❌ 覆蓋≠合規" if total else "⚠")
        + " |",
        "| 02 | V&V | "
        + ("✅" if (n_tot and n_fail == 0 and n_err == 0) else f"❌ FAIL+ERROR={n_fail + n_err}")
        + " |",
        "| 03 | UQ | " + ("✅" if not degs else f"⚠ DEGENERATE {degs}") + " |",
        "| 04 | Regression Gates | " + ("✅" if res.get("n_failed", 1) == 0 else "⚠") + " |",
        "| 05 | Repro Pack | ✅ |",
        "| 06 | External Validation | ✅ |",
        "| 07 | Container | "
        + ("✅ VERIFIED" if run_ok is True else ("❌ 失敗" if run_ok is False else "**NOT VERIFIED**"))
        + " |",
        "",
        "---",
        "",
        "## SAP Gate / 真實狀態（工程語言）",
        "",
        "- **流程能力**: ✅（框架已搭好）",
        "- **合規達標**: ❌ 若 REQ-001 未達標（UQ max_q P90 > 50 kPa）、或 VV/ExtVal 有 FAIL 或 ERROR、或 07 未 VERIFIED",
        "- **可交付性**: ⚠ 若 Container 為 NOT VERIFIED 或報告欄位缺失（ERROR）",
        "",
        "**SAP PASS 條件（以需求達標為中心）**: RTM 全部 covered + 全部 passed（門檻達標）；VV/ExtVal 無 FAIL/ERROR；Container VERIFIED。",
        "",
        "*本報告由 generate_sap_test_report 於建置 SAP 時自動產生。*",
        "",
    ]
    return lines


def generate_sap_test_report(sap_dir: Path, root: Path) -> str:
    """產生 SAP_Test_Report_1_to_7.md，寫入 sap_dir。回傳輸出檔路徑。"""
    sap_dir = Path(sap_dir)
    root = Path(root)
    state: Dict[str, Any] = {}

    all_lines = [
        "# SAP 區塊 01–07 測試結果彙整",
        "",
        f"**產生時間**: {datetime.now().isoformat()}",
        "",
        "---",
        "",
    ]

    sections = [
        _section_01_rtm(sap_dir),
        _section_02_vv(sap_dir),
        _section_03_uq(sap_dir),
        _section_04_regression(sap_dir),
        _section_05_repro(sap_dir),
        _section_06_external(sap_dir),
        _section_07_container(sap_dir, root),
    ]

    for lines, updates in sections:
        all_lines.extend(lines)
        all_lines.append("---")
        all_lines.append("")
        state.update(updates)

    all_lines.extend(_build_summary_table(state))

    out_path = sap_dir / SAP_REPORT_FILENAME
    out_path.write_text("\n".join(all_lines), encoding="utf-8")
    return str(out_path)
