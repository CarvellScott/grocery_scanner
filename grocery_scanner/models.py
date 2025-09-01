#!/usr/bin/env python3
import dataclasses
from datetime import datetime

_NOW = datetime.now()

@dataclasses.dataclass(unsafe_hash=True)
class GroceryItem:
    reference: str = dataclasses.field(hash=True)
    name: str = dataclasses.field(compare=False)
    url: dataclasses.field(compare=False)
    last_emptied: datetime = dataclasses.field(compare=False, default=_NOW)


@dataclasses.dataclass
class ItemContainer:
    reference: str = dataclasses.field(hash=True)
    content: GroceryItem = dataclasses.field(hash=True)
    last_request: datetime = dataclasses.field(compare=False, default=None)
    last_fill: datetime = dataclasses.field(compare=False, default=None)
