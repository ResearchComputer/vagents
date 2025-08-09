from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _generate_unique_id() -> str:
    """Generate a random, unique identifier.

    Prefers UUID7 when available (time-ordered, good for logs/storage),
    falls back to UUID4 for widely available random IDs.
    """
    try:  # uuid6 package exposes uuid7()
        from uuid6 import uuid7 as _uuid7  # type: ignore

        return str(_uuid7())
    except Exception:
        try:  # some environments provide a `uuid7` package
            from uuid7 import uuid7 as _uuid7  # type: ignore

            return str(_uuid7())
        except Exception:
            from uuid import uuid4

            return str(uuid4())


class AgentInput(BaseModel):
    """Standard input protocol for agent invocations."""

    id: str = Field(default_factory=_generate_unique_id, description="Unique input id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the input was created",
    )
    payload: Dict[str, Any] = Field(default_factory=dict, description="User input data")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional context/metadata for processing"
    )


class AgentOutput(BaseModel):
    """Standard output protocol for agent invocations."""

    id: str = Field(default_factory=_generate_unique_id, description="Unique output id")
    input_id: Optional[str] = Field(
        default=None, description="ID of the originating AgentInput, if available"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the output was created",
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Primary result payload"
    )
    error: Optional[str] = Field(default=None, description="Error message, if any")


__all__ = ["AgentInput", "AgentOutput"]
