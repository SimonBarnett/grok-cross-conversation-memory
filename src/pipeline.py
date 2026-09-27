"""Wire MemoryStore into the Grok conversation lifecycle.

Session start: build injectable context via ``context_for_conversation``.
Session end: persist a summary plus extracted facts/preferences.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .memory_store import Memory, MemoryStore


DEFAULT_USER_ENV = "GROK_MEMORY_USER"
REMEMBER_RE = re.compile(
    r"(?i)\b(?:remember|prefer|always|never|note that)\b[:\s]+(.+)"
)
BULLET_RE = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)


@dataclass
class PipelineResult:
    """Outcome of a pipeline lifecycle call."""

    context: str = ""
    memories: list[Memory] | None = None


class ConversationPipeline:
    """Lifecycle adapter around :class:`MemoryStore`."""

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        user_id: Optional[str] = None,
        sync_topic_path: Optional[Path] = None,
    ):
        self.store = store or MemoryStore()
        self.user_id = user_id or resolve_user_id()
        self.sync_topic_path = sync_topic_path

    def on_chat_start(self, max_tokens: int = 2000) -> str:
        """Inject stored memory at the start of a new conversation.

        Returns the markdown context block (empty when the user has none).
        Optionally mirrors the block into a Grok memory-v2 topic file so the
        built-in first-turn injector can pick it up when memory is enabled.
        """
        context = self.store.context_for_conversation(
            self.user_id, max_tokens=max_tokens
        )
        if context and self.sync_topic_path is not None:
            self._sync_topic(context)
        return context

    def on_chat_end(
        self,
        conversation_id: Optional[str] = None,
        transcript: str = "",
        summary: Optional[str] = None,
        facts: Optional[list[str]] = None,
    ) -> list[Memory]:
        """Write summaries and facts at chat end.

        When ``summary`` / ``facts`` are omitted, derives them heuristically
        from ``transcript`` (no LLM required).
        """
        written: list[Memory] = []
        text = (transcript or "").strip()
        derived_summary = summary if summary is not None else derive_summary(text)
        derived_facts = facts if facts is not None else derive_facts(text)

        if derived_summary:
            written.append(
                self.store.add(
                    self.user_id,
                    derived_summary,
                    kind="summary",
                    source_conversation=conversation_id,
                    importance=0.6,
                )
            )
        for fact in derived_facts:
            kind = "preference" if _looks_like_preference(fact) else "fact"
            written.append(
                self.store.add(
                    self.user_id,
                    fact,
                    kind=kind,
                    source_conversation=conversation_id,
                    importance=0.7 if kind == "preference" else 0.55,
                )
            )
        return written

    def session_start_hook_output(self, max_tokens: int = 2000) -> dict:
        """JSON payload for a SessionStart hook (Claude-compatible shape).

        Grok currently treats SessionStart as passive (stdout ignored for
        model injection). Callers still emit this for forward compatibility
        and mirror context via ``sync_topic_path`` when configured.
        """
        context = self.on_chat_start(max_tokens=max_tokens)
        if not context:
            return {}
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }

    def _sync_topic(self, context: str) -> None:
        path = Path(self.sync_topic_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = (
            "# Cross-conversation memory\n\n"
            "Synced from grok-cross-conversation-memory at session start.\n\n"
            f"{context}\n"
        )
        path.write_text(body, encoding="utf-8")


def resolve_user_id() -> str:
    explicit = os.environ.get(DEFAULT_USER_ENV, "").strip()
    if explicit:
        return explicit
    for key in ("USERNAME", "USER", "LOGNAME"):
        val = os.environ.get(key, "").strip()
        if val:
            return val.lower()
    return "default"


def default_sync_topic_path() -> Path:
    """Default memory-v2 topic path used for first-turn injection mirror."""
    return (
        Path.home()
        / ".grok"
        / "memory-v2"
        / "global"
        / "topics"
        / "cross-conversation-memory.md"
    )


def derive_summary(transcript: str, max_chars: int = 400) -> str:
    """Build a short summary from user-looking lines in a transcript."""
    if not transcript.strip():
        return ""
    user_lines = _userish_lines(transcript)
    if not user_lines:
        # Fall back to the first non-empty line of the whole transcript.
        for line in transcript.splitlines():
            stripped = line.strip()
            if stripped:
                user_lines = [stripped]
                break
    if not user_lines:
        return ""
    joined = " | ".join(user_lines[:5])
    if len(joined) > max_chars:
        joined = joined[: max_chars - 1].rstrip() + "…"
    return f"Session topics: {joined}"


def derive_facts(transcript: str, limit: int = 8) -> list[str]:
    """Extract remember/prefer lines and bullets from a transcript."""
    if not transcript.strip():
        return []
    found: list[str] = []
    seen: set[str] = set()

    for match in REMEMBER_RE.finditer(transcript):
        item = match.group(1).strip().rstrip(".")
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            found.append(item)
            if len(found) >= limit:
                return found

    for match in BULLET_RE.finditer(transcript):
        item = match.group(1).strip().rstrip(".")
        if len(item) < 8:
            continue
        key = item.lower()
        if key in seen:
            continue
        # Skip pure tool/path noise
        if item.startswith("`") or item.startswith("/") or item.startswith("C:\\"):
            continue
        seen.add(key)
        found.append(item)
        if len(found) >= limit:
            break
    return found


def _userish_lines(transcript: str) -> list[str]:
    lines: list[str] = []
    for raw in transcript.splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("user:") or lower.startswith("human:"):
            lines.append(line.split(":", 1)[1].strip())
        elif lower.startswith("> "):
            lines.append(line[2:].strip())
    return [x for x in lines if x]


def _looks_like_preference(text: str) -> bool:
    lower = text.lower()
    return any(
        token in lower
        for token in ("prefer", "always", "never", "style", "concise", "verbose")
    )


def load_transcript(path: Optional[str | Path]) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def hook_event_from_stdin(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
