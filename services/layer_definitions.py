from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Callable, Dict, List, Optional

import ee

from ..ee_client import initialize_earth_engine

initialize_earth_engine()


@dataclass(frozen=True)
class ComputedLayer:
    image: ee.Image
    vis_params: Dict[str, object]
    scale: int
    classification_image: Optional[ee.Image] = None


@dataclass(frozen=True)
class LayerDefinition:
    id: str
    name: str
    description: str
    units: str
    palette: List[str]
    min_value: float
    max_value: float
    scale: int
    compute: Callable[[ee.Geometry], ComputedLayer]


# Base datasets --------------------------------------------------------------

SRTM = ee.Image("USGS/SRTMGL1_003").select("elevation")
FLOW_ACC = ee.Image("WWF/HydroSHEDS/15ACC").select(0).rename("accumulation")
RAINFALL = (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterDate("2020-01-01", "2023-12-31")
            .mean()
            .select("precipitation"))

SENTINEL2 = (
    ee.ImageCollection("COPERNICUS/S2")
    .filterDate("2023-01-01", "2023-12-31")
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
)
CLAY = ee.Image("OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M/v02").select(0).rename("clay")
SAND = ee.Image("OpenLandMap/SOL/SOL_SAND-WFRACTION_USDA-3A1A1A_M/v02").select(0).rename("sand")
ORGANIC = ee.Image("OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02").select(0).rename("organic")


# Helper utilities ----------------------------------------------------------

def clamp_percentage(image: ee.Image) -> ee.Image:
    return image.multiply(100).clamp(0, 100)


def compute_ndvi(region: ee.Geometry) -> ee.Image:
    median = SENTINEL2.filterBounds(region).median()
    ndvi = median.normalizedDifference(["B8", "B4"]).rename("ndvi")
    return ndvi.clip(region)


def classification_from_percentage(image: ee.Image) -> ee.Image:
    band_name = ee.String(image.bandNames().get(0))
    classified = image.divide(33.34).floor().int().clamp(0, 2)
    return classified.rename(band_name.cat("_class"))


def soil_stability(region: ee.Geometry) -> ComputedLayer:
    clay = CLAY.clip(region).divide(100)
    sand = SAND.clip(region).divide(100)
    organic = ORGANIC.clip(region).divide(100)

    stability = (
        organic.multiply(0.45)
        .add(clay.multiply(0.4))
        .subtract(sand.multiply(0.2))
        .add(0.2)
    ).clamp(0, 1)

    percentage = stability.multiply(100).rename("soil_stability")
    return ComputedLayer(
        image=percentage,
        vis_params={
            "min": 0,
            "max": 100,
            "palette": ["#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#fee08b", "#f46d43", "#d53e4f"],
        },
        scale=250,
        classification_image=classification_from_percentage(percentage),
    )


def solid_rock(region: ee.Geometry) -> ComputedLayer:
    slope = ee.Terrain.slope(SRTM).clip(region)
    slope_norm = slope.divide(45).clamp(0, 1)
    sand = SAND.clip(region).divide(100)
    rockiness = slope_norm.multiply(0.6).add(sand.multiply(0.4))
    percentage = rockiness.multiply(100).rename("solid_rock")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#f7fbff", "#6baed6", "#08306b"]},
        scale=90,
        classification_image=classification_from_percentage(percentage),
    )


def water_source_availability(region: ee.Geometry) -> ComputedLayer:
    accumulation = FLOW_ACC.clip(region).add(1).log10()
    water = accumulation.unitScale(0, 6).clamp(0, 1)
    percentage = water.multiply(100).rename("water_sources")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"]},
        scale=120,
        classification_image=classification_from_percentage(percentage),
    )


def water_storage_capacity(region: ee.Geometry) -> ComputedLayer:
    slope = ee.Terrain.slope(SRTM).clip(region)
    slope_norm = slope.divide(30).clamp(0, 1)
    flatness = slope_norm.multiply(-1).add(1)
    accumulation = FLOW_ACC.clip(region).add(1).log10().unitScale(0, 5).clamp(0, 1)
    storage = flatness.multiply(0.6).add(accumulation.multiply(0.4)).clamp(0, 1)
    percentage = storage.multiply(100).rename("storage_capacity")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#ffffd4", "#fed98e", "#fe9929", "#d95f0e", "#993404"]},
        scale=120,
        classification_image=classification_from_percentage(percentage),
    )


