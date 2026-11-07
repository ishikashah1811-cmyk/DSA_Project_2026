from __future__ import annotations

import csv
import math
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.algorithms.graphs import HashtagGraph
from app.algorithms.heaps import MaxHeap
from app.algorithms.hash_tables import HashTable
from app.algorithms.sorting import merge_sort


HASHTAG_PATTERN = re.compile(r"#(\w+)", re.UNICODE)
REQUIRED_COLUMNS = {
    "Post_Hashtags",
    "No_of_likes",
    "No_of_comments",
    "No_of_shares",
}


class AnalyticsDatasetError(ValueError):
    """Raised when the analytics CSV is missing or malformed."""


@dataclass(frozen=True)
class HashtagAnalytics:
    hashtag: str
    usage_count: int
    average_likes: float
    average_comments: float
    average_shares: float
    average_engagement: float


@dataclass
class _HashtagTotals:
    usage_count: int = 0
    likes: float = 0.0
    comments: float = 0.0
    shares: float = 0.0


@dataclass(frozen=True)
class AnalyticsOverview:
    total_posts: int
    posts_with_hashtags: int
    unique_hashtags: int
    total_hashtag_uses: int
    total_likes: float
    total_comments: float
    total_shares: float


class HashtagAnalyticsService:
    """Build and query hashtag analytics independently of recommendations."""

    def __init__(self, dataset_path: str | Path | None = None) -> None:
        default_path = (
            Path(__file__).resolve().parents[4]
            / "Dataset"
            / "instagram_posts_synthetic.csv"
        )
        self.dataset_path = Path(
            dataset_path or os.getenv("CONTENTIQ_DATASET_PATH", default_path)
        )
        self._lock = threading.Lock()
        self._loaded = False
        self._post_count = 0
        self._tagged_post_count = 0
        self._total_likes = 0.0
        self._total_comments = 0.0
        self._total_shares = 0.0
        self._hashtags: HashTable[str, _HashtagTotals] = HashTable()
        self.graph = HashtagGraph()

    def overview(self) -> AnalyticsOverview:
        self._ensure_loaded()
        return AnalyticsOverview(
            total_posts=self._post_count,
            posts_with_hashtags=self._tagged_post_count,
            unique_hashtags=len(self._hashtags),
            total_hashtag_uses=sum(
                aggregate.usage_count for _, aggregate in self._hashtags.items()
            ),
            total_likes=self._total_likes,
            total_comments=self._total_comments,
            total_shares=self._total_shares,
        )

    def ranked_hashtags(
        self,
        sort_by: Literal["popularity", "engagement"] = "popularity",
        limit: int = 20,
    ) -> list[HashtagAnalytics]:
        if sort_by not in ("popularity", "engagement"):
            raise ValueError("sort_by must be 'popularity' or 'engagement'")
        if limit < 1:
            raise ValueError("limit must be at least 1")

        self._ensure_loaded()
        heap: MaxHeap[HashtagAnalytics] = MaxHeap()
        ordered_totals = merge_sort(
            list(self._hashtags.items()),
            key=lambda item: item[0],
            reverse=True,
        )
        for hashtag, totals in ordered_totals:
            analytics = self._to_analytics(hashtag, totals)
            priority = (
                float(analytics.usage_count)
                if sort_by == "popularity"
                else analytics.average_engagement
            )
            heap.push(priority, analytics)
        return [heap.pop()[1] for _ in range(min(limit, len(heap)))]

    def related_hashtags(self, hashtag: str, limit: int = 10) -> list[tuple[str, int]]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        self._ensure_loaded()
        normalized = hashtag.strip().lstrip("#").casefold()
        if not normalized or not all(character.isalnum() or character == "_" for character in normalized):
            raise ValueError("hashtag must contain only letters, numbers, or underscores")
        neighbors = self.graph.neighbors(normalized)
        return merge_sort(
            list(neighbors.items()),
            key=lambda item: (-item[1], item[0]),
        )[:limit]

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._load_dataset()
            self._loaded = True

    def _load_dataset(self) -> None:
        if not self.dataset_path.is_file():
            raise AnalyticsDatasetError(f"Dataset not found: {self.dataset_path}")

        hashtags: HashTable[str, _HashtagTotals] = HashTable()
        graph = HashtagGraph()
        post_count = 0
        tagged_post_count = 0
        total_likes = total_comments = total_shares = 0.0

        try:
            with self.dataset_path.open(
                "r", encoding="utf-8-sig", newline=""
            ) as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
                    raise AnalyticsDatasetError(
                        "CSV must have Post_Hashtags, No_of_likes, "
                        "No_of_comments, and No_of_shares columns."
                    )

                for row_number, row in enumerate(reader, start=2):
                    likes = self._read_metric(row["No_of_likes"], "No_of_likes", row_number)
                    comments = self._read_metric(
                        row["No_of_comments"], "No_of_comments", row_number
                    )
                    shares = self._read_metric(
                        row["No_of_shares"], "No_of_shares", row_number
                    )
                    post_count += 1
                    total_likes += likes
                    total_comments += comments
                    total_shares += shares

                    tags = list(
                        dict.fromkeys(
                            tag.casefold()
                            for tag in HASHTAG_PATTERN.findall(row["Post_Hashtags"] or "")
                        )
                    )
                    if not tags:
                        continue

                    tagged_post_count += 1
                    graph.add_post(tags)
                    for tag in tags:
                        aggregate = hashtags.get(tag)
                        if aggregate is None:
                            aggregate = _HashtagTotals()
                            hashtags[tag] = aggregate
                        aggregate.usage_count += 1
                        aggregate.likes += likes
                        aggregate.comments += comments
                        aggregate.shares += shares
        except AnalyticsDatasetError:
            raise
        except (OSError, csv.Error, UnicodeError) as error:
            raise AnalyticsDatasetError(f"Could not read dataset: {error}") from error

        self._hashtags = hashtags
        self.graph = graph
        self._post_count = post_count
        self._tagged_post_count = tagged_post_count
        self._total_likes = total_likes
        self._total_comments = total_comments
        self._total_shares = total_shares

    @staticmethod
    def _read_metric(value: str | None, column: str, row_number: int) -> float:
        try:
            metric = float(value or 0)
        except (TypeError, ValueError) as error:
            raise AnalyticsDatasetError(
                f"Invalid {column} value at CSV row {row_number}."
            ) from error
        if not math.isfinite(metric) or metric < 0:
            raise AnalyticsDatasetError(
                f"Invalid {column} value at CSV row {row_number}; "
                "metrics must be finite and non-negative."
            )
        return metric

    @staticmethod
    def _to_analytics(hashtag: str, totals: _HashtagTotals) -> HashtagAnalytics:
        count = totals.usage_count
        average_likes = totals.likes / count
        average_comments = totals.comments / count
        average_shares = totals.shares / count
        return HashtagAnalytics(
            hashtag=hashtag,
            usage_count=count,
            average_likes=average_likes,
            average_comments=average_comments,
            average_shares=average_shares,
            average_engagement=average_likes + average_comments + average_shares,
        )
