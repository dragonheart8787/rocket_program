# 火箭外觀與引擎完整設計生成器

`rocket_design_generator.py` 可依規格生成**火箭外觀幾何**與**引擎完整設計**，並匯出 JSON / SVG。

---

## 功能摘要

| 模組 | 內容 |
|------|------|
| **外觀** | 鼻錐（Von Kármán / 圓錐 / 橢圓 / Sears-Haack）、多段箭體、梯形尾翼 |
| **引擎** | 燃燒室壓力、喉部/出口面積、膨脹比、推力、比衝、質量流率、噴管輪廓 |
| **匯出** | 外觀 → `exterior.json`、`exterior.svg`；引擎 → `engine.json` |

---

## 使用方式

### 快速執行範例

```bash
python rocket_design_example.py
```

會在 `rocket_design_output/` 產生：
- `exterior.json`：外觀輪廓點與規格
- `exterior.svg`：2D 側視圖
- `engine.json`：引擎參數與噴管輪廓

### 程式呼叫

```python
from rocket_design_generator import (
    NoseConeSpec, BodyStageSpec, FinSpec, RocketExteriorSpec,
    EngineDesignSpec, generate_full_rocket_design,
)

# 外觀
nose = NoseConeSpec(type="von_karman", length_m=2.0, base_radius_m=0.5)
body = [BodyStageSpec(4.0, 0.5, "第一級"), BodyStageSpec(3.0, 0.5, "第二級")]
fins = FinSpec(count=4, root_chord_m=0.8, tip_chord_m=0.3, span_m=0.4, sweep_deg=35.0, position_from_tail_m=0.2)
exterior_spec = RocketExteriorSpec(nose=nose, body_stages=body, fins=fins)

# 引擎
engine_spec = EngineDesignSpec(
    propellant_id="LOX_RP1",
    thrust_vac_N=800_000.0,
    chamber_pressure_Pa=2.0e6,
    expansion_ratio=25.0,
    burn_time_s=180.0,
)

# 一鍵生成並寫入目錄
result = generate_full_rocket_design(exterior_spec, engine_spec, output_dir="my_rocket")
print(result["summary"])
```

---

## 外觀規格說明

- **NoseConeSpec**  
  - `type`: `"von_karman"` | `"conical"` | `"elliptical"` | `"sears_haack"`  
  - `length_m`, `base_radius_m`：長度與底部半徑（m）  
  - `von_karman_n`：僅 Von Kármán 時使用，預設 0.75  

- **BodyStageSpec**  
  - `length_m`, `radius_m`：該段圓柱長度與半徑（m）  

- **FinSpec**  
  - `count`：尾翼片數  
  - `root_chord_m`, `tip_chord_m`, `span_m`：根弦、梢弦、展長（m）  
  - `sweep_deg`：前緣後掠角（度）  
  - `position_from_tail_m`：前緣根部距箭尾距離（m）  

---

## 引擎規格與推進劑

- **EngineDesignSpec**  
  - `propellant_id`：見下表  
  - `thrust_vac_N`：真空推力（N）  
  - `chamber_pressure_Pa`：燃燒室壓力（Pa）  
  - `expansion_ratio`：A_e / A_t  
  - `burn_time_s`：可選，燃燒時間（s），用於計算推進劑質量  
  - `nozzle_efficiency`, `C_d`：噴管效率與流量係數  

| propellant_id | 說明 |
|---------------|------|
| LOX_LH2       | 液氧/液氫 |
| LOX_RP1       | 液氧/煤油 |
| NTO_UDMH      | 四氧化二氮/UDMH |
| Solid_HTPB    | HTPB 固體 |

---

## 輸出欄位摘要

- **exterior.json**：`total_length_m`, `max_radius_m`, `profile.x_m` / `profile.r_m`，尾翼多邊形、規格摘要。  
- **engine.json**：`F_vac_N`, `F_sea_N`, `I_sp_vac_s`, `I_sp_sea_s`, `mdot_kg_s`, `p_c_Pa`, `T_c_K`, `A_t_m2`, `A_e_m2`, `D_t_m`, `D_e_m`, `expansion_ratio`, `M_exit`, `p_e_Pa`, `v_e_m_s`, `c_star_m_s`, `C_F_vac`，以及 `nozzle_contour.x_m` / `r_m`。  

依賴：`von_karman_tsien_theory`（鼻錐輪廓）、`aerospace_sim.EngineeringFormulas`（可選，推力係數）。

---

## NASA CEA / RocketCEA（可選）

若安裝 **RocketCEA**（`pip install rocketcea`），引擎設計與系統驅動會**自動採用 NASA CEA 化學平衡**計算燃燒室溫度、比熱比、氣體常數與特徵速度，用於：

- `rocket_design_generator.generate_engine_design`：依 `propellant_id`、`chamber_pressure_Pa`、`expansion_ratio` 查 CEA，取得 T_c、γ、R 後再算喉部/出口與噴管輪廓。
- `rocket_system_driver.run_full_design`：依 `RocketSystemConfig.propellant_id` 與燃燒室壓力、膨脹比取得 CEA 結果，傳入推進與熱分析模組。

對應關係（本專案 → RocketCEA）：`LOX_RP1`→LOX/RP1、`LOX_LH2`→LOX/LH2、`NTO_UDMH`→N2O4/UDMH、`N2O4_MMH`→N2O4/MMH、`LOX_CH4`→LOX/CH4。未安裝 RocketCEA 或無對應推進劑時，沿用內建 `PROPELLANT_DB` 與等熵公式。

- **NASA CEA**：https://www1.grc.nasa.gov/research-and-engineering/ceaweb/  
- **RocketCEA**：https://rocketcea.readthedocs.io/
