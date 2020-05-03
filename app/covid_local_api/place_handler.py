import logging
import csv, json
from typing import List, Optional

from covid_local_api.utils.place_request_utils import (
    GEONAMES_ID_PREFIX,
    OSM_ID_PREFIX,
    map_geonames_to_wikidata,
    map_osm_to_wikidata,
    map_wikidata_to_geonames,
    map_wikidata_to_osm,
    request_geonames_hierarchy,
    request_osm_hierarchy,
    search_geonames,
    search_osm,
)


def load_place_hierarchy(hierarchy_csv_path: str):
    place_hierarchy = {}

    with open(hierarchy_csv_path, "r") as f:
        csv_reader = csv.reader(f, delimiter=",")
        for row in csv_reader:
            if row and len(row) == 2:
                place_hierarchy[row[0]] = row[1]
    return place_hierarchy


def load_place_mapping(mapping_json_path: str):
    place_mapping = {}

    with open(mapping_json_path, "r") as f:
        place_mapping = json.load(f)

    return place_mapping


def create_inverse_mapping(
    input_mapping: dict, filter_prefix: Optional[str] = None
) -> dict:
    new_mapping = {}
    for key, value_set in input_mapping.items():
        if filter_prefix and not key.startswith(filter_prefix):
            continue

        for item in value_set:
            new_mapping.setdefault(item, set()).add(key)
    return new_mapping


