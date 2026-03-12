# -*- coding: utf-8 -*-
"""
Cantera 橋接模組

用於化學動力學、熱力學與輸運性質。可計算平衡或給定組成下的
T、P、γ、R、cp、分子量等，供燃燒/推進或後處理比對。

參考：https://cantera.org/
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any

R_UNIVERSAL = 8314.462618  # J/(kmol·K)


@dataclass
class CanteraStateResult:
    """Cantera 熱力狀態結果（SI）"""
    T_K: float
    P_Pa: float
    gamma: float
    R_gas_J_kgK: float
    cp_J_kgK: float
    cv_J_kgK: float
    mean_molecular_weight: float
    density_kg_m3: float


def _get_cantera():
    """延遲載入 cantera，未安裝時回傳 None。"""
    try:
        import cantera as ct
        return ct
    except ImportError:
        return None


def is_cantera_available() -> bool:
    """回傳 Cantera 是否可用。"""
    return _get_cantera() is not None


def get_solution(mechanism: str):
    """
    載入 Cantera 機制（YAML 或 .cti 路徑，或內建名稱如 'gri30.yaml'）。
    若 Cantera 未安裝或載入失敗回傳 None。
    """
    ct = _get_cantera()
    if ct is None:
        return None
    try:
        return ct.Solution(mechanism)
    except Exception:
        return None


def get_state_at_tp(
    mechanism: str,
    T_K: float,
    P_Pa: float,
    X: Optional[Dict[str, float]] = None,
) -> Optional[CanteraStateResult]:
    """
    在給定 T、P（與可選摩爾分率 X）下計算熱力狀態。
    X 若為 None 則使用機制預設組成（常為空氣或純物）。
    """
    gas = get_solution(mechanism)
    if gas is None:
        return None
    try:
        if X is not None:
            gas.X = X
        gas.TP = T_K, P_Pa
        cp = float(gas.cp)
        cv = float(gas.cv)
        M = float(gas.mean_molecular_weight)
        R = R_UNIVERSAL / M
        gamma = cp / cv if cv > 0 else 1.4
        rho = float(gas.density)
        return CanteraStateResult(
            T_K=T_K,
            P_Pa=P_Pa,
            gamma=gamma,
            R_gas_J_kgK=R,
            cp_J_kgK=cp,
            cv_J_kgK=cv,
            mean_molecular_weight=M,
            density_kg_m3=rho,
        )
    except Exception:
        return None


def get_equilibrium_at_hp(
    mechanism: str,
    H_J_kg: float,
    P_Pa: float,
    X_init: Optional[Dict[str, float]] = None,
) -> Optional[CanteraStateResult]:
    """
    在給定比焓 H 與壓力 P 下求化學平衡狀態（如絕熱燃燒）。
    需能設定 HP 的相；X_init 為初始估計組成（可選）。
    """
    gas = get_solution(mechanism)
    if gas is None:
        return None
    try:
        if X_init is not None:
            gas.X = X_init
        gas.HP = H_J_kg, P_Pa
        T_K = float(gas.T)
        P_Pa = float(gas.P)
        cp = float(gas.cp)
        cv = float(gas.cv)
        M = float(gas.mean_molecular_weight)
        R = R_UNIVERSAL / M
        gamma = cp / cv if cv > 0 else 1.4
        rho = float(gas.density)
        return CanteraStateResult(
            T_K=T_K,
            P_Pa=P_Pa,
            gamma=gamma,
            R_gas_J_kgK=R,
            cp_J_kgK=cp,
            cv_J_kgK=cv,
            mean_molecular_weight=M,
            density_kg_m3=rho,
        )
    except Exception:
        return None


def get_properties_for_engine(
    mechanism: str,
    T_c_K: float,
    P_c_Pa: float,
    X: Optional[Dict[str, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    供引擎/熱力模組使用：回傳 gamma, R_gas, T_K, cp 等字典。
    若機制不支援或失敗則回傳 None。
    """
    s = get_state_at_tp(mechanism, T_c_K, P_c_Pa, X)
    if s is None:
        return None
    return {
        "gamma": s.gamma,
        "R_gas": s.R_gas_J_kgK,
        "T_K": s.T_K,
        "P_Pa": s.P_Pa,
        "cp_J_kgK": s.cp_J_kgK,
        "density_kg_m3": s.density_kg_m3,
        "source": "Cantera",
    }
