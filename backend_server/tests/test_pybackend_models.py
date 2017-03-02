import pytest
import json
import pybackend.models as M


def test_BaseRecord___init__():
    rec = M.BaseRecord()
    assert len(rec.serialized_keys) == 0


class DummyRecord(M.BaseRecord):
    serialized_keys = ['a']


def test_DummyRecord_flatten():
    a = dict(x=13, y=['d', 'e', 'f'])
    b = "fluflu"
    rec = DummyRecord(a=a, b=b)
    flatrec = rec.flatten()

    assert isinstance(flatrec['a'], str)
    assert isinstance(rec['a'], dict)
    assert flatrec['b'] == rec['b'] == b


def test_DummyRecord_expand():
    a = dict(x=13, y=['d', 'e', 'f'])
    aflat = json.dumps(a)
    b = "fluflu"

    rec = DummyRecord.from_flat(**{'a': aflat, 'b': b})
    assert rec['a'] == a
    assert rec['b'] == b


def test_AnnotationResponse_template():
    annot = M.AnnotationResponse.template(
        user_id="spotify:user:rockstr123",
        task_uri='task:abc123',
        request_uri='request:xyz123',
        response=dict(labels=['a', 'b']))
    assert annot is not None
    assert 'created' in annot


def test_Task_template():
    annot = M.Task.template(
        audio_uri='audio:123',
        source=dict(uri='audio:345', time=0.0, duration=10.0),
        taxonomy='instrument_taxonomy_v0', feedback='none',
        visualization='waveform')
    assert annot is not None
    for k in ['created', 'priority', 'payload']:
        assert k in annot


def test_TaskRequest_template():
    annot = M.TaskRequest.template(
        user_id="spotify:user:rockstr123",
        task_uri='task:abc123',
        expires=300)
    assert annot is not None
    assert annot['expires'] > annot['created']
