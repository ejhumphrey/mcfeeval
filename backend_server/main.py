"""Flask Backend Server for managing audio content.

Please see README.md for instructions.

Starting Locally
----------------
You have two options:

  $ python main.py --port 8080 --local --debug

Or, to use GCP backend by default:

  $ dev_appserver.py .


Endpoints
---------
  - /audio : POST
  - /audio/<uri> : GET
  - /annotation/submit : POST
  - /annotation/taxonomy : GET
"""
import argparse
import datetime
import io
import json
import logging
import mimetypes
import os
import requests
import yaml

from flask import Flask, Response, request, send_file
from flask import session, redirect, url_for, jsonify, render_template
from functools import wraps

import pybackend

# Python 2.7 doesn't ship with `.json`?
mimetypes.add_type(mimetypes.guess_type("x.json")[0], '.json')
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = 'development'

SOURCE = "https://cosmir.github.io/open-mic/"
AUDIO_EXTENSIONS = set(['wav', 'ogg', 'mp3', 'au', 'aiff'])
MAX_SUBMISSION_ATTEMPTS = 5
OAUTH = None


def configure(cfg):
    """Configure the (singleton) application object.

    TODO: Should yell if `cfg` is malformed.

    Parameters
    ----------
    cfg : dict
        Object containing configuration info.
    """
    app.static_folder = cfg['annotator']['static_folder']
    app.config.update(cloud=cfg['cloud'], oauth=cfg['oauth'])
    global OAUTH
    OAUTH = pybackend.oauth.OAuth(app, session)


# Default configuration
CONFIG = os.path.join(os.path.dirname(__file__), '.config.yaml')
with open(CONFIG) as fp:
    cfg = yaml.load(fp)
    configure(cfg)


