"""Read-only ACC v8 fastlane racing-line reference and geometric lateral deviation.

A lateral offset is distance to an AI reference, NOT proof of optimal apex.
This module does no network, game, GUI or memory I/O beyond loading a local file.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
import struct
import numpy as np

_HEADER = struct.Struct('<4i')
_POINT = struct.Struct('<4di')  # ACC v8: double x,y,z,distance + int id

@dataclass(frozen=True)
class Offset:
    distance_m: float
    side: str
    s_m: float
    segment: int
    vertical_m: float

class FastlaneReference:
    def __init__(self, xyz: np.ndarray, s: np.ndarray):
        xyz = np.asarray(xyz, dtype=float)
        s = np.asarray(s, dtype=float)
        if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) < 20 or len(xyz) != len(s):
            raise ValueError('Invalid AI reference geometry')
        if not np.isfinite(xyz).all() or not np.isfinite(s).all() or np.any(np.diff(s) <= 0):
            raise ValueError('Invalid AI reference point or distance order')
        if np.linalg.norm(xyz[0] - xyz[-1]) > 30:
            raise ValueError('Reference does not close (wrong version/track?)')
        self.xyz = xyz
        self.s = s
        # Curve projected onto the ground plane (x,z). No interpolation over
        # a distant point; the last segment wraps back to the first point.
        self.a = xyz[:, (0,2)]
        self.b = np.roll(self.a, -1, axis=0)
        self.vec = self.b - self.a
        self.length2 = np.sum(self.vec ** 2, axis=1)
        if np.count_nonzero(self.length2 < 1e-8):
            raise ValueError('Duplicate AI reference segment')
        self.y0 = xyz[:,1]
        self.y1 = np.roll(self.y0, -1)

    @classmethod
    def load_v8(cls, file: str | Path) -> 'FastlaneReference':
        path = Path(file)
        with path.open('rb') as f:
            header = f.read(_HEADER.size)
            if len(header) != _HEADER.size:
                raise ValueError('Short fastlane file')
            version, count, _, _ = _HEADER.unpack(header)
            if version != 8 or count < 20 or count > 100_000:
                raise ValueError(f'Expected ACC fastlane v8, got version {version}, count {count}')
            if path.stat().st_size < _HEADER.size + _POINT.size * count:
                raise ValueError('Truncated AI reference point block')
            points=[]
            distances=[]
            for index in range(count):
                block=f.read(_POINT.size)
                if len(block) != _POINT.size:
                    raise ValueError('Truncated point')
                x,y,z,s,i = _POINT.unpack(block)
                if i != index:
                    raise ValueError(f'Unexpected point ID at index {index}')
                points.append((x,y,z))
                distances.append(s)
        return cls(np.array(points, dtype=float), np.array(distances,dtype=float))

    def deviation(self, x: float, y: float, z: float, max_vertical_m: float = 8.0) -> Offset | None:
        if not all(math.isfinite(float(v)) for v in (x,y,z)):
            return None
        pos = np.array([x,z], dtype=float)
        ap = pos - self.a
        t = np.clip(np.sum(ap * self.vec, axis=1) / self.length2,0,1)
        nearest = self.a + self.vec * t[:,None]
        sq = np.sum((nearest - pos) ** 2, axis=1)
        vertical = np.abs(self.y0 + (self.y1 - self.y0) * t - y)
        # Bridge/overpass disambiguation. Too different in height is not the
        # same segment even when X/Z overlaps.
        sq = np.where(vertical <= max_vertical_m, sq, np.inf)
        k = int(np.argmin(sq))
        if not math.isfinite(float(sq[k])):
            return None
        cross = self.vec[k,0]*(pos[1]-nearest[k,1]) - self.vec[k,1]*(pos[0]-nearest[k,0])
        # Signed left relative to reference direction in XZ; sign must be
        # verified against actual coordinate conventions on Windows.
        side = 'LEFT' if cross > 1e-6 else 'RIGHT' if cross < -1e-6 else 'ON_LINE'
        along = float(self.s[k] + t[k] * math.sqrt(self.length2[k]))
        return Offset(math.sqrt(float(sq[k])), side, along, k, float(vertical[k]))


def describe_offset(offset: Offset | None, *, aligned: bool) -> str:
    """Strictly descriptive English guidance; no 'missed apex' claims."""
    if offset is None:
        return 'Position unavailable'
    if not aligned:
        return 'Reference alignment unverified'
    if offset.distance_m > 30:
        return 'Outside reference coverage'
    if offset.distance_m < .75:
        return 'Near AI reference'
    return f'{offset.distance_m:.1f} m {offset.side.lower()} of AI reference'
