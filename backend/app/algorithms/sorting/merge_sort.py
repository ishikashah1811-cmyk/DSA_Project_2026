"""Stable merge sort used for deterministic hashtag analytics ordering."""

from collections.abc import Callable, Sequence
from typing import TypeVar


T = TypeVar("T")
K = TypeVar("K")


def merge_sort(
    items: Sequence[T],
    key: Callable[[T], K],
    reverse: bool = False,
) -> list[T]:
    """Return a stable sorted copy of items in O(n log n) time."""
    if len(items) <= 1:
        return list(items)

    midpoint = len(items) // 2
    left = merge_sort(items[:midpoint], key, reverse)
    right = merge_sort(items[midpoint:], key, reverse)
    merged: list[T] = []
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        left_key = key(left[left_index])
        right_key = key(right[right_index])
        left_precedes = left_key >= right_key if reverse else left_key <= right_key
        if left_precedes:
            merged.append(left[left_index])
            left_index += 1
        else:
            merged.append(right[right_index])
            right_index += 1

    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged
