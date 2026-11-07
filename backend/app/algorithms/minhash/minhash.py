"""Deterministic MinHash and banded LSH algorithms for caption shingles."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Hashable, Iterable, Sequence
from itertools import combinations


def minhash_signature(
    shingles: Iterable[Hashable], num_hashes: int = 64
) -> tuple[int, ...]:
    """Build a reproducible signature using seeded BLAKE2b hashes.

    Each coordinate is the minimum seeded digest among the shingles. Unlike
    Python's hash(), BLAKE2b gives the same values across processes.
    """
    if num_hashes < 1:
        raise ValueError("num_hashes must be at least 1")
    # Min is order-independent, so avoid sorting and keep signature work O(H·S).
    values = [_stable_bytes(item) for item in set(shingles)]
    if not values:
        return (2**64 - 1,) * num_hashes

    signature = []
    for seed in range(num_hashes):
        prefix = seed.to_bytes(4, "big")
        signature.append(
            min(
                int.from_bytes(
                    hashlib.blake2b(prefix + value, digest_size=8).digest(), "big"
                )
                for value in values
            )
        )
    return tuple(signature)


def estimate_jaccard(first: Sequence[int], second: Sequence[int]) -> float:
    """Estimate Jaccard similarity as the fraction of matching signature cells."""
    if len(first) != len(second):
        raise ValueError("MinHash signatures must have the same length")
    if not first:
        return 1.0
    return sum(left == right for left, right in zip(first, second)) / len(first)


def lsh_candidates(
    signatures: Sequence[Sequence[int]], bands: int = 16
) -> list[tuple[int, int]]:
    """Return unique pairs sharing at least one band bucket.

    Rows per band are derived from the signature length. Candidate generation
    is modular so its recall/cost trade-off can be tested independently.
    """
    if bands < 1:
        raise ValueError("bands must be at least 1")
    if not signatures:
        return []
    width = len(signatures[0])
    if width == 0 or any(len(signature) != width for signature in signatures):
        raise ValueError("all signatures must have the same non-zero length")
    actual_bands = min(bands, width)
    rows_per_band = width // actual_bands
    buckets: dict[tuple[int, tuple[int, ...]], list[int]] = defaultdict(list)
    for item_index, signature in enumerate(signatures):
        for band in range(actual_bands):
            start = band * rows_per_band
            end = start + rows_per_band
            # Any unused signature tail is added to the last band.
            if band == actual_bands - 1:
                end = width
            buckets[(band, tuple(signature[start:end]))].append(item_index)

    pairs: set[tuple[int, int]] = set()
    for members in buckets.values():
        if len(members) > 1:
            pairs.update(combinations(members, 2))
    return sorted(pairs)


def _stable_bytes(value: Hashable) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return repr(value).encode("utf-8")
