"""Consolidated OAuth interfaces to third-party authentication."""

import flask_oauthlib.client as client

GOOGLE = 'google'
SPOTIFY = 'spotify'
TOKEN = 'access_token'


class BaseClient(object):

    # Subclasses should set the common name of the Client.
    NAME = ''

    def __init__(self, oauth, session, client_id, client_secret):
        if not self.NAME:
            raise NotImplementedError(
                "Subclasses must set `NAME` as a class variable")
        self.oauth = oauth
        self.session = session
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = self._build_client()
        self.client.tokengetter(self._tokengetter)

    def _build_client(self):
        raise NotImplementedError("Subclass for third-party apps.")

    @property
    def user(self):
        raise NotImplementedError("Subclass for third-party apps.")

    def _tokengetter(self):
        return self.session.get(TOKEN)


class Google(BaseClient):
    NAME = GOOGLE

    def _build_client(self):
        return self.oauth.remote_app(
            self.NAME,
            consumer_key=self.client_id,
            consumer_secret=self.client_secret,
            request_token_params={'scope': 'email'},
            base_url='https://www.googleapis.com/oauth2/v1/',
            request_token_url=None,
            access_token_method='POST',
            access_token_url='https://accounts.google.com/o/oauth2/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth')

    @property
    def user(self):
        return self.client.get('userinfo').data


class Spotify(BaseClient):
    NAME = SPOTIFY

    def _build_client(self):
        return self.oauth.remote_app(
            self.NAME,
            consumer_key=self.client_id,
            consumer_secret=self.client_secret,
            base_url='https://www.spotify.com/account/',
            authorize_url='https://accounts.spotify.com/authorize?'
                          'scope=user-read-email',
            access_token_url='https://accounts.spotify.com/api/token',
            request_token_url=None,
            request_token_params=dict(show_dialog=True),
            access_token_method='POST')

    @property
    def user(self):
        return self.client.get('https://api.spotify.com/v1/me').data

    @property
    def uri(self):
        return self.user.get("uri", None)


APPS = {
    Google.NAME: Google,
    Spotify.NAME: Spotify,
}


class OAuth(object):

    def __init__(self, app, session):
        """Create a multi-OAuth interface.

        Parameters
        ----------
        app : flask.Flask
            Identifier of the running Flask application.

        session : flask.session
            View of the current session.
        """
        self.oauth = client.OAuth(app)
        self.session = session
        self.apps = dict()
        for name, kwargs in app.config['oauth'].items():
            self.apps[name] = APPS[name](self.oauth, self.session, **kwargs)

    def get(self, name, default=None):
        """Get an interface to a 3rd-party OAuth app, e.g. 'google'."""
        return self.apps.get(name, default)
