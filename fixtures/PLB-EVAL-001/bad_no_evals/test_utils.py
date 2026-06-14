"""The knife-edge: a test file exists, but it tests an unrelated helper, NOT the
model paths. 'A test exists' is not 'the model is evaluated' — EVAL-001 fires."""
from slugify import slugify


def test_slugify():
    assert slugify("Hello World") == "hello-world"
