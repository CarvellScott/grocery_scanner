#!/usr/bin/env python3
import abc
import csv
import dataclasses
import hashlib
import os
import shelve
import sqlite3
import typing


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
    def __init__(self, cls):
        self._data = dict()
        self._cls = cls

    def obj_to_reference(self, obj):
        return hash(obj)

    def save(self, obj):
        self._data[obj.reference] = obj

    def load(self, reference):
        return self._data[reference]

    def clear(self):
        self._data.clear()

    def write_to_file(self, csv_filename):
        with open(csv_filename, "w") as f:
            entries = list(map(vars, self._data))
            header = tuple(entries[0].keys())
            writer = csv.DictWriter(f, header, dialect="unix")
            writer.writeheader()
            for row in entries:
                writer.writerow(row)

    def read_from_file(self, csv_filename):
        with open(csv_filename, "r") as f:
            reader = csv.DictReader(f, fieldnames=["reference", "name", "url"], dialect="unix")
            for i, row in enumerate(reader):
                if i == 0:
                    continue
                obj = self._cls(**row)
                self._data[obj.reference] = obj


    def iter_items(self):
        return iter(self._data.values())


INIT_SCRIPT = """
CREATE TABLE IF NOT EXISTS "grocery_item"(
  "reference" TEXT,
  "name" TEXT,
  "url" TEXT
);
"""

def row_factory(cursor, row):
    fields = (_[0] for _ in cursor.description)
    return dict(zip(fields, row))


class DBWrapper:
    def __init__(self):
        db = sqlite3.connect(os.environ.get("DB_URL") or ":memory:")
        db.row_factory = row_factory
        self._db = db

    def init_db(self):
        db = self._db
        with db:
            db.executescript(INIT_SCRIPT)

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
        >>> db = DBWrapper()
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

