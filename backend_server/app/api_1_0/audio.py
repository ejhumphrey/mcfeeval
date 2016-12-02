from . import api
import json
from flask import request


@api.route('/audio/upload', methods=['POST'])
def audio_upload():
    """
    To POST files to this endpoint:

    $ curl -F "audio=@some_file.mp3" localhost:8080/audio/upload

    """
    response = dict(message='nothing happened', status=400)
    if request.method == 'POST':
        afile = request.files['audio']
        audio_bytes = afile.stream.read()
        response['message'] = ("Received {} bytes of data."
                               .format(len(audio_bytes)))
        response['status'] = 200

    return json.dumps(response)
