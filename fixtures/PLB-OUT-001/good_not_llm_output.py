"""Good (precision): json.loads on a file/config, not model output -> no finding."""
import json


def load_config(path: str) -> dict:
    with open(path) as fh:
        return json.loads(fh.read())
