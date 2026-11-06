from __future__ import annotations

import csv

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.algorithms.graphs import HashtagGraph
from app.main import create_app
from app.modules.hashtag_recommendation.service import (
    DatasetError,
    HashtagRecommendationService,
)


class FixedEncoder:
    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = {
            "a relaxing beach vacation": [1.0, 0.0],
            "beach vacation with friends": [1.0, 0.0],
            "sunny beach and ocean": [0.9, 0.1],
            "city museum architecture": [0.0, 1.0],
            "weekend travel by the sea": [0.8, 0.2],
            "beach sunset": [1.0, 0.0],
        }
        return np.asarray([vectors[text] for text in texts], dtype=np.float32)


@pytest.fixture
def recommendation_csv(tmp_path):
    path = tmp_path / "posts.csv"
    rows = [
        ("beach vacation with friends", "#travel #beach #friends", "120", "20", "5"),
        ("sunny beach and ocean", "#travel #ocean #summer", "80", "10", "2"),
        ("city museum architecture", "#travel #city #art", "1000", "100", "40"),
        ("weekend travel by the sea", "#travel #beach #weekend", "200", "25", "10"),
        ("beach sunset", "#travel #sunset #beach", "50", "5", "1"),
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Post_Caption",
                "Post_Hashtags",
                "No_of_likes",
                "No_of_comments",
                "No_of_shares",
            ]
        )
        writer.writerows(rows)
    return path


def test_recommends_semantically_relevant_hashtags_and_excludes_selected(recommendation_csv):
    service = HashtagRecommendationService(recommendation_csv, FixedEncoder())

    results = service.recommend(
        "a relaxing beach vacation", selected_hashtags=["#travel"], top_k=10
    )

    names = [result.hashtag for result in results]
    assert "beach" in names
    assert "ocean" in names
    assert "travel" not in names
    assert names.index("beach") < names.index("city")
    assert all(0 <= result.score <= 1 for result in results)


def test_selected_hashtags_contribute_association_score(recommendation_csv):
    service = HashtagRecommendationService(recommendation_csv, FixedEncoder())

    results = service.recommend(
        "a relaxing beach vacation", selected_hashtags=["#travel"], top_k=10
    )
    beach = next(result for result in results if result.hashtag == "beach")

    assert beach.hashtag_association > 0
    assert beach.semantic_relevance > 0
    assert beach.engagement > 0


def test_graph_recommends_neighbors_outside_caption_matches(tmp_path):
    path = tmp_path / "posts.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Post_Caption",
                "Post_Hashtags",
                "No_of_likes",
                "No_of_comments",
                "No_of_shares",
            ]
        )
        writer.writerows(
            [
                ("nearest caption", "#beach #summer", 10, 0, 0),
                ("school memory", "#school #friends #throwback", 100, 0, 0),
                ("school friends", "#school #friends", 100, 0, 0),
            ]
        )

    class GraphEncoder:
        def encode(self, texts: list[str]) -> np.ndarray:
            vectors = {
                "caption query": [1.0, 0.0],
                "nearest caption": [1.0, 0.0],
                "school memory": [0.0, 1.0],
                "school friends": [0.0, 1.0],
            }
            return np.asarray([vectors[text] for text in texts], dtype=np.float32)

    service = HashtagRecommendationService(path, GraphEncoder())
    results = service.recommend(
        "caption query", selected_hashtags=["#school"], neighbors=1, top_k=10
    )
    friends = next(item for item in results if item.hashtag == "friends")

    assert friends.similar_posts == 0
    assert friends.hashtag_association > 0
    assert service.hashtag_graph.neighbors("school")["friends"] == 2


def test_graph_counts_cooccurrence_and_association():
    graph = HashtagGraph()
    graph.add_post(["school", "friends"])
    graph.add_post(["school", "friends"])
    graph.add_post(["school", "memories"])

    assert graph.neighbors("school")["friends"] == 2
    assert graph.association("friends", ["school"]) == pytest.approx(2 / 3)
    assert graph.association("memories", ["school"]) == pytest.approx(1 / 3)


def test_accepts_dataset_engagement_column_names(tmp_path):
    path = tmp_path / "dataset.csv"
    path.write_text(
        "Post_Caption,Post_Hashtags,No_of_likes,No_of_comments,No_of_shares\n"
        "beach sunset,#beach #sunset,20,3,2\n",
        encoding="utf-8",
    )
    service = HashtagRecommendationService(path, FixedEncoder())

    results = service.recommend("beach sunset")

    assert results[0].engagement == 1


def test_invalid_dataset_schema_is_reported(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_text("body,labels\nhello,#world\n", encoding="utf-8")
    service = HashtagRecommendationService(path, FixedEncoder())

    with pytest.raises(DatasetError, match="Post_Caption"):
        service.recommend("hello")


def test_empty_caption_is_rejected(recommendation_csv):
    service = HashtagRecommendationService(recommendation_csv, FixedEncoder())

    with pytest.raises(ValueError, match="caption must not be empty"):
        service.recommend("  ")


def test_recommendation_api_returns_ranked_results(recommendation_csv):
    service = HashtagRecommendationService(recommendation_csv, FixedEncoder())
    client = TestClient(create_app(service))

    response = client.post(
        "/api/hashtag-recommendations",
        json={
            "caption": "a relaxing beach vacation",
            "selected_hashtags": ["#travel"],
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    results = response.json()["recommendations"]
    assert len(results) == 3
    assert results[0]["score"] >= results[-1]["score"]
    assert all("semantic_relevance" in result for result in results)
