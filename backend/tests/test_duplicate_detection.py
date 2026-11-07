from __future__ import annotations

import csv

import pytest
from fastapi.testclient import TestClient

from app.algorithms.minhash.minhash import (
    estimate_jaccard,
    lsh_candidates,
    minhash_signature,
)
from app.algorithms.minhash.shingling import (
    create_shingles,
    normalize_caption,
    tokenize_caption,
)
from app.modules.duplicate_detection.service import (
    DuplicateDatasetError,
    DuplicateDetectionService,
    jaccard_similarity,
)
from app.main import create_app


def _write_csv(path, captions: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Post_id", "Post_Caption"])
        writer.writerows(captions)


def test_caption_normalization_preserves_hashtags_and_emoji():
    assert normalize_caption("  CAFÉ—time!!  #Summer 🤍  ") == "café time #summer 🤍"
    assert normalize_caption("Great-day") == normalize_caption("great day")
    assert tokenize_caption("#HappyDay 🤍") == ["#happyday", "🤍"]


def test_shingles_support_short_captions_and_empty_input():
    assert create_shingles(["one", "two"], 3) == {("one", "two")}
    assert create_shingles(["one"], 3) == {("one",)}
    assert create_shingles([], 3) == set()
    with pytest.raises(ValueError):
        create_shingles(["one"], 0)


def test_jaccard_similarity_handles_overlap_and_empty_sets():
    assert jaccard_similarity({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert jaccard_similarity(set(), set()) == 1
    assert jaccard_similarity(set(), {"x"}) == 0


def test_minhash_is_deterministic_and_estimates_overlap():
    first = {("one",), ("two",), ("three",)}
    second = {("one",), ("two",), ("other",)}
    signature_a = minhash_signature(first, num_hashes=128)
    signature_b = minhash_signature(first, num_hashes=128)

    assert signature_a == signature_b
    assert estimate_jaccard(signature_a, minhash_signature(second, 128)) == pytest.approx(
        1 / 2, abs=0.15
    )
    assert minhash_signature(set(), 4) == (2**64 - 1,) * 4


def test_lsh_candidate_generation_is_deterministic_and_deduplicated():
    signatures = [(1, 2, 3, 4), (1, 2, 8, 9), (5, 6, 7, 8)]
    assert lsh_candidates(signatures, bands=2) == [(0, 1)]
    assert lsh_candidates([], bands=2) == []


def test_service_classifies_exact_near_unique_and_empty_captions(tmp_path):
    path = tmp_path / "captions.csv"
    _write_csv(
        path,
        [
            ("p1", "A sunny beach walk with my best friends under the golden evening sky while we take photos and share stories beside gentle waves and warm sand before the quiet sunset settles over the ocean"),
            ("p2", " A SUNNY beach walk with my best friends under the golden evening sky while we take photos and share stories beside gentle waves and warm sand before the quiet sunset settles over the ocean! "),
            ("p3", "A sunny beach walk with my close friends under the golden evening sky while we take photos and share stories beside gentle waves and warm sand before the quiet sunset settles over the ocean"),
            ("p4", "Quantum computers change scientific research"),
            ("p5", "   "),
        ],
    )

    result = DuplicateDetectionService(path).scan(similarity_threshold=0.7)

    assert result.total_posts_scanned == 5
    assert result.captions_analyzed == 4
    assert result.empty_captions_skipped == 1
    assert result.exact_duplicate_groups == 1
    assert result.exact_duplicate_matches == 1
    assert result.exact_duplicates[0].posts[0].post_id == "p1"
    assert result.exact_duplicates[0].posts[1].post_id == "p2"
    assert result.near_duplicate_matches == 1
    assert result.near_duplicates[0].similarity >= 0.7
    assert result.unique_caption_count == 1
    assert result.unique_captions[0].posts[0].post_id == "p4"


def test_threshold_validation_and_missing_or_invalid_dataset(tmp_path):
    with pytest.raises(ValueError, match="between 0 and 1"):
        DuplicateDetectionService(tmp_path / "missing.csv").scan(-0.1)
    with pytest.raises(DuplicateDatasetError, match="Dataset not found"):
        DuplicateDetectionService(tmp_path / "missing.csv").scan()

    malformed = tmp_path / "malformed.csv"
    malformed.write_text("caption\nhello\n", encoding="utf-8")
    with pytest.raises(DuplicateDatasetError, match="Post_Caption"):
        DuplicateDetectionService(malformed).scan()


def test_duplicate_detection_api_returns_structured_results(tmp_path):
    path = tmp_path / "captions.csv"
    _write_csv(path, [("one", "hello world from the beach"), ("two", "hello world from the beach")])
    client = TestClient(
        create_app(duplicate_detection_service=DuplicateDetectionService(path))
    )

    response = client.post(
        "/api/duplicate-detection/scan", json={"similarity_threshold": 0.75}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_posts_scanned"] == 2
    assert body["exact_duplicate_groups"] == 1
    assert body["exact_duplicates"][0]["posts"][0]["post_id"] == "one"
    assert "/api/duplicate-detection/scan" in client.app.openapi()["paths"]

    invalid = client.post(
        "/api/duplicate-detection/scan", json={"similarity_threshold": 1.5}
    )
    assert invalid.status_code == 422

    missing_client = TestClient(
        create_app(
            duplicate_detection_service=DuplicateDetectionService(
                tmp_path / "not-present.csv"
            )
        )
    )
    missing = missing_client.post("/api/duplicate-detection/scan", json={})
    assert missing.status_code == 503
    assert "Dataset not found" in missing.json()["detail"]
