#!/usr/bin/env python3
"""Grok SessionEnd hook: persist summary and facts into MemoryStore."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import (  # noqa: E402
    ConversationPipeline,
    hook_event_from_stdin,
    load_transcript,
    resolve_session_transcript,
)


def main() -> int:
    event = hook_event_from_stdin(sys.stdin.read())
    session_id = (
        event.get("sessionId")
        or event.get("session_id")
        or event.get("conversationId")
        or None
    )
    cwd = (
        event.get("cwd")
        or event.get("workspaceRoot")
        or event.get("workspace_root")
        or None
    )
    transcript = ""
    for key in ("transcriptPath", "transcript_path", "transcriptFile"):
        if event.get(key):
            transcript = load_transcript(event[key])
            break
    if not transcript and isinstance(event.get("transcript"), str):
        transcript = event["transcript"]
    # Grok SessionEnd does not document transcriptPath — load from session dir.
    if not transcript.strip() and session_id:
        transcript = resolve_session_transcript(str(session_id), cwd=cwd)

    # Skip trivial empty ends — nothing to store.
    if not transcript.strip() and not event.get("summary") and not event.get("facts"):
        return 0

    pipeline = ConversationPipeline()
    written = pipeline.on_chat_end(
        conversation_id=str(session_id) if session_id else None,
        transcript=transcript,
        summary=event.get("summary"),
        facts=event.get("facts") if isinstance(event.get("facts"), list) else None,
    )
    sys.stdout.write(
        json.dumps({"stored": len(written), "ids": [m.id for m in written]})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
