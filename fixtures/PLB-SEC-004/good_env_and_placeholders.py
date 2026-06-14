"""Good: secrets loaded from the environment; env-var NAMES and placeholders are
not secrets and must NOT fire."""
import os

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]  # RHS is not a literal
api_key = os.getenv("API_KEY")  # "API_KEY" is the var name, not a secret
EXAMPLE_KEY = "your-api-key-here"  # placeholder
default_token = "changeme"  # secret-named but an obvious placeholder
