from __future__ import annotations

import csv

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.hashtag_analytics import create_analytics_router
from app.api.hashtag_recommendation import create_recommendation_router
from app.algorithms.hash_tables import HashTable
from app.algorithms.sorting import merge_sort
from app.modules.hashtag_analytics.service import (
    AnalyticsDatasetError,
    HashtagAnalyticsService,
)
from app.modules.hashtag_recommendation.service import HashtagRecommendationService


@pytest.fixture
def analytics_csv(tmp_path):
    path = tmp_path / "posts.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "Post_id",
                "Post_Caption",
                "Post_Hashtags",
                "No_of_likes",
                "No_of_comments",
                "No_of_shares",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "Post_id": "p1",
                    "Post_Caption": "Beach vacation with friends",
                    "Post_Hashtags": "#travel #beach #travel",
                    "No_of_likes": "100",
                    "No_of_comments": "10",
                    "No_of_shares": "5",
                },
                {
                    "Post_id": "p2",
                    "Post_Caption": "Sunset by the sea",
                    "Post_Hashtags": "#travel #sunset",
                    "No_of_likes": "50",
                    "No_of_comments": "5",
                    "No_of_shares": "2",
                },
                {
                    "Post_id": "p3",
                    "Post_Caption": "Summer beach day",
                    "Post_Hashtags": "#beach #summer",
                    "No_of_likes": "200",
                    "No_of_comments": "20",
                    "No_of_shares": "10",
                },
                {
                    "Post_id": "p4",
                    "Post_Caption": "A quiet day",
                    "Post_Hashtags": "",
                    "No_of_likes": "1",
                    "No_of_comments": "0",
                    "No_of_shares": "0",
                },
            ]
        )
    return path


def test_overview_counts_posts_and_hashtag_uses(analytics_csv):
    overview = HashtagAnalyticsService(analytics_csv).overview()

    assert overview.total_posts == 4
    assert overview.posts_with_hashtags == 3
    assert overview.unique_hashtags == 4
    assert overview.total_hashtag_uses == 6
    assert overview.total_likes == 351
    assert overview.total_comments == 35
    assert overview.total_shares == 17


def test_ranked_hashtags_uses_per_post_counts_and_average_engagement(analytics_csv):
    service = HashtagAnalyticsService(analytics_csv)

    popular = service.ranked_hashtags(sort_by="popularity", limit=2)
    engaged = service.ranked_hashtags(sort_by="engagement", limit=2)

    assert [item.hashtag for item in popular] == ["beach", "travel"]
    assert popular[0].usage_count == 2
    assert [item.hashtag for item in engaged] == ["summer", "beach"]
    assert engaged[1].average_engagement == pytest.approx(172.5)


def test_related_hashtags_return_cooccurrence_frequency(analytics_csv):
    service = HashtagAnalyticsService(analytics_csv)

    assert service.related_hashtags("#TRAVEL") == [
        ("beach", 1),
        ("sunset", 1),
    ]


def test_module_two_routes_coexist_with_module_three_recommendations(analytics_csv):
    class FixedEncoder:
        def encode(self, texts: list[str]) -> np.ndarray:
            return np.tile(np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1))

    app = FastAPI()
    app.include_router(create_analytics_router(HashtagAnalyticsService(analytics_csv)))
    recommendation_service = HashtagRecommendationService(
        analytics_csv,
        encoder=FixedEncoder(),
    )
    app.include_router(create_recommendation_router(recommendation_service))
    client = TestClient(app)

    overview = client.get("/api/hashtag-analytics/overview")
    popular = client.get("/api/hashtag-analytics/hashtags?sort_by=popularity&limit=2")
    related = client.get("/api/hashtag-analytics/hashtags/travel/related")
    recommendations = client.post(
        "/api/hashtag-recommendations",
        json={"caption": "A beach holiday", "selected_hashtags": ["travel"]},
    )

    assert overview.status_code == 200
    assert overview.json()["unique_hashtags"] == 4
    assert [item["hashtag"] for item in popular.json()] == ["beach", "travel"]
    assert related.json()[0] == {"hashtag": "beach", "cooccurrences": 1}
    assert recommendations.status_code == 200
    assert recommendations.json()["recommendations"]
    assert "/api/hashtag-recommendations" in app.openapi()["paths"]


def test_invalid_dataset_schema_is_reported(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_text("caption,tags\nhello,#world\n", encoding="utf-8")

    with pytest.raises(AnalyticsDatasetError, match="Post_Hashtags"):
        HashtagAnalyticsService(path).overview()


def test_invalid_numeric_metric_is_reported(tmp_path):
    path = tmp_path / "invalid_metric.csv"
    path.write_text(
        "Post_Hashtags,No_of_likes,No_of_comments,No_of_shares\n"
        "#travel,not-a-number,2,1\n",
        encoding="utf-8",
    )

    with pytest.raises(AnalyticsDatasetError, match="No_of_likes"):
        HashtagAnalyticsService(path).overview()


def test_hash_table_handles_collisions_updates_and_resize():
    class CollisionKey:
        def __init__(self, value: str) -> None:
            self.value = value

        def __hash__(self) -> int:
            return 1

        def __eq__(self, other: object) -> bool:
            return isinstance(other, CollisionKey) and self.value == other.value

    table: HashTable[CollisionKey, int] = HashTable(initial_capacity=2)
    keys = [CollisionKey(str(index)) for index in range(20)]
    for index, key in enumerate(keys):
        table[key] = index

    assert len(table) == 20
    assert table[keys[7]] == 7
    table[keys[7]] = 70
    assert table[keys[7]] == 70
    assert table.get(CollisionKey("missing")) is None


def test_merge_sort_is_stable_and_does_not_mutate_input():
    records = [("first", 2), ("second", 1), ("third", 2)]

    assert merge_sort(records, key=lambda item: item[1]) == [
        ("second", 1),
        ("first", 2),
        ("third", 2),
    ]
    assert merge_sort(records, key=lambda item: item[1], reverse=True) == [
        ("first", 2),
        ("third", 2),
        ("second", 1),
    ]
    assert records == [("first", 2), ("second", 1), ("third", 2)]


def test_analytics_index_uses_custom_hash_table_without_changing_shared_graph(
    analytics_csv,
):
    class FixedEncoder:
        def encode(self, texts: list[str]) -> np.ndarray:
            return np.tile(
                np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1)
            )

    service = HashtagAnalyticsService(analytics_csv)
    service.overview()
    assert isinstance(service._hashtags, HashTable)

    graph = service.graph
    assert graph.neighbors("travel")["beach"] == 1
    assert graph.association("beach", ["travel"]) == pytest.approx(1 / 3)

    recommendation_service = HashtagRecommendationService(
        analytics_csv,
        encoder=FixedEncoder(),
    )
    recommendations = recommendation_service.recommend(
        "Beach vacation with friends", selected_hashtags=["travel"]
    )
    assert recommendations
    assert recommendation_service.hashtag_graph.neighbors("travel")["beach"] == 1
