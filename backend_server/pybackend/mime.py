"""Defines a number of MIMETYPEs for different file formats.

See the following for a more complete list:

  https://www.sitepoint.com/web-foundations/mime-types-complete-list/

"""

import os

MIMETYPES = {
    'mp3': 'audio/mpeg3',
    'ogg': 'audio/ogg',
    'json': 'application/json',
    'wav': 'audio/wav',
    None: 'application/octet-stream'
}


def mimetype_for_file(fname, strict=False):
    fext = os.path.splitext(fname)[-1].strip('.')
    mtype = MIMETYPES.get(fext)
    if mtype is None and not strict:
        mtype = MIMETYPES[None]
    return mtype
