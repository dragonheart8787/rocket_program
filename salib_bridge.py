# -*- coding: utf-8 -*-
"""
SALib 橋接模組

敏感度分析：Sobol、Morris、FAST 等。可與本專案 UQ、MDO 模組搭配。

參考：https://salib.readthedocs.io/
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Callable

def _get_salib():
    try:
        import SALib
        from SALib.analyze import sobol, morris
        from SALib.sample import saltelli, morris as morris_sampler
        return {"SALib": SALib, "sobol": sobol, "morris": morris, "saltelli": saltelli, "morris_sampler": morris_sampler}
    except ImportError:
        return None


def is_salib_available() -> bool:
    return _get_salib() is not None


def define_problem(names: List[str], bounds: List[tuple], num_vars: Optional[int] = None) -> Dict[str, Any]:
    """SALib 格式的 problem 字典。bounds 為 [(low, high), ...]。"""
    n = num_vars or len(names)
    return {
        "num_vars": n,
        "names": names[:n],
        "bounds": list(bounds)[:n],
    }


def sobol_sampling(problem: Dict[str, Any], N: int, calc_second_order: bool = True, seed: Optional[int] = None) -> Any:
    """Saltelli 取樣，供 Sobol 分析。回傳 (X, param_names)。"""
    lib = _get_salib()
    if lib is None:
        return None, None
    saltelli = lib["saltelli"]
    X = saltelli.sample(problem, N, calc_second_order=calc_second_order, seed=seed)
    return X, problem.get("names", [])


def sobol_analyze(problem: Dict[str, Any], Y: Any, calc_second_order: bool = True, **kwargs: Any) -> Optional[Dict]:
    """Sobol 敏感度分析，Y 為模型輸出向量。"""
    lib = _get_salib()
    if lib is None:
        return None
    return lib["sobol"].analyze(problem, Y, calc_second_order=calc_second_order, **kwargs)


def run_sobol(
    problem: Dict[str, Any],
    model_func: Callable[[Any], Any],
    N: int = 256,
    calc_second_order: bool = False,
    seed: Optional[int] = None,
) -> Optional[Dict]:
    """取樣、跑模型、分析一氣呵成。model_func(X) 回傳 1D 陣列 Y。"""
    X, _ = sobol_sampling(problem, N, calc_second_order=calc_second_order, seed=seed)
    if X is None:
        return None
    import numpy as np
    Y = np.array([model_func(X[i]) for i in range(len(X))])
    return sobol_analyze(problem, Y, calc_second_order=calc_second_order)
