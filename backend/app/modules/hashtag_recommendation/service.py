from __future__ import annotations

import csv
import math
import os
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from app.algorithms.graphs import HashtagGraph
from app.algorithms.heaps import MaxHeap
from app.algorithms.similarity_search.sentence_transformer import (
    SentenceTransformerEncoder,
    TextEncoder,
)


HASHTAG_PATTERN = re.compile(r"#(\w+)")
SEMANTIC_WEIGHT = 0.50
ASSOCIATION_WEIGHT = 0.30
ENGAGEMENT_WEIGHT = 0.20


class DatasetError(ValueError):
    """Raised when the recommendation CSV is missing or invalid."""


@dataclass
class Post:
    caption: str
    hashtags: list[str]
    engagement: float


@dataclass
class Recommendation:
    hashtag: str
    score: float
    semantic_relevance: float
    hashtag_association: float
    engagement: float
    similar_posts: int


class HashtagRecommendationService:
    def __init__(
        self,
        dataset_path: str | Path | None = None,
        encoder: TextEncoder | None = None,
    ) -> None:
        default_path = (
            Path(__file__).resolve().parents[4]
            / "Dataset"
            / "instagram_posts_synthetic.csv"
        )
        self.dataset_path = Path(
            dataset_path or os.getenv("CONTENTIQ_DATASET_PATH", default_path)
        )
        self.encoder = encoder or SentenceTransformerEncoder()
        self.posts: list[Post] = []
        self.vectors: np.ndarray | None = None
        self.hashtag_posts: dict[str, list[int]] = {}
        self.hashtag_graph = HashtagGraph()
        self.max_engagement = 0.0
        self._load_lock = threading.Lock()

    def recommend(
        self,
        caption: str,
        selected_hashtags: Sequence[str] = (),
        top_k: int = 10,
        neighbors: int = 30,
    ) -> list[Recommendation]:
        if not caption.strip():
            raise ValueError("caption must not be empty")
        if not 1 <= top_k <= 50 or not 1 <= neighbors <= 100:
            raise ValueError("top_k must be 1-50 and neighbors must be 1-100")

        self._load_index()
        assert self.vectors is not None
        query = self._normalize(self.encoder.encode([caption]))[0]
        similarities = self.vectors @ query
        nearest = np.argsort(similarities)[-neighbors:][::-1]

        # Normalize input tags so `school` and `#School` refer to the same node.
        selected = {self._clean_tag(tag) for tag in selected_hashtags}
        selected.discard("")

        # Find tags from similar captions and from selected tags' graph neighbors.
        candidates = {
            tag
            for index in nearest
            for tag in self.posts[int(index)].hashtags
        }
        for tag in selected:
            candidates.update(self.hashtag_graph.neighbors(tag))
        candidates.difference_update(selected)

        # Score each candidate using its most relevant historical posts.
        heap: MaxHeap[Recommendation] = MaxHeap()
        for tag in candidates:
            post_indexes = self.hashtag_posts[tag]
            best_posts = sorted(
                post_indexes,
                key=lambda index: similarities[index],
                reverse=True,
            )[:5]
            relevance = sum(
                max(float(similarities[index]), 0.0) for index in best_posts
            ) / len(best_posts)
            engagement = sum(
                self._normalize_engagement(self.posts[index].engagement)
                for index in best_posts
            ) / len(best_posts)
            association = self.hashtag_graph.association(tag, selected)
            score = (
                SEMANTIC_WEIGHT * relevance
                + ASSOCIATION_WEIGHT * association
                + ENGAGEMENT_WEIGHT * engagement
            )
            heap.push(
                score,
                Recommendation(
                    hashtag=tag,
                    score=score,
                    semantic_relevance=relevance,
                    hashtag_association=association,
                    engagement=engagement,
                    similar_posts=sum(
                        tag in self.posts[int(index)].hashtags for index in nearest
                    ),
                ),
            )

        results = [heap.pop()[1] for _ in range(min(top_k, len(heap)))]
        return sorted(results, key=lambda item: (-item.score, item.hashtag))

    def _load_index(self) -> None:
        if self.vectors is not None:
            return

        with self._load_lock:
            if self.vectors is not None:
                return

            self.posts = self._read_posts()
            self.vectors = self._normalize(
                self.encoder.encode([post.caption for post in self.posts])
            )
            if len(self.vectors) != len(self.posts):
                raise RuntimeError("The embedding model returned an invalid index.")

            hashtag_posts: dict[str, list[int]] = defaultdict(list)
            for index, post in enumerate(self.posts):
                # Build co-occurrence edges and the tag-to-post lookup together.
                self.hashtag_graph.add_post(post.hashtags)
                for tag in post.hashtags:
                    hashtag_posts[tag].append(index)
            self.hashtag_posts = dict(hashtag_posts)
            self.max_engagement = max(post.engagement for post in self.posts)

    def _read_posts(self) -> list[Post]:
        if not self.dataset_path.is_file():
            raise DatasetError(f"Dataset not found: {self.dataset_path}")

        try:
            with self.dataset_path.open(encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                required = {
                    "Post_Caption",
                    "Post_Hashtags",
                    "No_of_likes",
                    "No_of_comments",
                    "No_of_shares",
                }
                if not reader.fieldnames or not required.issubset(reader.fieldnames):
                    raise DatasetError(
                        "CSV must have Post_Caption, Post_Hashtags, "
                        "No_of_likes, No_of_comments, and No_of_shares columns."
                    )

                posts = []
                for row in reader:
                    caption = (row["Post_Caption"] or "").strip()
                    hashtags = [
                        tag.casefold()
                        for tag in HASHTAG_PATTERN.findall(row["Post_Hashtags"] or "")
                    ]
                    if caption and hashtags:
                        engagement = sum(
                            self._number(row[column])
                            for column in ("No_of_likes", "No_of_comments", "No_of_shares")
                        )
                        posts.append(Post(caption, list(dict.fromkeys(hashtags)), engagement))
        except (OSError, csv.Error, UnicodeError) as error:
            raise DatasetError(f"Could not read dataset: {error}") from error

        if not posts:
            raise DatasetError("The CSV contains no posts with captions and hashtags.")
        return posts

    def _normalize_engagement(self, engagement: float) -> float:
        if self.max_engagement == 0:
            return 0
        return math.log1p(engagement) / math.log1p(self.max_engagement)

    @staticmethod
    def _number(value: str | None) -> float:
        try:
            return max(float(value or 0), 0)
        except ValueError:
            return 0

    @staticmethod
    def _clean_tag(tag: str) -> str:
        return tag.strip().lstrip("#").casefold()

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
        return np.divide(vectors, lengths, out=np.zeros_like(vectors), where=lengths != 0)
