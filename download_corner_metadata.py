"""Explicit download/import of third-party, GPL-3.0 RaceIQ corner-name data.

The JSON files are NOT part of the application's source distribution. Network
use happens only upon an explicit user command, never during normal driving.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import os
import sys
import urllib.request

from corner_names import CornerCatalog, META_DIR, META_FILE, SEGMENT_FILE, CONFIG_FILE

BASE = 'https://raw.githubusercontent.com/SpeedHQ/RaceIQ/main/'
SOURCES = {
    META_FILE: BASE + 'shared/data/tracks/meta/nordschleife.json',
    SEGMENT_FILE: BASE + 'shared/data/tracks/acc/nordschleife-segments.json',
}


def download_metadata(dest=META_DIR):
    dest.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, url in SOURCES.items():
        print('Downloading', name, 'from RaceIQ...')
        req = urllib.request.Request(url, headers={'User-Agent':'AdvancedTrailBraking-CornerNames/0.3.1'})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read(250_000)
        if not data or len(data) >= 250_000:
            raise ValueError('Unexpected metadata size')
        files[name] = data
    catalog = CornerCatalog.from_data(json.loads(files[META_FILE].decode('utf-8')),
                                     json.loads(files[SEGMENT_FILE].decode('utf-8')))
    for name, data in files.items():
        tmp = dest / (name+'.tmp')
        tmp.write_bytes(data)
        os.replace(tmp, dest/name)
    (dest/'SOURCE.txt').write_text(
        'Downloaded from https://github.com/SpeedHQ/RaceIQ\n'
        'RaceIQ repository license: GNU GPL-3.0; third-party data is separate.\n'
        + '\n'.join(f'{k}: {v}' for k,v in SOURCES.items())+'\n',encoding='utf-8')
    print(f'OK: {len(catalog.turns)} track turns recognized, data stored locally in {dest}')


def configure_fastlane(path, dest=META_DIR):
    from line_reference import FastlaneReference
    ref = FastlaneReference.load_v8(path)
    if len(ref.xyz) != 5046 or not 24_000 < float(ref.s[-1]-ref.s[0]) < 27_000:
        raise ValueError('Expected verified Nurburgring 24h fastlane.ai, not another track')
    dest.mkdir(parents=True, exist_ok=True)
    (dest/CONFIG_FILE).write_text(str(Path(path).resolve()), encoding='utf-8')
    print('Nurburgring 24h fastlane registered. Original game file unchanged.')


def main():
    ap=argparse.ArgumentParser(description='Optional corner-name metadata installer')
    ap.add_argument('--download',action='store_true', help='Download two RaceIQ metadata JSONs')
    ap.add_argument('--fastlane',help='Configure original ACC Nurburgring 24h fastlane.ai path')
    a=ap.parse_args()
    if not a.download and not a.fastlane:
        ap.error('Specify --download and/or --fastlane')
    try:
        if a.download: download_metadata()
        if a.fastlane: configure_fastlane(a.fastlane)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as ex:
        print('Metadata setup failed:',ex)
        return 2
    return 0

if __name__=='__main__': sys.exit(main())
