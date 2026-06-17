"""Good: dummy/test secret values that must NOT fire — these are the real-repo
false positives found scanning crewAI's test suite (a 'test' marker substring or
low character diversity gives them away; no test-path special-casing needed)."""
access_token = "test_token"  # 'test' marker substring
jwt_token = "aaaaa.bbbbbb.cccccc"  # only 3 distinct alphanumerics — a fake
api_key = "your-api-key-here"  # placeholder
client_secret = "example-secret-value"  # 'example' marker substring
sample_token = "sampletoken1234"  # 'sample' marker substring
