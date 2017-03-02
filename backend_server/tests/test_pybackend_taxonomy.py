import pytest

import pybackend.taxonomy as T
import pybackend.utils as utils


@pytest.mark.skipif(not utils.check_connection(), reason='no internetz')
def test_fetch():
    for key in T.KEYS:
        assert T.fetch(key)


@pytest.mark.skipif(not utils.check_connection(), reason='no internetz')
def test_get():
    key = T.KEYS[0]
    assert key not in T.TYPES
    assert T.get(key)
    assert T.TYPES[key]
