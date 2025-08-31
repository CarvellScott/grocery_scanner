#!/usr/bin/env python3
import unittest

from grocery_scanner import core
from grocery_scanner import models


class TestCoreImport(unittest.TestCase):
    def test_core(self):
        self.assertIsNotNone(core)
        pass


class TestModelImport(unittest.TestCase):
    def test_model(self):
        apples = models.GroceryItem("apples", "Apples", "about:blank")
        apple_box = models.ItemContainer("apple_box", apples)
        self.assertTrue(apple_box.content == apples)
