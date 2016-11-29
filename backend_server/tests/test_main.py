import pytest

from io import BytesIO
import json
import os

import pybackend.utils as utils


@pytest.fixture
def app():
    import main
    config = os.path.join(os.path.dirname(__file__), os.pardir,
                          'local_config.json')
    main.app.config['cloud'] = json.load(open(config, 'r'))
    main.app.testing = True
    return main.app.test_client()


def test_index(app):
    r = app.get('/')
    assert r.status_code == 200


def test_audio_upload(app):
    data = dict(audio=(BytesIO(b'my file contents'), 'blah.wav'))
    r = app.post('/audio/upload', data=data)
    assert r.status_code == 200


def test_audio_upload_bad_request(app):
    r = app.get('/audio/upload')
    assert r.status_code != 405


def test_audio_get(app):
    # First we'll generate data...
    data = dict(audio=(BytesIO(b'my new file contents'), 'blah.wav'))
    r = app.post('/audio/upload', data=data)
    assert r.status_code == 200
    uri = json.loads(r.data.decode('utf-8'))['uri']

    # Now let's go looking for it
    r = app.get('/audio/{}'.format(uri))
    assert r.status_code == 200


def test_audio_get_no_resource(app):
    r = app.get('/audio/{}'.format("definitelydoesntexist"))
    assert r.status_code == 404


def test_audio_post_fails(app):
    data = dict(audio=(BytesIO(b'my new file contents'), 'blah.wav'))
    r = app.post('/audio/{}'.format("abc"), data=data)
    assert r.status_code == 405


def test_annotation_submit(app):
    r = app.post('/annotation/submit',
                 data=json.dumps(dict(foo='bar')),
                 content_type='application/json')
    assert r.status_code == 200


@pytest.mark.skipif(not utils.check_connection(), reason='No internet')
def test_annotation_taxonomy(app):
    r = app.get('/annotation/taxonomy')
    assert r.status_code == 200
