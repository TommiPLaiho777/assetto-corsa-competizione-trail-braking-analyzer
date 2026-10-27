"""Pure offline probe regression. No ACC process required."""
import ctypes
from pathlib import Path
import math
import tempfile
import unittest
import numpy as np
from line_reference import FastlaneReference,describe_offset
from acc_graphics_probe import GraphicsPrefix,decode_graphics

class LineReferenceTests(unittest.TestCase):
    def setUp(self):
        # A closed loop in XZ, deliberately non-circular for segment testing.
        d=np.linspace(0,2*math.pi,200,endpoint=False)
        pts=np.column_stack((100*np.cos(d),np.zeros(200),60*np.sin(d)))
        self.ref=FastlaneReference(pts,np.arange(200,dtype=float)*4)

    def test_on_segment(self):
        a,b=self.ref.xyz[0],self.ref.xyz[1]
        p=.5*(a+b)
        x=self.ref.deviation(*p)
        self.assertAlmostEqual(x.distance_m,0,places=6)
        self.assertEqual(x.segment,0)

    def test_offset_magnitude(self):
        a,b=self.ref.xyz[0],self.ref.xyz[1]
        p=.5*(a+b)
        q=(p[0]+3,p[1],p[2])
        self.assertGreater(self.ref.deviation(*q).distance_m,0)
        self.assertIn('m',describe_offset(self.ref.deviation(*q),aligned=True))

    def test_vertical_disambiguation(self):
        self.assertIsNone(self.ref.deviation(100,30,0,max_vertical_m=8))

    def test_fail_closed_comment(self):
        self.assertEqual(describe_offset(self.ref.deviation(100,0,0),aligned=False),
                         'Reference alignment unverified')

    def test_invalid_geometry(self):
        with self.assertRaises(ValueError):
            FastlaneReference(np.full((30,3),math.nan),np.arange(30))

    def test_actual_fastlane_if_available(self):
        # Optional file from conversation not distributed; synthetic test above
        # always runs in CI. Actual game data only in local developer runtime.
        p=Path('/mnt/data/fastlane.ai')
        if not p.exists(): self.skipTest('ACC asset not present in this runtime')
        r=FastlaneReference.load_v8(p)
        self.assertEqual(len(r.xyz),5046)
        self.assertAlmostEqual(float(r.s[-1]),25200,delta=150)

class GraphicProbeTests(unittest.TestCase):
    def test_prefix_has_player_coordinate_id_and_ideal_line(self):
        self.assertGreater(GraphicsPrefix.player_car_id.offset,GraphicsPrefix.car_ids.offset)
        self.assertGreater(GraphicsPrefix.ideal_line_on.offset,GraphicsPrefix.player_car_id.offset)
        self.assertLess(ctypes.sizeof(GraphicsPrefix),4096)

    def test_player_not_first_car(self):
        g=GraphicsPrefix();g.packet=12;g.status=2;g.session=0
        g.active_cars=3;g.player_car_id=44;g.car_ids[0]=2
        g.car_ids[1]=44;g.car_ids[2]=3
        g.car_coordinates[1][0]=456.25
        g.car_coordinates[1][1]=61
        g.car_coordinates[1][2]=-554
        g.normalized_position=.4;g.ideal_line_on=1
        res=decode_graphics(bytes(g))
        self.assertIsNotNone(res)
        self.assertEqual(res.xyz,(456.25,61.,-554.))
        self.assertTrue(res.ideal_line_on)

    def test_ambiguous_player_rejected(self):
        g=GraphicsPrefix();g.packet=12;g.status=2;g.active_cars=2;g.player_car_id=44
        g.car_ids[0]=44;g.car_ids[1]=44
        self.assertIsNone(decode_graphics(bytes(g)))

    def test_pit_excluded(self):
        g=GraphicsPrefix();g.packet=12;g.status=2;g.active_cars=1;g.car_ids[0]=0
        g.player_car_id=0;g.in_pit_lane=1
        self.assertIsNone(decode_graphics(bytes(g)))

if __name__=='__main__':unittest.main()
