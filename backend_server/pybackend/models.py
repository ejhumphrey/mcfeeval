import copy
import datetime
import json


class BaseRecord(dict):
    """Data model for records in the database.

    Database technologies in use cannot handle nested objects. Records exist
    to flatten / expand nested fields through JSON serialization.

    To subclass, specify the keys to flatten / expand via the `serialized_keys`
    class variable.

    TODO: `serialized_keys` shouldn't be indexed in DataStore.
    """
    serialized_keys = []

    def flatten(self):
        """Return a flattened view of the object."""
        obj = copy.deepcopy(self)
        obj.update(**{k: json.dumps(v) for k, v in obj.items()
                      if k in self.serialized_keys})
        return obj

    @classmethod
    def from_flat(cls, **kwargs):
        """Create a record from a set of flattened key-value data."""
        kwargs.update(**{k: json.loads(v) for k, v in kwargs.items()
                         if k in cls.serialized_keys})
        return cls(**kwargs)


class AnnotationResponse(BaseRecord):
    serialized_keys = ['response']

    @classmethod
    def template(cls, user_id, task_uri, request_uri, response):
        now = datetime.datetime.utcnow(),
        return cls(user_id=user_id, task_uri=task_uri,
                   created=str(now), request_uri=request_uri,
                   response=response)


class Task(BaseRecord):
    serialized_keys = ['payload', 'source']

    @classmethod
    def template(cls, audio_uri, source, taxonomy,
                 feedback, visualization):
        return cls(
            audio_uri=audio_uri,
            source=source,
            serve_count=0,
            answer_count=0,
            priority=0,
            created=str(datetime.datetime.utcnow()),
            payload=dict(
                feedback=feedback,
                visualization=visualization,
                taxonomy=taxonomy,
                # TODO: maybe remove?
                proximityTag=[],
                alwaysShowTags=True,
                tutorialVideoURL='https://cosmir.github.io',
                # TODO: remove
                numRecordings='?',
                recordingIndex='?')
        )


class TaskRequest(BaseRecord):
    serialized_keys = ['attempts']

    @classmethod
    def template(cls, user_id, task_uri, expires_in):
        now = datetime.datetime.utcnow()
        tdelta = datetime.timedelta(seconds=expires_in)
        return cls(user_id=user_id, task_uri=task_uri,
                   created=str(now),
                   expires=int((now + tdelta).strftime("%s")),
                   attempts=[], complete=False)
