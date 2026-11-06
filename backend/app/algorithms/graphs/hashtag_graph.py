from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable


class HashtagGraph:
    """Weighted graph where tags are nodes and co-occurrences are edges."""

    def __init__(self) -> None:
        self.adjacency: dict[str, dict[str, int]] = defaultdict(dict)
        self.tag_counts: dict[str, int] = defaultdict(int)

    def add_post(self, hashtags: Iterable[str]) -> None:
        # Count each tag once per post, then add an edge for every tag pair.
        tags = sorted(set(hashtags))
        for tag in tags:
            self.tag_counts[tag] += 1

        for first, second in combinations(tags, 2):
            self.adjacency[first][second] = self.adjacency[first].get(second, 0) + 1
            self.adjacency[second][first] = self.adjacency[second].get(first, 0) + 1

    def neighbors(self, hashtag: str) -> dict[str, int]:
        """Return directly connected tags and their co-occurrence counts."""
        return self.adjacency.get(hashtag, {})

    def association(self, hashtag: str, selected_hashtags: Iterable[str]) -> float:
        # Average Jaccard overlap across selected tags to favor specific relations.
        selected = set(selected_hashtags)
        if not selected:
            return 0.0

        score = 0.0
        for selected_tag in selected:
            shared_posts = self.neighbors(hashtag).get(selected_tag, 0)
            total_posts = (
                self.tag_counts.get(hashtag, 0)
                + self.tag_counts.get(selected_tag, 0)
                - shared_posts
            )
            if total_posts:
                score += shared_posts / total_posts
        return score / len(selected)
