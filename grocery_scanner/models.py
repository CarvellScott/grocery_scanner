#!/usr/bin/env python3
import dataclasses


@dataclasses.dataclass(unsafe_hash=True)
class GroceryItem:
    """
    An entity representing some type of item to be tracked.
    >>> a1 = GroceryItem("apples", "Apples", "about:blank")
    >>> a2 = dataclasses.replace(a1, name="Honeycrisp Apples")
    >>> assert a1 == a2
    >>> assert len(set([a1, a2])) == 1
    """
    reference: str = dataclasses.field(hash=True)
    name: str = dataclasses.field(compare=False)
    url: str = dataclasses.field(compare=False)
    status: str = dataclasses.field(compare=False, default="OK")


@dataclasses.dataclass
class ItemContainer:
    reference: str = dataclasses.field(hash=True)
    content: GroceryItem = dataclasses.field(hash=True)
