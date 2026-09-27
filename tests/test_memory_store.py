"""Tests for the persistent memory store."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Allow running tests without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memory_store import MemoryStore


class TestMemoryStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "test.db"
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_and_get(self):
        m = self.store.add("user1", "Prefers concise answers", kind="preference")
        self.assertIsNotNone(m.id)
        fetched = self.store.get(m.id)
        self.assertEqual(fetched.content, "Prefers concise answers")
        self.assertEqual(fetched.kind, "preference")

    def test_list_for_user_orders_by_importance(self):
        self.store.add("user1", "low", importance=0.1)
        self.store.add("user1", "high", importance=0.9)
        results = self.store.list_for_user("user1")
        self.assertEqual(results[0].content, "high")

    def test_search(self):
        self.store.add("user1", "Likes hiking in Wales")
        self.store.add("user1", "Works in London")
        hits = self.store.search("user1", "wales")
        self.assertEqual(len(hits), 1)
        self.assertIn("hiking", hits[0].content)

    def test_update(self):
        m = self.store.add("user1", "old content")
        updated = self.store.update(m.id, content="new content", importance=0.8)
        self.assertEqual(updated.content, "new content")
        self.assertAlmostEqual(updated.importance, 0.8)

    def test_delete(self):
        m = self.store.add("user1", "doomed")
        self.assertTrue(self.store.delete(m.id))
        self.assertIsNone(self.store.get(m.id))

    def test_delete_all_for_user(self):
        self.store.add("user1", "a")
        self.store.add("user1", "b")
        self.store.add("user2", "c")
        removed = self.store.delete_all_for_user("user1")
        self.assertEqual(removed, 2)
        self.assertEqual(len(self.store.list_for_user("user1")), 0)
        self.assertEqual(len(self.store.list_for_user("user2")), 1)

    def test_context_for_conversation(self):
        self.store.add("user1", "Fact one", importance=0.9)
        self.store.add("user1", "Fact two", importance=0.8)
        ctx = self.store.context_for_conversation("user1")
        self.assertIn("Persistent memory", ctx)
        self.assertIn("Fact one", ctx)
        self.assertIn("Fact two", ctx)

    def test_context_empty_for_new_user(self):
        self.assertEqual(self.store.context_for_conversation("nobody"), "")

    def test_export_json(self):
        self.store.add("user1", "export me")
        data = self.store.export_json("user1")
        self.assertIn("export me", data)

    def test_isolation_between_users(self):
        self.store.add("alice", "alice secret")
        self.store.add("bob", "bob secret")
        self.assertEqual(len(self.store.list_for_user("alice")), 1)
        self.assertEqual(len(self.store.list_for_user("bob")), 1)


if __name__ == "__main__":
    unittest.main()
