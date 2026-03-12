# Reproducible Run Pack Spec v1.0

## 目的
確保每次運行都能完整重現結果。

## 包含內容

1. **config.json**: 完整模擬配置
   - 隨機種子: 42
   - 配置 Hash: b4980a5d447d8964

2. **model_versions.json**: 模型版本與 hash

3. **version_info.json**: Git commit、依賴版本

4. **output_summary.json**: 輸出 KPI 摘要

5. **README.md**: 使用說明

## 回歸測試

基準 KPI:
- max_q: 50000.0 (不允許變化 > 5%)
- fuel_margin: 0.9 (允許變化 < 10%)

## 使用方法

1. 解壓縮包
2. 安裝依賴: `pip install -r requirements.txt`
3. 運行: 使用 config.json 中的參數
4. 驗證: 對照 output_summary.json

## 驗證

配置 Hash 應匹配，確保輸入一致。
模型 Hash 應匹配，確保模型一致。
輸出 KPI 應在回歸測試容許範圍內。
