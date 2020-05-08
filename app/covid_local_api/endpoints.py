import logging
import os
import sys
import time
import datetime
import geocoder
import uvicorn
import requests
import random
from starlette.responses import Response, RedirectResponse
from fastapi import Depends, FastAPI, Query, status

from covid_local_api.__version__ import __version__
from covid_local_api.db_handler import DatabaseHandler
from covid_local_api.schema import (
    Hotline,
    Website,
    TestSite,
    HealthDepartment,
    ResultsList,
)
from covid_local_api.utils import endpoint_utils, place_request_utils
from covid_local_api.place_handler import (
    PlaceHandler,
    load_place_hierarchy,
    load_place_mapping,
)


data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")

# Initialize
log = logging.getLogger(__name__)
db = DatabaseHandler(data_path)

place_handler = PlaceHandler(
    load_place_mapping(os.path.join(data_path, "DE_placeid-to-wikidata.json")),
    load_place_hierarchy(os.path.join(data_path, "DE_place-hierarchy.csv")),
    country_codes=["DE"],
)

# TODO: Temporary fix, see if we still need the user in this file after adapting the endpoints.
geonames_username = random.choice(place_request_utils.GEONAMES_USERS)

# Initialize API
app = FastAPI(
    title="COVID-19 Local API",
    description="API to get local help information about COVID-19 (hotlines, websites, testing sites, ...)",
    version=__version__,
)


def get_from_sheet(sheet, geonames_id):
    # Find all hierarchically higher areas (this contains the area itself!).
    # This is important if geonames_id belongs e.g. to Berlin Mitte but there's a hotline for Berlin.
    hierarchy = geocoder.geonames(
        geonames_id, key=geonames_username, method="hierarchy"
    )
    hierarchy = hierarchy[::-1]  # reverse, so that more local areas come first

    # TODO: Maybe also search for children here, e.g. if geonames_id belongs to Berlin but the
    #   health departments are in the districts. Not sure if it makes sense to search only for
    #   direct children or whether we would need all children (which would be a massive overload).

    # Get all geonames ids
    all_geonames_ids = [item.geonames_id for item in hierarchy]
    print(all_geonames_ids)

    # Get all matching entries from the database
    results = db.get(sheet, all_geonames_ids)
    return results


@app.get("/test_place_handler")
# TODO: Import search via text and zip code, optionally country as filter.
def test_place_handler(place_id: str = Query(..., description="Place ID to filter.")):
    return place_handler.resolve_hierarchies(place_id)


@app.get("/test")
def test():
    """Show all results for Berlin Mitte."""
    response = RedirectResponse(url="/all?geonames_id=6545310")
    return response


@app.get("/places", summary="Search for places via free-form query.")
def search_places(
    query: str = Query(..., description="Free-form query string."),
    limit: int = Query(5, description="Maximum number of entries to return."),
):
    return place_handler.search_places(query)


@app.get(
    "/all",
    summary="Get all items filtered by a specified region.",
    response_model=ResultsList,
)
# TODO: Import search via text and zip code, optionally country as filter.
def get_all(
    geonames_id: int = Query(..., description="Geonames ID to filter."),
    max_distance: float = Query(
        0.5, description="Maximum distance in degrees lon/lat for test sites"
    ),
    max_count: int = Query(5, description="Maximum number of test sites to return"),
):
    return {
        "hotlines": get_hotlines(geonames_id)["hotlines"],
        "websites": get_websites(geonames_id)["websites"],
        "test_sites": get_test_sites(
            geonames_id, max_distance=max_distance, max_count=max_count
        )["test_sites"],
        "health_departments": get_health_departments(geonames_id)["health_departments"],
    }


@app.get(
    "/hotlines",
    summary=f"Get hotlines filtered by a specified region.",
    response_model=ResultsList,
)
# TODO: Import search via text and zip code, optionally country as filter.
def get_hotlines(geonames_id: int = Query(..., description="Geonames ID to filter.")):
    return {"hotlines": get_from_sheet("hotlines", geonames_id)}


@app.get(
    "/websites",
    summary=f"Get websites filtered by a specified region.",
    response_model=ResultsList,
)
# TODO: Import search via text and zip code, optionally country as filter.
def get_websites(geonames_id: int = Query(..., description="Geonames ID to filter.")):
    return {"websites": get_from_sheet("websites", geonames_id)}


@app.get(
    "/test_sites",
    summary=f"Get nearby test sites (sorted by distance to place).",
    response_model=ResultsList,
)
def get_test_sites(
    geonames_id: int = Query(..., description="Geonames ID to filter"),
    max_distance: float = Query(
        0.5, description="Maximum distance in degrees lon/lat for test sites"
    ),
    max_count: int = Query(5, description="Maximum number of test sites to return"),
):

    # Get latitude/longitude for this geonames_id.
    details = geocoder.geonames(geonames_id, key=geonames_username, method="details")
    lat = details.lat
    lon = details.lng

    # Get nearby test sites.
    return {
        "test_sites": db.get_nearby(
            "test_sites", lat, lon, max_distance=max_distance, max_count=max_count
        )
    }


@app.get(
    "/health_departments",
    summary=f"Get health departments filtered by a specified region.",
    response_model=ResultsList,
)
# TODO: This doesn't return results if e.g. Berlin is selected but the health department is in Berlin Mitte.
#   Maybe also search for the direct children of the geonames id (but is direct children enough)?
def get_health_departments(
    geonames_id: int = Query(..., description="Geonames ID to filter.")
):
    return {"health_departments": get_from_sheet("health_departments", geonames_id)}


# TODO: Make this endpoint optional, i.e. if no geonames id is stored in env variables, return an error.
@app.get(
    "/geonames",
    summary="Get geoname ids via free-form query. This redirects to the geonames API (https://www.geonames.org/export/web-services.html) but returns only results of feature class A (country, state, region) and P (city, village).",
)
async def get_geonames(
    q: str = Query(..., description="Free-form query string."),
    maxRows: int = Query(10, description="Maximum number of entries to return."),
):
    # TODO: Check out if I need to do await here.
    response = RedirectResponse(
        url=f"http://api.geonames.org/searchJSON?q={q}&maxRows={maxRows}&username={geonames_username}&featureClass=P&featureClass=A"
    )
    return response

    # TODO: For now, this simply redirects to the geonames api, maybe parse the results instead and return only a subset.
    # results = geocoder.geonames(region_query, key=credentials.geonames_username, maxRows=10, featureClass=['A', 'P'])
    # print(results)
    # return {"message": "not working yet"}


# Use function names as operation IDs
endpoint_utils.use_route_names_as_operation_ids(app)


# Run uvicorn server directly in here for debugging
if __name__ == "__main__":
    uvicorn.run(app)
