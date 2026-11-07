from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.modules.hashtag_analytics.service import (
    AnalyticsDatasetError,
    HashtagAnalyticsService,
)


class HashtagAnalyticsItem(BaseModel):
    hashtag: str
    usage_count: int
    average_likes: float
    average_comments: float
    average_shares: float
    average_engagement: float


class AnalyticsOverviewResponse(BaseModel):
    total_posts: int
    posts_with_hashtags: int
    unique_hashtags: int
    total_hashtag_uses: int
    total_likes: float
    total_comments: float
    total_shares: float


def create_analytics_router(service: HashtagAnalyticsService) -> APIRouter:
    router = APIRouter(prefix="/api/hashtag-analytics", tags=["hashtag analytics"])

    @router.get("/overview", response_model=AnalyticsOverviewResponse)
    def overview() -> AnalyticsOverviewResponse:
        try:
            return AnalyticsOverviewResponse(**service.overview().__dict__)
        except AnalyticsDatasetError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @router.get("/hashtags", response_model=list[HashtagAnalyticsItem])
    def ranked_hashtags(
        sort_by: Literal["popularity", "engagement"] = Query("popularity"),
        limit: int = Query(20, ge=1, le=100),
    ) -> list[HashtagAnalyticsItem]:
        try:
            results = service.ranked_hashtags(sort_by=sort_by, limit=limit)
        except AnalyticsDatasetError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return [HashtagAnalyticsItem(**item.__dict__) for item in results]

    @router.get("/hashtags/{hashtag}/related")
    def related_hashtags(
        hashtag: str,
        limit: int = Query(10, ge=1, le=100),
    ) -> list[dict[str, str | int]]:
        try:
            return [
                {"hashtag": related, "cooccurrences": count}
                for related, count in service.related_hashtags(hashtag, limit)
            ]
        except AnalyticsDatasetError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return router
