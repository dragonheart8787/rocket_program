# 外部工具與橋接模組

本專案透過橋接模組與以下外部工具整合，以提升燃燒、CFD、結構、軌道與火箭設計能力。除 **RocketCEA** 與 **Cantera** 可經 `pip` 安裝外，其餘需自行安裝並設定環境。

---

## 1. NASA CEA / RocketCEA

| 項目 | 說明 |
|------|------|
| **用途** | 化學平衡燃燒：燃燒室溫度、比熱比、氣體常數、特徵速度、真空比衝 |
| **安裝** | `pip install rocketcea`（見 `requirements.txt`） |
| **橋接** | `cea_bridge.py` |
| **整合** | 推進／引擎設計在支援的推進劑下會自動採用 CEA 結果（見 `ROCKET_DESIGN_README.md`） |

- 參考： [NASA CEA](https://www1.grc.nasa.gov/research-and-engineering/ceaweb/) · [RocketCEA](https://rocketcea.readthedocs.io/)

---

## 2. Cantera

| 項目 | 說明 |
|------|------|
| **用途** | 化學動力學、熱力學、輸運性質；平衡或給定組成下的 T、P、γ、R、cp、分子量等 |
| **安裝** | `pip install cantera`（Cantera 3.x 需 Python 3.10+；若為舊版 Python 可改裝 `cantera<3`） |
| **橋接** | `cantera_bridge.py` |

### API 摘要

- `is_cantera_available()`：是否可用
- `get_solution(mechanism)`：載入 YAML/.cti 機制（如 `gri30.yaml`）
- `get_state_at_tp(mechanism, T_K, P_Pa, X=None)`：給定 T、P（及可選摩爾分率）回傳熱力狀態
- `get_equilibrium_at_hp(mechanism, H_J_kg, P_Pa, X_init=None)`：給定 H、P 之平衡狀態
- `get_properties_for_engine(mechanism, T_c_K, P_c_Pa, X=None)`：回傳 `gamma`, `R_gas`, `T_K` 等字典供引擎／熱力模組使用

- 參考： [Cantera](https://cantera.org/)

---

## 3. OpenFOAM

| 項目 | 說明 |
|------|------|
| **用途** | 開放源碼 CFD（不可壓／可壓、湍流等） |
| **安裝** | 從 [openfoam.org](https://openfoam.org/) 或 [openfoam.com](https://www.openfoam.com/) 安裝，並在 shell 中 `source` 環境 |
| **橋接** | `openfoam_bridge.py` |

### 使用方式

- 確認 OpenFOAM 在 PATH：執行前需在終端 `source` 安裝目錄的 `etc/bashrc`（或等價），使 `blockMesh`、`simpleFoam` 等可用。
- `is_openfoam_available()`：檢查 `blockMesh` 是否存在。
- `run_openfoam_command(cmd, cwd, env, timeout)`：在指定目錄執行指令（如 `["blockMesh"]`）。
- `run_case_steps(case_dir, steps, env, timeout_per_step)`：依序執行步驟，例如 `["blockMesh", "simpleFoam"]`。
- `write_blockmesh_dict(path, ...)`：寫入簡化 `blockMeshDict`（長方體），供測試或替代手寫。

本橋接不包含完整案例檔；實際案例需自行準備 `system/`, `constant/`, `0/` 等目錄與設定。

---

## 4. SU2

| 項目 | 說明 |
|------|------|
| **用途** | 開放源碼 CFD（歐拉／NS、可壓流、優化） |
| **安裝** | 從 [SU2](https://su2code.github.io/) 下載並編譯；可選 Python wrapper（需 SWIG、`--enable-PY_WRAPPER`） |
| **橋接** | `su2_bridge.py` |

### 使用方式

- 設定環境變數 **SU2_RUN** 指向 SU2 可執行檔所在目錄（或將 SU2 加入 PATH）。
- `is_su2_available()`：檢查是否找到 `SU2_CFD`。
- `find_su2_cfd()`：回傳 `SU2_CFD` 可執行檔或 `SU2_CFD.py` 指令。
- `run_su2_cfd(config_path, cwd, n_cores, extra_args, timeout, env)`：執行給定 `.cfg` 的計算。
- `write_minimal_config(path, mesh_file, mach, aoa, output_dir)`：寫入最小設定檔範本。

網格檔（如 `mesh.su2`）需自行產生或由其他前處理輸出。

---

## 5. Abaqus

| 項目 | 說明 |
|------|------|
| **用途** | 商業 FEA（結構、熱、接觸等） |
| **安裝** | 安裝 SIMULIA Abaqus，並將指令（如 `abaqus` 或 `abq20xx`）加入 PATH，或設定 **SIMULIA_PATH** / **ABAQUS_HOME** |
| **橋接** | `abaqus_bridge.py` |

### 使用方式

- `is_abaqus_available()`：檢查 Abaqus 指令是否可用。
- `run_abaqus_job(inp_path, job_name, abaqus_cmd, cwd, ask_delete, timeout, env)`：提交 `.inp` 作業（`job=... input=...`）。
- `run_abaqus_cae_script(script_path, no_gui, ...)`：執行 Abaqus CAE 腳本（`abaqus cae script=... -noGUI`）。
- `write_minimal_inp(path, title, node_list, element_list)`：寫入最小 .inp 範本（僅供橋接測試）。

實際分析請以 Abaqus CAE 或完整關鍵字產生正確的 .inp。

---

## 6. CalculiX

| 項目 | 說明 |
|------|------|
| **用途** | 開放源碼 FEA（Abaqus 相容 .inp 關鍵字） |
| **安裝** | 從 [CalculiX](http://www.calculix.de/) 或套件管理安裝，將 ccx 加入 PATH 或設定 **CALCULIX_HOME** |
| **橋接** | `calculix_bridge.py` |

- `is_calculix_available()`、`find_ccx()`、`run_ccx(jobname, cwd, ...)`（jobname 不含 .inp）、`write_minimal_inp()`、`get_run_summary()`。

---

## 7. GMAT (General Mission Analysis Tool)

| 項目 | 說明 |
|------|------|
| **用途** | NASA 任務分析與軌道設計 |
| **安裝** | 從 [GMAT](https://github.com/nasa/GMAT) 安裝，將 GMATConsole 或 GMAT 加入 PATH 或 **GMAT_HOME** |
| **橋接** | `gmat_bridge.py` |

- `run_gmat_script(script_path, run_and_exit=True, use_console=True, ...)`、`write_minimal_script()`、`get_run_summary()`。

---

## 8. OpenRocket

| 項目 | 說明 |
|------|------|
| **用途** | 開放源碼火箭設計與飛行模擬（.ork 設計檔） |
| **安裝** | 安裝 Java 與 [OpenRocket](https://openrocket.info/)，設定 **OPENROCKET_HOME** 或 PATH |
| **橋接** | `openrocket_bridge.py` |

- `run_openrocket(open_file=None, ...)` 啟動 JAR 並可開啟 .ork；程式化模擬可搭配 **orhelper**（JPype + OpenRocket 15.03）。

---

## 9. Optuna

| 項目 | 說明 |
|------|------|
| **用途** | 超參數最佳化，可與 PyTorch、TensorFlow、本專案 MDO 搭配 |
| **安裝** | `pip install optuna` |
| **橋接** | `optuna_bridge.py` |

- `is_optuna_available()`、`create_study(objective, study_name, n_trials, sampler, ...)`、`suggest_params(trial, names, low, high)`。

---

## 10. Dakota

| 項目 | 說明 |
|------|------|
| **用途** | Sandia 優化與不確定度量化（變數、介面、回應、方法） |
| **安裝** | 從 [Dakota](https://dakota.sandia.gov/) 安裝，將 dakota 加入 PATH 或 **DAKOTA_HOME** |
| **橋接** | `dakota_bridge.py` |

- `run_dakota(input_path, output_path, error_path, ...)`、`write_minimal_input()`。

---

## 11. SALib

| 項目 | 說明 |
|------|------|
| **用途** | 敏感度分析（Sobol、Morris、FAST 等） |
| **安裝** | `pip install SALib` |
| **橋接** | `salib_bridge.py` |

- `define_problem()`、`sobol_sampling()`、`sobol_analyze()`、`run_sobol(problem, model_func, N, ...)`。

---

## 12. MATLAB / Simulink

| 項目 | 說明 |
|------|------|
| **用途** | 數值計算與 Simulink 仿真；從 Python 呼叫 MATLAB |
| **安裝** | 安裝 MATLAB，並 `pip install matlabengine`（需對應 MATLAB 版本） |
| **橋接** | `matlab_bridge.py` |

- `is_matlab_engine_available()`、`start_engine()`、`run_script(script_path, engine)`；或 `run_matlab_batch(script_path)` 以 subprocess 執行 `matlab -batch`。

---

## 13. Python Control

| 項目 | 說明 |
|------|------|
| **用途** | 控制系統分析與設計（傳遞函數、Bode、狀態空間） |
| **安裝** | `pip install control` |
| **橋接** | `control_bridge.py` |

- `is_control_available()`、`tf(num, den)`、`ss(A,B,C,D)`、`bode_plot(sys)`。

---

## 14. PyTorch / TensorFlow 與 Cantera 耦合

| 項目 | 說明 |
|------|------|
| **用途** | 以 Cantera 產生的熱力資料訓練 ROM／代理模型，供 MDO 或 UQ 快速評估 |
| **安裝** | `pip install cantera` + `pip install torch` 或 `tensorflow` |
| **說明** | 見 `ml_cantera_note.md` |

Cantera 計算 (P, T, 組成) → (γ, R, cp…) 作為訓練資料；以 PyTorch 或 TensorFlow 建模型後，在優化迴圈中取代直接呼叫 Cantera。

---

## 15. NASA Trick

| 項目 | 說明 |
|------|------|
| **用途** | NASA 高保真仿真框架（動力學、即時等） |
| **安裝** | 從 [Trick](https://nasa.github.io/trick/) 編譯，設定 **TRICK_HOME** |
| **橋接** | `trick_bridge.py` |

- `run_trick_sim(run_input, output_dir=None, ...)`，run_input 格式如 `RUN_<name>/input_<name>.py`；可執行檔為 `S_main_${TRICK_HOST_CPU}.exe`。

---

## 16. ANSYS Fluent

| 項目 | 說明 |
|------|------|
| **用途** | 商業 CFD；以 TUI 日誌檔批次自動化 |
| **安裝** | 安裝 ANSYS Fluent，將 fluent 加入 PATH 或 **FLUENT_BIN** |
| **橋接** | `fluent_bridge.py` |

- `write_journal(path, case_file, data_file, n_iters)` 寫入 TUI 日誌；`run_fluent_batch(journal_path, dimension='3d', ...)` 執行 `fluent 3d -g -i journal.jou`。

---

## 17. STK (Systems Tool Kit)

| 項目 | 說明 |
|------|------|
| **用途** | AGI 軌道／任務分析與可視化；Connect 指令或 COM API 自動化 |
| **安裝** | 安裝 STK，設定 **AGI_STK_HOME** 或 PATH |
| **橋接** | `stk_bridge.py` |

- `write_connect_script(path, commands)`、`run_stk_with_script(script_path)`；完整自動化請參照 STK 文件（Connect、Object Model、Containerize STK）。

---

## 依賴總覽

| 工具 | 安裝方式 | 是否必須 |
|------|----------|----------|
| RocketCEA | `pip install rocketcea` | 否（未安裝則用內建公式） |
| Cantera | `pip install cantera` | 否 |
| OpenFOAM | 官網安裝 + source 環境 | 否 |
| SU2 | 編譯 + 設定 SU2_RUN/PATH | 否 |
| Abaqus | 商業安裝 + PATH | 否 |
| CalculiX | 安裝 + PATH / CALCULIX_HOME | 否 |
| GMAT | 安裝 + PATH / GMAT_HOME | 否 |
| OpenRocket | Java + JAR，OPENROCKET_HOME | 否 |
| Optuna | `pip install optuna` | 否 |
| Dakota | 安裝 + PATH / DAKOTA_HOME | 否 |
| SALib | `pip install SALib` | 否 |
| MATLAB | 安裝 MATLAB + matlabengine | 否 |
| Python Control | `pip install control` | 否 |
| PyTorch/TensorFlow | `pip install torch` 或 `tensorflow` | 否（與 Cantera 耦合用） |
| NASA Trick | 編譯 + TRICK_HOME | 否 |
| ANSYS Fluent | 商業安裝 + PATH | 否 |
| STK | 商業安裝 + AGI_STK_HOME | 否 |

所有橋接在對應工具未安裝或不可用時，會安全回傳或拋出明確錯誤，不影響其餘程式流程。
