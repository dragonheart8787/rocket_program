# -*- coding: utf-8 -*-
"""
AI Surrogate 管線：氣動 / 熱通量 / 結構裕度代理模型

- DOE：Sobol / LHS 取樣
- Surrogate：可接 sklearn / 簡單 GP / MLP
- Active Learning：高不確定區域補樣本
- Fail-closed：OOD 偵測，超出訓練域回退 truth model
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Tuple
import numpy as np


# =============================================================================
# 1) DOE 取樣
# =============================================================================

def latin_hypercube_sample(
    bounds: List[Tuple[float, float]],
    n: int,
    seed: Optional[int] = None,
) -> np.ndarray:
    """LHS 取樣，bounds = [(lo, hi), ...]。"""
    rng = np.random.default_rng(seed)
    d = len(bounds)
    X = np.zeros((n, d))
    for j in range(d):
        lo, hi = bounds[j]
        perm = rng.permutation(n)
        X[:, j] = lo + (perm + rng.uniform(0, 1, n)) / n * (hi - lo)
    return X


def sobol_sample_from_salib(
    bounds: List[Tuple[float, float]],
    n: int,
    seed: Optional[int] = None,
) -> np.ndarray:
    """使用 SALib 的 Saltelli 取樣（若可用）。"""
    try:
        from SALib.sample import saltelli
        problem = {
            "num_vars": len(bounds),
            "names": [f"x{i}" for i in range(len(bounds))],
            "bounds": list(bounds),
        }
        X = saltelli.sample(problem, n, seed=seed)
        return X
    except ImportError:
        return latin_hypercube_sample(bounds, n, seed)


# =============================================================================
# 2) Surrogate 模型（可插拔 sklearn / 自建）
# =============================================================================

@dataclass
class SurrogateResult:
    mean: float
    std: Optional[float] = None  # 不確定度
    in_domain: bool = True      # 是否在訓練域內
    ood_distance: Optional[float] = None  # OOD 距離（如 Mahalanobis 或到最近訓練點）


class SimpleGP:
    """
    簡化高斯過程：RBF 核，用於小規模資料。
    預測 mean 與 std（不確定度）。
    """
    def __init__(self, length_scale: float = 1.0, sigma_f: float = 1.0, sigma_n: float = 1e-4):
        self.ls = length_scale
        self.sf = sigma_f
        self.sn = sigma_n
        self.X_train: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self.L: Optional[np.ndarray] = None  # Cholesky

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.X_train = np.asarray(X)
        self.y_train = np.asarray(y).ravel()
        K = self._kernel(self.X_train, self.X_train)
        K += (self.sn ** 2 + 1e-8) * np.eye(len(K))
        self.L = np.linalg.cholesky(K)

    def _kernel(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        d = np.sum((X1[:, None, :] - X2[None, :, :]) ** 2, axis=2)
        return (self.sf ** 2) * np.exp(-0.5 * d / (self.ls ** 2))

    def predict(self, X: np.ndarray, return_std: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        if self.X_train is None:
            return np.zeros(len(X)), np.ones(len(X)) if return_std else None
        k_star = self._kernel(X, self.X_train)
        alpha = np.linalg.solve(self.L.T, np.linalg.solve(self.L, self.y_train))
        mean = k_star @ alpha
        if not return_std:
            return mean, None
        v = np.linalg.solve(self.L, k_star.T)
        kss = self._kernel(X, X)
        var = np.diag(kss) - np.sum(v ** 2, axis=0)
        var = np.maximum(var, 0.0)
        std = np.sqrt(var)
        return mean, std


# =============================================================================
# 3) OOD 偵測與 Fail-closed
# =============================================================================

def ood_distance_to_nearest(X: np.ndarray, X_train: np.ndarray) -> np.ndarray:
    """到最近訓練點的歐氏距離（正規化維度後）。"""
    if len(X_train) == 0:
        return np.full(len(X), np.inf)
    d = np.linalg.norm(X[:, None, :] - X_train[None, :, :], axis=2)
    return np.min(d, axis=1)


def is_in_domain(
    x: np.ndarray,
    bounds: List[Tuple[float, float]],
) -> bool:
    """檢查是否在邊界內。"""
    x = np.atleast_1d(x)
    for i, (lo, hi) in enumerate(bounds):
        if i >= len(x):
            break
        if x[i] < lo or x[i] > hi:
            return False
    return True


@dataclass
class FailClosedSurrogate:
    """
    Fail-closed 代理：超出訓練域或 OOD 距離過大時回退 truth model。
    """
    predict_fn: Callable[[np.ndarray], np.ndarray]  # surrogate 預測
    truth_fn: Callable[[np.ndarray], np.ndarray]  # truth model（慢但可靠）
    uncertainty_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None  # 回傳 std
    X_train: Optional[np.ndarray] = None
    bounds: Optional[List[Tuple[float, float]]] = None
    ood_threshold: float = np.inf  # 超過此距離視為 OOD
    use_truth_on_ood: bool = True

    def predict(self, X: np.ndarray) -> List[SurrogateResult]:
        X = np.atleast_2d(X)
        results = []
        for i in range(len(X)):
            xi = X[i]
            in_bounds = self.bounds is None or is_in_domain(xi, self.bounds)
            ood_dist = ood_distance_to_nearest(xi.reshape(1, -1), self.X_train or np.empty((0, len(xi))))[0]
            is_ood = not in_bounds or ood_dist > self.ood_threshold

            if is_ood and self.use_truth_on_ood:
                y = self.truth_fn(xi.reshape(1, -1))[0]
                results.append(SurrogateResult(mean=float(y), std=None, in_domain=False, ood_distance=float(ood_dist)))
            else:
                y = self.predict_fn(xi.reshape(1, -1))[0]
                std = self.uncertainty_fn(xi.reshape(1, -1))[0] if self.uncertainty_fn else None
                results.append(SurrogateResult(mean=float(y), std=float(std) if std is not None else None, in_domain=True, ood_distance=float(ood_dist)))
        return results


# =============================================================================
# 4) Active Learning：高不確定區域補樣本
# =============================================================================

def active_learning_iteration(
    X_pool: np.ndarray,
    predict_fn: Callable[[np.ndarray], np.ndarray],
    uncertainty_fn: Callable[[np.ndarray], np.ndarray],
    truth_fn: Callable[[np.ndarray], np.ndarray],
    n_add: int = 5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    從 pool 中選不確定度最高的 n_add 點，用 truth 標註，回傳新增 (X_new, y_new)。
    """
    unc = uncertainty_fn(X_pool)
    idx = np.argsort(-unc)[:n_add]
    X_new = X_pool[idx]
    y_new = truth_fn(X_new)
    return X_new, y_new


