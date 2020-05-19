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
from typing import List

from covid_local_api.__version__ import __version__
from covid_local_api.db_handler import DatabaseHandler
from covid_local_api.schema import (
    Hotline,
    Website,
    TestSite,
    HealthDepartment,
    ResultsList,
    Place,
)
from covid_local_api.utils import endpoint_utils, place_request_utils
from covid_local_api.place_handler import (
    PlaceHandler,
    load_place_hierarchy,
    load_place_mapping,
)


# Initialize helper objects
data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
log = logging.getLogger(__name__)
db = DatabaseHandler(data_path)

# TODO: Remove this for now.
# place_handler = PlaceHandler(
#     load_place_mapping(os.path.join(data_path, "DE_placeid-to-wikidata.json")),
#     load_place_hierarchy(os.path.join(data_path, "DE_place-hierarchy.csv")),
#     country_codes=["DE"],
# )

# TODO: Change this to another way.
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


# TODO: Remove this for now
# @app.get("/test_place_handler")
# def test_place_handler(place_id: str = Query(..., description="Place ID to filter.")):
#     return place_handler.resolve_hierarchies(place_id)


@app.get("/test", summary="Test endpoint that shows all entries for Berlin Mitte")
def test():
    response = RedirectResponse(url="/all?geonames_id=6545310")
    return response


@app.get(
    "/places",
    summary="Search for places via free-form query",
    response_model=List[Place],
)
def search_places(
    q: str = Query(
        ...,
        description="Free-form query string (e.g. a city, neighborhood, state, ...)",
    ),
    limit: int = Query(5, description="Maximum number of entries to return"),
    search_provider: str = Query(
        "geonames", description="The search provider (only geonames supported so far)",
    ),
):
    if search_provider == "geonames":
        # Search geonames API.
        search_results = geocoder.geonames(
            q, key=geonames_username, maxRows=limit, featureClass=["A", "P"]
        )

        # Format the search results and return them.
        places = []
        for result in search_results:
            place = Place(
                name=result.address,
                country=result.country,
                country_code=result.country_code,
                state=result.state,
                description=result.description + " - " + result.class_description,
                geonames_id=result.geonames_id,
                lat=result.lat,
                lon=result.lng,
                search_provider="geonames",
            )
            places.append(place)
        return places
    else:
        # TODO: Return proper error message.
        raise ValueError("Search provider not supported:", search_provider)


def parse_place_parameters(place_name, geonames_id):
    """Returns the correct geonames id for the given query parameters. 
    
    If geonames_id is given, simply return it. If place_name is given, search the 
    /places endpoint and return the geonames id of the first search result. If none of 
    both is given, raise an error.
    """
    print(place_name, geonames_id)
    if geonames_id is None and place_name is None:
        raise ValueError("Either place_name or geonames_id must be provided")
    elif geonames_id is None:
        # Search by place_name and use first search result.
        places = search_places(q=place_name, limit=1, search_provider="geonames")
        return places[0].geonames_id
        # TODO: Raise error if search returned no results.
    else:
        return geonames_id


place_name_query = Query(
    None,
    description="The name of the place, e.g. a city, neighborhood, state (either "
    "place_name or geonames_id must be provided)",
)

geonames_id_query = Query(
    None,
    description="The geonames.org id of the place (either place_name or "
    "geonames_id must be provided)",
)


@app.get(
    "/all", summary="Get all items for a place", response_model=ResultsList,
)
# TODO: Import search via text and zip code, optionally country as filter.
def get_all(
    place_name: str = place_name_query,
    geonames_id: int = geonames_id_query,
    max_distance: float = Query(
        0.5, description="Maximum distance in degrees lon/lat for test sites"
    ),
    max_count: int = Query(5, description="Maximum number of test sites to return"),
):
    geonames_id = parse_place_parameters(place_name, geonames_id)
    print(geonames_id)
    return {
        "hotlines": get_hotlines(geonames_id=geonames_id)["hotlines"],
        "websites": get_websites(geonames_id=geonames_id)["websites"],
        "test_sites": get_test_sites(
            geonames_id=geonames_id, max_distance=max_distance, max_count=max_count
        )["test_sites"],
        "health_departments": get_health_departments(geonames_id=geonames_id)[
            "health_departments"
        ],
    }


@app.get(
    "/hotlines", summary=f"Get hotlines for a place", response_model=ResultsList,
)
# TODO: Import search via text and zip code, optionally country as filter.
def get_hotlines(
    place_name: str = place_name_query, geonames_id: int = geonames_id_query,
):
    geonames_id = parse_place_parameters(place_name, geonames_id)
    return {"hotlines": get_from_sheet("hotlines", geonames_id)}


@app.get(
    "/websites", summary=f"Get websites for a place", response_model=ResultsList,
)
# TODO: Import search via text and zip code, optionally country as filter.
def get_websites(
    place_name: str = place_name_query, geonames_id: int = geonames_id_query,
):
    geonames_id = parse_place_parameters(place_name, geonames_id)
    return {"websites": get_from_sheet("websites", geonames_id)}


@app.get(
    "/test_sites",
    summary=f"Get nearby test sites for a place (sorted by distance to place)",
    response_model=ResultsList,
)
def get_test_sites(
    place_name: str = place_name_query,
    geonames_id: int = geonames_id_query,
    max_distance: float = Query(
        0.5, description="Maximum distance in degrees lon/lat for test sites"
    ),
    max_count: int = Query(5, description="Maximum number of test sites to return"),
):
    geonames_id = parse_place_parameters(place_name, geonames_id)

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
    summary=f"Get responsible health departments for a place",
    response_model=ResultsList,
)
# TODO: This doesn't return results if e.g. Berlin is selected but the health department is in Berlin Mitte.
#   Maybe also search for the direct children of the geonames id (but is direct children enough)?
def get_health_departments(
    place_name: str = place_name_query, geonames_id: int = geonames_id_query,
):
    geonames_id = parse_place_parameters(place_name, geonames_id)
    return {"health_departments": get_from_sheet("health_departments", geonames_id)}


# Use function names as operation IDs
endpoint_utils.use_route_names_as_operation_ids(app)


# Run uvicorn server directly in here for debugging
if __name__ == "__main__":
    uvicorn.run(app)
