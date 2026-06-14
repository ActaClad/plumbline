"""Good: a constant destination URL carries no untrusted taint."""
import requests


def fetch():
    return requests.get("https://api.example.com/v1/data", timeout=10)
