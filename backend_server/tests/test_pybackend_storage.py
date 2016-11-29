import pytest
import os

import pybackend.storage as S


def test_LocalData___init__(tmpdir):
    assert S.LocalData('foo', str(tmpdir)) is not None


def test_LocalData_path(tmpdir):
    name = 'foobar'
    ldata = S.LocalData(name, str(tmpdir))
    assert ldata.path.endswith(name)


def test_LocalBlob_upload_from_string(tmpdir):
    blob = S.LocalBlob('foobaz.json', str(tmpdir))
    sdata = b"hooo boy, hooeee"
    blob.upload_from_string(sdata, "application/octet-stream")
    assert os.path.exists(blob.path)


def test_LocalBlob_download_as_string(tmpdir):
    blob = S.LocalBlob('foobaz.json', str(tmpdir))
    sdata = b"hooo boy, hooeee"
    blob.upload_from_string(sdata, "application/octet-stream")
    assert blob.download_as_string() == sdata


def test_LocalBucket_blob(tmpdir):
    bucket = S.LocalBucket('foobizbaz', str(tmpdir))
    key = "barbar.json"
    blob = bucket.blob(key)
    assert os.path.exists(bucket.path)
    assert blob.path.endswith(key)


def test_LocalBucket_get_blob(tmpdir):
    bucket = S.LocalBucket('foobizbaz', str(tmpdir))
    key = "barbar.json"
    blob = bucket.blob(key)
    assert os.path.exists(bucket.path)
    assert blob.path.endswith(key)

    blob2 = bucket.get_blob(key)
    assert blob2


def test_LocalClient___init__(tmpdir):
    assert S.LocalClient('my-project', str(tmpdir))


def test_LocalClient_get_bucket(tmpdir):
    client = S.LocalClient('my-project', str(tmpdir))
    bucket = client.get_bucket('fluflu')
    assert bucket
    assert isinstance(bucket, S.LocalBucket)


def test_Storage___init__(tmpdir):
    assert S.Storage('blah-blah', 'my-project', backend=S.GCLOUD)
    with pytest.raises(ValueError):
        S.Storage('blah-blah', 'my-project', backend=S.LOCAL)
    assert S.Storage('blah-blah', 'my-project', backend=S.LOCAL,
                     local_dir=str(tmpdir))


def test_Storage_client(tmpdir):
    store = S.Storage('blah-blah-1234', 'my-project-2', backend=S.LOCAL,
                      local_dir=str(tmpdir))
    assert store.client
    assert isinstance(store.client, S.LocalClient)


def test_Storage_upload(tmpdir):
    store = S.Storage('blah-blah-5678', 'my-project-3', backend=S.LOCAL,
                      local_dir=str(tmpdir))
    store.upload(b"hello darkness my old friend", 'song')
