"""Offline checks; synthetic telemetry only, no ACC mapping or Qt needed."""
import math
import tempfile
import json
from unittest.mock import patch
from pathlib import Path
import unittest
from dataclasses import dataclass

from corner_names import CornerCatalog, CornerNameGate, circular_delta
from hud_presentation import HUDMessage


def fixtures():
    names = {1:'Castrol-S',5:'Dunlop-Kehre',14:'Hatzenbach',36:'Bergwerk',39:'Karussell',52:'Pflanzgarten'}
    metadata = {'slug':'nordschleife', 'corners': [
        {'number':i, 'name':names.get(i,''), 'group':'Hatzenbach' if 14<=i<=19 else ''}
        for i in range(1,61)
    ]}
    fractions=[]
    for i in range(60):
        start=i/60
        fractions.append({'key':f't{i+1}','startFrac':start,'endFrac':start+.006})
    return metadata,{'segments':fractions}


@dataclass
class G:
    normalized_position: float
    xyz: tuple


class FakeOffset:
    def __init__(self, frac, side='ON_LINE', distance=0):
        self.s_m = frac*25_200
        self.vertical_m=0
        self.distance_m=distance
        self.side=side


class FakeReference:
    s = (0,25200)
    def deviation(self, x,y,z):
        return FakeOffset(x, distance=y)


class CornerNamesTests(unittest.TestCase):
    def test_catalog_is_name_and_fraction_data_not_invented(self):
        c=CornerCatalog.from_data(*fixtures())
        self.assertEqual(len(c.turns),60)
        self.assertEqual(c.at_fraction(35/60+.002).display_name,'Bergwerk')
        self.assertEqual(c.at_fraction(38/60+.002).display_name,'Karussell')
        self.assertEqual(c.at_fraction(14/60+.002).display_name,'Hatzenbach')
        self.assertEqual(c.at_fraction(27/60+.002).display_name,'Turn 28')
        self.assertIsNone(c.at_fraction(35/60+.012))

    def test_invalid_metadata_disabled(self):
        a,b=fixtures()
        del a['corners'][-1]
        with self.assertRaises(ValueError): CornerCatalog.from_data(a,b)
        a,b=fixtures()
        b['segments'][0]['startFrac']=-0.2
        with self.assertRaises(ValueError): CornerCatalog.from_data(a,b)

    def test_time_wrap_and_nonfinite(self):
        self.assertAlmostEqual(circular_delta(.999,.001),.002)
        c=CornerCatalog.from_data(*fixtures())
        self.assertIsNone(c.at_fraction(float('nan')))

    def test_gate_requires_consistent_moving_samples(self):
        c=CornerCatalog.from_data(*fixtures()); g=CornerNameGate(c, FakeReference(),min_frames=5)
        base=35/60+.002
        for i in range(4):
            x=base+i*.00011;g.observe(G(x,(x,0.,0.)),i*.07)
            self.assertIsNone(g.candidate(i*.07))
        x=base+.00044;g.observe(G(x,(x,0.,0.)),.28)
        self.assertEqual(g.candidate(.3).display_name,'Bergwerk')
        # Single missing/duplicate graphics packet cannot erase active state.
        g.observe(None,.32)
        self.assertEqual(g.candidate(.32).display_name,'Bergwerk')
        self.assertIsNone(g.candidate(.60))
        # Unmatched coordinate samples reset candidate.
        g.observe(G(base+.001,(base+.001,21.,0.)), .68)
        self.assertIsNone(g.candidate(.69))

    def test_gate_rejects_bad_progress_and_stationary(self):
        c=CornerCatalog.from_data(*fixtures());g=CornerNameGate(c, FakeReference(),min_frames=3)
        for i in range(8):
            g.observe(G(.59,(.59,0,0)),i*.08)
        self.assertIsNone(g.candidate(.6))
        for i in range(8):
            g.observe(G(.59,(.3,0,0)),1+i*.08)
        self.assertIsNone(g.candidate(1.6))

    def test_external_metadata_download_validates_before_saving(self):
        from download_corner_metadata import download_metadata, SOURCES
        from io import BytesIO
        a,b=fixtures()
        blocks=[json.dumps(a).encode(),json.dumps(b).encode()]
        class Response:
            def __init__(self,content): self._data=BytesIO(content)
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return self._data.read(n)
        with tempfile.TemporaryDirectory() as d:
            with patch('urllib.request.urlopen',side_effect=[Response(x) for x in blocks]) as downloader:
                download_metadata(Path(d))
                self.assertEqual(downloader.call_count,2)
            self.assertIsNotNone(CornerCatalog.load(Path(d)))
            self.assertIn('GPL-3.0',(Path(d)/'SOURCE.txt').read_text('utf-8'))

    def test_bad_download_does_not_replace_old_metadata(self):
        from download_corner_metadata import download_metadata
        from io import BytesIO
        a,b=fixtures()
        class R:
            def __init__(self,content): self.data=content
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,n):return self.data
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            (folder/'nordschleife.json').write_text('original',encoding='utf-8')
            with patch('urllib.request.urlopen',side_effect=[R(json.dumps(a).encode()),R(b'not JSON')]):
                with self.assertRaises(ValueError): download_metadata(folder)
            self.assertEqual((folder/'nordschleife.json').read_text('utf-8'),'original')

    def test_hud_message_supports_optional_name_without_timing_change(self):
        from dataclasses import replace
        msg=HUDMessage(4,'Good trail','#abc','#def')
        self.assertEqual(msg.corner_name, '')
        labeled=replace(msg,corner_name='Bergwerk')
        self.assertEqual(labeled.text,msg.text)
        self.assertEqual(labeled.grade,msg.grade)
        self.assertEqual(labeled.corner_name,'Bergwerk')

if __name__=='__main__': unittest.main()
