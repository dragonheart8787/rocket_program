# -*- coding: utf-8 -*-
"""
座標系與時間系統：明確定義、一致性檢查、轉換驗證
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable
import numpy as np
import math

OMEGA_EARTH = 7.2921159e-5  # rad/s


class TimeStandard(Enum):
    """時間標準"""
    UTC = "UTC"  # Coordinated Universal Time
    UT1 = "UT1"  # Universal Time 1 (考慮極移)
    TT = "TT"    # Terrestrial Time
    TAI = "TAI"  # International Atomic Time


class CoordinateFrame(Enum):
    """座標系"""
    ECI = "ECI"      # Earth-Centered Inertial
    ECEF = "ECEF"    # Earth-Centered Earth-Fixed
    NED = "NED"      # North-East-Down (本地)
    BODY = "BODY"    # 機體座標系


@dataclass
class EarthModel:
    """地球模型定義"""
    R_equatorial: float = 6378137.0  # m (WGS84)
    R_polar: float = 6356752.314  # m (WGS84)
    f: float = 1.0 / 298.257223563  # 扁率
    use_spherical: bool = True  # 簡化：使用球形
    mu: float = 3.986004418e14  # m³/s²
    omega: float = OMEGA_EARTH  # rad/s

    def R_mean(self) -> float:
        """平均半徑"""
        if self.use_spherical:
            return 6371000.0  # 簡化
        return (2.0 * self.R_equatorial + self.R_polar) / 3.0


@dataclass
class TimeSystem:
    """時間系統定義"""
    standard: TimeStandard = TimeStandard.UTC
    epoch_jd: float = 2451545.0  # J2000.0 (簡化)
    leap_seconds: int = 37  # 簡化：固定值

    def to_seconds_since_epoch(self, t: float) -> float:
        """轉換為自 epoch 以來的秒數"""
        return t  # 簡化：假設輸入已是秒


class CoordinateSystemManager:
    """座標系管理器：確保一致性"""

    def __init__(self, earth_model: EarthModel = None, time_system: TimeSystem = None):
        self.earth = earth_model or EarthModel()
        self.time = time_system or TimeSystem()
        self.current_frame = CoordinateFrame.ECI

    def ecef_from_eci(self, r_eci: np.ndarray, t: float) -> np.ndarray:
        """
        ECI → ECEF 轉換
        明確時間標準與轉換公式
        """
        # 使用 UTC 時間（簡化）
        angle = -self.earth.omega * t  # 負號：ECI 到 ECEF
        c, s = math.cos(angle), math.sin(angle)
        R_z = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        return R_z @ r_eci

    def eci_from_ecef(self, r_ecef: np.ndarray, t: float) -> np.ndarray:
        """
        ECEF → ECI 轉換
        """
        angle = self.earth.omega * t
        c, s = math.cos(angle), math.sin(angle)
        R_z = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        return R_z @ r_ecef

    def geodetic_from_ecef(self, r_ecef: np.ndarray) -> tuple:
        """
        ECEF → 地理座標（lat, lon, h）
        明確使用球形或橢球模型
        """
        if self.earth.use_spherical:
            # 球形近似
            r = np.linalg.norm(r_ecef)
            h = max(0.0, r - self.earth.R_mean())
            if r < 1e-6:
                return 0.0, 0.0, 0.0
            lat = math.asin(r_ecef[2] / r)
            lon = math.atan2(r_ecef[1], r_ecef[0])
            return lat, lon, h
        else:
            # 橢球模型（WGS84，需迭代求解）
            # 簡化：使用球形近似
            return self.geodetic_from_ecef(r_ecef)

    def ned_from_ecef(self, lat: float, lon: float) -> np.ndarray:
        """
        NED → ECEF 旋轉矩陣
        明確定義：N=北, E=東, D=下
        """
        clat, slat = math.cos(lat), math.sin(lat)
        clon, slon = math.cos(lon), math.sin(lon)
        N = np.array([-slat*clon, -slat*slon, clat])
        E = np.array([-slon, clon, 0.0])
        D = np.array([-clat*clon, -clat*slon, -slat])
        return np.column_stack([N, E, D])

    def coriolis_acceleration(self, v_ecef: np.ndarray) -> np.ndarray:
        """
        Coriolis 加速度（在 ECEF 框架）
        a_cor = -2 * ω × v
        """
        omega_vec = np.array([0.0, 0.0, self.earth.omega])
        return -2.0 * np.cross(omega_vec, v_ecef)

    def centrifugal_acceleration(self, r_ecef: np.ndarray) -> np.ndarray:
        """
        離心加速度（在 ECEF 框架）
        a_cen = -ω × (ω × r)
        """
        omega_vec = np.array([0.0, 0.0, self.earth.omega])
        return -np.cross(omega_vec, np.cross(omega_vec, r_ecef))

    def wind_frame_definition(self) -> str:
        """
        明確風場定義域
        返回：風場相對於哪個座標系
        """
        return "NED"  # 風場定義在 NED（相對地表）

    def wind_to_inertial(self, v_wind_ned: np.ndarray, lat: float, lon: float, t: float) -> np.ndarray:
        """
        風場轉換到慣性系
        明確轉換鏈：NED → ECEF → ECI
        """
        R_ned_ecef = self.ned_from_ecef(lat, lon)
        v_wind_ecef = R_ned_ecef @ v_wind_ned
        v_wind_eci = self.eci_from_ecef(v_wind_ecef, t)  # 注意：向量轉換需特殊處理
        # 簡化：假設風場在 ECEF 中定義，直接旋轉
        return self.eci_from_ecef(v_wind_ecef, t)


class ConsistencyChecker:
    """一致性檢查：座標轉換、時間系統一致性"""

    @staticmethod
    def check_coordinate_consistency(r_eci: np.ndarray, r_ecef: np.ndarray, t: float,
                                    coord_manager: CoordinateSystemManager) -> dict:
        """
        檢查座標轉換一致性（純數學互逆）
        """
        r_ecef_calc = coord_manager.ecef_from_eci(r_eci, t)
        error = np.linalg.norm(r_ecef_calc - r_ecef)
        rel_error = error / max(np.linalg.norm(r_ecef), 1e-9)
        
        return {
            "consistent": rel_error < 1e-6,
            "error": error,
            "relative_error": rel_error,
            "test_type": "mathematical_inverse"
        }

    @staticmethod
    def check_physical_consistency(r_eci: np.ndarray, v_eci: np.ndarray, t: float,
                                   coord_manager: CoordinateSystemManager,
                                   compute_kpi_func: Callable) -> dict:
        """
        檢查物理一致性：在 ECI/ECEF 下同一物理情境得到的 KPI 是否一致
        compute_kpi_func: 計算 KPI 的函數，接受 (r, v, frame) 參數
        """
        # 在 ECI 下計算 KPI
        kpi_eci = compute_kpi_func(r_eci, v_eci, "ECI")
        
        # 轉換到 ECEF
        r_ecef = coord_manager.ecef_from_eci(r_eci, t)
        v_ecef = coord_manager.ecef_from_eci(v_eci, t)  # 簡化：實際需考慮角速度
        
        # 在 ECEF 下計算 KPI
        kpi_ecef = compute_kpi_func(r_ecef, v_ecef, "ECEF")
        
        # 比較 KPI
        if isinstance(kpi_eci, dict) and isinstance(kpi_ecef, dict):
            # 多 KPI
            errors = {}
            for kpi_name in kpi_eci.keys():
                if kpi_name in kpi_ecef:
                    errors[kpi_name] = abs(kpi_eci[kpi_name] - kpi_ecef[kpi_name])
        else:
            # 單一 KPI
            errors = {"kpi": abs(kpi_eci - kpi_ecef)}
        
        return {
            "kpi_eci": kpi_eci,
            "kpi_ecef": kpi_ecef,
            "errors": errors,
            "consistent": all(e < 1e-3 for e in errors.values() if isinstance(e, (int, float))),
            "test_type": "physical_consistency"
        }

    @staticmethod
    def check_wind_frame_consistency(v_wind_ned: np.ndarray, v_aircraft_eci: np.ndarray,
                                    r_eci: np.ndarray, t: float,
                                    coord_manager: CoordinateSystemManager) -> dict:
        """
        檢查風場定義域一致性
        風場定義在 NED，轉到 ECI 再算空速/動壓，是否和直接在 NED 算一致
        """
        # 轉換到地理座標
        lat, lon, h = coord_manager.geodetic_from_ecef(
            coord_manager.ecef_from_eci(r_eci, t)
        )
        
        # 在 NED 下計算空速和動壓
        # 簡化：假設飛機速度在 NED 下為 v_aircraft_ned
        # 實際需從 ECI 轉換
        v_aircraft_ned = np.array([0.0, 0.0, 0.0])  # 佔位
        v_relative_ned = v_aircraft_ned - v_wind_ned
        v_relative_ned_norm = np.linalg.norm(v_relative_ned)
        
        # 轉換風場到 ECI
        v_wind_eci = coord_manager.wind_to_inertial(v_wind_ned, lat, lon, t)
        v_relative_eci = v_aircraft_eci - v_wind_eci
        v_relative_eci_norm = np.linalg.norm(v_relative_eci)
        
        # 比較
        error = abs(v_relative_ned_norm - v_relative_eci_norm)
        rel_error = error / max(v_relative_ned_norm, 1e-9)
        
        return {
            "v_relative_ned": v_relative_ned_norm,
            "v_relative_eci": v_relative_eci_norm,
            "error": error,
            "relative_error": rel_error,
            "consistent": rel_error < 1e-3,
            "test_type": "wind_frame_consistency"
        }

    @staticmethod
    def check_inverse_transform(r_eci: np.ndarray, t: float,
                               coord_mgr: 'CoordinateSystemManager' = None) -> dict:
        """
        ECI → ECEF → ECI 互逆轉換檢查
        返回: error_vector, max_error
        """
        if coord_mgr is None:
            coord_mgr = coord_manager  # 使用模組級實例
        r_ecef = coord_mgr.ecef_from_eci(r_eci, t)
        r_back = coord_mgr.eci_from_ecef(r_ecef, t)
        error_vector = r_back - r_eci
        max_err = np.max(np.abs(error_vector))
        return {
            "error_vector": error_vector.tolist(),
            "max_error": float(max_err),
            "consistent": max_err < 1e-10,
        }

    @staticmethod
    def check_time_consistency(t1: float, t2: float, tolerance: float = 1e-6) -> dict:
        """
        檢查時間一致性
        """
        error = abs(t1 - t2)
        return {
            "consistent": error < tolerance,
            "error": error
        }


# 實例化
earth_model = EarthModel()
time_system = TimeSystem()
coord_manager = CoordinateSystemManager(earth_model, time_system)
consistency_checker = ConsistencyChecker()
