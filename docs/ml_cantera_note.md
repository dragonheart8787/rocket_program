# PyTorch / TensorFlow 與 Cantera 耦合說明

本專案可將 **Cantera** 的化學／熱力結果與 **PyTorch** 或 **TensorFlow** 結合，用於：

- **降階模型 (ROM)**：以 Cantera 計算 (P, T, 組成) → (γ, R, cp, Isp…) 產生訓練資料，用神經網路擬合，加速 MDO／即時估算。
- **代理模型 (Surrogate)**：對燃燒室出口狀態、噴管性能等建代理，替代反覆呼叫 Cantera。
- **不確定度傳播**：在 ML 預測上做 UQ（如本專案 SAP 之 Monte Carlo、SALib）。

## 建議流程

1. 使用 `cantera_bridge.get_state_at_tp` 或 `get_equilibrium_at_hp` 在 (P, T) 或 (H, P) 網格上取樣，得到 `gamma`, `R_gas`, `T_K`, `cp` 等。
2. 將輸入 (P, T, 組成等) 與輸出 (γ, R, …) 組成資料集，以 PyTorch `Dataset` / TensorFlow `tf.data` 載入。
3. 訓練小型 MLP 或 GPR，預測熱力輸出；在優化或 UQ 迴圈中呼叫該模型取代直接呼叫 Cantera。

## 依賴

- **Cantera**：`pip install cantera`（見 `cantera_bridge.py`）。
- **PyTorch**：`pip install torch`。
- **TensorFlow**：`pip install tensorflow`。

二者可只裝其一；與 Cantera 的耦合方式相同（皆為「Cantera 產資料 → ML 訓練 → 推論取代 Cantera」）。
