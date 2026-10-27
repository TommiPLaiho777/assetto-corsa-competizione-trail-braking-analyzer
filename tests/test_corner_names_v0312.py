"""Regression: a constant ACC/AI lap-zero offset must not block turn names."""
import tempfile
from pathlib import Path
import unittest
from tests.test_corner_names_v031 import fixtures, G, FakeReference
from corner_names import CornerCatalog, CornerNameGate
from diagnose_corner_names import diagnose
from unittest.mock import patch


class V0312Regression(unittest.TestCase):
    def test_acc_startline_shift_is_accepted_for_same_ai_geometry(self):
        c=CornerCatalog.from_data(*fixtures())
        gate=CornerNameGate(c,FakeReference(),min_frames=8)
        base=35/60+.001
        for i in range(8):
            reference_frac=base+i*.00010
            acc_frac=(reference_frac+.081)%1
            gate.observe(G(acc_frac,(reference_frac,0.,0.)), i*.06)
        self.assertEqual(gate.candidate(.43).display_name,'Bergwerk')
        self.assertIn('aligned',gate.status.lower())

    def test_variable_alignment_is_rejected(self):
        c=CornerCatalog.from_data(*fixtures())
        gate=CornerNameGate(c,FakeReference(),min_frames=8)
        base=35/60+.001
        for i in range(8):
            reference_frac=base+i*.00011
            acc_frac=reference_frac + .09 + .014*i/7
            gate.observe(G(acc_frac,(reference_frac,0.,0.)), i*.06)
        self.assertIsNone(gate.candidate(.43))
        self.assertIn('inconsistently',gate.status)

    def test_offtrack_geometry_does_not_leak_old_names(self):
        c=CornerCatalog.from_data(*fixtures())
        gate=CornerNameGate(c,FakeReference(),min_frames=5)
        base=35/60+.001
        for i in range(5):
            r=base+i*.00011
            gate.observe(G(r+.02,(r,0.,0.)),i*.07)
        self.assertIsNotNone(gate.candidate(.3))
        gate.observe(G(base+.001,(base+.001,22.,0.)),.33)
        self.assertIsNone(gate.candidate(.34))

    def test_metadata_files_alone_are_insufficient(self):
        a,b=fixtures()
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            import json
            (folder/'nordschleife.json').write_text(json.dumps(a))
            (folder/'nordschleife-segments.json').write_text(json.dumps(b))
            self.assertEqual(diagnose(folder),2)

if __name__=='__main__': unittest.main()
