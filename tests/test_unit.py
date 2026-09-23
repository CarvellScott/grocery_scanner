#!/usr/bin/env python3
import unittest

from grocery_scanner import core
from grocery_scanner import models
from grocery_scanner import services


class TestCoreImport(unittest.TestCase):
    def test_core(self):
        self.assertIsNotNone(core)
        pass


class TestModelImport(unittest.TestCase):
    def test_model(self):
        apples = models.GroceryItem("apples", "Apples", "about:blank")
        apple_box = models.ItemContainer("apple_box", apples)
        self.assertTrue(apple_box.content == apples)

class TestServices(unittest.TestCase):
    def test_import_items_from_markdown(self):
        item_list = "- [ ] [Item Name](about:blank)"
        generator = services.read_items_from_markdown_str(item_list)
        repo = core.CSVRepository(models.GroceryItem)
        services.add_items_from_markdown_content(repo, item_list)
        self.assertIsNotNone(next(generator))
