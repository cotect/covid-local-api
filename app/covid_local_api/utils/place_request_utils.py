import logging
import os
import random
from typing import List

import requests
from qwikidata.linked_data_interface import get_entity_dict_from_api
from qwikidata.sparql import return_sparql_query_results

log = logging.getLogger(__name__)

GEONAMES_ENDPOINT = os.getenv("GEONAMES_ENDPOINT", "http://api.geonames.org")
GEONAMES_ENDPOINT_V3 = os.getenv("GEONAMES_ENDPOINT_V3", "http://www.geonames.org")
GEONAMES_USERS = os.getenv("GEONAMES_USERS", "sap_ekg").replace(" ", "").split(",")

OSM_NOMATIM_ENDPOINT = os.getenv(
    "OSM_NOMATIM_ENDPOINT", "https://nominatim.openstreetmap.org"
)

IGNORED_GEONAMES_ID = ["6295630", "6255148"]

OSM_TYPE_MAPPING = {"relation": "R", "way": "W", "node": "N"}
OSM_ID_PREFIX = "OSM:"
GEONAMES_ID_PREFIX = "GN:"


def request_geonames_hierarchy(geonames_id: str, fast: bool = True) -> List[str]:
    geonames_id = str(geonames_id).strip().upper().lstrip(GEONAMES_ID_PREFIX)
    if fast:
        # Only request a single JSON instead of the full hierarchy
        try:
            #
            request_url = (
                GEONAMES_ENDPOINT_V3
                + "/getJSON?geonameId={geonames_id}&style=full&username={geonames_user}"
            )
            response_json = requests.get(
                request_url.format(
                    geonames_id=geonames_id, geonames_user=random.choice(GEONAMES_USERS)
                )
            ).json()
            sorted_geonames_hierarchy = []

            if "countryId" in response_json and response_json["countryId"]:
                sorted_geonames_hierarchy.append(
                    GEONAMES_ID_PREFIX + str(response_json["countryId"])
                )

            if "adminId1" in response_json and response_json["adminId1"]:
                sorted_geonames_hierarchy.append(
                    GEONAMES_ID_PREFIX + str(response_json["adminId1"])
                )

            if "adminId2" in response_json and response_json["adminId2"]:
                sorted_geonames_hierarchy.append(
                    GEONAMES_ID_PREFIX + str(response_json["adminId2"])
                )

            if "adminId3" in response_json and response_json["adminId3"]:
                sorted_geonames_hierarchy.append(
                    GEONAMES_ID_PREFIX + str(response_json["adminId3"])
                )

            if "adminId4" in response_json and response_json["adminId4"]:
                sorted_geonames_hierarchy.append(
                    GEONAMES_ID_PREFIX + str(response_json["adminId4"])
                )

            if "adminId5" in response_json and response_json["adminId5"]:
                sorted_geonames_hierarchy.append(
                    GEONAMES_ID_PREFIX + str(response_json["adminId5"])
                )

            if "geonameId" in response_json and response_json["geonameId"]:
                sorted_geonames_hierarchy.append(
                    GEONAMES_ID_PREFIX + str(response_json["geonameId"])
                )

            return sorted_geonames_hierarchy
        except Exception:
            log.info("Failed to get geonames hierarchy.", exc_info=True)
            return None
    else:
        try:
            request_url = (
                GEONAMES_ENDPOINT_V3
                + "/hierarchyJSON?style=full&geonameId={geonames_id}&username={geonames_user}"
            )
            response = requests.get(
                request_url.format(
                    geonames_id=geonames_id, geonames_user=random.choice(GEONAMES_USERS)
                )
            )
            sorted_geonames_hierarchy = []
            for area in response.json()["geonames"]:
                area_id = str(area["geonameId"])
                if area_id and area_id not in IGNORED_GEONAMES_ID:
                    if "adminId5" in area and area["adminId5"]:
                        # admin id 5 does not seem to be fully supported in hierarchy
                        # add it manually
                        area_admin_id_5 = area["adminId5"]
                        if (
                            area_admin_id_5 not in sorted_geonames_hierarchy
                            and area_id != area_admin_id_5
                        ):
                            sorted_geonames_hierarchy.append(
                                GEONAMES_ID_PREFIX + str(area_admin_id_5)
                            )
                    sorted_geonames_hierarchy.append(GEONAMES_ID_PREFIX + str(area_id))
            return sorted_geonames_hierarchy
        except Exception:
            log.info("Failed to get geonames hierarchy.", exc_info=True)
            return None


