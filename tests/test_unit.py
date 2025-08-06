#!/usr/bin/env python3
import unittest

from grocery_scanner import core

class TestCoreImport(unittest.TestCase):
    def test_core(self):
        self.assertIsNotNone(core)

def main():
    pass

if __name__ == "__main__":
    main()

