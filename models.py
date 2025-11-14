from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LayerPreview(BaseModel):
    id: str
    name: str
    description: str
    thumb_url: str = Field(..., description="Public Earth Engine thumbnail URL for quick previews")
    legend_min: float
    legend_max: float
    legend_units: str
    palette: list[str]
    tile_url_template: str = Field(
        ..., description="Tile URL template suitable for Google Maps tile overlay usage."
    )


class LayerStatistics(BaseModel):
    mean: float
    min: float
    max: float
    std_dev: float = Field(..., alias="stdDev")


class LayerResult(BaseModel):
    layer: LayerPreview
    statistics: LayerStatistics
    classification_summary: dict[str, float] | None = Field(
        default=None,
        description="Optional categorical histogram summarising the layer distribution.",
    )


class AnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    buffer_meters: Optional[int] = Field(10000, ge=1000, le=50000)


class AnalysisResponse(BaseModel):
    requested_at: datetime
    region_area_sqkm: float
    layers: List[LayerResult]
