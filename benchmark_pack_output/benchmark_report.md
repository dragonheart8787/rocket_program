# Benchmark Pack 誤差報告
**生成時間**: 2026-02-21T15:15:15.877673Z

## 資料來源
- **SRC-USSA1976**: U.S. Standard Atmosphere, 1976 (NOAA-S/T 76-1562) — https://www.ngdc.noaa.gov/stp/space-weather/online-publications/miscellaneous/us-standard-atmosphere-1976/
- **SRC-SUTTON-GRAVES-1971**: A General Stagnation-Point Convective Heating Equation for Arbitrary Gas Mixtures (Sutton, K. and Graves, R.A.) — https://ntrs.nasa.gov/
- **SRC-GMAT**: General Mission Analysis Tool (GMAT) (GMAT Documentation) — https://gmat.atlassian.net/
- **SRC-CEA**: Chemical Equilibrium with Applications (CEA) (RP-1311) — https://www1.grc.nasa.gov/research-and-engineering/ceaweb/
- **SRC-ROCKETCEA**: RocketCEA Documentation (RocketCEA v1.2.x docs) — https://rocketcea.readthedocs.io/

## 摘要
- 總案例: 8
- 通過: 8
- 失敗: 0
- 通過率: 100.0%

## CEA 對標
| Case | 名稱 | 通過 | 參考值 | 模型值 | 相對誤差 | 門檻 |
|------|------|------|--------|--------|----------|------|
| CEA-001 | LOX_RP1 Isp_vac_s | ✅ | 340.00 | 345.73 | 0.0169 | 0.05 |
| CEA-002 | LOX_RP1 T_c_K | ✅ | 3650.00 | 3493.21 | 0.0430 | 0.05 |
| CEA-003 | LOX_LH2 Isp_vac_s | ✅ | 450.00 | 452.08 | 0.0046 | 0.05 |

## GMAT / 使命規劃對標
| Case | 名稱 | 通過 | 參考值 | 模型值 | 相對誤差 | 門檻 |
|------|------|------|--------|--------|----------|------|
| GMAT-001 | LEO_400km_orbital_velocity | ✅ | 7668.60 | 7672.60 | 0.0005 | 0.01 |
| GMAT-002 | LEO_total_dv_budget | ✅ | 9400.00 | 9082.60 | 0.0338 | 0.05 |

## Sutton-Graves 對標
| Case | 名稱 | 通過 | 參考值 | 模型值 | 相對誤差 | 門檻 |
|------|------|------|--------|--------|----------|------|
| SG-001 | Sutton-Graves h=70km V=7.0km/s | ✅ | 1396467 | 1396467 | 0.00e+00 | 1e-05 |
| SG-002 | Sutton-Graves h=50km V=5.0km/s | ✅ | 1846659 | 1846659 | 0.00e+00 | 1e-05 |
| SG-003 | Sutton-Graves h=40km V=4.0km/s | ✅ | 1876605 | 1876605 | 0.00e+00 | 1e-05 |