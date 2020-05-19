import pandas as pd
import sqlite3
import math
import threading


class DatabaseHandler:
    def __init__(self, update_every_seconds=3600):
        """Initializes the database connection. Downloads the Google Sheet, stores 
        its data as in-memory sqlite3 database and updates it regularly.

        Args:
            update_every_seconds(int, optional): If not None, the database will be 
                updated with the current data from the Google Sheet at this time 
                interval in seconds. Defaults to 3600 (equals 1 hour).
        """
        self.update_every_seconds = update_every_seconds
        self.con = None
        self._update_database()

    def _update_database(self):
        """Creates new database with the current data from the Google Sheet. 
        
        If self.update_every_seconds is not None, this will automatically schedule 
        the next update.
        """
        # Close old database. This will delete it as it is only stored in memory.
        # See https://stackoverflow.com/questions/48732439/deleting-a-database-file-in-memory
        if self.con is not None:
            print("Deleting old database...")
            self.con.close()

        print("Creating new database...")
        # Create in-memory sqlite3 database.
        # We can use check_same_thread because we only read from the database, so
        # there's no concurrency
        self.con = sqlite3.connect(":memory:", check_same_thread=False)

        # Download excel file from Google Sheets, read it with pandas and write to
        # database.
        url = "https://docs.google.com/spreadsheets/d/1AXadba5Si7WbJkfqQ4bN67cbP93oniR-J6uN0_Av958/export?format=xlsx"
        dfs = pd.read_excel(url, sheet_name=None)
        for table, df in dfs.items():
            df.to_sql(table, self.con)

        # Make database return dicts instead of tuples.
        # From: https://stackoverflow.com/questions/3300464/how-can-i-get-dict-from-sqlite-query
        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.con.row_factory = dict_factory

        print("Database successfully updated")

        # Schedule next update of the database.
        if self.update_every_seconds is not None:
            print(
                f"Scheduling next database update in {self.update_every_seconds} seconds"
            )
            threading.Timer(self.update_every_seconds, self._update_database).start()

    def get(self, sheet, geonames_ids):
        """Returns all entries from `sheet`, which match one of the ids in 
        `geonames_ids`.
        
        Args:
            sheet (str): The worksheet in the Google Sheet
            geonames_ids (int): The geonames_ids of the places to search for

        Returns:
            (list of dict): Filtered database entries as key-value dicts
        """
        cur = self.con.execute(
            f"SELECT * FROM {sheet} WHERE geonames_id "
            f"IN ({', '.join(map(str, geonames_ids))})"
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
            lat (float): The latitude of the place
            lon (float): The longitude of the place
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
