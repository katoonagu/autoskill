from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationTask:
    conversation_key: str
    brand_handle: str
    blogger_handle: str
    channel: str


@dataclass
class ConversationThread:
    conversation_key: str
    channel: str
    status: str = "pending_approval"
    last_message_summary: str = ""
    next_action: str = ""
    history: list[dict] = field(default_factory=list)
