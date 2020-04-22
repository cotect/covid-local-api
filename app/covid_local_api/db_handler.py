import pandas as pd
import sqlite3
import urllib.request


class DatabaseHandler():

    def __init__(self):
        """Download data from Google Sheets and store it as in-memory sqlite3 database"""
        # TODO: This should be done regularly or each time the Google Sheets database updates. 
        # Download data from Google Sheets as excel file
        url = "https://docs.google.com/spreadsheets/d/1AXadba5Si7WbJkfqQ4bN67cbP93oniR-J6uN0_Av958/export?format=xlsx"
        xlsx_filename = "data/spreedsheat.xlsx"
        urllib.request.urlretrieve(url, xlsx_filename)

        # Create in-memory sqlite3 database from excel file
        # We can use check_same_thread because we only read from the database, so there's no concurrency
        self.con = sqlite3.connect(":memory:", check_same_thread=False)
        dfs = pd.read_excel(xlsx_filename, sheet_name=None)
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
        """Get all entries from sheet where the geoname id is in geonames_ids.
        
        Args:
            sheet (str): The worksheet in the Google Sheet
            geonames_ids (list of int): The list of geonames ids to filter

        Returns:
            (list of dict): Filtered database entries as key-value dicts
        """
        cur = self.con.execute(f"SELECT * FROM {sheet} WHERE geonames_ids IN ({', '.join(map(str, geonames_ids))})")
        dicts = cur.fetchall()
        return dicts

