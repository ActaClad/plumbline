"""Good: eval of a constant expression carries no untrusted taint — SEC-002 is a
taint rule, so a non-tainted eval (however unusual) does not fire."""


def compute() -> int:
    return eval("2 + 2")
