"""A separate-chaining hash table for constant-time average key lookup."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, TypeVar


K = TypeVar("K")
V = TypeVar("V")


class HashTable(Generic[K, V]):
    """Map hashable keys to values, resizing as the table fills."""

    def __init__(self, initial_capacity: int = 8) -> None:
        if initial_capacity < 1:
            raise ValueError("initial_capacity must be at least 1")
        self._buckets: list[list[tuple[K, V]]] = [
            [] for _ in range(initial_capacity)
        ]
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: object) -> bool:
        return self._find(key) is not None

    def __getitem__(self, key: K) -> V:
        entry = self._find(key)
        if entry is None:
            raise KeyError(key)
        return entry[1]

    def __setitem__(self, key: K, value: V) -> None:
        bucket = self._bucket_for(key)
        for index, (stored_key, _) in enumerate(bucket):
            if stored_key == key:
                bucket[index] = (key, value)
                return

        bucket.append((key, value))
        self._size += 1
        if self._size / len(self._buckets) > 0.75:
            self._resize(len(self._buckets) * 2)

    def get(self, key: K, default: V | None = None) -> V | None:
        entry = self._find(key)
        return default if entry is None else entry[1]

    def items(self) -> Iterator[tuple[K, V]]:
        for bucket in self._buckets:
            yield from bucket

    def _find(self, key: object) -> tuple[K, V] | None:
        bucket = self._buckets[hash(key) % len(self._buckets)]
        for stored_key, value in bucket:
            if stored_key == key:
                return stored_key, value
        return None

    def _bucket_for(self, key: K) -> list[tuple[K, V]]:
        return self._buckets[hash(key) % len(self._buckets)]

    def _resize(self, capacity: int) -> None:
        old_items = list(self.items())
        self._buckets = [[] for _ in range(capacity)]
        for key, value in old_items:
            self._bucket_for(key).append((key, value))
