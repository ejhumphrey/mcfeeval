import json
from gcloud import datastore
import os

from . import GCLOUD, LOCAL

# Start clean
WRITE = 'w'
# Load any existing data
APPEND = 'a'
# Immutable / write-safe
READ = 'r'


class LocalClient():
    """    """

    def __init__(self, project_id, filepath='', mode=APPEND, atomic=True):
        self._collection = dict()
        self._filepath = filepath
        self.mode = mode
        self.atomic = atomic
        append_conds = [self.mode in [APPEND, READ],
                        os.path.exists(self._filepath)]
        if all(append_conds):
            with open(self._filepath) as fp:
                loaded_items = json.load(fp)
            self._collection.update(**loaded_items)

    def __del__(self):
        if self._collection is not None:
            self.flush()

    def flush(self):
        write_conds = [self.mode in [WRITE, APPEND],
                       bool(self._filepath)]
        if all(write_conds):
            with open(self._filepath, 'w') as fp:
                json.dump(self._collection, fp)

    def get(self, key):
        return self._collection.get(key)

    def put(self, key, record):
        # What happens if `key` is in self._collection?
        self._collection[key] = record
        if self.atomic:
            self.flush()

    def delete(self, key):
        if key in self._collection:
            self._collection.pop(key)

    def keys(self):
        """Returns an iterator over the keys in the Client."""
        return self._collection.keys()


class GClient(object):
    """Thin wrapper for gcloud's DataStore client"""

    def __init__(self, project_id):
        self.project_id = project_id

    @property
    def _client(self):
        return datastore.Client(self.project_id)

    def get(self, key):
        raise NotImplementedError("Placeholder, needs revisiting.")
        key = self._client.key("key", key)
        return self._client.get(key)

    def put(self, key, record):
        raise NotImplementedError("Placeholder, needs revisiting.")
        # Create Entity from record + key
        key = self._client.key("key", key)
        entity = datastore.Entity(key, exclude_from_indexes=[])
        entity.update(record)
        self._client.put(entity)

    def keys(self):
        raise NotImplementedError("Placeholder, needs revisiting.")
        query = self._client.query()
        query.keys_only()
        return query.fetch()


BACKENDS = {
    GCLOUD: GClient,
    LOCAL: LocalClient
}


def Database(project_id, backend, **kwargs):
    return BACKENDS[backend](project_id, **kwargs)
