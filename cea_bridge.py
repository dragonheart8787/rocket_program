# -*- coding: utf-8 -*-
"""
NASA CEA / RocketCEA 橋接模組

透過 RocketCEA（Python 封裝 NASA CEA）取得化學平衡燃燒之
燃燒室溫度、比熱比、氣體常數、特徵速度、真空比衝等，供推進與引擎設計使用。

參考：
- NASA CEA: https://www1.grc.nasa.gov/research-and-engineering/ceaweb/
- RocketCEA: https://rocketcea.readthedocs.io/
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any

# 單位換算常數（RocketCEA 使用英制）
PSI_TO_PA = 6894.757293168  # 1 psi = 6894.76 Pa
FT_PER_S_TO_M_PER_S = 0.3048  # ft/s -> m/s
DEGR_TO_K = 5.0 / 9.0  # deg R -> K
R_UNIVERSAL = 8314.462618  # J/(kmol·K)，通用氣體常數

# 本專案推進劑 ID 對應 RocketCEA 氧化劑/燃料名稱
PROPELLANT_TO_CEA = {
    "LOX_RP1": ("LOX", "RP1"),
    "LOX_LH2": ("LOX", "LH2"),
    "NTO_UDMH": ("N2O4", "UDMH"),
    "N2O4_MMH": ("N2O4", "MMH"),
    "LOX_CH4": ("LOX", "CH4"),
    "LOX_LCH4": ("LOX", "LCH4_NASA"),
}

# 典型混合比（氧化劑/燃料質量比），用於 CEA 查表；若未指定則用此預設
DEFAULT_MR = {
    "LOX_RP1": 2.56,
    "LOX_LH2": 6.0,
    "NTO_UDMH": 2.6,
    "N2O4_MMH": 2.6,
    "LOX_CH4": 3.2,
    "LOX_LCH4": 3.4,
}


@dataclass
class CEAResult:
    """NASA CEA 單次計算結果（SI 單位）"""
    T_c_K: float
    gamma: float
    R_gas_J_kgK: float
    c_star_m_s: float
    Isp_vac_s: float
    molwt_g_mol: float
    source: str = "NASA CEA (RocketCEA)"


_CEA_OBJ = None


def _get_cea_obj():
    """延遲載入 CEA_Obj，避免未安裝 rocketcea 時 import 即失敗。"""
    global _CEA_OBJ
    if _CEA_OBJ is not None:
        return _CEA_OBJ
    try:
        from rocketcea.cea_obj import CEA_Obj
        _CEA_OBJ = CEA_Obj
        return _CEA_OBJ
    except ImportError:
        return None


def is_cea_available() -> bool:
    """回傳 RocketCEA 是否可用。"""
    return _get_cea_obj() is not None


def get_cea_propellant_names(propellant_id: str) -> Optional[tuple]:
    """
    取得本專案推進劑 ID 對應的 RocketCEA (oxName, fuelName)。
    若無對應或為固體等則回傳 None。
    """
    return PROPELLANT_TO_CEA.get(propellant_id)


def get_cea_properties(
    propellant_id: str,
    Pc_Pa: float,
    expansion_ratio: float = 40.0,
    MR: Optional[float] = None,
) -> Optional[CEAResult]:
    """
    依推進劑、燃燒室壓力、膨脹比（與可選混合比）呼叫 NASA CEA，回傳 SI 單位結果。

    - propellant_id: 本專案代碼，如 "LOX_RP1", "LOX_LH2"
    - Pc_Pa: 燃燒室壓力 (Pa)
    - expansion_ratio: 噴管面積比 A_e/A_t
    - MR: 氧化劑/燃料質量比；若為 None 則使用內建預設

    若 RocketCEA 未安裝或該推進劑無對應，回傳 None。
    """
    CEA_Obj = _get_cea_obj()
    if CEA_Obj is None:
        return None

    names = get_cea_propellant_names(propellant_id)
    if names is None:
        return None

    ox_name, fuel_name = names
    if MR is None:
        MR = DEFAULT_MR.get(propellant_id, 2.5)

    Pc_psi = Pc_Pa / PSI_TO_PA
    try:
        cea = CEA_Obj(oxName=ox_name, fuelName=fuel_name)
        # (IspVac sec, Cstar ft/s, Tcomb degR, mw lbm/lbmole, gam)
        ivac, cstar_fts, tcomb_degR, mw, gam = cea.get_IvacCstrTc_ChmMwGam(
            Pc=Pc_psi, MR=MR, eps=expansion_ratio
        )
    except Exception:
        return None

    T_c_K = tcomb_degR * DEGR_TO_K
    c_star_m_s = cstar_fts * FT_PER_S_TO_M_PER_S
    # lbm/lbmole 數值上等同 g/mol
    R_gas = R_UNIVERSAL / mw  # J/(kg·K)

    return CEAResult(
        T_c_K=T_c_K,
        gamma=float(gam),
        R_gas_J_kgK=float(R_gas),
        c_star_m_s=float(c_star_m_s),
        Isp_vac_s=float(ivac),
        molwt_g_mol=float(mw),
        source="NASA CEA (RocketCEA)",
    )


def get_cea_properties_for_engine(
    propellant_id: str,
    chamber_pressure_Pa: float,
    expansion_ratio: float,
    MR: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """
    供引擎/推進模組呼叫的介面：回傳可作為設計輸入的字典。

    鍵：gamma, R_gas, T_c_K, c_star_m_s, Isp_vac_s；
    若 CEA 不可用或失敗則回傳 None。
    """
    r = get_cea_properties(propellant_id, chamber_pressure_Pa, expansion_ratio, MR)
    if r is None:
        return None
    return {
        "gamma": r.gamma,
        "R_gas": r.R_gas_J_kgK,
        "T_c_K": r.T_c_K,
        "c_star_m_s": r.c_star_m_s,
        "Isp_vac_s": r.Isp_vac_s,
        "cea_source": r.source,
    }
