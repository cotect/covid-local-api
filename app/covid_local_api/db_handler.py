import pandas as pd
import sqlite3
import urllib.request
import math
import os


class DatabaseHandler:
    def __init__(self, data_path="data"):
        """Downloads the Google Sheet and stores its data as in-memory sqlite3 database.

        Args:
            data_path (str, optional): The directory where the downloaded data should be stored. Defaults to "data".
        """
        # Create in-memory sqlite3 database.
        # We can use check_same_thread because we only read from the database, so there's no concurrency
        self.con = sqlite3.connect(":memory:", check_same_thread=False)
        
        # TODO: This should be done regularly or each time the Google Sheets database updates.
        # Download excel file from Google Sheets, read it with pandas and write to database.
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

    def get(self, sheet, geonames_ids):
        """Returns all entries from `sheet` whose geonames_id is in `geonames_ids`.
        
        Args:
            sheet (str): The worksheet in the Google Sheet
            geonames_ids (list of int): The list of geonames ids to filter

        Returns:
            (list of dict): Filtered database entries as key-value dicts
        """
        # TODO: Maybe integrate hierarchy thing here directly, as I also handle distance calculations now in this class (see get_nearby).
        cur = self.con.execute(
            f"SELECT * FROM {sheet} WHERE geonames_id IN ({', '.join(map(str, geonames_ids))})"
        )
        dicts = cur.fetchall()
        return dicts

    def get_nearby(self, sheet, lat, lon, max_distance=0.5, limit=5):
        """Returns nearby entries from `sheet` for a latitude/longitude pair, sorted by distance.

        Note: Distance is right now not the true distance in kilometers, but the "distance" in degrees lat/lon
            (i.e. sqrt((lat1-lat2)**2 + (lon1-lon2)**2)). This value is proportional to the kilometers at the 
            equator but deviates the further you move to the poles. We cannot calculate the true distance 
            because the sqlite database can't do complex math operations. 

        Args:
            sheet (str): The worksheet in the Google Sheet
            lon (float or str): Longitude of the target location
            lat (float or str): Latitude of the target location
            max_distance (float, optional): Maximum distance to search for objects (in degrees lat/lon; default: 0.5)
            limit (float, optional): Maximum number of elements to return (default: 5). If more elements 
                were found within `max_distance`, return the closest ones. 

        Returns:
            list of dict: Filtered database entries as key-value dicts
        """
        # Query elements from the sheet that are closer to lat/lon than max_distance,
        # order them by the distance, and limit number of rows to limit.
        # Distance is in degrees lat/lon, see comment in docstring.
        # TODO: Find a better solution to calculate distances, based on true distance in kilometers.
        squared_distance = f"(lat-{lat})*(lat-{lat})+(lon-{lon})*(lon-{lon})"
        query = f"SELECT *, {squared_distance} AS distance FROM test_sites WHERE {squared_distance} <= {max_distance}*{max_distance} ORDER BY {squared_distance} LIMIT {limit}"
        cur = self.con.execute(query)

        dicts = cur.fetchall()
        for d in dicts:
            # Distance in SQL query is squared, so take the sqrt here.
            d["distance"] = math.sqrt(d["distance"])
        return dicts
