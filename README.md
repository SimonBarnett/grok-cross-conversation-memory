# Grok Cross-Conversation Memory

Persistent memory across separate Grok conversations, so context carries over between chats instead of starting from scratch each time.

## Status

- Store API on `main` (`MemoryStore`).
- Conversation pipeline wiring (issue #4): inject at new-chat start, write summaries/facts at chat end, shipped as a Grok plugin with `SessionStart` / `SessionEnd` hooks.

## Memory location (important)

**All memories are stored in this repository.** When a new memory is created during a conversation, it is written here as a markdown file under `memories/` (e.g. `memories/bobiverse.md`), committed on a branch, and opened as a pull request against `main` for review before merging.

Do not create separate repositories for memories. This repo is the single source of truth for cross-conversation memory.

## Goals

- Store conversation summaries and key facts per user
- Retrieve relevant context automatically at the start of a new conversation
- Allow users to view, edit, or delete stored memories
- Privacy-first: opt-in, transparent, and deletable

## Non-goals

- Not a replacement for in-conversation context
- Not shared across different users

## Install (Grok plugin)

From this repo (trusted local install):

```bash
grok plugin install . --trust
```

Or from GitHub:

```bash
grok plugin install SimonBarnett/grok-cross-conversation-memory --trust
```

Hooks run on **new session startup** (`SessionStart` matcher `startup`) and on **session end**:

1. **Start** — `context_for_conversation()` builds the markdown block, emits Claude-compatible `additionalContext` JSON, and mirrors the block into `~/.grok/memory-v2/global/topics/cross-conversation-memory.md` so Grok’s built-in first-turn memory injection can pick it up when `[memory]` / memory-v2 is enabled.
2. **End** — heuristic summary + fact/preference extraction written via `MemoryStore.add`. Uses `transcriptPath` / `transcript` when present; otherwise loads `~/.grok/sessions/<encoded-cwd>/<sessionId>/chat_history.jsonl` (Grok SessionEnd does not document a transcript path).

Optional env:

| Variable | Purpose |
|---|---|
| `GROK_MEMORY_USER` | User id for the store (default: Windows/`USER` login) |
| `GROK_MEMORY_SYNC_TOPIC` | Override topic mirror path, or `0` to disable mirroring |

## Library usage

```python
from src.memory_store import MemoryStore
from src.pipeline import ConversationPipeline

store = MemoryStore()  # defaults to ~/.grok/memory.db
store.add("simon", "Prefers concise answers", kind="preference")

pipeline = ConversationPipeline(store=store, user_id="simon")
print(pipeline.on_chat_start())
pipeline.on_chat_end(
    conversation_id="abc",
    transcript="User: remember: deploy only from main\n",
)
```

## Design notes

- **Backend**: SQLite (single file, stdlib only, no server). The database lives at `~/.grok/memory.db` by default.
- **Context injection**: `context_for_conversation()` builds a markdown block sized to a token budget (~4 chars/token) for prepending to a new chat.
- **Pipeline**: `ConversationPipeline` is the lifecycle adapter; hook scripts under `src/hooks/` call it.
- **Privacy**: `delete_all_for_user()` wipes everything for one user; `export_json()` gives a portable backup.
- **Search**: simple substring match, ordered by importance.

## Tests

```bash
python -m pytest tests/
# or
python -m unittest discover -s tests
```
