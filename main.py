from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# استيرادات مطلقة بدل النسبية
from config import Settings, settings
from models import AnalysisRequest, AnalysisResponse
from services.analysis_service import run_analysis

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class HealthResponse(BaseModel):
    status: str
    service_account: str
    region_asset: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return settings


def create_app() -> FastAPI:
    app = FastAPI(title="Reservoir Analyzer GIS API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health_check(config: Settings = Depends(get_settings)) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service_account=config.ee_service_account,
            region_asset=config.algeria_asset_id,
        )

    @app.post("/analysis", response_model=AnalysisResponse)
    async def perform_analysis(request: AnalysisRequest) -> AnalysisResponse:
        try:
            logger.info(
                "Running analysis for lat=%s, lon=%s, buffer=%sm",
                request.latitude,
                request.longitude,
                request.buffer_meters,
            )
            return run_analysis(request)
        except Exception as exc:
            logger.exception("Analysis failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app


app = create_app()
