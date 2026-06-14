"""Bad: a real-shaped provider key committed to source."""
OPENAI_API_KEY = "sk-proj-abc123def456ghi789jkl012mno345pqr"


def client_config():
    return {"api_key": OPENAI_API_KEY}