def request_osm_hierarchy(osm_id: str) -> List[str]:
    osm_id = str(osm_id).strip().upper().lstrip(OSM_ID_PREFIX)
    try:
        # Assume R as base type
        osm_type = "R"
        if osm_id[0] in OSM_TYPE_MAPPING.values():
            osm_type = osm_id[0]
            osm_id = osm_id[1:]

        request_url = (
            OSM_NOMATIM_ENDPOINT
            + "/details.php?osmtype={osm_type}&osmid={osm_id}&format=json&addressdetails=1&hierarchy=0&linkedplaces=0&polygon_geojson=0&keywords=0&extratags=0"
        )
        response = requests.get(request_url.format(osm_type=osm_type, osm_id=osm_id))

        country_code = None
        osm_id_to_level = []
        for area in response.json()["address"]:
            if "osm_id" in area and area["osm_id"]:
                osm_id = str(area["osm_type"]) + str(area["osm_id"])
                osm_id_to_level.append((osm_id, int(area["admin_level"])))
            elif "type" in area and area["type"] == "country_code":
                # extract country code
                country_code = area["localname"]

        sorted_osm_hierarchy = []
        if country_code:
            country_id = map_countrycode_to_osm(country_code)
            if country_id:
                sorted_osm_hierarchy.append(country_id)

        # sort by admin level
        osm_id_to_level.sort(key=lambda x: x[1])
        for osm_id in list(zip(*osm_id_to_level))[0]:
            sorted_osm_hierarchy.append(OSM_ID_PREFIX + osm_id)

        return sorted_osm_hierarchy
    except Exception:
        log.debug("Failed to get osm geonames hierarchy: " + osm_id, exc_info=True)
        return None


def map_countrycode_to_osm(country_code: str) -> str:
    try:
        request_url = (
            OSM_NOMATIM_ENDPOINT + "/search?country={country_code}&format=json"
        )
        response = requests.get(request_url.format(country_code=country_code.upper()))
        osm_obj = response.json()[0]
        osm_type = OSM_TYPE_MAPPING[osm_obj["osm_type"]]
        osm_id = osm_type + str(osm_obj["osm_id"])
        return OSM_ID_PREFIX + osm_id
    except Exception:
        log.debug("Failed to map country code to osm id.", exc_info=True)
        return None


def map_osm_to_wikidata(osm_id: str) -> str:
    osm_id = str(osm_id).strip().upper().lstrip(OSM_ID_PREFIX)
    try:
        # Try to get wikidata id from nominatim API
        if osm_id[0] not in OSM_TYPE_MAPPING.values():
            raise Exception("Only ids with N,W,R prefix are allowed.")

        nominatim_lookup_url = (
            OSM_NOMATIM_ENDPOINT
            + "/lookup?osm_ids={osm_id}&format=json&extratags=1&addressdetails=0&namedetails=0"
        )
        response = requests.get(nominatim_lookup_url.format(osm_id=osm_id))
        if len(response.json()) > 1:
            log.info("Found more than one wikidata id for osm id: " + osm_id)
        if "wikidata" not in response.json()[0]["extratags"]:
            raise Exception("No wikidata information found with OSM item.")
        return response.json()[0]["extratags"]["wikidata"]
    except Exception:
        try:
            if osm_id[0] != "R":
                raise Exception(
                    "Only osm relations (prefix R) are supported by wikidata."
                )

            osm_id = osm_id[1:]

            # Fallback: search for id in wikidata
            sparql_query = """
            SELECT ?id WHERE {{      
              ?id wdt:{id_type} "{id}".
            }}
            """

            res = return_sparql_query_results(
                sparql_query.format(id_type="P402", id=osm_id)
            )
            if len(res["results"]["bindings"]) > 1:
                log.info("Found more than one wikidata id for osm id: " + osm_id)
            return os.path.basename(res["results"]["bindings"][0]["id"]["value"])
        except Exception:
            log.info("Failed to map osm id to wikidata id.", exc_info=True)
            return None


