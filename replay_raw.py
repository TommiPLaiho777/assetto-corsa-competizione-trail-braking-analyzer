"""Offline replay of raw trail traces created by >=0.2.4. Never opens ACC."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from raw_event_store import decode_event
from coaching_engine import assess

def run(input_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows=[]
    with input_path.open(encoding='utf-8') as f:
        for lineno,line in enumerate(f,1):
            if not line.strip(): continue
            try:
                record=json.loads(line)
                samples,n=decode_event(record)
                evaluation=assess(samples,n,'final')
                rows.append({'event_id':record['event_id'],
                             'score_0241':evaluation.score,
                             'label_0241':evaluation.label,
                             'confidence':evaluation.confidence,
                             'explanation':evaluation.explanation,
                             'exit_progress':evaluation.evidence.get('exit_verified',False),
                             'coast_s':evaluation.evidence.get('coasting_after_release_s','')})
            except (ValueError,TypeError,KeyError) as exc:
                print(f'Skipped invalid raw event line {lineno}: {exc}')
    keys=['event_id','score_0241','label_0241','confidence','explanation','exit_progress','coast_s']
    with output_path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return len(rows)

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Offline replay of raw event logs with corrected 0.2.4.1 scoring')
    p.add_argument('input',type=Path)
    p.add_argument('--out',type=Path,default=Path('calibration_reports/replay.csv'))
    args=p.parse_args()
    print(f'Replayed {run(args.input,args.out)} raw events. Report: {args.out}')
