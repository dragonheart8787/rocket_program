# -*- coding: utf-8 -*-
"""
事件系統：事件驅動模擬、模式切換、事件偵測
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict
from enum import Enum
import numpy as np
import math


class EventType(Enum):
    """事件類型"""
    PROPULSION_ON = "propulsion_on"
    PROPULSION_OFF = "propulsion_off"
    THROTTLE_CHANGE = "throttle_change"
    MAX_DYNAMIC_PRESSURE = "max_q"
    OVERHEAT = "overheat"
    OVERLOAD = "overload"
    FUEL_DEPLETED = "fuel_depleted"
    GROUND_IMPACT = "ground_impact"
    MODEL_BOUNDARY = "model_boundary"
    ALTITUDE_THRESHOLD = "altitude_threshold"


@dataclass
class Event:
    """事件定義"""
    event_type: EventType
    time: float
    state: np.ndarray
    data: Dict = field(default_factory=dict)
    handled: bool = False


class EventDetector:
    """事件偵測器"""

    def __init__(self):
        self.events: List[Event] = []
        self.event_handlers: Dict[EventType, Callable] = {}
        self.event_priorities: Dict[EventType, int] = {
            EventType.FUEL_DEPLETED: 1,  # 最高優先級
            EventType.GROUND_IMPACT: 2,
            EventType.OVERHEAT: 3,
            EventType.OVERLOAD: 4,
            EventType.MAX_DYNAMIC_PRESSURE: 5,
            EventType.MODEL_BOUNDARY: 6,
            EventType.THROTTLE_CHANGE: 7,
            EventType.PROPULSION_ON: 8,
            EventType.PROPULSION_OFF: 9,
            EventType.ALTITUDE_THRESHOLD: 10
        }

    def register_handler(self, event_type: EventType, handler: Callable):
        """註冊事件處理器"""
        self.event_handlers[event_type] = handler

    def set_priority(self, event_type: EventType, priority: int):
        """設置事件優先級（數字越小優先級越高）"""
        self.event_priorities[event_type] = priority

    def detect_max_q(self, q: float, q_max: float, t: float, state: np.ndarray) -> Optional[Event]:
        """偵測最大動壓"""
        if q >= q_max:
            return Event(
                event_type=EventType.MAX_DYNAMIC_PRESSURE,
                time=t,
                state=state,
                data={"q": q, "q_max": q_max}
            )
        return None

    def detect_overheat(self, T_w: float, T_max: float, t: float, state: np.ndarray) -> Optional[Event]:
        """偵測過熱"""
        if T_w >= T_max:
            return Event(
                event_type=EventType.OVERHEAT,
                time=t,
                state=state,
                data={"T_w": T_w, "T_max": T_max}
            )
        return None

    def detect_overload(self, n: float, n_max: float, t: float, state: np.ndarray) -> Optional[Event]:
        """偵測過載"""
        if n >= n_max:
            return Event(
                event_type=EventType.OVERLOAD,
                time=t,
                state=state,
                data={"n": n, "n_max": n_max}
            )
        return None

    def detect_fuel_depleted(self, m: float, m_min: float, t: float, state: np.ndarray) -> Optional[Event]:
        """偵測燃料耗盡"""
        if m <= m_min:
            return Event(
                event_type=EventType.FUEL_DEPLETED,
                time=t,
                state=state,
                data={"m": m, "m_min": m_min}
            )
        return None

    def detect_ground_impact(self, h: float, t: float, state: np.ndarray) -> Optional[Event]:
        """偵測地面碰撞"""
        if h <= 0.0:
            return Event(
                event_type=EventType.GROUND_IMPACT,
                time=t,
                state=state,
                data={"h": h}
            )
        return None

    def detect_model_boundary(self, h: float, h_max: float, M: float, M_max: float,
                             t: float, state: np.ndarray) -> Optional[Event]:
        """偵測模型適用邊界"""
        if h > h_max or M > M_max:
            return Event(
                event_type=EventType.MODEL_BOUNDARY,
                time=t,
                state=state,
                data={"h": h, "h_max": h_max, "M": M, "M_max": M_max}
            )
        return None

    def check_all_events(self, t: float, state: np.ndarray, aux: Dict) -> List[Event]:
        """檢查所有事件"""
        detected = []
        
        # 從 aux 提取量
        q = aux.get("q_dynamic", 0.0)
        T_w = aux.get("T_w", 300.0)
        n = aux.get("load_factor", 1.0)
        m = state[13] if len(state) > 13 else 100.0
        h = aux.get("altitude", 0.0)
        M = aux.get("Mach", 0.0)
        
        # 檢查各類事件
        if event := self.detect_max_q(q, 50000.0, t, state):
            detected.append(event)
        if event := self.detect_overheat(T_w, 1500.0, t, state):
            detected.append(event)
        if event := self.detect_overload(n, 10.0, t, state):
            detected.append(event)
        if event := self.detect_fuel_depleted(m, 1.0, t, state):
            detected.append(event)
        if event := self.detect_ground_impact(h, t, state):
            detected.append(event)
        if event := self.detect_model_boundary(h, 86000.0, M, 10.0, t, state):
            detected.append(event)
        
        return detected

    def handle_event(self, event: Event) -> Dict:
        """處理事件"""
        if event.event_type in self.event_handlers:
            return self.event_handlers[event.event_type](event)
        return {"handled": False, "action": "no_handler"}

    def handle_concurrent_events(self, events: List[Event]) -> List[Dict]:
        """
        處理同時事件（按優先級排序）
        返回: 處理結果列表（按優先級順序）
        """
        # 按優先級排序
        sorted_events = sorted(events, 
                              key=lambda e: self.event_priorities.get(e.event_type, 999))
        
        results = []
        for event in sorted_events:
            result = self.handle_event(event)
            result["event_type"] = event.event_type.value
            result["priority"] = self.event_priorities.get(event.event_type, 999)
            results.append(result)
        
        return results

    def check_event_timing_accuracy(self, event_time: float, true_event_time: float) -> dict:
        """
        檢查事件定位精度
        返回: 時間誤差、是否在容許範圍內
        """
        time_error = abs(event_time - true_event_time)
        threshold = 1e-3  # 1 ms
        
        return {
            "time_error": time_error,
            "threshold": threshold,
            "within_tolerance": time_error < threshold,
            "event_time": event_time,
            "true_event_time": true_event_time
        }

    def check_state_continuity(self, state_before: np.ndarray, state_after: np.ndarray,
                              event_type: EventType) -> dict:
        """
        檢查事件處理後狀態連續性
        返回: 狀態跳變量、是否產生非物理跳變
        """
        state_jump = np.linalg.norm(state_after - state_before)
        
        # 定義不同事件的容許跳變
        thresholds = {
            EventType.THROTTLE_CHANGE: 0.1,  # 節流變化允許小跳變
            EventType.PROPULSION_ON: 0.5,
            EventType.PROPULSION_OFF: 0.5,
            EventType.MAX_DYNAMIC_PRESSURE: 0.2,  # 節流降低允許小跳變
        }
        
        threshold = thresholds.get(event_type, 0.01)  # 默認嚴格
        
        return {
            "state_jump_magnitude": state_jump,
            "threshold": threshold,
            "continuous": state_jump < threshold,
            "event_type": event_type.value,
            "note": "檢查速度/角速度是否產生非物理瞬跳"
        }

    def detect_zeno_events(self, event_history: List[Event], time_window: float = 0.1) -> dict:
        """
        偵測 Zeno/抖動事件：同一事件在短時間內反覆觸發
        返回: 抖動事件列表、建議處理方式
        """
        if len(event_history) < 2:
            return {"zeno_events": [], "n_zeno": 0}
        
        zeno_events = []
        event_counts = {}
        
        # 按事件類型分組
        for event in event_history:
            event_key = event.event_type.value
            if event_key not in event_counts:
                event_counts[event_key] = []
            event_counts[event_key].append(event.time)
        
        # 檢查每個事件類型是否有抖動
        for event_type, times in event_counts.items():
            if len(times) < 2:
                continue
            
            times_sorted = sorted(times)
            for i in range(len(times_sorted) - 1):
                dt = times_sorted[i+1] - times_sorted[i]
                if dt < time_window:
                    zeno_events.append({
                        "event_type": event_type,
                        "time_1": times_sorted[i],
                        "time_2": times_sorted[i+1],
                        "dt": dt,
                        "recommendation": "需要 debounce/hysteresis"
                    })
        
        return {
            "zeno_events": zeno_events,
            "n_zeno": len(zeno_events),
            "recommendations": {
                "hysteresis": "添加滯後（hysteresis）防止抖動",
                "deadband": "添加死區（deadband）",
                "cooldown": "添加冷卻時間（cooldown）",
                "debounce": "事件去彈跳（debounce）"
            }
        }

    def event_root_finding(self, event_func: Callable, t_start: float, t_end: float,
                          state_start: np.ndarray, state_end: np.ndarray,
                          tolerance: float = 1e-6, max_iter: int = 100) -> dict:
        """
        事件回溯：使用內插/二分法找到事件發生時間
        返回: 事件時間、狀態、是否可重現
        """
        # 簡化：二分法
        t_low, t_high = t_start, t_end
        state_low, state_high = state_start, state_end
        
        for i in range(max_iter):
            t_mid = (t_low + t_high) / 2.0
            # 簡化：線性內插狀態
            alpha = (t_mid - t_low) / max(t_high - t_low, 1e-9)
            state_mid = state_low + alpha * (state_high - state_low)
            
            # 檢查事件
            event_result = event_func(t_mid, state_mid)
            if isinstance(event_result, bool):
                has_event = event_result
            else:
                has_event = event_result.get("triggered", False)
            
            if has_event:
                t_high = t_mid
                state_high = state_mid
            else:
                t_low = t_mid
                state_low = state_mid
            
            if t_high - t_low < tolerance:
                break
        
        event_time = (t_low + t_high) / 2.0
        event_state = (state_low + state_high) / 2.0
        
        return {
            "event_time": event_time,
            "event_state": event_state.tolist(),
            "tolerance_achieved": (t_high - t_low) < tolerance,
            "n_iterations": i + 1,
            "note": "事件回溯後需驗證狀態重算可重現性"
        }

    def check_reproducibility_after_root_finding(self, event_time: float, event_state: np.ndarray,
                                                 dynamics_func: Callable, random_seed: Optional[int] = None) -> dict:
        """
        檢查事件回溯後狀態重算是否可重現
        """
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # 重算狀態（從事件時間開始）
        state_recomputed = dynamics_func(event_time, event_state)
        if isinstance(state_recomputed, tuple):
            state_recomputed = state_recomputed[0]
        
        # 比較
        error = np.linalg.norm(state_recomputed - event_state)
        
        return {
            "reproducible": error < 1e-6,
            "error": error,
            "event_time": event_time,
            "note": "同 seed 應得到相同結果"
        }


class ModeSwitcher:
    """模式切換器：推進開/關、模型切換等"""

    def __init__(self):
        self.current_mode = "normal"
        self.mode_history = []

    def switch_propulsion_mode(self, mode: str, t: float):
        """切換推進模式"""
        if mode != self.current_mode:
            self.mode_history.append({"time": t, "from": self.current_mode, "to": mode})
            self.current_mode = mode

    def get_propulsion_mode(self) -> str:
        """獲取當前推進模式"""
        return self.current_mode

    def should_use_high_mach_model(self, M: float, threshold: float = 1.0) -> bool:
        """判斷是否使用高馬赫數模型"""
        return M >= threshold

    def should_use_hypersonic_heating(self, M: float, threshold: float = 5.0) -> bool:
        """判斷是否使用高超音速加熱模型"""
        return M >= threshold


# =============================================================================
# 自適應步長積分器
# =============================================================================

class AdaptiveIntegrator:
    """自適應步長積分器（Dormand-Prince 5(4)）"""

    def __init__(self, rtol: float = 1e-6, atol: float = 1e-9, min_dt: float = 1e-6, max_dt: float = 1.0):
        self.rtol = rtol
        self.atol = atol
        self.min_dt = min_dt
        self.max_dt = max_dt

    def dopri54_step(self, f: Callable, t: float, x: np.ndarray, dt: float, *args, **kwargs) -> tuple:
        """
        Dormand-Prince 5(4) 一步
        返回: (x_new, error_estimate, dt_new)
        """
        # Dormand-Prince 5(4) 係數（簡化實現）
        # 完整實現需完整 Butcher tableau
        
        # 5 階解
        k1 = f(t, x, *args, **kwargs)
        if isinstance(k1, tuple):
            k1 = k1[0]
        
        k2 = f(t + dt/5, x + dt/5*k1, *args, **kwargs)
        if isinstance(k2, tuple):
            k2 = k2[0]
        
        k3 = f(t + 3*dt/10, x + dt*(3*k1 + 9*k2)/40, *args, **kwargs)
        if isinstance(k3, tuple):
            k3 = k3[0]
        
        # 簡化：使用 RK4 作為 5 階近似
        k4 = f(t + 4*dt/5, x + dt*(44*k1 - 168*k2 + 160*k3)/45, *args, **kwargs)
        if isinstance(k4, tuple):
            k4 = k4[0]
        
        # 5 階解
        x5 = x + dt * (35*k1 + 500*k2 + 125*k3 + 512*k4) / 192
        
        # 簡化誤差估計（完整 Dormand-Prince 需更多階段）
        # 使用兩次不同階數的近似來估計誤差
        error_est = np.linalg.norm(k4 - k3) * dt * 0.01  # 簡化誤差估計
        
        # 步長調整
        if error_est > 0:
            scale = 0.9 * (self.rtol / (error_est / (self.atol + np.max(np.abs(x5))))) ** 0.2
            dt_new = np.clip(scale * dt, self.min_dt, self.max_dt)
        else:
            dt_new = min(dt * 1.2, self.max_dt)
        
        return x5, error_est, dt_new

    def integrate_adaptive(self, f: Callable, t0: float, x0: np.ndarray, t_end: float,
                          dt_initial: float, *args, **kwargs) -> tuple:
        """
        自適應積分
        返回: (t_history, x_history, dt_history)
        """
        t = t0
        x = np.copy(x0)
        dt = dt_initial
        
        t_history = [t]
        x_history = [np.copy(x)]
        dt_history = [dt]
        
        while t < t_end:
            x_new, error, dt_new = self.dopri54_step(f, t, x, dt, *args, **kwargs)
            
            # 如果誤差可接受，接受步長
            if error < self.rtol * (self.atol + np.max(np.abs(x_new))):
                x = x_new
                t += dt
                t_history.append(t)
                x_history.append(np.copy(x))
                dt = dt_new
            else:
                # 拒絕步長，縮小
                dt = dt_new
            
            dt_history.append(dt)
            
            if len(t_history) > 100000:  # 防止無限循環
                break
        
        return np.array(t_history), np.array(x_history), np.array(dt_history)


# 實例化
event_detector = EventDetector()
mode_switcher = ModeSwitcher()
adaptive_integrator = AdaptiveIntegrator()
