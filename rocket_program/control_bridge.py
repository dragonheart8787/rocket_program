# -*- coding: utf-8 -*-
"""
Python Control 橋接模組

控制系統分析與設計：傳遞函數、Bode、根軌跡等。可與 GNC、Simulink 比對。

參考：https://python-control.readthedocs.io/
"""

from __future__ import annotations
from typing import Optional, Tuple, Any, List

def _get_control():
    try:
        import control as ct
        return ct
    except ImportError:
        return None


def is_control_available() -> bool:
    return _get_control() is not None


def tf(num: List[float], den: List[float], dt: Optional[float] = None) -> Any:
    """建立 SISO 傳遞函數。dt 不為 None 則為離散系統。"""
    ct = _get_control()
    if ct is None:
        return None
    if dt is not None:
        return ct.tf(num, den, dt)
    return ct.tf(num, den)


def ss(A: Any, B: Any, C: Any, D: Any) -> Any:
    """狀態空間模型。"""
    ct = _get_control()
    if ct is None:
        return None
    return ct.ss(A, B, C, D)


def bode_plot(sys: Any, dB: bool = True, deg: bool = True, **kwargs: Any) -> Optional[Tuple[Any, Any, Any]]:
    """Bode 資料；回傳 (mag, phase, omega) 或 None。若要繪圖可另呼叫 ct.bode_plot。"""
    ct = _get_control()
    if ct is None or sys is None:
        return None
    return ct.bode(sys, dB=dB, deg=deg, **kwargs)
