# Grok Cross-Conversation Memory

Persistent memory across separate Grok conversations, so context carries over between chats instead of starting from scratch each time.

## Status

Implementation complete on the `feature/persistent-memory` branch.

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

## Usage

```python
from src.memory_store import MemoryStore

store = MemoryStore()  # defaults to ~/.grok/memory.db
store.add("simon", "Prefers concise answers", kind="preference")
print(store.context_for_conversation("simon"))
```

## Design notes

- **Backend**: SQLite (single file, stdlib only, no server). The database lives at `~/.grok/memory.db` by default.
- **Context injection**: `context_for_conversation()` builds a markdown block sized to a token budget (~4 chars/token) for prepending to a new chat.
- **Privacy**: `delete_all_for_user()` wipes everything for one user; `export_json()` gives a portable backup.
- **Search**: simple substring match, ordered by importance.

## Tests

```bash
python -m pytest tests/
# or
python -m unittest discover -s tests
```
