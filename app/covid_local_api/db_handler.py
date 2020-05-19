import pandas as pd
import sqlite3
import urllib.request
import math
import os


class DatabaseHandler:
    def __init__(self, data_path="data"):
        """Downloads the Google Sheet and stores its data as in-memory sqlite3 database.

        Args:
            data_path (str, optional): The directory where the downloaded data should be 
                stored. Defaults to "data".
        """
        # Create in-memory sqlite3 database.
        # We can use check_same_thread because we only read from the database, so
        # there's no concurrency
        self.con = sqlite3.connect(":memory:", check_same_thread=False)

        # TODO: This should be done regularly or each time the Google Sheets database
        # updates.
        # Download excel from Google Sheets, read with pandas and write to database.
        url = "https://docs.google.com/spreadsheets/d/1AXadba5Si7WbJkfqQ4bN67cbP93oniR-J6uN0_Av958/export?format=xlsx"
        dfs = pd.read_excel(url, sheet_name=None)
        for table, df in dfs.items():
            df.to_sql(table, self.con)

        # Make database return dicts instead of tuples (https://stackoverflow.com/questions/3300464/how-can-i-get-dict-from-sqlite-query)
        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.con.row_factory = dict_factory

    def get(self, sheet, geonames_id, include_hierarchy=True):
        """Returns all entries from `sheet`, filtered by `geonames_id` and its 
        hierarchical parents. 
        
        If include_hierarchy is True, this method also looks for matches with 
        hierarchical parents (e.g. if geonames_id belongs to a city, it looks for items 
        for the state and country).
        
        Args:
            sheet (str): The worksheet in the Google Sheet
            geonames_id (int): The geonames_id to search for
            include_hierarchy (boolean, optional): Whether to search for hierarchical 
                parents. Defaults to False.

        Returns:
            (list of dict): Filtered database entries as key-value dicts
        """
        if include_hierarchy:
            hierarchy = geocoder.geonames(
                geonames_id, key=geonames_username, method="hierarchy"
            )
            hierarchy = hierarchy[::-1]  # reverse, so that more local areas come first
            all_geonames_ids = [item.geonames_id for item in hierarchy]

            # TODO: Maybe also search for children here, e.g. if geonames_id belongs to
            #   Berlin but the health departments are in the districts. Not sure if it
            #   makes sense to search only for direct children or whether we would need
            #   all children (which would be a massive overload).
        else:
            all_geonames_ids = [geonames_id]

        # Make SQL request on database
        cur = self.con.execute(
            f"SELECT * FROM {sheet} WHERE geonames_id "
            f"IN ({', '.join(map(str, all_geonames_ids))})"
        )
        dicts = cur.fetchall()
        return dicts

    def get_nearby(self, sheet, lat, lon, max_distance=0.5, limit=5):
        """Returns nearby entries from `sheet` for a latitude/longitude pair, sorted by 
        distance.

        Note: Distance is right now not the true distance in kilometers, but the 
            "distance" in degrees lat/lon (i.e. sqrt((lat1-lat2)**2 + (lon1-lon2)**2)). 
            This value is proportional to the kilometers at the equator but deviates the 
            further you move to the poles. We cannot calculate the true distance 
            because the sqlite database can't do complex math operations. 

        Args:
            sheet (str): The worksheet in the Google Sheet
            lon (float or str): Longitude of the target location
            lat (float or str): Latitude of the target location
            max_distance (float, optional): Maximum distance to search for objects (in 
                degrees lat/lon; default: 0.5)
            limit (float, optional): Maximum number of elements to return (default: 5). 
                If more elements were found within `max_distance`, return the closest 
                ones. 

        Returns:
            list of dict: Filtered database entries as key-value dicts
        """
        # Query elements from the sheet that are closer to lat/lon than max_distance,
        # order them by the distance, and limit number of rows to limit.
        # Distance is in degrees lat/lon, see comment in docstring.
        # TODO: Find a better solution to calculate distances, based on true distance
        #   in kilometers.
        squared_distance = f"(lat-{lat})*(lat-{lat})+(lon-{lon})*(lon-{lon})"
        query = (
            f"SELECT *, {squared_distance} AS distance FROM test_sites "
            f"WHERE {squared_distance} <= {max_distance}*{max_distance} "
            f"ORDER BY {squared_distance} LIMIT {limit}"
        )
        cur = self.con.execute(query)

        dicts = cur.fetchall()
        for d in dicts:
            # Distance in SQL query is squared, so take the sqrt here.
            d["distance"] = math.sqrt(d["distance"])
        return dicts
