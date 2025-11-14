from __future__ import annotations

import logging
from functools import lru_cache

import ee

from .config import settings

logger = logging.getLogger(__name__)


def initialize_earth_engine() -> None:
    """Initialise the Earth Engine client using the configured service account."""

    if ee.data._credentials:  # pylint: disable=protected-access
        logger.debug("Earth Engine is already initialised.")
        return

    logger.info("Initialising Earth Engine using service account %s", settings.ee_service_account)
    credentials = ee.ServiceAccountCredentials(
        settings.ee_service_account,
        str(settings.ee_credentials_path),
    )
    ee.Initialize(credentials)


@lru_cache(maxsize=1)
def get_algeria_geometry() -> ee.Geometry:
    """Return the geometry of the Algeria study area asset."""

    initialize_earth_engine()
    feature_collection = ee.FeatureCollection(settings.algeria_asset_id)
    return feature_collection.geometry()
