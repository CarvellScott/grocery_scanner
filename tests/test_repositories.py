#!/usr/bin/env python3
import io
import unittest
import dataclasses

from grocery_scanner.core import CSVRepository
from grocery_scanner.models import GroceryItem

class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self._sample_item = GroceryItem(
            "perfectly_generic_object",
            "Perfectly Generic Object",
            "about:blank"
        )
        self.repo = CSVRepository()

    def test_generic_save_and_load(self):
        expected_item = self._sample_item
        self.repo.save(expected_item)
        actual_item = self.repo.load(expected_item.reference)
        self.assertEqual(expected_item, actual_item)

    def test_iter_items(self):
        expected_item_1 = self._sample_item
        expected_item_2 = dataclasses.replace(self._sample_item,
                                              reference="imperfectly_generic_object")
        expected_item_set = [expected_item_1, expected_item_2]
        self.repo.save(expected_item_1)
        self.repo.save(expected_item_2)
        actual_item_set = set(self.repo.iter_items())
        self.assertEqual(len(expected_item_set), len(actual_item_set))
        self.assertIn(expected_item_1, actual_item_set)
        self.assertIn(expected_item_2, actual_item_set)

    def test_clear(self):
        self.repo.save(self._sample_item)
        self.assertEqual(len(set(self.repo.iter_items())), 1)
        self.repo.clear()
        self.assertEqual(len(set(self.repo.iter_items())), 0)

    def test_csv_support(self):
        self.repo.save(self._sample_item)
        csv_fh = io.StringIO()
        self.repo.write_to_csv_file_handler(csv_fh)
        csv_fh.seek(0)
        self.repo.clear()
        repo = CSVRepository()

        repo.read_from_csv_file_handler(csv_fh)
        self.assertEqual(repo.load(self._sample_item.reference), self._sample_item)

    def test_markdown_support(self):
        markdown_str = "- [ ] [Perfectly Generic Object](about:blank)"
        md_fh = io.StringIO(markdown_str)
        self.repo.read_from_markdown_file_handler(md_fh)
        actual_item = self.repo.load(self._sample_item.reference)
        self.assertEqual(self._sample_item, actual_item)
        pass


def main():
    pass

if __name__ == "__main__":
    main()