def map_geonames_to_wikidata(geonames_id: str) -> str:
    geonames_id = str(geonames_id).strip().upper().lstrip(GEONAMES_ID_PREFIX)
    try:
        request_url = (
            GEONAMES_ENDPOINT_V3
            + "/getJSON?geonameId={geonames_id}&style=full&username={geonames_user}"
        )
        response_json = requests.get(
            request_url.format(
                geonames_id=geonames_id, geonames_user=random.choice(GEONAMES_USERS)
            )
        ).json()

        if "alternateNames" in response_json and response_json["alternateNames"]:
            for tag in response_json["alternateNames"]:
                if "lang" in tag and tag["lang"] == "wkdt":
                    if tag["name"]:
                        return tag["name"]
        raise Exception()
    except Exception:
        try:
            # Fallback: search for id in wikidata
            sparql_query = """
            SELECT ?id WHERE {{      
              ?id wdt:{id_type} "{id}".
            }}
            """

            res = return_sparql_query_results(
                sparql_query.format(id_type="P1566", id=geonames_id)
            )

            if len(res["results"]["bindings"]) > 1:
                log.info(
                    "Found more than one wikidata id for geonames id: "
                    + str(geonames_id)
                )
            return os.path.basename(res["results"]["bindings"][0]["id"]["value"])
        except Exception:
            log.debug("Failed to map geonames id to wikidata id.", exc_info=True)
            return None


def map_wikidata_to_osm(wikidata_id: str) -> str:
    wikidata_id = wikidata_id.upper()
    try:
        wikidata_result = get_entity_dict_from_api(wikidata_id)
        if len(wikidata_result["claims"]["P402"]) > 1:
            log.info("Found more than one osm id for wikidata id: " + wikidata_id)
        return (
            OSM_ID_PREFIX
            + "R"
            + wikidata_result["claims"]["P402"][0]["mainsnak"]["datavalue"]["value"]
        )
    except Exception:
        log.debug("Failed to map wikidata id to osm id.", exc_info=True)
        return None


def map_wikidata_to_geonames(wikidata_id: str) -> str:
    wikidata_id = wikidata_id.upper()
    try:
        wikidata_result = get_entity_dict_from_api(wikidata_id)
        if len(wikidata_result["claims"]["P1566"]) > 1:
            log.info("Found more than one geonames id for wikidata id: " + wikidata_id)
        return (
            GEONAMES_ID_PREFIX
            + wikidata_result["claims"]["P1566"][0]["mainsnak"]["datavalue"]["value"]
        )
    except Exception:
        log.debug("Failed to map wikidata id to geonames id.", exc_info=True)
        return None


def search_osm(query: str, limit: int = 5, country_codes: List[str] = None) -> str:
    try:
        country_code_filter = ""
        if country_codes:
            country_code_filter = "&countrycodes=" + ",".join(country_codes)

        request_url = (
            OSM_NOMATIM_ENDPOINT
            + "/search?q={query}&limit={limit}&format=json"
            + country_code_filter
        )
        response = requests.get(request_url.format(query=query, limit=limit))
        results = []
        for place in response.json():
            if (
                "osm_type" in place
                and place["osm_type"]
                and "osm_id" in place
                and place["osm_id"]
            ):
                name = place["display_name"]
                results.append(
                    (
                        name,
                        OSM_ID_PREFIX
                        + OSM_TYPE_MAPPING[place["osm_type"]]
                        + str(place["osm_id"]),
                    )
                )
        return results
    except Exception:
        log.info("Failed to execute search for: " + query, exc_info=True)
        return []


def search_geonames(query: str, limit: int = 5, country_codes: List[str] = None) -> str:
    try:
        country_code_filter = ""
        if country_codes:
            for country_code in country_codes:
                country_code_filter += "&country=" + country_code

        request_url = (
            GEONAMES_ENDPOINT
            + "/searchJSON?q={query}&maxRows={max_rows}&username={username}&orderby=relevance&featureClass=P&featureClass=A"
            + country_code_filter
        )
        response = requests.get(
            request_url.format(
                query=query, max_rows=limit, username=random.choice(GEONAMES_USERS)
            )
        )
        results = []
        for place in response.json()["geonames"]:
            name = place["toponymName"]
            results.append((GEONAMES_ID_PREFIX + str(place["geonameId"]), name))
        return results
    except Exception:
        log.info("Failed to execute search for: " + query, exc_info=True)
        return []