def flood_risk(region: ee.Geometry) -> ComputedLayer:
    rain = RAINFALL.clip(region).divide(3000).clamp(0, 1)
    accumulation = FLOW_ACC.clip(region).add(1).log10().unitScale(0, 5).clamp(0, 1)
    flood = rain.multiply(0.6).add(accumulation.multiply(0.4))
    percentage = flood.multiply(100).rename("flood_risk")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"]},
        scale=500,
        classification_image=classification_from_percentage(percentage),
    )


def topographic_suitability(region: ee.Geometry) -> ComputedLayer:
    slope = ee.Terrain.slope(SRTM).clip(region)
    suitability = slope.multiply(-1).add(30).divide(30).clamp(0, 1)
    percentage = suitability.multiply(100).rename("topographic_suitability")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#ffffcc", "#c2e699", "#78c679", "#31a354", "#006837"]},
        scale=90,
        classification_image=classification_from_percentage(percentage),
    )


def drainage_density(region: ee.Geometry) -> ComputedLayer:
    accumulation = FLOW_ACC.clip(region).add(1).log10().unitScale(0, 6).clamp(0, 1)
    percentage = accumulation.multiply(100).rename("drainage_density")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#f7fcf0", "#ccebc5", "#7bccc4", "#2b8cbe", "#084081"]},
        scale=120,
        classification_image=classification_from_percentage(percentage),
    )


def aspect_sun_exposure(region: ee.Geometry) -> ComputedLayer:
    aspect = ee.Terrain.aspect(SRTM).clip(region)
    sun = aspect.subtract(180).multiply(pi / 180).cos().add(1).divide(2)
    percentage = sun.multiply(100).rename("sun_aspect")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#fff7ec", "#fee8c8", "#fdbb84", "#fc8d59", "#e34a33", "#b30000"]},
        scale=250,
        classification_image=classification_from_percentage(percentage),
    )


def wildlife_impact(region: ee.Geometry) -> ComputedLayer:
    ndvi = compute_ndvi(region)
    wildlife = ndvi.unitScale(0.2, 0.8).clamp(0, 1)
    percentage = wildlife.multiply(100).rename("wildlife_impact")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#fff7ec", "#d0d1e6", "#74a9cf", "#0570b0", "#034e7b"]},
        scale=20,
        classification_image=classification_from_percentage(percentage),
    )


def undisturbed_areas(region: ee.Geometry) -> ComputedLayer:
    ndvi = compute_ndvi(region)
    natural = ndvi.gt(0.55).selfMask().multiply(100).rename("undisturbed_areas")
    vis = {
        "min": 0,
        "max": 100,
        "palette": ["#f7fcb9", "#c2e699", "#78c679", "#238443"],
    }
    return ComputedLayer(
        image=natural,
        vis_params=vis,
        scale=20,
        classification_image=classification_from_percentage(natural.unmask(0)),
    )


def groundwater_quality(region: ee.Geometry) -> ComputedLayer:
    clay = CLAY.clip(region).divide(100)
    sand = SAND.clip(region).divide(100)
    organic = ORGANIC.clip(region).divide(100)
    quality = (
        organic.multiply(0.5)
        .add(clay.multiply(0.3))
        .subtract(sand.multiply(0.2))
        .add(0.2)
    ).clamp(0, 1)
    percentage = quality.multiply(100).rename("groundwater_quality")
    return ComputedLayer(
        image=percentage,
        vis_params={"min": 0, "max": 100, "palette": ["#edf8fb", "#b3cde3", "#8c96c6", "#8856a7", "#810f7c"]},
        scale=250,
        classification_image=classification_from_percentage(percentage),
    )


