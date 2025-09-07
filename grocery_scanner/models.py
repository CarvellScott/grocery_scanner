#!/usr/bin/env python3
import dataclasses


@dataclasses.dataclass(unsafe_hash=True)
class GroceryItem:
    reference: str = dataclasses.field(hash=True)
    name: str = dataclasses.field(compare=False)
    url: str = dataclasses.field(compare=False)
    status: str = dataclasses.field(compare=False, default="OK")


@dataclasses.dataclass
class ItemContainer:
    reference: str = dataclasses.field(hash=True)
    content: GroceryItem = dataclasses.field(hash=True)
