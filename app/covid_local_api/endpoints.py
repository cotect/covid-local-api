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

# from covid_local_api.place_handler import (
#     PlaceHandler,
#     load_place_hierarchy,
#     load_place_mapping,
# )


# Initialize helper objects
data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
log = logging.getLogger(__name__)
db = DatabaseHandler(data_path)

# TODO: Implement place handler code.
# place_handler = PlaceHandler(
#     load_place_mapping(os.path.join(data_path, "DE_placeid-to-wikidata.json")),
#     load_place_hierarchy(os.path.join(data_path, "DE_place-hierarchy.csv")),
#     country_codes=["DE"],
# )


# Initialize API
app = FastAPI(
    title="COVID-19 Local API",
    description="API to get local help information about COVID-19 (hotlines, websites, "
    "testing sites, ...)",
    version=__version__,
)


# TODO: Implement place handler code.
# @app.get("/test_place_handler")
# def test_place_handler(place_id: str = Query(..., description="Place ID to filter.")):
#     return place_handler.resolve_hierarchies(place_id)


class SearchProvider(str, Enum):
    """Enum of the available search providers for the places endpoint"""

    geonames = "geonames"


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

        # Format the search results and return them.
        places = [
            Place(
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
            for result in search_results
        ]
        return places
    else:
        raise HTTPException(400, f"Search provider not supported: {search_provider}")


def parse_place_parameters(place_name, geonames_id):
    """Returns the correct geonames id for the given query parameters. 
    
    If geonames_id is given, simply return it. If place_name is given, search the 
    /places endpoint and return the geonames id of the first search result. If none of 
    both is given, raise an error.
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
            return places[0].geonames_id
    else:
        return geonames_id


def get_hierarchy(geonames_id):
    """Returns geonames ids of hierarchical parents (e.g. country for a city)"""
    hierarchy = geocoder.geonames(
        geonames_id, key=place_request_utils.get_geonames_user(), method="hierarchy",
    )
    hierarchy = hierarchy[::-1]  # reverse, so that more local areas come first
    geonames_ids_hierarchy = [item.geonames_id for item in hierarchy]
    return geonames_ids_hierarchy


def get_lat_lon(geonames_id):
    """Returns the latitude and longitude of the place"""
    details = geocoder.geonames(
        geonames_id, key=place_request_utils.get_geonames_user(), method="details"
    )
    return details.lat, details.lng


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
def get_all(
    place_name: str = place_name_query,
    geonames_id: int = geonames_id_query,
    max_distance: float = Query(
        0.5, description="Maximum distance in degrees lon/lat for test sites"
    ),
    limit: int = Query(5, description="Maximum number of test sites to return"),
):
    geonames_id = parse_place_parameters(place_name, geonames_id)
    geonames_ids_hierarchy = get_hierarchy(geonames_id)
    lat, lon = get_lat_lon(geonames_id)
    return {
        "geonames_id": geonames_id,
        "hotlines": db.get("hotlines", geonames_ids_hierarchy),
        "websites": db.get("websites", geonames_ids_hierarchy),
        "test_sites": db.get_nearby(
            "test_sites", lat, lon, max_distance=max_distance, limit=limit
        ),
        "health_departments": db.get("health_departments", geonames_ids_hierarchy),
    }


@app.get(
    "/hotlines", summary=f"Get hotlines for a place", response_model=ResultsList,
)
def get_hotlines(
    place_name: str = place_name_query, geonames_id: int = geonames_id_query,
):
    geonames_id = parse_place_parameters(place_name, geonames_id)
    geonames_ids_hierarchy = get_hierarchy(geonames_id)
    return {
        "geonames_id": geonames_id,
        "hotlines": db.get("hotlines", geonames_ids_hierarchy),
    }


@app.get(
    "/websites", summary=f"Get websites for a place", response_model=ResultsList,
)
def get_websites(
    place_name: str = place_name_query, geonames_id: int = geonames_id_query,
):
    geonames_id = parse_place_parameters(place_name, geonames_id)
    geonames_ids_hierarchy = get_hierarchy(geonames_id)
    return {
        "geonames_id": geonames_id,
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
    geonames_id = parse_place_parameters(place_name, geonames_id)
    lat, lon = get_lat_lon(geonames_id)
    return {
        "geonames_id": geonames_id,
        "test_sites": db.get_nearby(
            "test_sites", lat, lon, max_distance=max_distance, limit=limit
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
    geonames_id = parse_place_parameters(place_name, geonames_id)
    geonames_ids_hierarchy = get_hierarchy(geonames_id)
    return {
        "geonames_id": geonames_id,
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
