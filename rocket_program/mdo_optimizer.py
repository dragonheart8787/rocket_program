# -*- coding: utf-8 -*-
"""
多學科設計優化 (MDO) 模組：設計變數、約束、Nelder-Mead 優化、Sobol 敏感度
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple
import math
import numpy as np


@dataclass
class DesignVariable:
    """設計變數"""
    name: str
    lower: float
    upper: float
    initial: float
    unit: str = ""

    def normalize(self, x: float) -> float:
        span = self.upper - self.lower
        return (x - self.lower) / max(span, 1e-12)

    def denormalize(self, xn: float) -> float:
        return self.lower + xn * (self.upper - self.lower)


@dataclass
class Constraint:
    """約束 g(x) <= 0"""
    name: str
    func: Callable[[Dict[str, float]], float]
    type: str = "inequality"  # "inequality" or "equality"


@dataclass
class MDOResult:
    """MDO 優化結果"""
    best_x: Dict[str, float]
    best_obj: float
    n_iterations: int
    n_function_evals: int
    convergence_history: List[float]
    constraint_violations: Dict[str, float]
    feasible: bool
    sensitivity: Optional[Dict[str, float]]


class MDOProblem:
    """多學科設計優化問題定義"""

    def __init__(
        self,
        design_vars: List[DesignVariable],
        objective: Callable[[Dict[str, float]], float],
        constraints: Optional[List[Constraint]] = None,
        penalty_weight: float = 1e6,
    ):
        self.design_vars = design_vars
        self.objective = objective
        self.constraints = constraints or []
        self.penalty_weight = penalty_weight
        self._n_evals = 0

    def evaluate(self, x_dict: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        """計算目標 + 約束違反。"""
        self._n_evals += 1
        obj = self.objective(x_dict)
        violations = {}
        penalty = 0.0
        for c in self.constraints:
            g = c.func(x_dict)
            violations[c.name] = g
            if c.type == "inequality" and g > 0:
                penalty += self.penalty_weight * g ** 2
            elif c.type == "equality":
                penalty += self.penalty_weight * g ** 2
        return obj + penalty, violations

    def _vec_to_dict(self, x_vec: np.ndarray) -> Dict[str, float]:
        return {dv.name: dv.denormalize(float(x_vec[i])) for i, dv in enumerate(self.design_vars)}

    def _penalized(self, x_vec: np.ndarray) -> float:
        x_dict = self._vec_to_dict(np.clip(x_vec, 0.0, 1.0))
        val, _ = self.evaluate(x_dict)
        return val


def _nelder_mead(func: Callable, x0: np.ndarray, max_iter: int = 300, tol: float = 1e-8) -> Tuple[np.ndarray, List[float]]:
    """Nelder-Mead 最佳化（無梯度）。"""
    n = len(x0)
    alpha, gamma_nm, rho, sigma = 1.0, 2.0, 0.5, 0.5
    simplex = [x0.copy()]
    for i in range(n):
        xi = x0.copy()
        xi[i] += 0.05
        simplex.append(xi)
    f_vals = [func(s) for s in simplex]
    history = [min(f_vals)]

    for iteration in range(max_iter):
        order = np.argsort(f_vals)
        simplex = [simplex[i] for i in order]
        f_vals = [f_vals[i] for i in order]

        centroid = np.mean(simplex[:-1], axis=0)
        xr = centroid + alpha * (centroid - simplex[-1])
        fr = func(xr)

        if f_vals[0] <= fr < f_vals[-2]:
            simplex[-1] = xr
            f_vals[-1] = fr
        elif fr < f_vals[0]:
            xe = centroid + gamma_nm * (xr - centroid)
            fe = func(xe)
            if fe < fr:
                simplex[-1] = xe
                f_vals[-1] = fe
            else:
                simplex[-1] = xr
                f_vals[-1] = fr
        else:
            xc = centroid + rho * (simplex[-1] - centroid)
            fc = func(xc)
            if fc < f_vals[-1]:
                simplex[-1] = xc
                f_vals[-1] = fc
            else:
                for i in range(1, len(simplex)):
                    simplex[i] = simplex[0] + sigma * (simplex[i] - simplex[0])
                    f_vals[i] = func(simplex[i])

        history.append(f_vals[0])
        if len(history) > 2 and abs(history[-1] - history[-2]) < tol:
            break

    return simplex[0], history


def _latin_hypercube(n_samples: int, n_dims: int, seed: int = 42) -> np.ndarray:
    """拉丁超立方取樣 (0, 1)^n。"""
    rng = np.random.default_rng(seed)
    samples = np.zeros((n_samples, n_dims))
    for j in range(n_dims):
        perm = rng.permutation(n_samples)
        samples[:, j] = (perm + rng.random(n_samples)) / n_samples
    return samples


def run_optimization(
    problem: MDOProblem,
    n_starts: int = 5,
    max_iter: int = 300,
    seed: int = 42,
) -> MDOResult:
    """多起始點 Nelder-Mead 優化。"""
    n = len(problem.design_vars)
    lhs = _latin_hypercube(n_starts, n, seed)
    problem._n_evals = 0

    best_x = lhs[0]
    best_f = 1e30
    all_history: List[float] = []

    for i in range(n_starts):
        x_opt, hist = _nelder_mead(problem._penalized, lhs[i], max_iter=max_iter)
        x_opt = np.clip(x_opt, 0.0, 1.0)
        f_opt = problem._penalized(x_opt)
        all_history.extend(hist)
        if f_opt < best_f:
            best_f = f_opt
            best_x = x_opt

    x_dict = problem._vec_to_dict(best_x)
    _, violations = problem.evaluate(x_dict)
    feasible = all(v <= 0 for v in violations.values()) if violations else True

    return MDOResult(
        best_x=x_dict,
        best_obj=best_f,
        n_iterations=len(all_history),
        n_function_evals=problem._n_evals,
        convergence_history=all_history,
        constraint_violations=violations,
        feasible=feasible,
        sensitivity=None,
    )


def run_sobol_sensitivity(
    problem: MDOProblem,
    n_samples: int = 256,
    seed: int = 42,
) -> Dict[str, float]:
    """Sobol 全域敏感度（一階指標近似）。"""
    n = len(problem.design_vars)
    rng = np.random.default_rng(seed)
    A = rng.random((n_samples, n))
    B = rng.random((n_samples, n))

    f_A = np.array([problem._penalized(A[i]) for i in range(n_samples)])
    f_B = np.array([problem._penalized(B[i]) for i in range(n_samples)])

    var_total = np.var(np.concatenate([f_A, f_B]))
    if var_total < 1e-20:
        return {dv.name: 0.0 for dv in problem.design_vars}

    S1 = {}
    for j in range(n):
        AB_j = A.copy()
        AB_j[:, j] = B[:, j]
        f_AB_j = np.array([problem._penalized(AB_j[i]) for i in range(n_samples)])
        S1[problem.design_vars[j].name] = float(
            np.mean(f_B * (f_AB_j - f_A)) / max(var_total, 1e-20)
        )

    return S1