class PlaceHandler:
    def __init__(
        self,
        place_wikidata_mapping: dict,
        place_hierarchy: dict,
        country_codes: List[str] = None,
        resolve_unknown: bool = False,
    ):

        self._log = logging.getLogger(__name__)

        self._place_wikidata_mapping = place_wikidata_mapping
        self._place_hierarchy = place_hierarchy
        self._country_codes = country_codes

        self._place_inverse_mapping = create_inverse_mapping(
            self._place_wikidata_mapping
        )

    def __getitem__(self, key):
        key = key.strip().upper()

        if key in self._place_wikidata_mapping:
            return list(self._place_wikidata_mapping[key])

        if key in self._place_inverse_mapping:
            return list(self._place_inverse_mapping[key])

        return []

    def __contains__(self, key):
        key = key.strip().upper()

        if key in self._place_wikidata_mapping or key in self._place_inverse_mapping:
            return True

    def search_places(self, query: str, limit: int = 5):
        search_result = []
        added_wikidata_ids = set()
        geonames_results = search_geonames(query, limit, self._country_codes)
        for result in geonames_results:
            wikidata_id = self.map_geonames_to_wikidata(result[0])
            if wikidata_id and wikidata_id not in added_wikidata_ids:
                search_result.append((wikidata_id, result[1]))
                added_wikidata_ids.add(wikidata_id)

        if len(search_result) < limit:
            osm_results = search_osm(query, limit, self._country_codes)
            for result in osm_results:
                wikidata_id = self.map_osm_to_wikidata(result[0])
                if wikidata_id and wikidata_id not in added_wikidata_ids:
                    search_result.append((wikidata_id, result[1]))
                    added_wikidata_ids.add(wikidata_id)
                if len(search_result) == limit:
                    break

        return search_result

    def resolve_hierarchies(self, key: str) -> list:
        key = key.strip().upper()

        place_hierarchies = []

        if key in self._place_wikidata_mapping:
            for wikidata_id in self._place_wikidata_mapping[key]:
                place_hierarchies.append(self.resolve_wikidata_hierarchy(wikidata_id))
            return place_hierarchies

        key_to_add = None
        if key in self._place_inverse_mapping:
            key_to_add = key
        elif key.startswith(GEONAMES_ID_PREFIX):
            key_to_add = self.map_geonames_to_wikidata(key)
            print(key_to_add)
        elif key.startswith(OSM_ID_PREFIX):
            key_to_add = self.map_osm_to_wikidata()(key)

        if key_to_add:
            # Key is wikidata id
            place_hierarchies.append(self.resolve_wikidata_hierarchy(key_to_add))
            return place_hierarchies

    def map_geonames_to_wikidata(self, geonames_id: str) -> str:
        geonames_id = str(geonames_id).strip().upper()
        if not geonames_id.startswith(GEONAMES_ID_PREFIX):
            geonames_id = GEONAMES_ID_PREFIX + geonames_id

        # TODO only return one result?
        if geonames_id in self and self[geonames_id]:
            return self[geonames_id][0]
        else:
            return map_geonames_to_wikidata(geonames_id)

    def map_wikidata_to_geonames(self, wikidata_id: str) -> str:
        if wikidata_id in self and self[wikidata_id]:
            for result in self[wikidata_id]:
                if result.startswith(GEONAMES_ID_PREFIX):
                    return result
        return map_wikidata_to_geonames(wikidata_id)

    def map_osm_to_wikidata(self, osm_id: str) -> list:
        osm_id = str(osm_id).strip().upper()
        if not osm_id.startswith(OSM_ID_PREFIX):
            osm_id = OSM_ID_PREFIX + osm_id

        # TODO only return one result?
        if osm_id in self and self[osm_id]:
            return self[osm_id][0]
        else:
            return map_osm_to_wikidata(osm_id)

    def map_wikidata_to_osm(self, wikidata_id: str):
        if wikidata_id in self and self[wikidata_id]:
            for result in self[wikidata_id]:
                if result.startswith(OSM_ID_PREFIX):
                    return result

        return map_wikidata_to_osm(wikidata_id)

    def request_wikidata_hierarchy_with_geonames(self, wikidata_id: str):
        wikidata_id = wikidata_id.strip().upper()
        wikidata_hierarchy = []
        try:
            geonames_id = self.map_wikidata_to_geonames(wikidata_id)
            if not geonames_id:
                return []
            geonames_hierarchy = request_geonames_hierarchy(geonames_id)
            for geonames_id in geonames_hierarchy:
                wikidata_id = self.map_geonames_to_wikidata(geonames_id)
                if wikidata_id and wikidata_id not in wikidata_hierarchy:
                    wikidata_hierarchy.append(wikidata_id)
            return wikidata_hierarchy
        except Exception:
            self._log.info("Failed to request geonames hierarchy.", exc_info=True)
            return []

    def request_wikidata_hierarchy_with_osm(self, wikidata_id: str):
        wikidata_id = wikidata_id.strip().upper()
        wikidata_hierarchy = []
        try:
            osm_id = self.map_wikidata_to_osm(wikidata_id)
            if not osm_id:
                return []
            osm_hierarchy = request_osm_hierarchy(osm_id)
            for osm_id in osm_hierarchy:
                wikidata_id = self.map_osm_to_wikidata(osm_id)
                if wikidata_id and wikidata_id not in wikidata_hierarchy:
                    wikidata_hierarchy.append(wikidata_id)
            return wikidata_hierarchy
        except Exception:
            self._log.info("Failed to request osm hierarchy.", exc_info=True)
            return []

    def resolve_wikidata_hierarchy(
        self, wikidata_id: str, prefer_geonames: bool = True, prefer_osm: bool = False
    ) -> List[str]:

        if wikidata_id in self._place_hierarchy:
            wikidata_hierarchy = []
            current_item = wikidata_id
            wikidata_hierarchy.append(current_item)
            while current_item in self._place_hierarchy:
                current_item = self._place_hierarchy[current_item]
                wikidata_hierarchy.append(current_item)
            return list(reversed(wikidata_hierarchy))

        geonames_wkdt_hierarchy = []
        osm_wkdt_hierarchy = []

        if prefer_geonames or not prefer_osm:
            geonames_wkdt_hierarchy = self.request_wikidata_hierarchy_with_geonames(
                wikidata_id
            )
            if not geonames_wkdt_hierarchy:
                # Use osm as fallback
                self._log.info(
                    "Fallback to using osm to resolve wikidata hierachy: " + wikidata_id
                )
                return self.request_wikidata_hierarchy_with_osm(wikidata_id)

        if prefer_osm or not prefer_geonames:
            osm_wkdt_hierarchy = self.request_wikidata_hierarchy_with_osm(wikidata_id)
            if not osm_wkdt_hierarchy and not geonames_wkdt_hierarchy:
                # Use geonames as fallback
                self._log.info(
                    "Fallback to using geonames to resolve wikidata hierachy: "
                    + wikidata_id
                )
                return self.request_wikidata_hierarchy_with_geonames(wikidata_id)

        if not geonames_wkdt_hierarchy and not osm_wkdt_hierarchy:
            self._log.info("Failed to get wikidata hiearchy for " + wikidata_id)

        if len(geonames_wkdt_hierarchy) > len(osm_wkdt_hierarchy):
            return geonames_wkdt_hierarchy
        else:
            return osm_wkdt_hierarchy
