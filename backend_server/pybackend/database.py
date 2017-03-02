"""Client interfaces for local and backend (NoSQL) databases.

Example
-------
>>> import pybackend.database as D
>>> dbase = D.Database(project='my-fun-project',
                       backend=S.LOCAL, filepath='my-db.json',
                       mode=D.APPEND, atomic=True)
>>> key = "my_song"
>>> record = dict(a=15, b=['heya', 'hihi'])
>>> dbase.put(key, record)
>>> print(dbase.get(key))
{'a': 15, 'b': ['heya', 'hihi']}
"""

import json
from google.cloud import datastore
import os

from . import GCLOUD, LOCAL
from . import urilib

# Start clean
WRITE = 'w'
# Load any existing data
APPEND = 'a'
# Immutable / write-safe
READ = 'r'


class QueryResult(object):

    def __init__(self, db, key_gen):
        self.key_gen = key_gen
        self.db = db
        self._keys_only = False

    def filter_keys(self):
        self._keys_only = True

    def __iter__(self):
        return self

    def __next__(self):
        for key in self.key_gen:
            if self._keys_only:
                return key
            else:
                # TODO: Check that this maintains parity with DataStore
                return self.db.get(key)


class LocalClient(object):
    """A "local" JSON backed database object.

    TODO: Can / could use a slightly smarter backend to easily mimic the
    functionality we'll need (multiple indexing), e.g. pandas, mongo, etc.
    """

    def __init__(self, project, filepath='', mode=APPEND, atomic=True):
        """Create a local database client.

        Parameters
        ----------
        project : str
            Unique identifier for the owner of this storage object.

        filepath : str
            Path on disk for writing the persistent database JSON.

        mode : str, default='a'
            File mode for accessing the "database", one of
             * 'r': read only
             * 'w': write; overwrites the existing file
             * 'a': append; will attempt to add to the current database.

        atomic : bool, default=True
            If True, will flush the database to disk on every `put` operation.
            Trades performance / speed for guarantees that all data is written.
        """
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
        """Flush all changes to disk."""
        write_conds = [self.mode in [WRITE, APPEND],
                       bool(self._filepath)]
        if all(write_conds):
            with open(self._filepath, 'w') as fp:
                json.dump(self._collection, fp)

    def get(self, uri):
        """Get the record for the given URI."""
        urilib.validate(uri)
        return self._collection.get(uri)

    def put(self, uri, record, atomic=False):
        """Store a record under the given URI.

        Parameters
        ----------
        uri : str
            URI under which to write the record.

        record : dict
            Dictionary object to write.
        """
        urilib.validate(uri)
        # What happens if `uri` is in self._collection?
        self._collection[uri] = record
        if self.atomic or atomic:
            self.flush()

    def delete(self, uri):
        """Delete the record for a given URI.

        Parameters
        ----------
        uri : str
            URI to delete. Passes quietly if URI does not exist.
        """
        urilib.validate(uri)
        if uri in self._collection:
            self._collection.pop(uri)

    def uris(self, kind=None):
        """Returns an iterator over the URIs in the Client.

        Parameters
        ----------
        kind : str, default=None
            Optionally filter over the URI kind in the database.

        Yields
        ------
        uri : str
            A URI in the collection.
        """
        for uri in self._collection.keys():
            if kind is None or kind == urilib.split(uri)[0]:
                yield uri

    def query(self, filter=None):
        key_gen = self.uris()
        if filter:
            name, value = filter
            if name == 'kind':
                key_gen = self.uris(kind=value)
        return QueryResult(self, key_gen)


class GClient(object):
    """Thin wrapper for gcloud's DataStore client.

    Notes:
    - We use a URI format (<kind>:<gid>) to pass DataStore "kinds" around.
      This doesn't allow us to hierarchically nest keys, which DS makes
      possible, but we *probably* won't need to leverage this functionality.
    - The put/get interface for Google's native Datastore client requires
      some wrangling in terms of how Key objects are constructed. This
      interface serves to abstract that behavior away.
    """

    def __init__(self, project):
        """Create a GCP Datastore client.

        Parameters
        ----------
        project : str
            Unique identifier for the owner of this storage object.
        """
        self.project = project

    @property
    def _client(self):
        return datastore.Client(self.project)

    def get(self, uri):
        """Return a record for the given URI."""
        kind, gid = urilib.split(uri)
        key = self._client.key(kind, gid)
        return dict(**self._client.get(key))

    def put(self, uri, record, exclude_from_indexes=None):
        """Put a record into the database."""
        exclude_from_indexes = exclude_from_indexes or []

        # Create Entity from record + key
        kind, gid = urilib.split(uri)
        key = self._client.key(kind, gid)

        entity = datastore.Entity(
            key, exclude_from_indexes=exclude_from_indexes)
        entity.update(record)
        self._client.put(entity)

    def uris(self, kind=None):
        """Iterator over the URIs in the database.

        Parameters
        ----------
        kind : str, default=None
            Optionally filter over the URI kind in the database.

        Yields
        ------
        uri : str
            A URI in the collection.
        """
        kwargs = dict()
        if kind:
            kwargs.update(kind=kind)
        query = self._client.query(**kwargs)

        # Sets a filter in-place on the query to return keys.
        query.keys_only()
        for v in query.fetch():
            yield urilib.join(v.kind, v.key.name)


BACKENDS = {
    GCLOUD: GClient,
    LOCAL: LocalClient
}


def Database(project, backend, **kwargs):
    """Factory constructor for different database backends.

    Parameters
    ----------
    project : str
        Unique identifier for the owner of this storage object.

    backend : str, default='gcloud'
        Backend storage platform to use, one of ['local', 'gcloud'].

    **kwargs : Additional arguments to pass through to the different backends.
    """
    return BACKENDS[backend](project, **kwargs)
