"""User-facing error types.

Raw tracebacks must never be shown to normal users; raise UserFacingError
with what happened / why / what to do instead, and log the traceback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

log = logging.getLogger(__name__)


@dataclass
class UserFacingError(Exception):
    what: str
    why: str = ""
    actions: list[str] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - display only
        text = self.what
        if self.why:
            text += f"\n\nWhy: {self.why}"
        if self.actions:
            text += "\n\nWhat you can do:\n" + "\n".join(f"- {a}" for a in self.actions)
        return text


def report_exception(exc: Exception) -> UserFacingError:
    """Convert an unexpected exception into a safe user-facing error."""
    log.exception("Unhandled error", exc_info=exc)
    return UserFacingError(
        what="An unexpected error occurred.",
        why=str(exc) or exc.__class__.__name__,
        actions=["Check the Logs folder for technical details and try again."],
    )


ErrorCallback = Callable[[UserFacingError], None]
