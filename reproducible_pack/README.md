# 可重現性包

## 配置
- 模擬 ID: sim_001
- 時間戳: 2026-03-12T08:39:54.997536
- 配置 Hash: b4980a5d447d8964
- 隨機種子: 42

## 版本資訊
- Git Commit: N/A
- Python: 3.14.3

## 模型版本
- aero_table: v1.0 (hash: 37007c776e809d59)
- material_db: v1.0 (hash: 98108d102073fb64)

## 依賴
見 version_info.json

## Artifact Manifest
所有檔案的 SHA256 hash 見 artifact_manifest.json

## Determinism Checklist
見 determinism_checklist.json

## 使用方法
1. 安裝依賴: `pip install -r requirements.txt` 或使用 Docker/Conda
2. 設置環境變數: `export OMP_NUM_THREADS=1` (BLAS 線程)
3. 運行模擬: 使用 config.json 中的參數
4. 驗證結果: 對照 output_summary.json 和 artifact_manifest.json
