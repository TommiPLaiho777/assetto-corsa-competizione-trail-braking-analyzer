"""Check safe initialization even when Qt isn't available in CI."""
import ast
from pathlib import Path
import unittest


class MiniHudConstructionOrder(unittest.TestCase):
    def test_drag_filter_added_after_all_required_widgets(self):
        source = (Path(__file__).resolve().parent.parent / 'mini_hud.py').read_text('utf-8')
        ast.parse(source)
        positions = {}
        for index, line in enumerate(source.splitlines()):
            for attr in ('number', 'feedback', 'corner_name', 'drag_handle'):
                if line.strip().startswith('self.' + attr + ' ='):
                    positions[attr] = index
            if 'self.drag_handle.installEventFilter(self)' in line:
                positions['filter'] = index
        self.assertEqual(set(positions), {'number','feedback','corner_name','drag_handle','filter'})
        self.assertGreater(positions['filter'], max(positions[k] for k in ('number','feedback','corner_name','drag_handle')))

    def test_event_filter_uses_safe_preconstruction_lookup(self):
        src = (Path(__file__).resolve().parent.parent / 'mini_hud.py').read_text('utf-8')
        filter_fn = src.split('    def eventFilter(', 1)[1].split('    def hideEvent(', 1)[0]
        for attribute in ('number','feedback','corner_name','drag_handle'):
            self.assertIn("getattr(self, '%s', None)" % attribute, filter_fn)

if __name__ == '__main__':
    unittest.main()
