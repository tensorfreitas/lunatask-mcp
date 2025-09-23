"""Composed LunaTask API client with modular functionality.

This module provides the LunaTaskClient class that combines the base HTTP
infrastructure with feature-specific mixins for a complete API client.
"""

from types import TracebackType

from lunatask_mcp.api.client_base import BaseClient
from lunatask_mcp.api.client_habits import HabitsClientMixin
from lunatask_mcp.api.client_journal import JournalClientMixin
from lunatask_mcp.api.client_notes import NotesClientMixin
from lunatask_mcp.api.client_people import PeopleClientMixin
from lunatask_mcp.api.client_tasks import TasksClientMixin


class LunaTaskClient(
    BaseClient,
    TasksClientMixin,
    NotesClientMixin,
    JournalClientMixin,
    HabitsClientMixin,
    PeopleClientMixin,
):
    """Complete LunaTask API client with all functionality.

    This class composes the base HTTP client with all feature-specific mixins
    to provide a unified interface for interacting with the LunaTask API.
    """

    def __str__(self) -> str:
        """Return string representation without exposing bearer token."""
        return f"LunaTaskClient(base_url={self._base_url}, token=***redacted***)"

    def __repr__(self) -> str:
        """Return repr without exposing bearer token."""
        return f"LunaTaskClient(base_url='{self._base_url}', token='***redacted***')"

    async def __aenter__(self) -> "LunaTaskClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await super().__aexit__(exc_type, exc_val, exc_tb)


__all__ = ["LunaTaskClient"]
