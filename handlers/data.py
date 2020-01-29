import rethinkdb as r
r.connect = r.RethinkDB.connect
from typing import Union
import json
import os
from collections import deque
from pathlib import Path
from .exceptions import NotConnected


class Rethink:
    """This handles all the RethinkDB data,
    as well as the JSON data and any syncing required between any number of them.
    """

    def __init__(self, *, db='dlist', ip='localhost', port=28015,
                 loop_type='asynico', **options):
        self.host = f"{ip}"
        self.loop_type = loop_type
        self.db = db
        self.conn = None
        # r.set_loop_type(self.loop_type)

    async def _connect(self) -> None:
        """Connects to the RethinkDB instance"""
        self.conn = (r.connect(db=self.db, host=self.host))
        return self.conn

    async def to_json(self, table, row, db=None) -> dict:
        """Converts cursor to JSON."""
        if self.conn is None:
            raise NotConnected("You must login before you use this function!")
        db = self.db if db is None else db
        json_string = r.db(db).table(table).get(row).to_json_string().run(self.conn)
        return json.loads(json_string)

    async def table_create(self, table, db=None) -> dict:
        """Creates a table on the provided database, default is dlist."""
        if self.conn is None:
            raise NotConnected("You must login before you use this function!")
        db = self.db if db is None else db
        return r.db(db).table_create(table).run(self.conn)

    async def table_drop(self, table, db=None) -> dict:
        """Removes a table on the provided database, default is dlist."""
        if self.conn is None:
            raise NotConnected("You must login before you use this function!")
        db = self.db if db is None else db
        return r.db(db).table_drop(table).run(self.conn)

    async def insert(self, table, data: dict, db=None) -> dict:
        """Inserts data to a table on the provided database.
        Default database is dlist."""
        if self.conn is None:
            raise NotConnected("You must login before you use this function!")
        db = self.db if db is None else db
        return r.db(db).table(table).insert(data).run(self.conn)

    async def update(self, table, row, data: dict, db=None) -> dict:
        """Updates data on a row in a table on the provided database.
        Default database is dlist."""
        if self.conn is None:
            raise NotConnected("You must login before you use this function!")
        db = self.db if db is None else db
        data['id'] = row
        return r.db(db).table(table).get(row).update(data).run(self.conn)

    async def replace(self, table, row, data: dict, db=None) -> dict:
        """Replaces data in a row."""
        if self.conn is None:
            raise NotConnected("You must login before you use this function!")
        db = self.db if db is None else db
        data['id'] = row
        return r.db(db).table(table).get(row).replace(data).run(self.conn)

    async def remove(self, table, key, db=None) -> dict:
        """Removes data in the table on the provided database.
        Default database is dlist."""
        if self.conn is None:
            raise NotConnected("You must login before you use this function!")
        db = self.db if db is None else db
        return r.db(db).table(table).replace(r.row.without(key)).run(self.conn)

    async def find(self, table, row, db=None) -> dict:
        """Finds a row in the provided table on the provided database.
        Default database is dlist."""
        if self.conn is None:
            raise NotConnected("You must login before you use this function!")
        db = self.db if db is None else db
        data = r.db(db).table(table).get(row).run(self.conn)
        del data['id']
        return data

class JSON:
    """JSON data support."""

    def write(self, filename, key, value, list=None) -> dict:
        """Writes to a JSON file."""
        if not list:
            with open(filename, "r", encoding="utf8") as jsonFile:
                data = json.load(jsonFile)
            data[key] = value
            with open(filename, "w", encoding="utf8") as jsonFile:
                json.dump(data, jsonFile)
        else:
            with open(filename, "r", encoding="utf8") as jsonFile:
                data = json.load(jsonFile)
            if isinstance(a, int):
                key = str(key)
            data[key].append(value)
            with open(filename, "w", encoding="utf8") as jsonFile:
                json.dump(data, jsonFile)
            return data

    def delete(self, filename, key, list=None) -> dict:
        """Deletes a key from the JSON."""
        if not list:
            with open(filename, "r", encoding="utf8") as jsonFile:
                data = json.load(jsonFile)
            del data[str(key)]
            with open(filename, "w", encoding="utf8") as jsonFile:
                json.dump(data, jsonFile)
        else:
            with open(filename, "r", encoding="utf8") as jsonFile:
                data = json.load(jsonFile)
            if isinstance(key, int):
                key = str(key)
            data[key].remove(list)
            with open(filename, "w", encoding="utf8") as jsonFile:
                json.dump(data, jsonFile)
            return data


    def read(self, filename) -> dict:
        """Reads the JSON."""
        with open(filename, encoding="utf8") as f:
            data = json.load(f)
        return data

rethink = Rethink()
jsonio = JSON()
