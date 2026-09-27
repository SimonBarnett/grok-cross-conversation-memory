# Grok Cross-Conversation Memory

Feature request: persistent memory across separate Grok conversations, so context carries over between chats instead of starting from scratch each time.

## Status

Implementation in progress on the `feature/persistent-memory` branch.

## Goals

- Store conversation summaries and key facts per user
- Retrieve relevant context automatically at the start of a new conversation
- Allow users to view, edit, or delete stored memories
- Privacy-first: opt-in, transparent, and deletable

## Non-goals

- Not a replacement for in-conversation context
- Not shared across different users
