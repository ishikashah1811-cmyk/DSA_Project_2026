from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

from app.algorithms.hash_tables import HashTable
from app.algorithms.minhash.minhash import lsh_candidates, minhash_signature
from app.algorithms.minhash.shingling import (
    create_shingles,
    normalize_caption,
    tokenize_caption,
)


REQUIRED_COLUMNS = {"Post_Caption"}
DEFAULT_THRESHOLD = 0.75
SHINGLE_SIZE = 3
MINHASH_COUNT = 64
LSH_BANDS = 16


class DuplicateDatasetError(ValueError):
    """Raised when the caption dataset is missing or malformed."""


@dataclass(frozen=True)
class CaptionRecord:
    post_id: str
    row_number: int
    caption: str


@dataclass(frozen=True)
class ExactDuplicateGroup:
    normalized_caption: str
    posts: list[CaptionRecord]


@dataclass(frozen=True)
class NearDuplicateMatch:
    caption_a: str
    caption_b: str
    posts_a: list[CaptionRecord]
    posts_b: list[CaptionRecord]
    similarity: float
    category: str = "near_duplicate"


@dataclass(frozen=True)
class UniqueCaption:
    caption: str
    posts: list[CaptionRecord]


@dataclass(frozen=True)
class DuplicateDetectionResult:
    total_posts_scanned: int
    captions_analyzed: int
    empty_captions_skipped: int
    exact_duplicate_groups: int
    exact_duplicate_matches: int
    near_duplicate_matches: int
    unique_caption_count: int
    exact_duplicates: list[ExactDuplicateGroup]
    near_duplicates: list[NearDuplicateMatch]
    unique_captions: list[UniqueCaption]
    similarity_threshold: float


class DuplicateDetectionService:
    """Find exact and near-duplicate caption groups in the configured CSV."""

    def __init__(self, dataset_path: str | Path | None = None) -> None:
        default_path = (
            Path(__file__).resolve().parents[4]
            / "Dataset"
            / "instagram_posts_synthetic.csv"
        )
        self.dataset_path = Path(
            dataset_path or os.getenv("CONTENTIQ_DATASET_PATH", default_path)
        )

    def scan(self, similarity_threshold: float = DEFAULT_THRESHOLD) -> DuplicateDetectionResult:
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")

        rows = self._read_captions()
        # The project's custom separate-chaining table performs exact lookup.
        exact_index: HashTable[str, list[CaptionRecord]] = HashTable()
        for record in rows:
            normalized = normalize_caption(record.caption)
            if not normalized:
                continue
            group = exact_index.get(normalized)
            if group is None:
                group = []
                exact_index[normalized] = group
            group.append(record)

        normalized_groups = sorted(exact_index.items(), key=lambda item: item[0])
        exact_groups = [
            ExactDuplicateGroup(normalized, records)
            for normalized, records in normalized_groups
            if len(records) > 1
        ]
        distinct_captions = [
            (normalized, records)
            for normalized, records in normalized_groups
        ]

        shingles = [
            create_shingles(tokenize_caption(normalized), SHINGLE_SIZE)
            for normalized, _ in distinct_captions
        ]
        signatures = [minhash_signature(item, MINHASH_COUNT) for item in shingles]
        candidates = lsh_candidates(signatures, LSH_BANDS)

        near_matches: list[NearDuplicateMatch] = []
        matched_caption_indexes: set[int] = set()
        for first, second in candidates:
            similarity = jaccard_similarity(shingles[first], shingles[second])
            if similarity < similarity_threshold:
                continue
            first_text, first_records = distinct_captions[first]
            second_text, second_records = distinct_captions[second]
            near_matches.append(
                NearDuplicateMatch(
                    caption_a=first_records[0].caption,
                    caption_b=second_records[0].caption,
                    posts_a=first_records,
                    posts_b=second_records,
                    similarity=similarity,
                )
            )
            matched_caption_indexes.update((first, second))

        near_matches.sort(
            key=lambda match: (
                -match.similarity,
                normalize_caption(match.caption_a),
                normalize_caption(match.caption_b),
            )
        )
        unique_captions = [
            UniqueCaption(records[0].caption, records)
            for index, (_, records) in enumerate(distinct_captions)
            if len(records) == 1 and index not in matched_caption_indexes
        ]

        return DuplicateDetectionResult(
            total_posts_scanned=len(rows),
            captions_analyzed=sum(
                bool(normalize_caption(record.caption)) for record in rows
            ),
            empty_captions_skipped=sum(
                not normalize_caption(record.caption) for record in rows
            ),
            exact_duplicate_groups=len(exact_groups),
            exact_duplicate_matches=sum(len(group.posts) - 1 for group in exact_groups),
            near_duplicate_matches=len(near_matches),
            unique_caption_count=len(unique_captions),
            exact_duplicates=exact_groups,
            near_duplicates=near_matches,
            unique_captions=unique_captions,
            similarity_threshold=similarity_threshold,
        )

    def _read_captions(self) -> list[CaptionRecord]:
        if not self.dataset_path.is_file():
            raise DuplicateDatasetError(f"Dataset not found: {self.dataset_path}")

        records: list[CaptionRecord] = []
        try:
            with self.dataset_path.open(encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
                    raise DuplicateDatasetError(
                        "CSV must contain the Post_Caption column."
                    )
                for row_number, row in enumerate(reader, start=2):
                    caption = (row.get("Post_Caption") or "").strip()
                    post_id = (row.get("Post_id") or "").strip() or str(row_number - 1)
                    records.append(CaptionRecord(post_id, row_number, caption))
        except DuplicateDatasetError:
            raise
        except (OSError, csv.Error, UnicodeError, AttributeError) as error:
            raise DuplicateDatasetError(f"Could not read dataset: {error}") from error

        return records


def jaccard_similarity(first: set[object], second: set[object]) -> float:
    """Return exact Jaccard similarity; two empty sets are treated as identical."""
    if not first and not second:
        return 1.0
    union_size = len(first | second)
    return len(first & second) / union_size if union_size else 1.0
