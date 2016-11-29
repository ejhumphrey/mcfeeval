import pytest

import pybackend.utils


def test_utils_uuid():
    data = 'blahblah'
    uuid1 = pybackend.utils.uuid(data)
    assert uuid1 == pybackend.utils.uuid(data)
    assert uuid1 != pybackend.utils.uuid('foobar')
