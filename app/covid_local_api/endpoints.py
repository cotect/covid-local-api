import logging
import geocoder
import uvicorn
import os
from starlette.responses import RedirectResponse
from fastapi import FastAPI, Query, HTTPException
from typing import List
from enum import Enum

from covid_local_api.__version__ import __version__
from covid_local_api.db_handler import DatabaseHandler
from covid_local_api.schema import (
    ResultsList,
    Place,
)
from covid_local_api.utils import endpoint_utils, place_request_utils


# TODO: Implement place handler code at some point in the future like below.
# from covid_local_api.place_handler import (
#     PlaceHandler,
#     load_place_hierarchy,
#     load_place_mapping,
# )
# place_handler = PlaceHandler(
#     load_place_mapping(os.path.join(data_path, "DE_placeid-to-wikidata.json")),
#     load_place_hierarchy(os.path.join(data_path, "DE_place-hierarchy.csv")),
#     country_codes=["DE"],
# )
# @app.get("/test_place_handler")
# def test_place_handler(place_id: str = Query(..., description="Place ID to filter.")):
#     return place_handler.resolve_hierarchies(place_id)


# Initialize database
data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
db = DatabaseHandler(data_path)
log = logging.getLogger(__name__)


# Initialize API
app = FastAPI(
    title="COVID-19 Local API",
    description="API to get local help information about COVID-19 (hotlines, websites, "
    "test sites, health departments)",
    version=__version__,
)


# ---------------------------------- Helper functions ----------------------------------
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


class SearchProvider(str, Enum):
    """Enum of the available search providers for the places endpoint"""

    geonames = "geonames"


def geocoder_to_place(result):
    """Convert a result object from geocoder to a Place object"""
    return Place(
        name=result.address,
        country=result.country,
        country_code=result.country_code,
        state=result.state,
        description=result.description + " - " + result.class_description,
        geonames_id=result.geonames_id,
        lat=result.lat,
        lon=result.lng,
        search_provider=SearchProvider.geonames,
    )


def find_place(place_name=None, geonames_id=None):
    """Finds and returns the place for the given query parameters. 
    
    If geonames_id is given, simply get some more information about it. If 
    place_name is given, search the /places endpoint and return the first result. If 
    neither is given, raise an error.
    
    Args:
        place_name (str, optional): The name of the place to search for (used as query 
            parameter for the places endpoint)
        geonames_id (int, optional): The geonames.org id of the place

    Returns:
        Place: The found place
    """
    if geonames_id is None and place_name is None:
        raise HTTPException(400, "Either place_name or geonames_id must be provided")
    elif geonames_id is None:
        # Search by place_name and use first search result.
        places = search_places(q=place_name, limit=1, search_provider="geonames")
        if len(places) == 0:
            raise HTTPException(
                400, f"Could not find any match for place_name: {place_name}"
            )
        else:
            return places[0]
    else:
        # Get details for this geonames_id and return as Place object.
        search_result = geocoder.geonames(
            geonames_id, key=place_request_utils.get_geonames_user(), method="details"
        )[0]
        place = geocoder_to_place(search_result)
        return place


def get_hierarchy(geonames_id):
    """Returns geonames ids of hierarchical parents (e.g. country for a city)"""
    hierarchy = geocoder.geonames(
        geonames_id, key=place_request_utils.get_geonames_user(), method="hierarchy",
    )
    hierarchy = hierarchy[::-1]  # reverse, so that more local areas come first
    geonames_ids_hierarchy = [item.geonames_id for item in hierarchy]
    return geonames_ids_hierarchy


# ---------------------------------- Endpoints -----------------------------------------
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
    search_provider: SearchProvider = Query(
        SearchProvider.geonames,
        description="The search provider (only geonames supported so far)",
    ),
):
    if search_provider == SearchProvider.geonames:
        # Search geonames API.
        search_results = geocoder.geonames(
            q,
            key=place_request_utils.get_geonames_user(),
            maxRows=limit,
            featureClass=["A", "P"],
        )

        # Format the search results to Place objects and return them.
        places = [geocoder_to_place(result) for result in search_results]
        return places
    else:
        raise HTTPException(400, f"Search provider not supported: {search_provider}")


@app.get(
    "/all", summary="Get all items for a place", response_model=ResultsList,
)
def get_all(
    place_name: str = place_name_query,
    geonames_id: int = geonames_id_query,
    max_distance: float = Query(
        0.5, description="Maximum distance in degrees lon/lat for test sites"
    ),
    limit: int = Query(5, description="Maximum number of test sites to return"),
):
    place = find_place(place_name, geonames_id)
    geonames_ids_hierarchy = get_hierarchy(place.geonames_id)
    return {
        "place": place,
        "hotlines": db.get("hotlines", geonames_ids_hierarchy),
        "websites": db.get("websites", geonames_ids_hierarchy),
        "test_sites": db.get_nearby(
            "test_sites", place.lat, place.lon, max_distance=max_distance, limit=limit
        ),
        "health_departments": db.get("health_departments", geonames_ids_hierarchy),
    }


@app.get(
    "/hotlines", summary=f"Get hotlines for a place", response_model=ResultsList,
)
def get_hotlines(
    place_name: str = place_name_query, geonames_id: int = geonames_id_query,
):
    place = find_place(place_name, geonames_id)
    geonames_ids_hierarchy = get_hierarchy(place.geonames_id)
    return {
        "place": place,
        "hotlines": db.get("hotlines", geonames_ids_hierarchy),
    }


@app.get(
    "/websites", summary=f"Get websites for a place", response_model=ResultsList,
)
def get_websites(
    place_name: str = place_name_query, geonames_id: int = geonames_id_query,
):
    place = find_place(place_name, geonames_id)
    geonames_ids_hierarchy = get_hierarchy(place.geonames_id)
    return {
        "place": place,
        "websites": db.get("websites", geonames_ids_hierarchy),
    }


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
    limit: int = Query(5, description="Maximum number of test sites to return"),
):
    place = find_place(place_name, geonames_id)
    # lat, lon = get_lat_lon(geonames_id)
    return {
        "geonames_id": geonames_id,
        "test_sites": db.get_nearby(
            "test_sites", place.lat, place.lon, max_distance=max_distance, limit=limit
        ),
    }


@app.get(
    "/health_departments",
    summary=f"Get responsible health departments for a place",
    response_model=ResultsList,
)
# TODO: This doesn't return results if e.g. Berlin is selected but the health department
#   is in Berlin Mitte. Maybe also search for the direct children of the geonames id
#   (but is direct children enough)?
def get_health_departments(
    place_name: str = place_name_query, geonames_id: int = geonames_id_query,
):
    place = find_place(place_name, geonames_id)
    geonames_ids_hierarchy = get_hierarchy(place.geonames_id)
    return {
        "place": place,
        "health_departments": db.get("health_departments", geonames_ids_hierarchy),
    }


@app.get(
    "/test", summary="Shows all entries for Berlin Mitte (redirects to /all endpoint)",
)
def test():
    response = RedirectResponse(url="/all?geonames_id=6545310")
    return response


# Use function names as operation IDs
endpoint_utils.use_route_names_as_operation_ids(app)


# Run uvicorn server directly in here for debugging
if __name__ == "__main__":
    uvicorn.run(app)
