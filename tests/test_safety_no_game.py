"""Regression checks that can be run without Windows or ACC."""
import ast
import os
import pathlib
import struct
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from acc_memory import ACCSharedMemory

class SafetyRegression(unittest.TestCase):
    def test_no_shared_memory_creation_primitive(self):
        source = (ROOT / 'acc_memory.py').read_text(encoding='utf-8')
        self.assertNotIn('mmap.mmap(', source)
        self.assertNotIn('CreateFileMappingW(', source)
        self.assertIn('OpenFileMappingW(', source)
        self.assertIn('FILE_MAP_READ', source)

    def test_windows_only_backend_when_on_linux(self):
        if os.name != 'nt':
            reader = ACCSharedMemory()
            self.assertFalse(reader.try_connect())
            self.assertIsNone(reader.read())

    def test_no_phantom_mapping_when_acc_absent_on_windows(self):
        if os.name != 'nt':
            self.skipTest('Windows named mappings only')
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        k.OpenFileMappingW.restype = wintypes.HANDLE
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        name = ACCSharedMemory.MAP_NAME
        before = k.OpenFileMappingW(0x0004, False, name)
        if before:
            k.CloseHandle(before)
            self.skipTest('ACC mapping already exists; run with ACC stopped')
        reader = ACCSharedMemory()
        self.assertFalse(reader.try_connect())
        reader.close()
        after = k.OpenFileMappingW(0x0004, False, name)
        if after:
            k.CloseHandle(after)
        self.assertFalse(after, 'Program must not create an ACC mapping')

    def test_decode_known_packet_without_win32(self):
        buf=bytearray(320)
        struct.pack_into('<i',buf,0,123)
        for off,val in ((4,.3),(8,.6),(24,.2),(28,180.),(300,.18)):
            struct.pack_into('<f',buf,off,val)
        sample=ACCSharedMemory.decode(bytes(buf),42.)
        self.assertIsNotNone(sample)
        self.assertEqual(sample.packet,123)
        self.assertAlmostEqual(sample.yaw_rate,.18,places=5)

    def test_short_data_rejected(self):
        self.assertIsNone(ACCSharedMemory.decode(bytes(64),42.))

if __name__ == '__main__': unittest.main()
