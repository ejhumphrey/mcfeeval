#!/usr/bin/env python
"""Run a local demo of the server-annotator system.

Performs the following:
- Starts the CMS server
- Uploads some audio content
- Restarts the CMS server
- Holds until the user shuts down the demo.

Note: It is advisable to use a private / incognito browser session to avoid
caching behavior, which can cause the web app to use stale source files.
"""
from __future__ import print_function

import argparse
import atexit
from builtins import input
import logging
import os
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import signal
import subprocess

SERVER_PORT = 8080
PROCESSES = []


def kill(*proccesses):
    """Kills a list of processes.

    Parameters
    ----------
    processes: list
        List of process ids to be killed.
    """
    for proc in proccesses:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)


@atexit.register
def kill_all():
    kill(*PROCESSES)


def launch_cms(port, noauth=False, max_retries=8):
    """Thin wrapper around kick-starting the CMS server.

    Parameters
    ----------
    port : int
        Port for running the server locally.

    noauth : bool, default=False
        If True, do not use authentication.

    Returns
    -------
    pid : int
        Process ID of the server.
    """
    flags = ['--debug']
    if noauth:
        flags += ['--noauth']

    cmd = "python {} --port {} --config {} {}".format(
        os.path.join('backend_server', 'main.py'), port,
        os.path.join('backend_server', '.config.yaml'), " ".join(flags))
    logging.info("server: {}".format(cmd))
    server = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE,
                              preexec_fn=os.setsid)

    # Test that the server is on; will raise an exception after enough attempts
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(total=max_retries,
                                            backoff_factor=0.1))
    session.mount('http://', adapter)
    try:
        session.get('http://localhost:{}'.format(port))
    except requests.exceptions.ConnectionError:
        kill(server)
        raise EnvironmentError(
            "Unable to confirm that the server started successfully.")
    return server


def run(port):
    """Main process to run the demo.

    Parameters
    ----------
    port: int
        Server port number.
    """
    # Some sanity checks
    if not os.path.isdir("backend_server"):
        raise EnvironmentError(
            "This script must be launched from OpenMic's root directory.")
    if not os.path.isdir("audio-annotator"):
        raise EnvironmentError("Audio Annotator not found: please run:\n\t"
                               "git submodule update --init")

    # Run the server
    server = launch_cms(port, noauth=True)

    # Upload audio to the server
    fnames = ["267508__mickleness__3nf.ogg",
              "345515__furbyguy__strings-piano.ogg"]
    for fn in fnames:
        # Upload audio
        fpath = os.path.abspath(os.path.join('data', 'audio', fn))
        resp = requests.post('http://localhost:{}/api/v0.1/audio'.format(port),
                             files=dict(audio=open(fpath, 'rb')))

        # Build a task over it
        requests.post(
            'http://localhost:{}/api/v0.1/task'.format(port),
            json=dict(uri=resp.json()['uri'],
                      taxonomy='instrument_taxonomy_v0',
                      feedback='none', visualization='waveform'))
    kill(server)

    # Run the two servers
    PROCESSES.append(launch_cms(port, noauth=False))
    logging.info("Now serving at: http://localhost:{}".format(port))
    try:
        input("Press return to exit.\n")
    except KeyboardInterrupt:
        # Capturing Ctrl-C, to make sure we always shutdown the server
        pass
    logging.info("Shutting down server")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Run a local demo of the server-annotator system.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-p",
                        dest="port",
                        default=SERVER_PORT,
                        type=int,
                        help="Server port number")
    args = parser.parse_args()

    # Setup the logger
    logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                        level=logging.INFO)

    # Call main process
    run(args.port)
