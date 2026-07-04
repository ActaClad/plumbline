"""A same-named class from an unrelated library (no autogen import) — must stay silent.

Guards the import gate: the team constructor names are generic, so the rule only
engages when an AutoGen SDK is imported in the file.
"""
from mylib.teams import RoundRobinGroupChat

team = RoundRobinGroupChat([1, 2])  # not AutoGen -> no finding
