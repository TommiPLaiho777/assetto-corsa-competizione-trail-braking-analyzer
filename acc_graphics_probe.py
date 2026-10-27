"""Independent read-only ACC graphics probe (research, not yet integrated in HUD).

Uses OpenFileMappingW(FILE_MAP_READ) ONLY. Never CreateFileMapping/mmap(-1) or
writes to any game memory. Attached only with an ACC process guard and after ACC
is on track. Offsets follow ACC's documented graphics v1.8 layout, packed to 4.
"""
from __future__ import annotations
import ctypes
from dataclasses import dataclass
import math
import os
import time
from ctypes import wintypes

I = ctypes.c_int32
F = ctypes.c_float
U = ctypes.c_uint16
Vec3 = F * 3

class GraphicsPrefix(ctypes.LittleEndianStructure):
    _pack_ = 4
    _fields_ = [
        ('packet', I), ('status',I), ('session', I),
        ('current_time',U*15),('last_time',U*15),('best_time',U*15),('split',U*15),
        ('completed_laps',I),('race_position',I),('current_ms',I),('last_ms',I),('best_ms',I),
        ('session_left',F),('distance',F),('in_pit',I),('sector',I),('last_sector',I),('number_of_laps',I),
        ('tyre_compound',U*33),('replay_speed',F),('normalized_position',F),('active_cars',I),
        ('car_coordinates',Vec3*60),('car_ids',I*60),('player_car_id',I),
        ('penalty_time',F),('flag',I),('penalty',I),('ideal_line_on',I),('in_pit_lane',I),
    ]

@dataclass(frozen=True)
class GraphicsSample:
    packet: int
    xyz: tuple[float,float,float]
    normalized_position: float
    active_cars: int
    ideal_line_on: bool
    session: int
    status: int
    completed_laps: int | None = None


def decode_graphics(buf: bytes) -> GraphicsSample | None:
    if len(buf) < ctypes.sizeof(GraphicsPrefix):
        return None
    g=GraphicsPrefix.from_buffer_copy(buf)
    if g.packet < 0 or g.status != 2 or not 0 <= g.session <= 5:
        return None
    if not 1 <= g.active_cars <= 60 or not -.02 <= g.normalized_position <= 1.02:
        return None
    if g.in_pit or g.in_pit_lane or g.ideal_line_on not in (0,1):
        return None
    matches=[i for i in range(g.active_cars) if g.car_ids[i] == g.player_car_id]
    if len(matches) != 1:  # Never assume player vehicle is slot 0.
        return None
    pos=g.car_coordinates[matches[0]]
    xyz=(float(pos[0]),float(pos[1]),float(pos[2]))
    if not all(math.isfinite(c) and abs(c)<100_000 for c in xyz):
        return None
    return GraphicsSample(g.packet,xyz,float(g.normalized_position),
                          g.active_cars,bool(g.ideal_line_on),g.session,g.status,
                          int(g.completed_laps) if 0 <= g.completed_laps <= 100000 else None)

class GraphicsReader:
    MAP_NAME = r'Local\acpmf_graphics'
    READ = 0x0004
    def __init__(self, process_guard):
        self._k=None; self._view=None; self._last_packet=None; self._last_attempt=0
        self.process_guard=process_guard
        if os.name != 'nt':
            return
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.OpenFileMappingW.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.LPCWSTR]
        k.OpenFileMappingW.restype=wintypes.HANDLE
        k.MapViewOfFile.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.c_size_t]
        k.MapViewOfFile.restype=ctypes.c_void_p
        k.UnmapViewOfFile.argtypes=[ctypes.c_void_p]
        k.UnmapViewOfFile.restype=wintypes.BOOL
        k.CloseHandle.argtypes=[wintypes.HANDLE]
        k.CloseHandle.restype=wintypes.BOOL
        self._k=k

    def close(self):
        if self._view is not None:
            self._k.UnmapViewOfFile(self._view)
            self._view=None

    def try_connect(self):
        if self._view is not None: return True
        if self._k is None or not self.process_guard(): return False
        if time.monotonic()-self._last_attempt < 1: return False
        self._last_attempt=time.monotonic()
        k=self._k
        handle=k.OpenFileMappingW(self.READ,False,self.MAP_NAME)
        if not handle: return False
        try:
            view=k.MapViewOfFile(handle,self.READ,0,0,ctypes.sizeof(GraphicsPrefix))
        finally:
            k.CloseHandle(handle)
        if not view: return False
        self._view=view
        self._last_packet=None
        return True

    def read(self) -> GraphicsSample | None:
        if not self.process_guard():
            self.close(); return None
        if not self.try_connect(): return None
        try:
            n=ctypes.sizeof(GraphicsPrefix)
            before=I.from_buffer_copy(ctypes.string_at(self._view,4)).value
            buf=ctypes.string_at(self._view,n)
            after=I.from_buffer_copy(ctypes.string_at(self._view,4)).value
            if before!=after: return None
            data=decode_graphics(buf)
            if data is None or before!=data.packet or data.packet == self._last_packet:
                return None
            self._last_packet=data.packet
            return data
        except (OSError, ValueError, BufferError):
            self.close(); return None

    def __enter__(self): return self
    def __exit__(self,*_): self.close()