# =============================================================================
# 5) 多目標 Pareto（NSGA-II 風格前緣近似）
# =============================================================================

def pareto_front_2d(
    objectives: np.ndarray,
    minimize: Tuple[bool, bool] = (True, True),
) -> np.ndarray:
    """
    objectives: (n, 2)，兩目標。
    minimize: (min_f1, min_f2)，True 表示該目標要最小化。
    回傳 Pareto 前緣的索引。
    """
    n = len(objectives)
    sign = np.array([-1.0 if m else 1.0 for m in minimize])
    obj = objectives * sign
    idx = []
    for i in range(n):
        dominated = False
        for j in range(n):
            if i == j:
                continue
            if np.all(obj[j] >= obj[i]) and np.any(obj[j] > obj[i]):
                dominated = True
                break
        if not dominated:
            idx.append(i)
    return np.array(idx)


def nsga2_crowding_distance(objectives: np.ndarray, front_indices: np.ndarray) -> np.ndarray:
    """計算擁擠距離（簡化版）。"""
    f = objectives[front_indices]
    n = len(front_indices)
    if n <= 2:
        return np.full(n, np.inf)
    d = np.zeros(n)
    for k in range(f.shape[1]):
        order = np.argsort(f[:, k])
        d[order[0]] = np.inf
        d[order[-1]] = np.inf
        ran = f[order[-1], k] - f[order[0], k]
        if ran < 1e-12:
            continue
        for i in range(1, n - 1):
            idx = order[i]
            d[idx] += (f[order[i + 1], k] - f[order[i - 1], k]) / ran
    return d


# =============================================================================
# 6) 預製 Surrogate 建構器（氣動 / 熱通量 / 結構裕度）
# =============================================================================

def build_aero_surrogate(
    X: np.ndarray,
    y_cl: np.ndarray,
    y_cd: np.ndarray,
    bounds: List[Tuple[float, float]],
) -> Dict[str, Any]:
    """
    X: (n, 3) = [M, alpha_deg, log10(Re)]
    y_cl, y_cd: (n,)
    回傳 { "C_L": (predict_fn, unc_fn), "C_D": (predict_fn, unc_fn), "bounds": bounds }
    """
    gp_cl = SimpleGP(length_scale=0.5)
    gp_cd = SimpleGP(length_scale=0.5)
    gp_cl.fit(X, y_cl)
    gp_cd.fit(X, y_cd)

    def pred_cl(x):
        return gp_cl.predict(np.atleast_2d(x), return_std=False)[0]
    def pred_cd(x):
        return gp_cd.predict(np.atleast_2d(x), return_std=False)[0]
    def unc_cl(x):
        return gp_cl.predict(np.atleast_2d(x), return_std=True)[1]
    def unc_cd(x):
        return gp_cd.predict(np.atleast_2d(x), return_std=True)[1]

    return {
        "C_L": (pred_cl, unc_cl),
        "C_D": (pred_cd, unc_cd),
        "bounds": bounds,
        "X_train": X,
    }


def build_heat_flux_surrogate(
    X: np.ndarray,
    y_q: np.ndarray,
    bounds: List[Tuple[float, float]],
) -> Tuple[Callable, Callable]:
    """
    X: (n, 3) 如 [h_km, V_km_s, rho] 或 [h, V, rho]
    y_q: (n,) 熱通量 W/m^2
    """
    gp = SimpleGP(length_scale=0.5)
    gp.fit(X, y_q)
    def pred(x):
        return gp.predict(np.atleast_2d(x), return_std=False)[0]
    def unc(x):
        return gp.predict(np.atleast_2d(x), return_std=True)[1]
    return pred, unc


def build_margin_surrogate(
    X: np.ndarray,
    y_mos: np.ndarray,
    bounds: List[Tuple[float, float]],
) -> Tuple[Callable, Callable]:
    """
    X: (n, d) loads + geometry + material 參數
    y_mos: (n,) 安全裕度
    """
    gp = SimpleGP(length_scale=0.5)
    gp.fit(X, y_mos)
    def pred(x):
        return gp.predict(np.atleast_2d(x), return_std=False)[0]
    def unc(x):
        return gp.predict(np.atleast_2d(x), return_std=True)[1]
    return pred, unc
