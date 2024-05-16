#!/usr/bin/env python3
import dataclasses

@dataclasses.dataclass(unsafe_hash=True)
class _GroceryItem:
    reference: str
    name: str
    url: str

class GroceryItem(_GroceryItem):
    pass
