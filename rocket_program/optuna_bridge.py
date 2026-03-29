# -*- coding: utf-8 -*-
"""
Optuna 橋接模組

超參數最佳化：建立 Study、建議參數、優化目標函數。可與 PyTorch、TensorFlow、本專案 MDO 等搭配。

參考：https://optuna.readthedocs.io/
"""

from __future__ import annotations
from typing import Optional, Callable, Dict, Any, List

def _get_optuna():
    try:
        import optuna
        return optuna
    except ImportError:
        return None


def is_optuna_available() -> bool:
    return _get_optuna() is not None


def create_study(
    objective: Optional[Callable] = None,
    study_name: str = "rocket_study",
    n_trials: int = 50,
    sampler: str = "TPE",
    **kwargs: Any,
) -> Any:
    """
    建立並執行 Optuna Study。objective(trial) 需在內部用 trial.suggest_* 定義搜尋空間並回傳純量。
    若 objective 為 None 則只建立 study 不 optimize。回傳 study 物件；Optuna 未安裝時回傳 None。
    """
    optuna = _get_optuna()
    if optuna is None:
        return None
    if sampler == "TPE":
        sampler_obj = optuna.samplers.TPESampler(**kwargs.get("sampler_kwargs", {}))
    else:
        sampler_obj = optuna.samplers.TPESampler()
    study = optuna.create_study(direction="minimize", study_name=study_name, sampler=sampler_obj)
    if objective is not None and n_trials > 0:
        study.optimize(objective, n_trials=n_trials, **{k: v for k, v in kwargs.items() if k != "sampler_kwargs"})
    return study


def suggest_params(trial: Any, names: List[str], low: float, high: float, log: bool = False) -> Dict[str, float]:
    """對單一 trial 建議一組浮點參數（名稱與上下界）。"""
    out = {}
    for n in names:
        out[n] = trial.suggest_float(n, low, high, log=log)
    return out
