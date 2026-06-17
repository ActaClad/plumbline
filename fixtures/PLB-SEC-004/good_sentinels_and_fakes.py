"""Good: sentinel defaults and obviously-fake keys that are not real secrets
(real-repo FPs from pydantic-ai). Must NOT fire."""
api_key = "api-key-not-set"  # a "not set" sentinel default
aws_default = "AKIA6666666666666666"  # provider-shaped but all-6s — low entropy, fake
client_secret = "your_secret_here"  # placeholder
