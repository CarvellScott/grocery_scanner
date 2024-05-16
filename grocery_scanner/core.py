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
    def __init__(self):
        self._csv_filename = "data.csv"
        self._data = set()

    def save(self, obj):
        self._data.add(obj)

    def load(self, reference):
        next(_ for _ in self._data if _.reference == reference)

    def dump(self):
        with open(self._csv_filename, "w") as f:
            entries = list(map(vars, self._data))
            header = tuple(entries[0].keys())
            writer = csv.DictWriter(f, header, dialect="unix")
            writer.writeheader()
            for row in entries:
                writer.writerow(row)


class ShelveRepository(AbstractRepository):
    def __init__(self):
        self._entities = set()
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
        return obj.reference

    def keys(self):
        with shelve.open(self._db_filename) as db:
            return tuple(db.keys())

    def __getitem__(self, key):
        with shelve.open(self._db_filename) as db:
            return db[key]


class Repository(ShelveRepository):
    def save(self, entity):
        return super().save(entity)

    def load(self, reference):
        return super().load(reference)


def main():
    pass

if __name__ == "__main__":
    main()

