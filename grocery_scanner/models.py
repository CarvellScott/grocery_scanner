#!/usr/bin/env python3
import dataclasses
from datetime import datetime

@dataclasses.dataclass(frozen=True)
class GroceryItem:
    reference: str
    name: str
    url: str

@dataclasses.dataclass
class ItemContainer:
    reference: str = dataclasses.field(hash=True)
    content: GroceryItem = dataclasses.field(hash=True)
    last_request: datetime = dataclasses.field(compare=False, default=None)
    last_fill: datetime = dataclasses.field(compare=False, default=None)
