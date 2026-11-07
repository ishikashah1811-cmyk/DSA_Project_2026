from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.hashtag_analytics import create_analytics_router
from app.api.hashtag_recommendation import create_recommendation_router
from app.modules.hashtag_analytics.service import HashtagAnalyticsService
from app.modules.hashtag_recommendation.service import HashtagRecommendationService


def create_app(
    recommendation_service: HashtagRecommendationService | None = None,
) -> FastAPI:
    service = recommendation_service or HashtagRecommendationService()
    application = FastAPI(
        title="ContentIQ API",
        description="Context-aware hashtag recommendations from caption and post data.",
        version="1.0.0",
    )
    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "CONTENTIQ_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(create_recommendation_router(service))
    application.include_router(
        create_analytics_router(HashtagAnalyticsService())
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
