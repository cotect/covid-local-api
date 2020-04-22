import logging
import os
import sys
import time
import datetime
import geocoder
import uvicorn
import requests
from starlette.responses import Response, RedirectResponse
from fastapi import Depends, FastAPI, Query, status

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
    "/geonames",
    summary="Get geoname ids via free-form query. This redirects to the geonames API (https://www.geonames.org/export/web-services.html) but returns only results of feature class A (country, state, region) and P (city, village)."
)
async def get_geonames(
    q: str = Query(..., description="Free-form query string."), 
    maxRows: int = Query(10, description="Maximum number of entries to return.")
):
    response = RedirectResponse(url=
        f"http://api.geonames.org/searchJSON?q={q}&maxRows={maxRows}&username={os.environ['GEONAMES_USERNAME']}&featureClass=P&featureClass=A")
    return response

    # TODO: For now, this simply redirects to the geonames api, maybe parse the results instead and return only a subset.
    #results = geocoder.geonames(region_query, key=credentials.geonames_username, maxRows=10, featureClass=['A', 'P'])
    #print(results)
    #return {"message": "not working yet"}

@app.get(
    "/hotlines",
    summary="Get hotlines filtered by a specified region.",
    response_model=HotlineList
)
def get_hotlines(region_id: str = Query(..., description="Region ID to filter hotlines.")):
    return None


# Use function names as operation IDs
endpoint_utils.use_route_names_as_operation_ids(app)


# Run uvicorn server directly in here for debugging
if __name__ == "__main__":
    uvicorn.run(app)
