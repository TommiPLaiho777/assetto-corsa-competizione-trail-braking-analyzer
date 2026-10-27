"""Private offline/event-log trace serialization; no ACC integration or controls.

Separate trace file avoids inflating summary history and allows genuine later
recalibration (unlike 0.2.2/0.2.3 summary-only historical events).
"""
from __future__ import annotations
from advanced_engine import TelemetrySample

SIGNALS = ('time','packet','speed_kph','brake','throttle','steer',
           'yaw_rate','abs_active','front_load','front_slip')

def encode_event(event_id: str, samples, release_index: int) -> dict:
    if not samples or not 0 < release_index <= len(samples):
        raise ValueError('invalid event/release index')
    t0 = samples[0].time
    data=[]
    for s in samples:
        data.append([round(s.time-t0,5), int(s.packet),
                     round(s.speed_kph,3), round(s.brake,5),
                     round(s.throttle,5), round(s.steer,5),
                     round(s.yaw_rate,6), round(s.abs_active,4),
                     round(s.front_load,3), round(s.front_slip,6)])
    return {'schema':1,'event_id':event_id,'release_index':release_index,
            'fields':list(SIGNALS),'samples':data}

def decode_event(row):
    if row.get('schema') != 1 or row.get('fields') != list(SIGNALS):
        raise ValueError('unsupported raw event format')
    if len(row.get('samples',[])) > 3000 or not row.get('samples'):
        raise ValueError('invalid event size')
    samples=[TelemetrySample(*s) for s in row['samples']]
    n=row.get('release_index')
    if not isinstance(n,int) or not 0 < n <= len(samples):
        raise ValueError('invalid release index')
    return samples,n
