"""Offline compare original 0.2.2 vs 0.2.3 shadow scoring for JSONL logs.

Offline historical scores are limited: there are only summary metrics, no
raw curves from which to verify controlled release. Never mix demo/live data.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from calibration_engine import calibrate_metrics, CALIBRATION_VERSION


def compare_rows(rows):
    results=[]
    for row in rows:
        if row.get('mode') != 'advanced' or row.get('phase') != 'final':
            continue
        cal = row.get('calibration')
        # Existing 0.2.3 log entries include additional on-event evidence.
        # For prior logs, use metrics-only comparison and mark limited.
        if not isinstance(cal, dict) or cal.get('algorithm') != CALIBRATION_VERSION:
            cal = calibrate_metrics(row).as_log()
        results.append({
            'timestamp': str(row.get('timestamp','')),
            'original_v022': row.get('score'),
            'shadow_v023': cal.get('score'),
            'legacy_label': str(row.get('label','')),
            'shadow_label': str(cal.get('label','')),
            'confidence': str(cal.get('confidence','')),
            'reason': str(cal.get('explanation','')),
        })
    return results


def load_jsonl(path):
    rows=[]
    with open(path,encoding='utf-8-sig') as f:
        for num,line in enumerate(f, 1):
            if not line.strip(): continue
            try:
                val=json.loads(line)
                if isinstance(val,dict): rows.append(val)
            except json.JSONDecodeError:
                print(f'WARNING: invalid JSON on line {num}; skipped')
    return rows


def produce(input_path, output_dir):
    output_dir.mkdir(parents=True,exist_ok=True)
    items=compare_rows(load_jsonl(input_path))
    with (output_dir/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['timestamp','original_v022','shadow_v023','legacy_label','shadow_label','confidence','reason'])
        w.writeheader();w.writerows(items)
    before=Counter(x['original_v022'] for x in items)
    after=Counter(x['shadow_v023'] for x in items)
    lns=['# Advanced Trail Braking 0.2.3 – score calibration comparison','',
         f'Input: `{input_path.name}`','',
         f'Final event count: **{len(items)}**. The old 0.2.2 score is untouched.','',
         '| Grade | 0.2.2 original | 0.2.3 shadow |','|---|---:|---:|']
    for g in [None,1,2,3,4,5]:
        lns.append(f"| {'Not graded' if g is None else g} | {before[g]} | {after[g]} |")
    graded_old=sum(before[g] for g in [1,2,3,4,5])
    graded_new=sum(after[g] for g in [1,2,3,4,5])
    lns+=['',f'Original graded events: {graded_old}; shadow graded events: {graded_new}.','',
          '**Important:** 0.2.2 historical log rows contain summary metrics only. They do not',
          'contain the full brake/steering/yaw traces required to establish controlled',
          'brake taper. Therefore historical shadow scores have LIMITED evidence and',
          'cannot award 5/5. This is deliberately NOT an apples-to-apples validation.',
          'New 0.2.3 LIVE rows save richer evidence separately (the original score stays).',
          '',
          'Neither score proves optimal braking points, vehicle rotation caused by the',
          'brake, track position, nor good corner-exit time. Absence of trail braking',
          'is not automatically a driving error. This is a coaching comparison.','']
    (output_dir/'summary.md').write_text('\n'.join(lns),encoding='utf-8')
    return items


if __name__=='__main__':
    p=argparse.ArgumentParser(description='Offline comparison; does not touch ACC')
    p.add_argument('input',type=Path)
    p.add_argument('--out',type=Path,default=Path('calibration_reports'))
    args=p.parse_args()
    rows=produce(args.input,args.out)
    print(f'Compared {len(rows)} final events. Reports: {args.out.resolve()}')
