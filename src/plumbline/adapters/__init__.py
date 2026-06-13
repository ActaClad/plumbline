"""Framework adapters. Registered in an explicit, priority-ordered list
(ADR-0004 D5): adapters are few, core-owned, and conflict-resolved by priority,
unlike rules (which are convention-discovered). Higher priority wins a
(tag, node) conflict — framework adapters outrank the raw SDK.
"""

from __future__ import annotations

from .base import Adapter
from .openai_sdk import OpenAISDKAdapter

#: The registry. Order is documentation; conflict resolution uses `priority`.
ADAPTERS: tuple[Adapter, ...] = (OpenAISDKAdapter(),)

__all__ = ["ADAPTERS", "Adapter"]