LAYER_DEFINITIONS: List[LayerDefinition] = [
    LayerDefinition(
        id="soil_stability",
        name="Soil Stability",
        description="Composite soil erodibility indicator combining clay, sand, and organic carbon fractions.",
        units="Suitability (%)",
        palette=[
            "#5e4fa2",
            "#3288bd",
            "#66c2a5",
            "#abdda4",
            "#e6f598",
            "#fee08b",
            "#f46d43",
            "#d53e4f",
        ],
        min_value=0,
        max_value=100,
        scale=250,
        compute=soil_stability,
    ),
    LayerDefinition(
        id="solid_rock",
        name="Presence of Solid Rock",
        description="Higher values represent exposed or shallow bedrock derived from slope and coarse soil fractions.",
        units="Likelihood (%)",
        palette=["#f7fbff", "#08306b"],
        min_value=0,
        max_value=100,
        scale=90,
        compute=solid_rock,
    ),
    LayerDefinition(
        id="water_sources",
        name="Water Source Availability",
        description="Flow accumulation-based index highlighting potential surface water presence.",
        units="Availability (%)",
        palette=["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"],
        min_value=0,
        max_value=100,
        scale=120,
        compute=water_source_availability,
    ),
    LayerDefinition(
        id="storage_capacity",
        name="Water Storage Capacity",
        description="Suitability for building reservoirs considering slope flatness and upstream accumulation.",
        units="Suitability (%)",
        palette=["#ffffd4", "#fed98e", "#fe9929", "#d95f0e", "#993404"],
        min_value=0,
        max_value=100,
        scale=120,
        compute=water_storage_capacity,
    ),
    LayerDefinition(
        id="flood_risk",
        name="Flood Risk",
        description="Combined rainfall intensity (2020-2023 mean) and flow accumulation likelihood of flooding.",
        units="Risk (%)",
        palette=["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
        min_value=0,
        max_value=100,
        scale=500,
        compute=flood_risk,
    ),
    LayerDefinition(
        id="topographic_suitability",
        name="Topographic Suitability",
        description="Inverse slope metric identifying flat surfaces better suited for reservoirs.",
        units="Suitability (%)",
        palette=["#ffffcc", "#c2e699", "#78c679", "#31a354", "#006837"],
        min_value=0,
        max_value=100,
        scale=90,
        compute=topographic_suitability,
    ),
    LayerDefinition(
        id="drainage_density",
        name="Drainage Density",
        description="Hydrological connectivity index derived from HydroSHEDS flow accumulation.",
        units="Density (%)",
        palette=["#f7fcf0", "#ccebc5", "#7bccc4", "#2b8cbe", "#084081"],
        min_value=0,
        max_value=100,
        scale=120,
        compute=drainage_density,
    ),
    LayerDefinition(
        id="sun_aspect",
        name="Aspect (Sun Exposure)",
        description="South-facing slopes receive higher solar exposure (useful for solar-powered infrastructure).",
        units="Exposure (%)",
        palette=["#fff7ec", "#fee8c8", "#fdbb84", "#fc8d59", "#e34a33", "#b30000"],
        min_value=0,
        max_value=100,
        scale=250,
        compute=aspect_sun_exposure,
    ),
    LayerDefinition(
        id="wildlife_impact",
        name="Impact on Wildlife",
        description="Higher NDVI indicates healthier habitats; higher values suggest greater ecological sensitivity.",
        units="Sensitivity (%)",
        palette=["#fff7ec", "#d0d1e6", "#74a9cf", "#0570b0", "#034e7b"],
        min_value=0,
        max_value=100,
        scale=20,
        compute=wildlife_impact,
    ),
    LayerDefinition(
        id="undisturbed_areas",
        name="Undisturbed Natural Areas",
        description="Binary mask of dense vegetation (NDVI > 0.55) representing preserved natural terrain.",
        units="Presence (%)",
        palette=["#f7fcb9", "#c2e699", "#78c679", "#238443"],
        min_value=0,
        max_value=100,
        scale=20,
        compute=undisturbed_areas,
    ),
    LayerDefinition(
        id="groundwater_quality",
        name="Impact on Groundwater Quality",
        description="Soil composition proxy for groundwater recharge quality (organic carbon + clay, low sand).",
        units="Quality (%)",
        palette=["#edf8fb", "#b3cde3", "#8c96c6", "#8856a7", "#810f7c"],
        min_value=0,
        max_value=100,
        scale=250,
        compute=groundwater_quality,
    ),
]
