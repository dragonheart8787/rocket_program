# TRL4 升級路線圖與實作摘要

對應工程審查建議之三項動作，本專案已實作並可一鍵執行。

---

## 1. Benchmark Pack（CEA + GMAT + Sutton-Graves）

### 模組：`benchmark_pack.py`

- **CEA 對標**：RocketCEA 計算 LOX/RP1、LOX/LH2 之 Isp、T_c，與文獻典型值比對
- **GMAT / 使命規劃對標**：軌道速度、ΔV 預算與圓軌解析解／典型值比對；若 GMAT 可用則執行腳本
- **Sutton-Graves 對標**：`aerospace_sim.ThermalTPS.heating_rate` 與公式手算值比對

### 使用方式

```bash
python benchmark_pack.py
```

輸出：`benchmark_pack_output/benchmark_report.json`、`benchmark_report.md`

### Pass 門檻

- 相對誤差 ≤ 5%（可調 `REPORT_REL_TOL`）

---

## 2. 氣動升級（可插拔來源 + 不確定度 + 覆蓋率）

### 模組：`aero_upgrade.py`

- **可插拔來源**：`AeroSource` 介面
  - `AeroTableSource`：包裝既有 `AeroTable`
  - `AeroSurrogateSource`：接 ML 代理
  - `load_aero_from_csv`：從 CSV 載入
  - `get_pluggable_aero(source="placeholder"|"csv"|"surrogate", ...)`
- **不確定度模型**：`AeroUncertaintyWrapper`，係數附 `(mean, std)`
- **覆蓋率檢查**：`check_coverage(alpha_deg, M, space)`，回傳 `covered_ratio`、`coverage_ok`、`gaps`
- **與 aerospace_sim 整合**：`aero_source_to_table()` 將 `AeroSource` 採樣為 `AeroTable`，供 `AeroModel.table` 使用

### 使用方式

```python
from aero_upgrade import get_pluggable_aero, check_coverage, DesignSpace, aero_source_to_table
from aerospace_sim import AeroModel

source = get_pluggable_aero(source="placeholder", uncertainty={"C_L": 0.05, "C_D": 0.10})
tbl = aero_source_to_table(source, np.linspace(-5, 15, 11), np.linspace(0.3, 1.5, 9))
model = AeroModel(table=tbl)
```

---

## 3. AI Surrogate 管線

### 模組：`ai_surrogate_pipeline.py`

- **DOE**：`latin_hypercube_sample`、`sobol_sample_from_salib`（若已裝 SALib）
- **Surrogate**：`SimpleGP`（簡化 GP，具 mean/std）、`build_aero_surrogate`、`build_heat_flux_surrogate`、`build_margin_surrogate`
- **Fail-closed**：`FailClosedSurrogate`，OOD 時回退 truth model；`ood_distance_to_nearest`、`is_in_domain`
- **Active Learning**：`active_learning_iteration`，依不確定度補樣本
- **Pareto**：`pareto_front_2d`、`nsga2_crowding_distance`

### 建議 ROI 順序

1. **氣動代理**：Mach, α, Re → C_L, C_D
2. **熱通量代理**：trajectory state → q̇
3. **結構裕度代理**：loads + geometry + material → MOS

### 使用方式

```python
from ai_surrogate_pipeline import (
    latin_hypercube_sample,
    build_aero_surrogate,
    pareto_front_2d,
)
import numpy as np

bounds = [(0.3, 1.5), (-5, 15), (5.0, 7.0)]  # M, alpha_deg, log10(Re)
X = latin_hypercube_sample(bounds, 50, seed=42)
y_cl = ...  # truth model
y_cd = ...
surr = build_aero_surrogate(X, y_cl, y_cd, bounds)
```

---

## 4. 一鍵執行

```bash
python run_tr14_upgrade.py
```

依序執行：Benchmark Pack → 氣動升級檢查 → AI Surrogate 示範。

---

## 5. 風險控制（審查建議）

| 風險 | 控制 |
|------|------|
| 氣動佔位 | 使用 `aero_upgrade` 插拔 CFD/風洞/代理；覆蓋率檢查 |
| V&V 偏內部 | Benchmark Pack 提供 CEA/GMAT/Sutton-Graves 外部對標 |
| Surrogate 外推 | Fail-closed + OOD 偵測 + 回退 truth model |
| 可重現性 | 維持既有 SAP 流程；Benchmark 報告可納入 Reproducible Pack |
