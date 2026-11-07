from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.duplicate_detection.service import (
    DEFAULT_THRESHOLD,
    DuplicateDatasetError,
    DuplicateDetectionService,
)


class DuplicateDetectionRequest(BaseModel):
    similarity_threshold: float = Field(default=DEFAULT_THRESHOLD, ge=0, le=1)


class CaptionRecordResponse(BaseModel):
    post_id: str
    row_number: int
    caption: str


class ExactDuplicateGroupResponse(BaseModel):
    normalized_caption: str
    posts: list[CaptionRecordResponse]


class NearDuplicateResponse(BaseModel):
    caption_a: str
    caption_b: str
    posts_a: list[CaptionRecordResponse]
    posts_b: list[CaptionRecordResponse]
    similarity: float
    category: str


class UniqueCaptionResponse(BaseModel):
    caption: str
    posts: list[CaptionRecordResponse]


class DuplicateDetectionResponse(BaseModel):
    total_posts_scanned: int
    captions_analyzed: int
    empty_captions_skipped: int
    exact_duplicate_groups: int
    exact_duplicate_matches: int
    near_duplicate_matches: int
    unique_caption_count: int
    exact_duplicates: list[ExactDuplicateGroupResponse]
    near_duplicates: list[NearDuplicateResponse]
    unique_captions: list[UniqueCaptionResponse]
    similarity_threshold: float


def create_duplicate_detection_router(
    service: DuplicateDetectionService,
) -> APIRouter:
    router = APIRouter(prefix="/api/duplicate-detection", tags=["duplicate detection"])

    @router.post("/scan", response_model=DuplicateDetectionResponse)
    def scan(request: DuplicateDetectionRequest) -> DuplicateDetectionResponse:
        try:
            result = service.scan(request.similarity_threshold)
        except DuplicateDatasetError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return DuplicateDetectionResponse(**asdict(result))

    return router
