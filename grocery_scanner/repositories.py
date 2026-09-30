#!/usr/bin/env python3
import abc
import csv
import dataclasses
import hashlib
import os
import re
import shelve
import sqlite3
import typing

import grocery_scanner.models

class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, obj):
        raise NotImplementedError

    @abc.abstractmethod
    def load(self, obj):
        raise NotImplementedError

    @abc.abstractmethod
    def obj_to_reference(self, obj):
        raise NotImplementedError

    @abc.abstractmethod
    def iter_items(self):
        raise NotImplementedError


class CSVRepository(AbstractRepository):
    """
    This class is intended to serve as an abstraction around data storage,
    specifically writing to .csv for now because if something goes wrong, I
    don't want to have to walk my parents through SQL.
    """
    def __init__(self, cls=None):
        self._data = dict()

    def obj_to_reference(self, obj):
        return hash(obj)

    def save(self, obj):
        self._data[obj.reference] = obj

    def load(self, reference):
        return self._data[reference]

    def clear(self):
        self._data.clear()

    def iter_items(self):
        return iter(self._data.values())

    def write_to_csv_file_handler(self, writeable):
        entries = list(map(dataclasses.asdict, self._data.values()))
        header = tuple(entries[0].keys())
        writer = csv.DictWriter(writeable, header, dialect="unix")
        writer.writeheader()
        for row in entries:
            writer.writerow(row)

    def read_from_csv_file_handler(self, readable):
        reader = csv.DictReader(readable, dialect="unix")
        for i, row in enumerate(reader):
            item = grocery_scanner.models.GroceryItem(**row)
            self.save(item)

    def read_from_csv_file(self, filename):
        with open(filename, "r") as f:
            read_from_csv_file_handler(f)

    def read_from_markdown_file_handler(self, readable):
        identity_regex = re.compile(r"- \[[ x]\] ?\[(.*)\]\((.*)\)")
        for i, line in enumerate(readable.readlines()):
            regex_match = identity_regex.search(line)
            if not regex_match:
                continue
            if regex_match:
                name, url = regex_match.groups()
            reference = re.sub(r"[^a-zA-Z0-9]", "_", name.lower())
            item = grocery_scanner.models.GroceryItem(reference, name, url)
            self.save(item)

    def read_from_markdown_file(self, filename):
        with open(filename, "r") as f:
            read_from_markdown_file_handler(f)


_INIT_SCRIPT = """
CREATE TABLE IF NOT EXISTS "grocery_item"(
  "reference" TEXT,
  "name" TEXT,
  "url" TEXT
);
"""

def _row_factory(cursor, row):
    fields = (_[0] for _ in cursor.description)
    return dict(zip(fields, row))


class _DBWrapper:
    def __init__(self):
        db = sqlite3.connect(os.environ.get("DB_URL") or ":memory:")
        db.row_factory = _row_factory
        self._db = db

    def init_db(self):
        db = self._db
        with db:
            db.executescript(_INIT_SCRIPT)

    def _generic_insert(self, dataclass_instance):
        fields = dataclasses.fields(dataclass_instance)
        names = [_.name for _ in fields]
        obj_dict = dataclasses.asdict(dataclass_instance)

    def upsert_item(self, grocery_item):
        with self._db:
            db_cmd = "INSERT OR REPLACE INTO grocery_item (reference, name, url) VALUES (?, ?, ?)"
            values = (grocery_item.reference, grocery_item.name, grocery_item.url)
            self._db.execute(db_cmd, values)

    def get_item(self, reference):
        """
        >>> from grocery_scanner.models import GroceryItem
        >>> db = _DBWrapper()
        >>> db.init_db()
        >>> expected_item = GroceryItem("test_item", "Test Item", "about:blank")
        >>> db.upsert_item(expected_item)
        >>> actual_item = GroceryItem(**db.get_item("test_item"))
        >>> assert expected_item == actual_item
        """
        db_cmd = "SELECT * FROM grocery_item WHERE reference = ?"
        cur = self._db.execute(db_cmd, (reference,))
        row = cur.fetchone()
        if row:
            return dict(row)
        raise KeyError(reference)

    def dump(self):
        print("\n".join(self.db.iterdump()))


def main():
    pass

if __name__ == "__main__":
    main()

