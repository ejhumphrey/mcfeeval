from gcloud import storage
import io
import logging
import os

from . import GCLOUD, LOCAL

logger = logging.getLogger(__name__)


def _makedirs(dpath):
    if not os.path.exists(dpath):
        os.makedirs(dpath)
    return dpath


class LocalData(object):

    def __init__(self, name, root):
        self.name = name
        self.root = root

    @property
    def path(self):
        return os.path.join(self.root, self.name)


class LocalBlob(LocalData):

    def upload_from_string(self, bstream, content_type):
        """Upload data as a bytestring.

        Parameters
        ----------
        bstream : bytes
            Bytestring to upload.

        content_type : str
            Not used; preserved for consistency with gcloud.storage.
        """
        # obj = dict(bstream=bstream, content_type=content_type)
        with open(self.path, 'wb') as fp:
            fp.write(bstream)

    def download_as_string(self):
        """Upload data as a bytestring.

        Returns
        -------
        bstream : bytes
            Bytestring format of the data.
        """
        with open(self.path, 'rb') as fp:
            fdata = fp.read()
        return fdata


class LocalBucket(LocalData):

    def __init__(self, name, root):
        super(LocalBucket, self).__init__(name, root)

    def blob(self, name):
        return LocalBlob(name, root=_makedirs(self.path))

    def get_blob(self, name):
        return LocalBlob(name, root=self.path)


class LocalClient(object):

    def __init__(self, project_id, root_dir):
        self.project_id = project_id
        self.root_dir = _makedirs(root_dir)

    def get_bucket(self, name):
        return LocalBucket(name=name, root=self.root_dir)


BACKENDS = {
    GCLOUD: storage.Client,
    LOCAL: LocalClient
}


class Storage(object):

    def __init__(self, name, project_id, backend=GCLOUD,
                 local_dir=None):
        if backend == LOCAL and local_dir is None:
            raise ValueError(
                "`local_dir` must be given if backend is '{}'".format(LOCAL))
        self.name = name
        self.project_id = project_id
        self._backend = backend
        self._backend_kwargs = dict(project_id=project_id)
        if self._backend == LOCAL:
            self._backend_kwargs.update(
                root_dir=os.path.abspath(os.path.expanduser(local_dir)))

    @property
    def client(self):
        return BACKENDS[self._backend](**self._backend_kwargs)

    def upload(self, fdata, key):
        """Upload a local file to GCS.

        Parameters
        ----------
        fdata : str
            File's bytestream.

        key : str
            Key for writing the file data.

        Returns
        -------
        nothing?
            Not sure what a sane response object is here.
        """
        logger.debug("Uploading {} bytes to {}.".format(len(fdata), key))
        bucket = self.client.get_bucket(self.name)
        blob = bucket.blob(key)
        blob.upload_from_string(fdata, content_type="application/octet-stream")
        return

    def download(self, key):
        bucket = self.client.get_bucket(self.name)
        blob = bucket.get_blob(key)
        return blob.download_as_string()
