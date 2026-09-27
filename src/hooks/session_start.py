#!/usr/bin/env python3
"""Grok SessionStart hook: inject MemoryStore context for the new chat."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import (  # noqa: E402
    ConversationPipeline,
    default_sync_topic_path,
    hook_event_from_stdin,
)


def main() -> int:
    event = hook_event_from_stdin(sys.stdin.read())
    sync = os.environ.get("GROK_MEMORY_SYNC_TOPIC", "").strip()
    sync_path = Path(sync) if sync else default_sync_topic_path()
    # Opt out of topic mirror with GROK_MEMORY_SYNC_TOPIC=0
    if sync == "0":
        sync_path = None

    pipeline = ConversationPipeline(sync_topic_path=sync_path)
    payload = pipeline.session_start_hook_output()
    if payload:
        sys.stdout.write(json.dumps(payload))
    # Always succeed; SessionStart is fail-open / passive.
    _ = event  # reserved for future matcher fields (startup vs resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
