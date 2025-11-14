from __future__ import annotations

import logging
import os
from functools import lru_cache

import ee

from config import settings  # استيراد مطلق

logger = logging.getLogger(__name__)


def initialize_earth_engine() -> None:
    """Initialise the Earth Engine client using the configured service account."""

    # لو كان فيه اتصال مفعّل من قبل، لا تعيد التهيئة
    if ee.data._credentials:  # pylint: disable=protected-access
        logger.debug("Earth Engine is already initialised.")
        return

    # الإيميل نأخذه من settings (من EE_SERVICE_ACCOUNT)
    service_account = settings.ee_service_account

    # المفتاح الخاص نأخذه من متغير بيئة جديد
    private_key = os.getenv("EE_PRIVATE_KEY")
    if not private_key:
        raise RuntimeError(
            "EE_PRIVATE_KEY environment variable is missing. "
            "Set it in Render with the private key of the service account."
        )

    logger.info("Initialising Earth Engine using service account %s", service_account)

    # نمرر الـ private_key مباشرة بدل مسار ملف JSON
    credentials = ee.ServiceAccountCredentials(
        service_account,
        key_data=private_key,
    )
    ee.Initialize(credentials)


@lru_cache(maxsize=1)
def get_algeria_geometry() -> ee.Geometry:
    """Return the geometry of the Algeria study area asset."""

    initialize_earth_engine()
    feature_collection = ee.FeatureCollection(settings.algeria_asset_id)
    return feature_collection.geometry()
