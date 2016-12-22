"""Flask Backend Server for managing audio content.

SCRATCH SPACE WHILE FIGURING OUT HOW TO APPENGINE

Deploying to AppEngine
----------------------
1. Install deps
  $ pip install .[appengine] -t lib

2. Deploy to AppEngine
  # py2.7
  $ appcfg.py -A <PROJECT_ID> -V <version> update appengine.yaml

  # py2.7/3.4 flex, can only be deployed in US?
  $ gcloud app deploy -v v1

Endpoints
---------
  - /audio : POST
  - /audio/<uri> : GET
  - /annotation/submit : POST
  - /annotation/taxonomy : GET
"""
from __future__ import print_function

import argparse
import datetime
from flask import Flask, request, Response
from flask import send_file
import io
import json
import logging
import mimetypes
import requests
import os


import pybackend.database
import pybackend.storage
import pybackend.utils


logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

# Set the cloud backend
# TODO: This should be controlled by `app.yaml`, right?
CLOUD_CONFIG = os.path.join(os.path.dirname(__file__), 'gcloud_config.json')
app.config['cloud'] = json.load(open(CLOUD_CONFIG))

SOURCE = "https://cosmir.github.io/open-mic/"
AUDIO_EXTENSIONS = set(['wav', 'ogg', 'mp3', 'au', 'aiff'])

# Python 2.7 doesn't ship with `.json`?
mimetypes.add_type(mimetypes.guess_type("x.json")[0], '.json')


@app.route('/', methods=['GET'])
def index():
    return "we on"


@app.route('/api/v0.1/audio', methods=['POST'])
def audio_upload():
    """
    To POST files to this endpoint:

    $ curl -F "audio=@some_file.mp3" localhost:8080/api/v0.1/audio

    TODOs:
      - Store user data (who uploaded this? IP address?)
      - File metadata
    """
    audio_data = request.files['audio']
    file_ext = os.path.splitext(audio_data.filename)[-1][1:]
    if file_ext not in AUDIO_EXTENSIONS:
        logging.exception('Attempted upload of unsupported filetype.')
        return 'Filetype not supported.', 400

    bytestring = audio_data.stream.read()
    app.logger.info("Uploaded data: type={}, len={}"
                    .format(type(bytestring), len(bytestring)))

    # Copy to storage
    store = pybackend.storage.Storage(
        project_id=app.config['cloud']['project_id'],
        **app.config['cloud']['storage'])

    uri = str(pybackend.utils.uuid(bytestring))
    filepath = os.path.extsep.join([uri, file_ext])
    store.upload(bytestring, filepath)

    # Index in datastore
    # Keep things like extension, storage platform, mimetype, etc.
    # dbase = pybackend.database.Database(
    #     project_id=app.config['cloud']['project_id'],
    #     **app.config['cloud']['database'])
    record = dict(filepath=filepath,
                  created=str(datetime.datetime.now()))
    # dbase.put(uri, record)
    # record.update(
    #     uri=uri,
    #     message="Received {} bytes of data.".format(len(bytestring)))

    resp = Response(json.dumps(record), status=200,
                    mimetype=mimetypes.types_map[".json"])
    resp.headers['Link'] = SOURCE
    return resp


@app.route('/api/v0.1/audio/<uri>', methods=['GET'])
def audio_download(uri):
    """
    To GET responses from this endpoint:

    $ curl -XGET localhost:8080/audio/bbdde322-c604-4753-b828-9fe8addf17b9
    """

    # dbase = pybackend.database.Database(
    #     project_id=app.config['cloud']['project_id'],
    #     **app.config['cloud']['database'])

    # entity = dbase.get(uri)
    # if entity is None:
    #     msg = "Resource not found: {}".format(uri)
    #     app.logger.info(msg)
    #     resp = Response(
    #         json.dumps(dict(message=msg)),
    #         status=404)

    # else:
    store = pybackend.storage.Storage(
        project_id=app.config['cloud']['project_id'],
        **app.config['cloud']['storage'])

    data = store.download(uri)
    app.logger.debug("Returning {} bytes".format(len(data)))

    resp = send_file(
        io.BytesIO(data),
        attachment_filename=uri,
        mimetype=mimetypes.types_map[".json"])

    resp.headers['Link'] = SOURCE
    return resp


@app.route('/api/v0.1/annotation/submit', methods=['POST'])
def annotation_submit():
    """
    To POST data to this endpoint:

    $ curl -H "Content-type: application/json" -X POST \
        http://{version}-{PROJECT_ID}.appspot.com/api/v0.1/annotation/submit \
        -d '{"message":"Hello Data"}'
    """

    if request.headers['Content-Type'] == 'application/json':
        app.logger.info("Received Annotation:\n{}"
                        .format(json.dumps(request.json, indent=2)))
        # obj = json.loads(request.data)
        data = json.dumps(dict(message='Success!'))
        status = 200

    else:
        status = 400
        data = json.dumps(dict(message='Invalid Content-Type; '
                                       'only accepts application/json'))

    resp = Response(data, status=status,
                    mimetype=mimetypes.types_map[".json"])
    resp.headers['Link'] = SOURCE
    return resp


@app.route('/api/v0.1/annotation/taxonomy', methods=['GET'])
def annotation_taxonomy():
    """
    To fetch data at this endpoint:

    $ curl -X GET localhost:8080/annotation/taxonomy

    TODO: Clean this up per @alastair's feedback.
    """
    data = json.dumps(dict(message='Resource not found'))
    status = 404

    tax_url = ("https://raw.githubusercontent.com/marl/jams/master/jams/"
               "schemata/namespaces/tag/medleydb_instruments.json")
    res = requests.get(tax_url)
    if res.text:
        data = json.loads(res.text)
        status = 200

    resp = Response(data, status=status)
    resp.headers['Link'] = SOURCE
    return resp


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500