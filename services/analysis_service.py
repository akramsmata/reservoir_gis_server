from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

import ee

from ..config import settings
from ..ee_client import get_algeria_geometry, initialize_earth_engine
from ..models import AnalysisRequest, AnalysisResponse, LayerPreview, LayerResult, LayerStatistics
from .layer_definitions import ComputedLayer, LAYER_DEFINITIONS

initialize_earth_engine()


def _create_analysis_region(request: AnalysisRequest) -> ee.Geometry:
    """Create the buffered geometry for the requested point and clip it to Algeria asset."""

    study_area = get_algeria_geometry()
    point = ee.Geometry.Point([request.longitude, request.latitude])
    buffered = point.buffer(request.buffer_meters)
    clipped = buffered.intersection(study_area, request.buffer_meters)
    return clipped


def _build_tile_url(image: ee.Image, vis_params: Dict[str, object]) -> str:
    map_info = image.getMapId(vis_params)
    map_id = map_info['mapid']
    token = map_info['token']
    return f"https://earthengine.googleapis.com/map/{map_id}/{{z}}/{{x}}/{{y}}?token={token}"


def _build_thumb_url(image: ee.Image, vis_params: Dict[str, object], region: ee.Geometry) -> str:
    params = {
        'region': region,
        'dimensions': 768,
        'format': 'png',
        'min': vis_params.get('min'),
        'max': vis_params.get('max'),
        'palette': vis_params.get('palette'),
    }
    return image.getThumbURL(params)


def _compute_statistics(image: ee.Image, region: ee.Geometry, scale: int) -> LayerStatistics:
    reducer = ee.Reducer.mean().combine(
        reducer2=ee.Reducer.minMax(),
        sharedInputs=True,
    ).combine(
        reducer2=ee.Reducer.stdDev(),
        sharedInputs=True,
    )

    stats = image.reduceRegion(
        reducer=reducer,
        geometry=region,
        scale=scale,
        bestEffort=True,
        maxPixels=1_000_000,
    ).getInfo()

    band_name = image.bandNames().getInfo()[0]
    return LayerStatistics(
        mean=stats.get(f"{band_name}_mean", 0.0) or 0.0,
        min=stats.get(f"{band_name}_min", 0.0) or 0.0,
        max=stats.get(f"{band_name}_max", 0.0) or 0.0,
        std_dev=stats.get(f"{band_name}_stdDev", 0.0) or 0.0,
    )


def _compute_classification_summary(classification_image: ee.Image | None, region: ee.Geometry, scale: int) -> Dict[str, float] | None:
    if classification_image is None:
        return None

    histogram = classification_image.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=region,
        scale=scale,
        bestEffort=True,
        maxPixels=1_000_000,
    ).getInfo()

    band_name = classification_image.bandNames().getInfo()[0]
    class_counts = histogram.get(band_name)
    if not class_counts:
        return None

    total = sum(class_counts.values())
    if total == 0:
        return None

    return {str(int(cls)): (count / total) * 100 for cls, count in class_counts.items()}


def _evaluate_layer(definition, region: ee.Geometry) -> LayerResult:
    computed: ComputedLayer = definition.compute(region)
    vis_params = {
        'min': definition.min_value,
        'max': definition.max_value,
        'palette': definition.palette,
    }

    layer_image = computed.image.clip(region)

    statistics = _compute_statistics(layer_image, region, computed.scale)
    classification = _compute_classification_summary(
        computed.classification_image, region, computed.scale
    )

    tile_url = _build_tile_url(layer_image, vis_params)
    thumb_url = _build_thumb_url(layer_image, vis_params, region)

    preview = LayerPreview(
        id=definition.id,
        name=definition.name,
        description=definition.description,
        thumb_url=thumb_url,
        legend_min=definition.min_value,
        legend_max=definition.max_value,
        legend_units=definition.units,
        palette=definition.palette,
        tile_url_template=tile_url,
    )

    return LayerResult(
        layer=preview,
        statistics=statistics,
        classification_summary=classification,
    )


def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    initialize_earth_engine()
    region = _create_analysis_region(request)
    area_sqkm = ee.Number(region.area()).divide(1_000_000).getInfo()

    layer_results: List[LayerResult] = []
    for definition in LAYER_DEFINITIONS:
        layer_results.append(_evaluate_layer(definition, region))

    return AnalysisResponse(
        requested_at=datetime.now(timezone.utc),
        region_area_sqkm=area_sqkm,
        layers=layer_results,
    )
