# Changelog

本專案依 [Semantic Versioning](https://semver.org/lang/zh-TW/) 標註版本；Git **Tags** 建議與此對齊（例如 `v1.0.0`）。

## [1.0.0] — 2026-03-29

### Added
- `rocket_program` 套件：任務規劃、推進、結構、熱力、GNC、外觀／引擎設計生成
- V&V、UQ／敏感度、可重現包、Benchmark Pack、氣動升級與代理管線
- 根目錄精簡：`scripts/` 啟動腳本、`docs/` 說明文件
- `pyproject.toml`（pip 可安裝）、`LICENSE`（MIT）、整合版 `README.md`

### Changed
- 專案內 `import` 改為套件內相對匯入；資料路徑以儲存庫根目錄為準
