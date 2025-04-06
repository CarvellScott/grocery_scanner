#!/usr/bin/env python3
import abc
import csv
import dataclasses
import shelve
import hashlib
import typing

class AbstractRepository(typing.Protocol):
    def save(self, obj):
        raise NotImplementedError

    def load(self, obj):
        raise NotImplementedError

    def obj_to_reference(self, obj):
        raise NotImplementedError


class CSVRepository(AbstractRepository):
    def __init__(self, cls, filename):
        self._csv_filename = filename
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

    def dump(self):
        with open(self._csv_filename, "w") as f:
            entries = list(map(vars, self._data))
            header = tuple(entries[0].keys())
            writer = csv.DictWriter(f, header, dialect="unix")
            writer.writeheader()
            for row in entries:
                writer.writerow(row)

    def from_file(self):
        with open(self._csv_filename, "r") as f:
            reader = csv.DictReader(f, fieldnames=["reference", "name", "url"], dialect="unix")
            for i, row in enumerate(reader):
                if i == 0:
                    continue
                obj = self._cls(**row)
                self._data[obj.reference] = obj


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        return

    def keys(self):
        return list(self._data.keys())

    def __getitem__(self, key):
        return self.load(key)


class ShelveRepository(AbstractRepository):
    def __init__(self):
        self._db_filename = "scr.shelf"

    def create(self):
        with shelve.open(self._db_filename, "w") as db:
            pass

    def save(self, entity):
        with shelve.open(self._db_filename) as db:
            reference = self.obj_to_reference(entity)
            db[reference] = entity

    def load(self, reference):
        with shelve.open(self._db_filename) as db:
            return db.get(reference)

    def list(self):
        with shelve.open(self._db_filename) as db:
            return [_ for _ in db]

    def obj_to_reference(self, obj):
        return str(obj.reference)

    def keys(self):
        with shelve.open(self._db_filename) as db:
            return tuple(db.keys())

    def __getitem__(self, key):
        return self.load(key)


class Repository(ShelveRepository):
    def save(self, entity):
        return super().save(entity)

    def load(self, reference):
        return super().load(reference)


def main():
    pass

if __name__ == "__main__":
    main()

