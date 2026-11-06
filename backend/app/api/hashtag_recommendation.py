from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.hashtag_recommendation.service import (
    DatasetError,
    HashtagRecommendationService,
)


class RecommendationRequest(BaseModel):
    caption: str = Field(min_length=1, max_length=5000)
    selected_hashtags: list[str] = Field(default_factory=list, max_length=100)
    top_k: int = Field(default=10, ge=1, le=50)
    neighbors: int = Field(default=30, ge=1, le=100)


class RecommendationItem(BaseModel):
    hashtag: str
    score: float
    semantic_relevance: float
    hashtag_association: float
    engagement: float
    similar_posts: int


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationItem]


def create_recommendation_router(
    service: HashtagRecommendationService,
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/hashtag-recommendations",
        response_model=RecommendationResponse,
    )
    def recommend(request: RecommendationRequest) -> RecommendationResponse:
        if not request.caption.strip():
            raise HTTPException(status_code=422, detail="caption must not be empty")
        try:
            recommendations = service.recommend(
                caption=request.caption,
                selected_hashtags=request.selected_hashtags,
                top_k=request.top_k,
                neighbors=request.neighbors,
            )
        except DatasetError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return RecommendationResponse(
            recommendations=[
                RecommendationItem(
                    hashtag=item.hashtag,
                    score=item.score,
                    semantic_relevance=item.semantic_relevance,
                    hashtag_association=item.hashtag_association,
                    engagement=item.engagement,
                    similar_posts=item.similar_posts,
                )
                for item in recommendations
            ]
        )

    return router
