# -*- coding: utf-8 -*-
"""
氣動升級：可插拔來源、不確定度模型、覆蓋率檢查

- 可插拔來源：AeroSource 介面，可接 AeroTable、外部檔案、Surrogate
- 不確定度模型：係數附 mean ± std 或 bounds，供 UQ 使用
- 覆蓋率檢查：設計空間 (Mach, α, Re) 是否被網格覆蓋，標記缺口
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Tuple
import csv
import math
import numpy as np

try:
    from aerospace_sim import AeroTable, make_placeholder_aero_table
except ImportError:
    AeroTable = None
    make_placeholder_aero_table = None


# =============================================================================
# 1) 可插拔來源介面
# =============================================================================

class AeroSource(ABC):
    """氣動係數來源抽象介面。"""

    @abstractmethod
    def coeffs(self, alpha_rad: float, beta_rad: float, M: float, Re: float) -> Dict[str, float]:
        """回傳 C_L, C_D, C_Y, C_l, C_m, C_n。"""
        pass

    def coeffs_with_uncertainty(
        self, alpha_rad: float, beta_rad: float, M: float, Re: float
    ) -> Dict[str, Tuple[float, Optional[float]]]:
        """
        回傳 (mean, std) 或 (value, None) 若無不確定度。
        預設：std = None。
        """
        c = self.coeffs(alpha_rad, beta_rad, M, Re)
        return {k: (v, None) for k, v in c.items()}


@dataclass
class AeroTableSource(AeroSource):
    """包裝既有 AeroTable 為 AeroSource。"""
    table: Any  # AeroTable

    def coeffs(self, alpha_rad: float, beta_rad: float, M: float, Re: float) -> Dict[str, float]:
        return self.table.coeffs(alpha_rad, beta_rad, M, Re)


@dataclass
class AeroUncertaintyWrapper(AeroSource):
    """
    為任一 AeroSource 加上不確定度模型。
    uncertainty_map: 如 {"C_L": 0.05, "C_D": 0.10} 表示相對 std (5%, 10%)
    """
    inner: AeroSource
    uncertainty_map: Dict[str, float] = field(default_factory=dict)

    def coeffs(self, alpha_rad: float, beta_rad: float, M: float, Re: float) -> Dict[str, float]:
        return self.inner.coeffs(alpha_rad, beta_rad, M, Re)

    def coeffs_with_uncertainty(
        self, alpha_rad: float, beta_rad: float, M: float, Re: float
    ) -> Dict[str, Tuple[float, Optional[float]]]:
        c = self.inner.coeffs(alpha_rad, beta_rad, M, Re)
        out = {}
        for k, v in c.items():
            rel_std = self.uncertainty_map.get(k)
            std = abs(v) * rel_std if rel_std is not None else None
            out[k] = (v, std)
        return out


@dataclass
class AeroSurrogateSource(AeroSource):
    """
    代理模型來源：f(M, alpha_deg, Re) -> dict。
    可接 ML surrogate。
    """
    predict_fn: Callable[[float, float, float], Dict[str, float]]
    source_name: str = "surrogate"

    def coeffs(self, alpha_rad: float, beta_rad: float, M: float, Re: float) -> Dict[str, float]:
        alpha_deg = math.degrees(alpha_rad)
        d = self.predict_fn(M, alpha_deg, Re)
        defaults = {"C_L": 0.0, "C_D": 0.02, "C_Y": 0.0, "C_l": 0.0, "C_m": 0.0, "C_n": 0.0}
        return {k: d.get(k, defaults.get(k, 0.0)) for k in defaults}


# =============================================================================
# 2) 覆蓋率檢查
# =============================================================================

@dataclass
class DesignSpace:
    """設計空間：Mach, alpha (deg), log10(Re) 範圍。"""
    M_min: float = 0.0
    M_max: float = 2.0
    alpha_min_deg: float = -5.0
    alpha_max_deg: float = 15.0
    Re_min: float = 1e5
    Re_max: float = 1e7


def _bilinear_extrap(x: float, y: float, xs: np.ndarray, ys: np.ndarray, Z: np.ndarray) -> float:
    """2D 插值，外推時用邊界值。"""
    if len(xs) < 2 or len(ys) < 2:
        return float(Z.flat[0]) if Z.size else 0.0
    ix = np.searchsorted(xs, x, side="right") - 1
    iy = np.searchsorted(ys, y, side="right") - 1
    ix = max(0, min(ix, len(xs) - 2))
    iy = max(0, min(iy, len(ys) - 2))
    x0, x1 = xs[ix], xs[ix + 1]
    y0, y1 = ys[iy], ys[iy + 1]
    tx = (x - x0) / max(x1 - x0, 1e-12)
    ty = (y - y0) / max(y1 - y0, 1e-12)
    tx = max(0.0, min(1.0, tx))
    ty = max(0.0, min(1.0, ty))
    z00, z10 = Z[iy, ix], Z[iy, ix + 1]
    z01, z11 = Z[iy + 1, ix], Z[iy + 1, ix + 1]
    return (1 - tx) * (1 - ty) * z00 + tx * (1 - ty) * z10 + (1 - tx) * ty * z01 + tx * ty * z11


def check_coverage(
    alpha_deg: np.ndarray,
    M: np.ndarray,
    space: DesignSpace,
    n_sample: int = 50,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    檢查設計空間覆蓋率。
    在 space 內均勻採樣，判斷落在 (alpha, M) 網格內/外的比例；
    若網格有 Re 維度則需擴展，此處簡化為 alpha x M。
    """
    M_span = space.M_max - space.M_min
    alpha_span = space.alpha_max_deg - space.alpha_min_deg
    if M_span <= 0 or alpha_span <= 0:
        return {"covered_ratio": 1.0, "n_in": n_sample, "n_out": 0, "gaps": []}

    M_min, M_max = float(np.min(M)), float(np.max(M))
    a_min, a_max = float(np.min(alpha_deg)), float(np.max(alpha_deg))

    rng = np.random.default_rng(seed)
    n_in = 0
    gaps = []

    for _ in range(n_sample):
        Mi = space.M_min + rng.random() * M_span
        ai = space.alpha_min_deg + rng.random() * alpha_span

        in_M = M_min <= Mi <= M_max
        in_a = a_min <= ai <= a_max
        if in_M and in_a:
            n_in += 1
        else:
            gaps.append({"M": Mi, "alpha_deg": ai, "reason": "M" if not in_M else "alpha"})

    covered = n_in / max(n_sample, 1)
    return {
        "covered_ratio": covered,
        "n_in": n_in,
        "n_out": n_sample - n_in,
        "n_sample": n_sample,
        "grid_M_range": [M_min, M_max],
        "grid_alpha_range": [a_min, a_max],
        "space_M_range": [space.M_min, space.M_max],
        "space_alpha_range": [space.alpha_min_deg, space.alpha_max_deg],
        "gaps": gaps[:10],  # 最多列 10 個
        "coverage_ok": covered >= 0.95,
    }


