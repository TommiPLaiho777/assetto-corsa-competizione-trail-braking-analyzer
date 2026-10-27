"""Read-only ACC physics telemetry, Windows named mapping API.

SAFETY CONTRACT:
- Never CreateFileMapping, mmap(-1, ..., tagname=...) or write to mappings.
- Attach only in explicit --live mode, guarded by ACC process presence.
- Never launch ACC or acquire process write handles.
- Validate a packet snapshot before forwarding it to scoring.
This code cannot independently certify stability on an actual ACC installation.
"""
from __future__ import annotations
import ctypes
import math
import os
import struct
import time
from typing import Callable
from advanced_engine import TelemetrySample


class ACCSharedMemory:
    MAP_NAME = r"Local\acpmf_physics"
    MAP_SIZE = 320
    _READ = 0x0004  # FILE_MAP_READ; read-only
    _INT = struct.Struct('<i')
    _FLOAT = struct.Struct('<f')
    OFFSETS = {
        "packet": 0, "throttle": 4, "brake": 8,
        "steer": 24, "speed": 28, "acc_g": 44,
        "front_slip": 56, "front_load": 72,
        "abs": 252, "yaw_rate": 300,
    }

    def __init__(self, process_guard: Callable[[], bool] | None = None):
        """process_guard MUST check that ACC is running before access.

        No guard => connection disabled (fail-closed), including on Windows.
        """
        self._view = None
        self._k32 = None
        self.process_guard = process_guard
        self.last_packet = None
        self.last_seen = 0.0
        self.last_attempt = 0.0
        self._guard_check_time = -1e9
        self._guard_result = False
        self._ready_frames = 0
        self.connect_error = "Live connection disabled; use explicit --live mode"
        if os.name == 'nt':
            from ctypes import wintypes
            k = ctypes.WinDLL('kernel32', use_last_error=True)
            k.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
            k.OpenFileMappingW.restype = wintypes.HANDLE
            k.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                        wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
            k.MapViewOfFile.restype = ctypes.c_void_p
            k.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
            k.UnmapViewOfFile.restype = wintypes.BOOL
            k.CloseHandle.argtypes = [wintypes.HANDLE]
            k.CloseHandle.restype = wintypes.BOOL
            self._k32 = k
        else:
            self.connect_error = "Live ACC telemetry requires Windows"

    def _acc_running(self) -> bool:
        if self.process_guard is None:
            self.connect_error = "Process guard unavailable: live attach refused"
            return False
        now = time.monotonic()
        if now - self._guard_check_time < 1.0:
            return self._guard_result
        self._guard_check_time = now
        try:
            self._guard_result = bool(self.process_guard())
        except Exception:
            self._guard_result = False
        if not self._guard_result:
            self.connect_error = "Waiting for ACC process; no shared memory opened"
        return self._guard_result

    def try_connect(self) -> bool:
        if self._view is not None:
            return True
        if self._k32 is None or not self._acc_running():
            return False
        now = time.monotonic()
        if now - self.last_attempt < 1.5:
            return False
        self.last_attempt = now
        k = self._k32
        # OpenFileMappingW: OPEN ONLY. Never create an ACC-owned section.
        handle = k.OpenFileMappingW(self._READ, False, self.MAP_NAME)
        if not handle:
            self.connect_error = "ACC physics mapping not ready"
            return False
        view = None
        map_error = 0
        try:
            # A too-small section causes MapViewOfFile to fail, not extend it.
            view = k.MapViewOfFile(handle, self._READ, 0, 0, self.MAP_SIZE)
            if not view:
                map_error = ctypes.get_last_error()
        finally:
            k.CloseHandle(handle)
        if not view:
            self.connect_error = f"Physics mapping not suitable (Win32 {map_error}); detached"
            return False
        self._view = view
        self.last_packet = None
        self.last_seen = time.monotonic()
        self._ready_frames = 0
        self.connect_error = "Waiting for two coherent physics frames"
        return True

    def close(self):
        view = self._view
        self._view = None
        if view is not None and self._k32 is not None:
            self._k32.UnmapViewOfFile(view)
        self.last_packet = None
        self._ready_frames = 0

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    @classmethod
    def decode(cls, buf: bytes, timestamp: float) -> TelemetrySample | None:
        if len(buf) < 308:
            return None
        f = lambda off: cls._FLOAT.unpack_from(buf, off)[0]
        packet = cls._INT.unpack_from(buf, cls.OFFSETS['packet'])[0]
        speed, brake = f(cls.OFFSETS['speed']), f(cls.OFFSETS['brake'])
        throttle, steer = f(cls.OFFSETS['throttle']), f(cls.OFFSETS['steer'])
        yaw, abs_signal = f(cls.OFFSETS['yaw_rate']), f(cls.OFFSETS['abs'])
        front_load = f(cls.OFFSETS['front_load']) + f(cls.OFFSETS['front_load'] + 4)
        front_slip = max(abs(f(cls.OFFSETS['front_slip'])),
                         abs(f(cls.OFFSETS['front_slip'] + 4)))
        vals = (speed, brake, throttle, steer, yaw, abs_signal, front_load, front_slip)
        if not all(map(math.isfinite, vals)):
            return None
        if not (0 <= speed <= 500 and -.02 <= brake <= 1.05 and
                -.02 <= throttle <= 1.05 and -1.5 <= steer <= 1.5 and abs(yaw) <= 20 and
                -10000 <= front_load <= 100000 and 0 <= front_slip <= 1000 and
                -1 <= abs_signal <= 100):
            return None
        if packet < 0:
            return None
        return TelemetrySample(timestamp, packet, speed,
                               max(0., min(1., brake)), max(0., min(1., throttle)),
                               max(-1., min(1., steer)), yaw, max(0., abs_signal),
                               front_load, front_slip)

    def read(self) -> TelemetrySample | None:
        if self._view is not None and not self._acc_running():
            self.close()
            return None
        if self._view is None and not self.try_connect():
            return None
        try:
            # Pre- and post-copy packet IDs prevent torn data from being graded.
            before = self._INT.unpack(ctypes.string_at(self._view, 4))[0]
            data = ctypes.string_at(self._view, self.MAP_SIZE)
            after = self._INT.unpack(ctypes.string_at(self._view, 4))[0]
            if before != after or before != self._INT.unpack_from(data, 0)[0]:
                self.connect_error = "Physics packet changed during read; skipped"
                return None
            stamp = time.monotonic()
            sample = self.decode(data, stamp)
            if sample is None:
                self.connect_error = "Unrecognized physics data, frame skipped"
                self._ready_frames = 0
                return None
            if sample.packet == self.last_packet:
                if stamp - self.last_seen > 2.5:
                    self.connect_error = "Physics telemetry stalled; detached"
                    self.close()
                return None
            self.last_seen = stamp
            self.last_packet = sample.packet
            self._ready_frames += 1
            if self._ready_frames < 2:
                self.connect_error = "Waiting for a second valid physics packet"
                return None
            self.connect_error = ''
            return sample
        except (OSError, ValueError, BufferError, struct.error) as exc:
            self.connect_error = f"Read-only physics error: {exc}"
            self.close()
            return None


def acc_process_running() -> bool:
    """Read-only check to avoid connecting to stale/unowned sections."""
    import psutil
    try:
        return any((p.info['name'] or '').lower() == 'ac2-win64-shipping.exe'
                   for p in psutil.process_iter(['name']))
    except (psutil.Error, OSError):
        return False
