import requests

TYPES = dict()
KEYS = ['instrument_taxonomy_v0']


def fetch(key):
    tax_url = ("https://raw.githubusercontent.com/cosmir/open-mic/"
               "master/data/{}.json".format(key))
    res = requests.get(tax_url)
    schema = res.json()
    return schema['tag_open_mic_instruments']['value']['enum']


def get(key):
    if key not in TYPES:
        TYPES[key] = fetch(key)
    return TYPES[key]