def load_aero_from_csv(path: str) -> Optional[AeroTable]:
    """
    從 CSV 載入氣動表。
    支援兩種格式：
    1) Header 格式：alpha_deg,M,C_L,C_D,C_m（欄位順序可不同）
    2) 舊格式：固定欄序 alpha_deg, M, C_L, C_D, C_m
    目前仍假設資料可映射為規則 alpha x M 網格。
    """
    if AeroTable is None:
        return None
    try:
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = set(reader.fieldnames or [])
            needed = {"alpha_deg", "M", "C_L", "C_D", "C_m"}
            if needed.issubset(fieldnames):
                for r in reader:
                    rows.append({
                        "alpha_deg": float(r["alpha_deg"]),
                        "M": float(r["M"]),
                        "C_L": float(r["C_L"]),
                        "C_D": float(r["C_D"]),
                        "C_m": float(r["C_m"]),
                    })

        # fallback：嘗試舊式固定欄位
        if not rows:
            data = np.loadtxt(path, delimiter=",", skiprows=1)
            if data.ndim == 1:
                data = data.reshape(1, -1)
            if data.shape[1] < 5:
                return None
            for row in data:
                rows.append({
                    "alpha_deg": float(row[0]),
                    "M": float(row[1]),
                    "C_L": float(row[2]),
                    "C_D": float(row[3]),
                    "C_m": float(row[4]),
                })

        if not rows:
            return None

        alphas = np.unique(np.array([r["alpha_deg"] for r in rows], dtype=float))
        Ms = np.unique(np.array([r["M"] for r in rows], dtype=float))
        n_a, n_m = len(alphas), len(Ms)
        C_L = np.zeros((n_a, n_m))
        C_D = np.zeros((n_a, n_m))
        C_m = np.zeros((n_a, n_m))
        for row in rows:
            ia = np.argmin(np.abs(alphas - row["alpha_deg"]))
            im = np.argmin(np.abs(Ms - row["M"]))
            C_L[ia, im] = row["C_L"]
            C_D[ia, im] = row["C_D"]
            C_m[ia, im] = row["C_m"]
        return AeroTable(alpha_deg=alphas, M=Ms, C_L=C_L, C_D=C_D, C_m=C_m, Re_scale=None)
    except Exception:
        return None


def get_pluggable_aero(
    source: str = "placeholder",
    path: Optional[str] = None,
    surrogate_fn: Optional[Callable] = None,
    uncertainty: Optional[Dict[str, float]] = None,
) -> AeroSource:
    """
    工廠：取得可插拔氣動來源。
    source: "placeholder" | "csv" | "surrogate"
    """
    if source == "csv" and path:
        tbl = load_aero_from_csv(path)
        if tbl is not None:
            s: AeroSource = AeroTableSource(tbl)
        else:
            s = _default_source()
    elif source == "surrogate" and surrogate_fn is not None:
        s = AeroSurrogateSource(surrogate_fn)
    else:
        s = _default_source()

    if uncertainty:
        s = AeroUncertaintyWrapper(s, uncertainty)
    return s


def aero_source_to_table(
    source: AeroSource,
    alpha_deg: np.ndarray,
    M: np.ndarray,
    Re_ref: float = 1e6,
) -> Any:
    """
    將 AeroSource 採樣到規則網格，產生 AeroTable，供 aerospace_sim.AeroModel 使用。
    """
    if AeroTable is None:
        return None
    C_L = np.zeros((len(alpha_deg), len(M)))
    C_D = np.zeros((len(alpha_deg), len(M)))
    C_m = np.zeros((len(alpha_deg), len(M)))
    for i, a in enumerate(alpha_deg):
        for j, m in enumerate(M):
            c = source.coeffs(math.radians(a), 0.0, m, Re_ref)
            C_L[i, j] = c["C_L"]
            C_D[i, j] = c["C_D"]
            C_m[i, j] = c["C_m"]
    return AeroTable(alpha_deg=alpha_deg, M=M, C_L=C_L, C_D=C_D, C_m=C_m, Re_scale=None)


def _default_source() -> AeroSource:
    if make_placeholder_aero_table is not None:
        return AeroTableSource(make_placeholder_aero_table())
    # 退化：簡單公式
    class SimpleSource(AeroSource):
        def coeffs(self, a, b, M, Re):
            return {"C_L": 0.08 * math.degrees(a), "C_D": 0.02, "C_Y": 0.0, "C_l": 0.0, "C_m": -0.05 * a, "C_n": 0.0}
    return SimpleSource()
