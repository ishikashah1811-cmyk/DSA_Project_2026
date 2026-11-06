from __future__ import annotations

from typing import Generic, TypeVar


T = TypeVar("T")


class MaxHeap(Generic[T]):
    """A max heap that ranks items by a numeric priority."""

    def __init__(self) -> None:
        self._items: list[tuple[float, int, T]] = []
        self._next_order = 0

    def __len__(self) -> int:
        return len(self._items)

    def push(self, priority: float, item: T) -> None:
        entry = (priority, self._next_order, item)
        self._next_order += 1
        self._items.append(entry)
        index = len(self._items) - 1
        while index > 0:
            parent = (index - 1) // 2
            if self._items[parent][:2] >= self._items[index][:2]:
                break
            self._items[parent], self._items[index] = (
                self._items[index],
                self._items[parent],
            )
            index = parent

    def pop(self) -> tuple[float, T]:
        if not self._items:
            raise IndexError("pop from an empty max heap")

        root = self._items[0]
        last = self._items.pop()
        if self._items:
            self._items[0] = last
            index = 0
            while True:
                left = index * 2 + 1
                right = left + 1
                largest = index
                if left < len(self._items) and self._items[left][:2] > self._items[largest][:2]:
                    largest = left
                if right < len(self._items) and self._items[right][:2] > self._items[largest][:2]:
                    largest = right
                if largest == index:
                    break
                self._items[index], self._items[largest] = (
                    self._items[largest],
                    self._items[index],
                )
                index = largest
        return root[0], root[2]
