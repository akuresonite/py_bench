"""Attribute access, instance creation, type checks."""

import dataclasses

GROUP = "micro"


class _Plain(object):
    def __init__(self, x=1, y=2):
        self.x = x
        self.y = y


class _Slotted(object):
    __slots__ = ("x", "y")

    def __init__(self, x=1, y=2):
        self.x = x
        self.y = y


class _WithProperty(object):
    def __init__(self, x=1):
        self._x = x

    @property
    def x(self):
        return self._x


@dataclasses.dataclass
class _Point:
    x: int = 1
    y: int = 2


def setup_attr_access():
    return _Plain()


def bench_attr_access(loops, state):
    """Read and write instance attributes on a normal class."""
    obj = state
    total = 0
    for _ in range(loops):
        obj.x = total
        total = obj.x + 1
    return total


def setup_attr_slots():
    return _Slotted()


def bench_attr_slots(loops, state):
    """Read and write attributes on a __slots__ class."""
    obj = state
    total = 0
    for _ in range(loops):
        obj.x = total
        total = obj.x + 1
    return total


def setup_attr_property():
    return _WithProperty()


def bench_attr_property(loops, state):
    """Read through a property descriptor."""
    obj = state
    total = 0
    for _ in range(loops):
        total += obj.x
    return total


def bench_instance_create(loops):
    """Instantiate a small class."""
    cls = _Plain
    obj = None
    for i in range(loops):
        obj = cls(i, i)
    return obj


def bench_dataclass_create(loops):
    """Instantiate a dataclass."""
    cls = _Point
    obj = None
    for i in range(loops):
        obj = cls(i, i)
    return obj


def bench_isinstance_check(loops):
    """isinstance against a normal class."""
    obj = _Plain()
    cls = _Plain
    check = isinstance
    total = 0
    for _ in range(loops):
        if check(obj, cls):
            total += 1
    return total
