from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import uuid4
from typing import Optional


@dataclass(frozen=True)
class ChatMessageModel:
    """Value Object representing a single chat message."""
    id: str
    conversation_id: str
    role: str  # "user" | "assistant" | "tool"
    content: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    created_at: datetime | None = None


class ConversationModel:
    """Aggregate Root representing a conversation."""

    def __init__(
        self,
        id: str,
        user_id: str,
        title: str | None = None,
        messages: list[ChatMessageModel] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self._id = id
        self._user_id = user_id
        self._title = title
        self._messages = messages or []
        self._created_at = created_at
        self._updated_at = updated_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def title(self) -> str | None:
        return self._title

    @property
    def messages(self) -> list[ChatMessageModel]:
        return self._messages

    @property
    def created_at(self) -> datetime | None:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @staticmethod
    def create(user_id: str) -> "ConversationModel":
        return ConversationModel(
            id=str(uuid4()),
            user_id=user_id,
            created_at=datetime.now(UTC),
        )

    def set_title(self, title: str) -> None:
        self._title = title[:255] if title else None
        self._updated_at = datetime.now(UTC)

    def is_owner(self, user_id: str) -> bool:
        return self._user_id == user_id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConversationModel):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
