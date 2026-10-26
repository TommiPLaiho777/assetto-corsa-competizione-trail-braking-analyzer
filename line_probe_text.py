"""Read-only text-only racing line alignment research, not game scoring.

No automatic HUD comments until the user has verified coordinates/references.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
from pathlib import Path
import os
import sys
import time
from line_reference import FastlaneReference, describe_offset
from acc_graphics_probe import GraphicsReader


def process_running():
    import psutil
    now=time.monotonic()
    if now - getattr(process_running, '_last', -1e9) < .8:
        return getattr(process_running, '_result', False)
    process_running._last=now
    try:
        process_running._result=any((p.info['name'] or '').lower()=='ac2-win64-shipping.exe'
                                    for p in psutil.process_iter(['name']))
    except (psutil.Error,OSError):
        process_running._result=False
    return process_running._result


def main():
    cli=argparse.ArgumentParser(description='ACC Line Coach read-only text probe')
    cli.add_argument('--fastlane',required=True,help='Full path of installed ACC fastlane.ai')
    cli.add_argument('--live',action='store_true',help='Attach graphics memory read-only')
    cli.add_argument('--seconds',type=int,default=90,help='Capture duration 15..600 s')
    args=cli.parse_args()
    if not 15 <= args.seconds <= 600:
        cli.error('Duration must be between 15 and 600 seconds')
    try:
        ref=FastlaneReference.load_v8(args.fastlane)
    except (OSError,ValueError) as exc:
        print('Cannot load private AI line:',exc); return 2
    print(f'AI reference loaded: {len(ref.xyz)} points; geometry only, NOT proven green overlay')
    print('No game changes and NO existing Mini HUD changes.')
    if not args.live:
        print('Offline check passed. For live: run_line_probe_live.bat with ACC already on track.')
        return 0
    if os.name != 'nt':
        print('Live graphics only supported on Windows');return 2
    if not process_running():
        print('Start ACC and load a practice session on track FIRST.');return 2
    out=Path(__file__).parent/'data'/('line_probe_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.csv')
    out.parent.mkdir(exist_ok=True)
    near=0; frames=0; rejected=0; last_display=0
    print('Recording read-only for',args.seconds,'s; CSV stays local:',out)
    with out.open('w',newline='',encoding='utf-8') as f, GraphicsReader(process_running) as rd:
        writer=csv.writer(f)
        writer.writerow(['t_s','packet','x_m','y_m','z_m','normalized_progress','reference_s_m',
                         'reference_offset_m','side','height_difference_m','alignment_candidate','ideal_line_toggle'])
        start=time.monotonic()
        while time.monotonic()-start < args.seconds:
            time.sleep(.10)
            g=rd.read()
            if g is None: rejected+=1; continue
            offset=ref.deviation(*g.xyz)
            # Detect plausible alignment from independent frames, never
            # one lucky intersection. This is NOT calibration to the green line.
            near = min(20,near+1) if offset is not None and offset.distance_m < 12 else 0
            candidate=near>=15
            writer.writerow([f'{time.monotonic()-start:.3f}',g.packet,*[f'{p:.4f}' for p in g.xyz],
                             f'{g.normalized_position:.5f}',
                             f'{offset.s_m:.2f}' if offset else '',
                             f'{offset.distance_m:.3f}' if offset else '',offset.side if offset else '',
                             f'{offset.vertical_m:.3f}' if offset else '',int(candidate),int(g.ideal_line_on)])
            frames += 1
            if time.monotonic()-last_display > 2:
                last_display=time.monotonic()
                print(describe_offset(offset,aligned=candidate),
                      f'| samples={frames} | assist={int(g.ideal_line_on)}')
    print('Finished. Valid samples:',frames,'Skipped:',rejected)
    print('Result file:',out)
    print('Please provide the CSV for cross-check before enabling live line-coaching.')
    return 0 if frames else 2

if __name__=='__main__': sys.exit(main())
