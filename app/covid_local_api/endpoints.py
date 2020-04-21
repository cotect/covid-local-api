import logging
import os
import sys
import time
import datetime

from fastapi import Depends, FastAPI, Query, status
from starlette.responses import Response

from covid_local_api.__version__ import __version__
from covid_local_api.schema import HotlineList
from covid_local_api.utils import endpoint_utils

# Initialize logger
log = logging.getLogger(__name__)

# Get environment variables

# Initialize API
app = FastAPI(
    title="COVID-19 Local API",
    description="API to get local help information about COVID-19 (hotlines, websites, testing sites, ...)",
    version=__version__,
)


@app.get(
    "/region",
    summary="Get region id via a free-form query."
)
def get_region_id(region_query: str = Query(..., description="Free-form query string.")):
    return None

@app.get(
    "/hotlines",
    summary="Get hotlines filtered by a specified region.",
    response_model=HotlineList
)
def get_hotlines(region_id: str = Query(..., description="Region ID to filter hotlines.")):
    return None


# Use function names as operation IDs
endpoint_utils.use_route_names_as_operation_ids(app)
