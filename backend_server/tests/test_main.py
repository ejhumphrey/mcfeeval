import pytest

from io import BytesIO
import json


@pytest.fixture
def app():
    import main
    main.app.testing = True
    return main.app.test_client()


def test_index(app):
    r = app.get('/')
    assert r.status_code == 200


def test_audio_upload(app):
    data = dict(audio=(BytesIO(b'my file contents'), 'blah.wav'))
    r = app.post('/audio/upload', data=data)
    assert r.status_code == 200


def test_annotation_submit(app):
    r = app.post('/annotation/submit',
                 data=json.dumps(dict(foo='bar')),
                 content_type = 'application/json')
    assert r.status_code == 200


def test_annotation_taxonomy(app):
    r = app.get('/annotation/taxonomy')
    assert r.status_code == 200