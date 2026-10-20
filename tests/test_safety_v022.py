"""0.2.2 test suite, designed to run with ACC closed on all platforms."""
import ast
import ctypes
import os
import pathlib
import struct
import sys
import time
import unittest
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from acc_memory import ACCSharedMemory
from demo_source import DemoSource
from advanced_engine import EventTracker


class FakeKernel:
    def __init__(self, handle=0, view=None):
        self.handle = handle
        self.view = view
        self.calls = []

    def OpenFileMappingW(self, mode, inherit, name):
        self.calls.append(("open", mode, inherit, name))
        return self.handle

    def MapViewOfFile(self, handle, mode, hi, lo, size):
        self.calls.append(("map", handle, mode, size))
        return self.view

    def CloseHandle(self, handle):
        self.calls.append(("close", handle))
        return 1

    def UnmapViewOfFile(self, view):
        self.calls.append(("unmap", view))
        return 1


def fake_reader(kernel, guard=lambda: True):
    obj = ACCSharedMemory()
    obj._k32 = kernel
    obj.process_guard = guard
    return obj


class SafetyV022(unittest.TestCase):
    def test_missing_guard_refuses_connection(self):
        k = FakeKernel(42)
        r = fake_reader(k, guard=None)
        self.assertFalse(r.try_connect())
        self.assertEqual(k.calls, [])

    def test_acc_process_absent_refuses_mapping(self):
        k = FakeKernel(42)
        r = fake_reader(k, guard=lambda: False)
        self.assertFalse(r.try_connect())
        self.assertEqual(k.calls, [])

    def test_missing_mapping_does_not_create(self):
        k = FakeKernel(handle=0)
        r = fake_reader(k)
        self.assertFalse(r.try_connect())
        self.assertEqual(len(k.calls), 1)
        self.assertEqual(k.calls[0], ('open', 4, False, r.MAP_NAME))

    def test_mapping_uses_only_read_permissions(self):
        buf = ctypes.create_string_buffer(320)
        view = ctypes.addressof(buf)
        k = FakeKernel(handle=42, view=view)
        r = fake_reader(k)
        self.assertTrue(r.try_connect())
        self.assertEqual(k.calls[:3], [('open', 4, False, r.MAP_NAME),
                                       ('map', 42, 4, 320), ('close', 42)])
        r.close()
        self.assertIn(('unmap', view), k.calls)

    def test_reader_waits_for_multiple_valid_packets(self):
        buf = ctypes.create_string_buffer(320)
        v = ctypes.addressof(buf)
        struct.pack_into('<i', buf, 0, 1)
        struct.pack_into('<f', buf, 28, 150.)
        k = FakeKernel(42,v)
        r = fake_reader(k)
        self.assertIsNone(r.read())
        struct.pack_into('<i', buf, 0, 2)
        self.assertIsNotNone(r.read())
        r.close()

    def test_stalled_packet_disconnects(self):
        buf = ctypes.create_string_buffer(320)
        v = ctypes.addressof(buf)
        struct.pack_into('<i', buf, 0, 1)
        k=FakeKernel(42,v)
        r=fake_reader(k)
        self.assertIsNone(r.read())
        r.last_seen = time.monotonic()-3
        self.assertIsNone(r.read())
        self.assertIsNone(r._view)

    def test_offline_demo_never_opens_shared_memory(self):
        d = DemoSource()
        s = d.read()
        self.assertIsNotNone(s)
        self.assertLessEqual(s.brake, 1.0)
        d.close()

    def test_sources_do_not_use_dangerous_shared_memory_creation(self):
        source = (ROOT/'acc_memory.py').read_text(encoding='utf8')
        self.assertNotIn('mmap.mmap(',source)
        self.assertNotIn('CreateFileMappingW(',source)
        main = (ROOT/'main.py').read_text(encoding='utf8')
        tree = ast.parse(main)
        self.assertIn('chosen_mode = "live" if args.live else "demo"',main)
        self.assertIn('if self.mode == "live" else DemoSource()',main)

    def test_invalid_and_small_buffers_refused(self):
        self.assertIsNone(ACCSharedMemory.decode(bytes(50),1))
        b=bytearray(320)
        struct.pack_into('<i',b,0,5)
        struct.pack_into('<f',b,28,float('nan'))
        self.assertIsNone(ACCSharedMemory.decode(bytes(b),1))
