# Benchmark 資料與資料來源

本專案將外部對標基準資料放在：

- `data/benchmarks/source_registry.json`：來源註冊表（來源 ID、標題、引用、URL）
- `data/benchmarks/cea_reference_cases.json`：CEA 對標案例
- `data/benchmarks/gmat_reference_cases.json`：GMAT / 軌道對標案例
- `data/benchmarks/sutton_graves_reference_cases.json`：Sutton–Graves 對標案例

## 使用方式

`benchmark_pack.py` 會直接讀取上述 JSON，執行後輸出：

- `benchmark_pack_output/benchmark_report.json`
- `benchmark_pack_output/benchmark_report.md`

`build_system_assurance_package.py` 會把報告與資料來源複製進：

- `System_Assurance_Package_v1.0/06_External_Validation/benchmark_report.json`
- `System_Assurance_Package_v1.0/06_External_Validation/benchmark_report.md`
- `System_Assurance_Package_v1.0/06_External_Validation/data_sources/*.json`

## 來源治理原則

1. 新增案例時，先在 `source_registry.json` 註冊來源。
2. 對標案例必須填 `threshold_rel` 與 `notes`。
3. 不可只保留硬編碼參考值，必須保留可追溯資料檔與引用。
