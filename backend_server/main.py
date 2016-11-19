"""Flask Backend Server for managing audio content.

Please see README.md for instructions.

Starting Locally
----------------
You have two options:

  $ python main.py --local --debug

Or, to use GCP backend by default:

  $ dev_appserver.py .


Endpoints
---------
  - /audio/upload : POST
  - /audio/<uri> : GET
  - /annotation/submit : POST
  - /annotation/taxonomy : GET
"""

import argparse
import datetime
from flask import Flask, request, Response
from flask import send_file
from flask_cors import CORS
import io
import json
import logging
import random
import requests
import os

import pybackend.database
import pybackend.mime
import pybackend.storage
import pybackend.utils


logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
CORS(app)

# Set the cloud backend
# TODO: This should be controlled by `app.yaml`, right?
CLOUD_CONFIG = os.path.join(os.path.dirname(__file__), 'gcloud_config.json')
app.config['cloud'] = json.load(open(CLOUD_CONFIG))

SOURCE = "https://cosmir.github.io/open-mic/"


@app.route('/')
def hello():
    return 'oh hai'


@app.route('/audio/upload', methods=['POST'])
def audio_upload():
    """
    To POST files to this endpoint:

    $ curl -F "audio=@some_file.mp3" localhost:8080/audio/upload

    TODOs:
      - Store user data (who uploaded this? IP address?)
      -
    """
    audio_data = request.files['audio']
    bytestring = audio_data.stream.read()

    # Copy to cloud storage
    store = pybackend.storage.Storage(
        project_id=app.config['cloud']['project_id'],
        **app.config['cloud']['storage'])

    uri = str(pybackend.utils.uuid(bytestring))
    fext = os.path.splitext(audio_data.filename)[-1]
    filepath = "{}{}".format(uri, fext)
    store.upload(bytestring, filepath)

    # Index in datastore
    # Keep things like extension, storage platform, mimetype, etc.
    dbase = pybackend.database.Database(
        project_id=app.config['cloud']['project_id'],
        **app.config['cloud']['database'])
    record = dict(filepath=filepath,
                  created=str(datetime.datetime.now()))
    dbase.put(uri, record)
    record.update(
        uri=uri,
        message="Received {} bytes of data.".format(len(bytestring)))

    resp = Response(json.dumps(record), status=200,
                    mimetype=pybackend.mime.MIMETYPES['json'])
    resp.headers['Link'] = SOURCE
    return resp


@app.route('/audio/<uri>', methods=['GET'])
def audio_download(uri):
    """
    To GET responses from this endpoint:

    $ curl -XGET localhost:8080/audio/bbdde322-c604-4753-b828-9fe8addf17b9
    """

    dbase = pybackend.database.Database(
        project_id=app.config['cloud']['project_id'],
        **app.config['cloud']['database'])

    entity = dbase.get(uri)
    if entity is None:
        msg = "Resource not found: {}".format(uri)
        app.logger.info(msg)
        resp = Response(
            json.dumps(dict(message=msg)),
            status=404)

    else:
        store = pybackend.storage.Storage(
            project_id=app.config['cloud']['project_id'],
            **app.config['cloud']['storage'])

        data = store.download(entity['filepath'])
        app.logger.debug("Returning {} bytes".format(len(data)))

        resp = send_file(
            io.BytesIO(data),
            attachment_filename=entity['filepath'],
            mimetype=pybackend.mime.mimetype_for_file(entity['filepath']))

    resp.headers['Link'] = SOURCE
    return resp


@app.route('/annotation/submit', methods=['POST'])
def annotation_submit():
    """
    To POST data to this endpoint:

    $ curl -H "Content-type: application/json" \
        -X POST localhost:8080/annotation/submit \
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

    resp = Response(
        data, status=status, mimetype=pybackend.mime.MIMETYPES['json'])
    resp.headers['Link'] = SOURCE
    return resp


def get_taxonomy():
    tax_url = ("https://raw.githubusercontent.com/marl/jams/master/jams/"
               "schemata/namespaces/tag/medleydb_instruments.json")
    res = requests.get(tax_url)
    values = []
    try:
        schema = res.json()
        values = schema['tag_medleydb_instruments']['value']['enum']
    except BaseException as derp:
        app.logger.error("Failed loading taxonomy: {}".format(derp))

    return values


@app.route('/annotation/taxonomy', methods=['GET'])
def annotation_taxonomy():
    """
    To fetch data at this endpoint:

    $ curl -X GET localhost:8080/annotation/taxonomy
    """
    instruments = get_taxonomy()
    status = 200 if instruments else 400

    resp = Response(json.dumps(instruments), status=status)
    resp.headers['Link'] = SOURCE
    return resp


@app.route('/task', methods=['GET'])
def next_task():
    """
    To fetch data at this endpoint:

    $ curl -X GET localhost:8080/task
    """
    urls = ["/static/wav/paris.wav",
            "/static/wav/spectrogram_demo_doorknock_mono.wav"]
    task = dict(feedback="none",
                visualization='spectrogram',
                proximityTag=[],
                annotationTag=get_taxonomy(),
                url=random.choice(urls),
                numRecordings=10,
                recordingIndex=random.randint(0, 10),
                tutorialVideoURL="https://www.youtube.com/embed/Bg8-83heFRM",
                alwaysShowTags=True)
    resp = Response(json.dumps(dict(task=task)))
    resp.headers['Link'] = SOURCE
    return resp


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Port on which to serve.")
    parser.add_argument(
        "--local",
        action='store_true', help="Use local backend services.")
    parser.add_argument(
        "--debug",
        action='store_true',
        help="Run the Flask application in debug mode.")

    args = parser.parse_args()

    if args.local:
        config = os.path.join(os.path.dirname(__file__), 'local_config.json')
        app.config['cloud'] = json.load(open(config))

    app.run(debug=args.debug, port=args.port)
