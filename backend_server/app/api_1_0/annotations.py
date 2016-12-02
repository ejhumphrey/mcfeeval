from . import api
import json
import requests
from flask import request

print(test)
@api.route('/annotation/taxonomy', methods=['GET'])
def annotation_taxonomy():
    """
    To fetch data at this endpoint:

    $ curl -X GET localhost:8080/annotation/taxonomy
    """
    # tax_url = ("https://raw.githubusercontent.com/marl/jams/master/jams/"
    #            "schemata/namespaces/tag/medleydb_instruments.json")
    # res = requests.get(tax_url)
    # tax = {}
    # if res.text:
    #     tax = json.loads(res.text)
    #
    # return json.dumps(tax)
    return 'test'


@api.route('/annotation/submit', methods=['POST'])
def annotation_submit():
    """
    To POST data to this endpoint:

    $ curl -H "Content-type: application/json" \
        -X POST localhost:8080/annotation/submit \
        -d '{"message":"Hello Data"}'
    """
    response = dict(message='nothing happened', status=400)
    conds = [request.method == 'POST',
             request.headers['Content-Type'] == 'application/json']
    if all(conds):
        print(request.json)
        # obj = json.loads(request.data)
        response['message'] = ("Received JSON data! {}".format(request.json))
        response['status'] = 200

    return json.dumps(response)