def authenticate(f):
    """Decorate a route as requiring authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        app.logger.info(session)
        if any([app.config.get('noauth', False),
                session.get(pybackend.oauth.TOKEN, None)]):
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login', _external=True))

    return decorated


@app.route('/login')
@app.route('/login/<app_name>')
def login(app_name='spotify'):
    """Start the OAuth login process.

    Query Parameters
    ----------------
    complete : {yes, no}, default=yes
        Direct the OAuth login process to complete; must be 'no' in order to
        allow commandline interfaces to successfully authenticate.
    """
    app_name = app_name.lower()
    callback = url_for('authorized', app_name=app_name, _external=True)
    query = ""
    if request.args.get('complete', 'yes') == 'no':
        query += "?complete=no"
    return OAUTH.get(app_name).client.authorize(callback + query)


@app.route('/login/authorized/<app_name>')
def authorized(app_name='spotify'):
    """Finish the OAuth login process.

    This is the callback endpoint registered with different OAuth handlers. For
    commandline interfaces, which require manual intervention, the complete=no
    parameter must be passed through the login redirect route.

    TODO: Update this to a more appropriate response once the annotator is
    updated.

    Query Parameters
    ----------------
    complete : {yes, no}, default=yes
        Direct the OAuth login process to complete; must be 'no' in order to
        allow commandline interfaces to successfully authenticate.
    """
    app.logger.info("{}".format(request))
    app_name = app_name.lower()
    if request.args.get('complete', 'yes') == 'yes':
        oauthor = OAUTH.get(app_name)
        resp = oauthor.client.authorized_response()
        app.logger.info(resp)
        if resp is None:
            return ('Access denied: reason={error_reason} '
                    'error={error_description}'.format(**request.args))

        # TODO: Cannot access `oauthor.uri` until after the session token has
        #       been set ... :thinkingface:
        session[pybackend.oauth.TOKEN] = (resp['access_token'], app_name)
        session[pybackend.oauth.TOKEN] = (resp['access_token'], app_name,
                                          oauthor.uri)
        app.logger.info("current_user: {}".format(oauthor.user))
        return redirect(url_for('index'))
    else:
        return ("To complete log-in, proceed to this URL: {}"
                .format(request.url))


@app.route('/logout')
def logout():
    """Log the user out of the current session.

    TODO: Update this to a more appropriate response once the annotator is
    updated.
    """
    token = session.pop(pybackend.oauth.TOKEN, None)
    return "Success!" if token else "Not currently logged in."


@app.route("/")
@authenticate
def index():
    """Main entry point for the annotation application."""
    return render_template("index.html")


@app.route("/me")
@authenticate
def me():
    """Demonstrate that the user has been successfully logged in."""
    token = session.get(pybackend.oauth.TOKEN)
    app.logger.debug(str(token))
    if not token:
        return "No user logged in."

    oauthor = OAUTH.get(token[1])
    return jsonify(oauthor.user)


def store_raw_audio(db, store, audio, source=None):
    """Convenience function to store an audio file object through the webapp.

    TODO: This should probably move ... somewhere else? Perhaps inside a
    controller / delegate?

    Parameters
    ----------
    db : pybackend.database.Database
        Interface to the database backend.

    store : pybackend.database.Database
        Interface to the binary storage backend.

    audio : werkzeug.datastructures.FileStorage
        Audio object referenced by a request object, when passed as a file in a
        POST request.

    source : dict, default=None
        Optional source metadata, describing where in another audio file this
        data may have been drawn from.

    Returns
    -------
    record : dict
        Object containing data about the new audio object, including but not
        limited to the `uri`.
        TODO: This response object has drifted on the audio upload branch, and
              should follow that lead.
    """
    file_ext = os.path.splitext(audio.filename)[-1][1:]
    if file_ext not in AUDIO_EXTENSIONS:
        raise ValueError('Attempted upload of unsupported filetype.')

    bytestring = audio.stream.read()
    # Copy to cloud storage
    gid = str(pybackend.utils.uuid(bytestring))
    store.put(gid, bytestring)

    # Index in datastore
    uri = pybackend.urilib.join('audio', gid)
    record = dict(file_ext=file_ext, created=str(datetime.datetime.utcnow()))

    # TODO: Discuss how we want to handle 'sourced' relationships.
    if source:
        record['source'] = source

    db.put(uri, record)
    return dict(uri=uri,
                message="Received {} bytes of data.".format(len(bytestring)))


def fetch_audio_data(db, store, gid):
    """Convenience function to retrieve audio data through the webapp.

    TODO: This should probably move ... somewhere else? Perhaps inside a
    controller / delegate?

    Parameters
    ----------
    db : pybackend.database.Database
        Interface to the database backend.

    store : pybackend.database.Database
        Interface to the binary storage backend.

    gid : str
        A gid, pointing to a unique audio object.

    Returns
    -------
    data : bytes
        Raw bytestring of the audio data.

    file_ext : str
        File extension of the audio bytestream.
    """
    uri = pybackend.urilib.join('audio', gid)
    entity = db.get(uri)
    data, fext = b'', None
    if entity:
        data = store.get(gid)
        app.logger.debug("Downloaded {} bytes".format(len(data)))
        fext = entity['file_ext']
    return data, fext


@app.route('/api/v0.1/audio', methods=['POST'])
@authenticate
def audio_upload():
    """Endpoint for uploading source audio content.

    To POST files to this endpoint:

    $ curl -F "audio=@some_file.mp3" localhost:8080/api/v0.1/audio

    TODOs:
      - Store user data (who uploaded this? IP address?)
      - File metadata
    """
    app.logger.info("Upload request from {}".format(request.remote_addr))
    audio = request.files['audio']
    store = pybackend.storage.Storage(
        project=app.config['cloud']['project'],
        **app.config['cloud']['storage'])
    db = pybackend.database.Database(
        project=app.config['cloud']['project'],
        **app.config['cloud']['database'])
    try:
        record = store_raw_audio(db, store, audio)
        resp = Response(json.dumps(dict(uri=record['uri'])), status=200,
                        mimetype=mimetypes.types_map[".json"])
    except ValueError as derp:
        resp = Response(
            json.dumps(dict(message=str(derp))),
            status=requests.status_codes.codes.BAD_REQUEST,
            mimetype=mimetypes.types_map[".json"])
    finally:
        resp.headers['Link'] = SOURCE
        return resp


@app.route('/api/v0.1/audio/<gid>', methods=['GET'])
@authenticate
def audio_download(gid):
    """
    To GET responses from this endpoint:

    $ curl -XGET "localhost:8080/api/v0.1/audio/
        bbdde322-c604-4753-b828-9fe8addf17b9"
    """
    store = pybackend.storage.Storage(
        project=app.config['cloud']['project'],
        **app.config['cloud']['storage'])
    db = pybackend.database.Database(
        project=app.config['cloud']['project'],
        **app.config['cloud']['database'])
    data, fext = fetch_audio_data(db, store, gid)
    if data:
        # TODO: can this use a FileStorage object also?
        filename = os.path.extsep.join([gid, fext])
        resp = send_file(
            io.BytesIO(data),
            attachment_filename=filename,
            mimetype=pybackend.utils.mimetype_for_file(filename))
    else:
        msg = "Resource not found: {}".format(gid)
        app.logger.info(msg)
        resp = Response(
            json.dumps(dict(message=msg)),
            status=404)

    resp.headers['Link'] = SOURCE
    return resp


@app.route('/api/v0.1/annotation', methods=['POST'])
@authenticate
def annotation_submit():
    """
    To POST data to this endpoint:

    $ curl -H "Content-type: application/json" \
        -X POST localhost:8080/annotation \
        -d '{"request_id": "xyz", "tags": ["a"]}'
    """
    if request.headers['Content-Type'] != 'application/json':
        raise ValueError("Invalid content type.")

    app.logger.info("Received Annotation:\n{}"
                    .format(json.dumps(request.json, indent=2)))

    user_id = session.get(pybackend.oauth.TOKEN)[2]
    request_gid = request.json['request_id']
    # Fetch the request object and validate this submission.
    request_uri = pybackend.urilib.join('request', request_gid)

    db = pybackend.database.Database(
        project=app.config['cloud']['project'],
        **app.config['cloud']['database'])
    entity = db.get(request_uri)
    if not entity:
        raise ValueError("Invalid `request_id`.")

    task_request = pybackend.models.TaskRequest.from_flat(**entity)
    app.logger.info("Retrieved task: {}".format(task_request))

    # TODO: Each failure should be a status response rather than an exception.
    # TODO: And they should redirect?
    if task_request['user_id'] != user_id:
        raise ValueError("You are not authorized to submit data for this "
                         "request_id.")
    # TODO: Do we want expiration dates to be ints or datetime strings?
    elif task_request['expires'] < int(datetime.datetime.utcnow()
                                       .strftime("%s")):
        raise ValueError(
            "The submission period for this task has expired.")
    # TODO: How many attempts vs the limit
    elif len(task_request['attempts']) > MAX_SUBMISSION_ATTEMPTS:
        raise ValueError("This request has exceeded its valid number of "
                         "submissions.")
    elif task_request['complete']:
        raise ValueError("An annotation has already been accepted for this "
                         "request.")
    # TODO: Does the task have an answer to compare with?
    # TODO: If the response is invalid, log it (in `attempts`) and return

    # Alright! The submission has passed all the tests.
    # Update the Request record
    # TODO: These records should be flattened by default...
    task_request['complete'] = True
    db.put(request_uri, task_request.flatten())

    # Store the annotation
    data = json.dumps(dict(message='Success!'))
    status = 200

    annot = pybackend.models.AnnotationResponse.template(
        response=request.json,
        task_uri=task_request['task_uri'],
        request_uri=request_uri,
        user_id=user_id)

    annot_gid = str(pybackend.utils.uuid(json.dumps(annot)))
    annot_uri = pybackend.urilib.join('annotation', annot_gid)
    db.put(annot_uri, annot.flatten())

    resp = Response(
        data, status=status, mimetype=mimetypes.types_map[".json"])
    resp.headers['Link'] = SOURCE
    return resp


@app.route('/api/v0.1/taxonomy/<key>', methods=['GET'])
def annotation_taxonomy(key):
    """
    To fetch data at this endpoint:

        $ curl -X GET localhost:8080/taxonomy/instrument_taxonomy_v0
    """
    # Break this out into application state. Should at least cache, but
    # probably fetch once.
    instruments = pybackend.taxonomy.get(key)
    status = 200 if instruments else 400

    resp = Response(json.dumps(instruments), status=status)
    resp.headers['Link'] = SOURCE
    return resp


@app.route('/api/v0.1/task', methods=['POST'])
def create_task():
    """Create an annotation 'task' from given metadata.

    TODO: Unclear what the relationship between uploading, trimming, and task
    creation should be here.

    Body Data
    ---------
    uri : str
        URI of the object over which to build a task.

    taxonomy : str, default='instrument_taxonomy_v0'
        A taxonomy key; see `pybackend.taxonomy.get` for more info.

    feedback : str, default='none'

    visualization : str, default=waveform

    Response
    --------
    uri : str
        A URI for the generated task.
    """
    app.logger.info("json: {}".format(request.json))

    db = pybackend.database.Database(
        project=app.config['cloud']['project'],
        **app.config['cloud']['database'])
    uri = request.json.get("uri", None)
    if not uri:
        raise ValueError(
            "'audio_uri' must be specified if no audio is uploaded.")

    # `source` should track provenance information (from whence it came).
    source = dict()
    task = pybackend.models.Task.template(
        audio_uri=uri, source=source,
        taxonomy=request.json.get('taxonomy', 'instrument_taxonomy_v0'),
        feedback=request.json.get('feedback', 'none'),
        visualization=request.json.get('visualization', 'waveform'))

    gid = str(pybackend.utils.uuid(json.dumps(task)))
    task_uri = pybackend.urilib.join('task', gid)

    db.put(task_uri, task.flatten())
    # TODO: Maybe don't return this? depends on who can create them...
    return jsonify(dict(uri=task_uri))


# TODO: It's not clear that we want this route to be public. Or at all.
@app.route('/api/v0.1/task/<gid>', methods=['GET'])
def get_task(gid):
    """
    To fetch data at this endpoint:

    $ curl -X GET localhost:8080/task/<gid>
    """
    db = pybackend.database.Database(
        project=app.config['cloud']['project'],
        **app.config['cloud']['database'])

    uri = pybackend.urilib.join('task', gid)
    entity = db.get(uri)
    if not entity:
        raise ValueError("No task exists for the given gid: {}".format(gid))

    task = pybackend.models.Task.from_flat(**entity)
    audio_url = "api/v0.1/audio/{gid}".format(
        gid=pybackend.urilib.split(task['audio_uri'])[1])

    tax = pybackend.taxonomy.get(task['payload'].pop('taxonomy'))
    data = json.dumps(dict(audio_url=audio_url, taxonomy=tax,
                           **task['payload']))
    app.logger.debug("Returning:\n{}".format(data))
    resp = Response(data)
    resp.headers['Link'] = SOURCE
    return resp


@app.route('/api/v0.1/task', methods=['GET'])
@authenticate
def request_task():
    """Creates a "Request"

    To fetch data at this endpoint:

    $ curl -X GET localhost:8080/api/v0.1/task
    """
    db = pybackend.database.Database(
        project=app.config['cloud']['project'],
        **app.config['cloud']['database'])

    # TODO: Improve task selection logic
    #   - User conditional
    #   - Get the URI of the highest priority task, i.e.
    #         sortby=['priority'], order='descending'
    query = db.query(filter=('kind', 'task'))

    query.filter_keys()
    task_uri = next(query)
    if not task_uri:
        raise ValueError("No tasks exists!")

    # Build a request object
    # TODO: This *should* be sufficiently unique, but some kind of salt / rng
    #       couldn't hurt.
    task_request = pybackend.models.TaskRequest.template(
        user_id=session.get(pybackend.oauth.TOKEN)[2],
        task_uri=task_uri, expires_in=600)

    app.logger.debug("task_request: {}".format(task_request))
    request_gid = str(pybackend.utils.uuid(json.dumps(task_request)))
    request_uri = pybackend.urilib.join('request', request_gid)

    # TODO: Database objects should try to flatten (and maybe expand?) records
    #       on their own.
    db.put(request_uri, task_request.flatten())

    # Retrieve the actual task data & build a unique response.
    # TODO: Give `get` a strict field to raise its own errors. (Flask recovers
    #       from exceptions well, right?)
    entity = db.get(task_uri)
    if not entity:
        # This should never happen, unless a task is deleted between the above
        # query and now.
        raise ValueError("No entity exists for the given uri: {}"
                         "".format(task_uri))

    task = pybackend.models.Task.from_flat(**entity)
    audio_url = "api/v0.1/audio/{gid}".format(
        gid=pybackend.urilib.split(task['audio_uri'])[1])
    app.logger.info("retrieved task: {}".format(task))
    tax = pybackend.taxonomy.get(task['payload'].pop('taxonomy'))
    data = json.dumps(
        dict(request_id=request_gid,
             task=dict(url=audio_url,
                       # This `annotationTag` field is pain waiting to happen.
                       annotationTag=tax,
                       **task['payload'])))
    app.logger.debug("Returning:\n{}".format(data))
    resp = Response(data)
    resp.headers['Link'] = SOURCE
    return resp


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '--host', type=str, default='localhost',
        help='Host address for deployment -- 0.0.0.0 for live')
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Port on which to serve.")
    parser.add_argument(
        "--config", type=str,
        help="Absolute path to a config YAML file.")
    parser.add_argument(
        "--noauth",
        action='store_true', help="Disable authentication, for testing.")
    parser.add_argument(
        "--debug",
        action='store_true',
        help="Run the Flask application in debug mode.")

    args = parser.parse_args()
    app.config['noauth'] = args.noauth
    if args.config:
        cfg_file = os.path.join(args.config)
        with open(cfg_file) as fp:
            cfg = yaml.load(fp)
            configure(cfg)

    app.run(debug=args.debug, host=args.host, port=args.port)
