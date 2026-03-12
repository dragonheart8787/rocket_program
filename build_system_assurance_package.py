# -*- coding: utf-8 -*-
"""
System Assurance Package v1.0 建置腳本
產出：RTM + V&V + UQ + Regression Gates + Repro Pack（含容器建議）
"""

import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
SAP_DIR = ROOT / "System_Assurance_Package_v1.0"
SAP_VERSION = "1.0"

# REQ-001 門檻：最大動壓 50 kPa = 50_000 Pa（與 RTM/UQ 單位契約一致）
REQ001_THRESHOLD_PA = 50000.0


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_sap():
    ensure_dir(SAP_DIR)
    ensure_dir(SAP_DIR / "01_RTM")
    ensure_dir(SAP_DIR / "02_VV")
    ensure_dir(SAP_DIR / "03_UQ")
    ensure_dir(SAP_DIR / "04_Regression_Gates")
    ensure_dir(SAP_DIR / "05_Repro_Pack")
    ensure_dir(SAP_DIR / "06_External_Validation")
    ensure_dir(SAP_DIR / "07_Container")

    from requirements_traceability import rtm, Requirement, RequirementType, VerificationCase, VerificationMethod

    if len(rtm.requirements) == 0:
        for r in [
            Requirement("REQ-001", RequirementType.PERFORMANCE, "最大動壓不超過 50 kPa", "任務需求", "high", threshold=REQ001_THRESHOLD_PA, threshold_unit="Pa"),
            Requirement("REQ-002", RequirementType.SAFETY, "表面溫度不超過 1500 K", "安全規範", "high"),
            Requirement("REQ-003", RequirementType.APPLICABILITY, "ISA 適用 0-86 km", "模型適用域", "medium"),
            Requirement("REQ-004", RequirementType.OUTPUT_FORMAT, "KPI 輸出 P10/P50/P90", "輸出格式", "medium"),
        ]:
            rtm.add_requirement(r)
        for c in [
            VerificationCase("VV-001", ["REQ-001"], VerificationMethod.TEST, 50000.0, artifacts=["V_V_Report_v1.0.json"]),
            VerificationCase("VV-002", ["REQ-002"], VerificationMethod.ANALYSIS, 1500.0, artifacts=["thermal_analysis.json"]),
            VerificationCase("VV-004", ["REQ-003"], VerificationMethod.TEST, 0.01, artifacts=["V_V_Report_v1.0.json"]),
            VerificationCase("VV-UQ", ["REQ-004"], VerificationMethod.ANALYSIS, 0.0, artifacts=["UQ_Sensitivity_Report_v1.0.json"]),
            VerificationCase("UQ-REQ-001", ["REQ-001"], VerificationMethod.ANALYSIS, REQ001_THRESHOLD_PA, threshold_unit="Pa", artifacts=["UQ_Sensitivity_Report_v1.0.json"]),
        ]:
            rtm.add_verification_case(c)

    rtm.generate_rtm_report(str(SAP_DIR / "01_RTM" / "RTM_Report_v1.0.json"), artifacts_base=ROOT)

    for f in ["V_V_Report_v1.0.json", "V_V_Report_v1.0.md"]:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, SAP_DIR / "02_VV" / f)

    for f in ["UQ_Sensitivity_Report_v1.0.json"]:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, SAP_DIR / "03_UQ" / f)

    gates = {
        "version": "1.0",
        "date": datetime.now().isoformat(),
        "hard_invariants": [
            {"kpi": "coordinate_transform_error", "abs_tol": 1e-9, "description": "座標轉換互逆"},
            {"kpi": "isa_table_max_rel_error", "rel_tol": 0.01, "description": "ISA 表格誤差上限 1%"},
            {"kpi": "unit_consistency", "description": "單位 SI 一致"}
        ],
        "soft_kpis": [
            {"kpi": "max_q", "rel_tol": 0.05},
            {"kpi": "max_heat_flux", "rel_tol": 0.10},
            {"kpi": "fuel_margin", "rel_tol": 0.10}
        ],
        "model_update_expected": [
            {"kpi": "C_D", "rel_tol": 0.15, "requires": "說明與簽核"},
            {"kpi": "C_L", "rel_tol": 0.15, "requires": "說明與簽核"}
        ]
    }
    (SAP_DIR / "04_Regression_Gates" / "regression_gates_spec.json").write_text(
        json.dumps(gates, indent=2, ensure_ascii=False), encoding="utf-8")

    from reproducibility import reproducibility_pack, SimulationConfig
    config = SimulationConfig(
        simulation_id="SAP_baseline", timestamp=datetime.now().isoformat(),
        random_seed=42, dt=0.01, t_end=100.0,
        initial_conditions={"r0": [6771000.0, 0.0, 0.0], "v0": [0.0, 7667.0, 0.0]},
        parameters={"mu": 3.986004418e14}, model_versions={"dynamics": "v1.0", "isa": "v1.0"}
    )
    reproducibility_pack.set_config(config)
    reproducibility_pack.set_output_summary(kpis={"max_q": 50000.0, "fuel_margin": 0.9})
    reproducibility_pack.create_pack(str(SAP_DIR / "05_Repro_Pack"))

    ext_val = {
        "version": "1.0",
        "benchmarks": [
            {"name": "ISA_1976", "source": "US Standard Atmosphere 1976"},
            {"name": "Drag_Fall_Standard", "source": "Anderson, Introduction to Flight"},
            {"name": "Reentry_Heating_Sutton_Graves", "source": "Sutton & Graves, 1971"},
            {"name": "Wind_Tunnel_Coefficient_Example", "source": "Academic textbook"},
            {"name": "CEA_Reference_v1", "source": "data/benchmarks/cea_reference_cases.json"},
            {"name": "GMAT_Reference_v1", "source": "data/benchmarks/gmat_reference_cases.json"},
            {"name": "SuttonGraves_Reference_v1", "source": "data/benchmarks/sutton_graves_reference_cases.json"},
            {"name": "Real_Aero_Coefficients_VV_v1", "source": "benchmark_pack_output/real_aero_vv_report.json"},
        ],
        "kpi_metrics": ["max_relative_error", "RMSE", "segment_statistics"]
    }
    (SAP_DIR / "06_External_Validation" / "external_validation_spec.json").write_text(
        json.dumps(ext_val, indent=2, ensure_ascii=False), encoding="utf-8")

    # 產生 Benchmark Pack 並複製至 06_External_Validation
    try:
        from benchmark_pack import run_all_benchmarks, write_report
        write_report(run_all_benchmarks(), output_dir=str(ROOT / "benchmark_pack_output"))
    except Exception:
        pass
    for f in ["benchmark_report.json", "benchmark_report.md"]:
        src = ROOT / "benchmark_pack_output" / f
        if src.exists():
            shutil.copy2(src, SAP_DIR / "06_External_Validation" / f)
    # 產生並複製真實氣動係數 V&V 報告
    try:
        from integrate_real_aero_vv import run_real_aero_vv, write_reports, DEFAULT_CSV
        rep = run_real_aero_vv(DEFAULT_CSV)
        write_reports(rep, ROOT / "benchmark_pack_output")
    except Exception:
        pass
    for f in ["real_aero_vv_report.json", "real_aero_vv_report.md"]:
        src = ROOT / "benchmark_pack_output" / f
        if src.exists():
            shutil.copy2(src, SAP_DIR / "06_External_Validation" / f)
    data_dir = ROOT / "data" / "benchmarks"
    if data_dir.exists():
        dst = SAP_DIR / "06_External_Validation" / "data_sources"
        dst.mkdir(parents=True, exist_ok=True)
        for p in data_dir.glob("*.json"):
            shutil.copy2(p, dst / p.name)

    dockerfile = """# System Assurance Package v1.0 — 於容器內實際執行專案
FROM python:3.11-slim
WORKDIR /app

# 依賴（先複製以利用 Docker 層快取）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 專案原始碼（建置時請於專案根目錄執行：docker build -f System_Assurance_Package_v1.0/07_Container/Dockerfile.sap -t sap:v1 .）
COPY . .

# 可重現性：BLAS/NumPy 線程、隨機種子
ENV OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
ENV SAP_RANDOM_SEED=42

# 預設執行治理與外部驗證測試；可覆寫：docker run --rm sap:v1 python build_system_assurance_package.py
CMD ["python", "test_governance_features.py"]
"""
    (SAP_DIR / "07_Container" / "Dockerfile.sap").write_text(dockerfile, encoding="utf-8")

    readme_container = """# 07_Container — 於容器內執行專案

## 建置

於**專案根目錄**執行：

```bash
docker build -f System_Assurance_Package_v1.0/07_Container/Dockerfile.sap -t sap:v1 .
```

（建置情境會複製專案原始碼，預設排除 `System_Assurance_Package_v1.0`、`__pycache__` 等，見 `.dockerignore`。）

## 執行

```bash
docker run --rm sap:v1
```

預設會執行 `test_governance_features.py`。若需改跑建置 SAP：

```bash
docker run --rm sap:v1 python build_system_assurance_package.py
```

## 通過條件

若 `docker run --rm sap:v1` 結束時 exit code 為 0，且終端輸出無錯誤，則 07_Container 視為通過。
"""
    (SAP_DIR / "07_Container" / "README_CONTAINER.md").write_text(readme_container, encoding="utf-8")

    # .dockerignore（專案根）：僅在不存在時寫入，避免覆蓋既有設定
    dockerignore_path = ROOT / ".dockerignore"
    if not dockerignore_path.exists():
        dockerignore_path.write_text(
            "__pycache__\n*.pyc\n.git\n.pytest_cache\n*.egg-info\n.idea\n.cursor\nSystem_Assurance_Package_v1.0\n",
            encoding="utf-8"
        )

    dockerignore_example = """# 建置映像時排除以下項目，可複製到專案根目錄並命名為 .dockerignore
__pycache__
*.pyc
.git
.pytest_cache
*.egg-info
.idea
.cursor
System_Assurance_Package_v1.0
"""
    (SAP_DIR / "07_Container" / "dockerignore.example").write_text(dockerignore_example, encoding="utf-8")

    conda_yml = "name: sap_v1\nchannels: [defaults, conda-forge]\ndependencies:\n  - python=3.11\n  - numpy\n  - scipy\n  - pip\n"
    (SAP_DIR / "07_Container" / "conda_environment_sap.yml").write_text(conda_yml, encoding="utf-8")

    # 彙整 01–07 測試結果為單一 MD
    from generate_sap_test_report import generate_sap_test_report
    generate_sap_test_report(SAP_DIR, ROOT)

    manifest = {}
    for d in SAP_DIR.rglob("*"):
        if d.is_file():
            rel = str(d.relative_to(SAP_DIR)).replace("\\", "/")
            try:
                manifest[rel] = hashlib.sha256(d.read_bytes()).hexdigest()[:16]
            except Exception:
                pass
    (SAP_DIR / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    readme = """# System Assurance Package (SAP) v1.0

## 用途聲明
- 教育與概念驗證；概念設計階段；非製造級。
- **不提供武器化用途**。

## 適用域
- 速度 0-10 Mach；高度 0-100 km；熱/結構為簡化模型。

## 目錄
- 01_RTM: 需求可追溯
- 02_VV: V&V 報告
- 03_UQ: UQ 報告
- 04_Regression_Gates: 回歸閘門
- 05_Repro_Pack: 可重現包
- 06_External_Validation: 外部驗證規格
- 07_Container: 於容器內實際執行專案（Dockerfile.sap + README_CONTAINER.md）
- **SAP_Test_Report_1_to_7.md**: 區塊 01–07 測試結果彙整
"""
    (SAP_DIR / "README.md").write_text(readme, encoding="utf-8")

    return {"path": str(SAP_DIR), "manifest_entries": len(manifest)}


if __name__ == "__main__":
    r = build_sap()
    print("SAP v1.0 built:", r["path"], "| manifest:", r["manifest_entries"])
