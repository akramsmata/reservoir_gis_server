from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

import ee

# FIXED IMPORTS — absolute imports instead of relative
from config import settings
from ee_client import get_algeria_geometry, initialize_earth_engine
from models import (
    AnalysisRequest,
    AnalysisResponse,
    LayerPreview,
    LayerResult,
    LayerStatistics
)
from services.layer_definitions import ComputedLayer, LAYER_DEFINITIONS


initialize_earth_engine()


def _create_analysis_region(request: AnalysisRequest) -> ee.Geometry:
    """Create the buffered geometry for the requested point and clip it to Algeria asset."""

    study_area = get_algeria_geometry()
    point = ee.Geometry.Point([request.longitude, request.latitude])
    buffered = poi
