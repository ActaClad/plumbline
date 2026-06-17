"""Good: `token`/`secret` are overloaded — these are sentinels/labels, not
credentials, and must NOT fire (real-repo FPs from open-interpreter)."""
STDERR_NULL_TOKEN = "{stderr-null}"  # a sentinel string
bearer_token = "bearerToken"  # a field-name label in generated code
next_page_token = "page-2-cursor"  # a pagination cursor, not a secret
