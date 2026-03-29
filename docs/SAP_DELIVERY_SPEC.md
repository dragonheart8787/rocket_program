# System Assurance Package (SAP) v1.0 — 可交付物規格

**目的**：整合 RTM + V&V + UQ + Regression Gates + Repro Pack（含容器），形成**單一工程可交付物**，可供審查與第三方復現。

---

## 一、包內涵蓋

| 區塊 | 內容 | 審查對應 |
|------|------|----------|
| **01_RTM** | 需求可追溯矩陣（REQ-### → 驗證方式 / Case ID / 門檻 / 產物） | 「保證了什麼」 |
| **02_VV** | V&V 報告（驗算、收斂、ISA、基準案例） | 證據鏈 |
| **03_UQ** | UQ 與敏感度（多 KPI、Bootstrap、模型不確定度） | 誤差帶、敏感度 |
| **04_Regression_Gates** | 回歸閘門規格（硬 / 軟 / 預期變動） | 分層回歸 |
| **05_Repro_Pack** | 可重現包（config、hash、manifest、determinism） | 可重現性 |
| **06_External_Validation** | 外部驗證基準規格（ISA、阻力落體、再入、風洞示例） | 外部可置信 |
| **07_Container** | 於容器內實際執行專案（Dockerfile.sap、README_CONTAINER.md） | 一鍵凍結環境、預設 CMD=test_governance_features |

另含：

- **SAP_Test_Report_1_to_7.md**：區塊 01–07 測試結果彙整

- **artifact_manifest.json**：包內各檔案 SHA256
- **README.md**：用途聲明、適用域、**不提供武器化用途**

---

## 二、建置方式

```bash
python build_system_assurance_package.py
```

產出目錄：`System_Assurance_Package_v1.0/`。07_Container 的 Docker 建置與執行方式見 `07_Container/README_CONTAINER.md`。

---

## 三、用途聲明（摘錄，README 內完整）

- 教育與概念驗證；概念設計階段；**非製造級**。
- **不提供武器化用途**（風控必備）。

---

## 四、適用域

- 速度：0–10 Mach（部分模型更窄）
- 高度：0–100 km（ISA 至 86 km）
- 熱 / 結構：簡化模型，需專業工具交叉驗證

---

## 五、與「你說通過就通過」的區隔

本包提供：

1. **需求 → 測試 → 證據** 的 RTM，可回答「保證了什麼」。
2. **外部基準** 與誤差 KPI（最大相對誤差、RMSE、分段）。
3. **模型不確定度**（誤差項 / 集成）與參數 UQ 分開。
4. **分層回歸閘門**，避免一刀切。
5. **Artifact manifest + determinism checklist**，便於排查「跑出來不一樣」。
6. **容器內可執行**（Dockerfile.sap），支援環境凍結與預設 CMD 測試。

此包作為 **System Assurance Package v1.0** 可交付物，用於工程審查與交接。

---

## 六、SAP Gate 規格（四數值契約）

| 項目 | 數值／出處 |
|------|------------|
| **REQ-001 門檻** | 50 kPa = **50_000 Pa**（threshold_unit=Pa）；合規由 UQ-REQ-001 從 UQ 報告讀 max_q P90 判定 |
| **VV-004** | max_relative_error、threshold_used(0.01)、n_reference_points 見 V_V_Report；metric_value 取自 max(max_relative_errors) |
| **External Validation** | n_points_compared、threshold_used(0.05)、fail_reason(no_data / metric_exceeded) 見 compare_with_benchmark 回傳 |
| **max_q 輸出單位** | **Pa**（UQ 報告 kpi_units.max_q = Pa） |

Coverage ≠ Compliance：覆蓋率 100% 僅表有對應案例；合規需門檻達標（compliance_status=passed）。07 未建置/執行＝**NOT VERIFIED**。
