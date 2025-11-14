from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Callable, Dict, List, Optional

import ee

# استيراد مطلق (مهم جداً)
from ee_client import initialize_earth_engine

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

# -----------------------------
# باقي الكود كما هو بدون تعديل
# -----------------------------

SRTM = ee.Image("USGS/SRTMGL1_003").select("elevation")
FLOW_ACC = ee.Image("WWF/HydroSHEDS/15ACC").select(0).rename("accumulation")
RAINFALL = (
    ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
    .filterDate("2020-01-01", "2023-12-31")
    .mean()
    .select("precipitation")
)

SENTINEL2 = (
    ee.ImageCollection("COPERNICUS/S2")
    .filterDate("2023-01-01", "2023-12-31")
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
)

CLAY = ee.Image("OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M/v02").select(0).rename("clay")
SAND = ee.Image("OpenLandMap/SOL/SOL_SAND-WFRACTION_USDA-3A1A1A_M/v02").select(0).rename("sand")
ORGANIC = ee.Image("OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02").select(0).rename("organic")
