"""Tests for the conversation pipeline wiring."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.memory_store import MemoryStore
from src.pipeline import (
    ConversationPipeline,
    derive_facts,
    derive_summary,
    resolve_user_id,
)


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "test.db"
        self.topic = Path(self._tmp.name) / "topic.md"
        self.store = MemoryStore(self.db)
        self.pipeline = ConversationPipeline(
            store=self.store,
            user_id="tester",
            sync_topic_path=self.topic,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_on_chat_start_empty(self):
        self.assertEqual(self.pipeline.on_chat_start(), "")
        self.assertFalse(self.topic.exists())

    def test_on_chat_start_injects_and_syncs_topic(self):
        self.store.add("tester", "Prefers concise answers", kind="preference")
        ctx = self.pipeline.on_chat_start()
        self.assertIn("Persistent memory", ctx)
        self.assertIn("Prefers concise answers", ctx)
        self.assertTrue(self.topic.is_file())
        self.assertIn("Prefers concise answers", self.topic.read_text(encoding="utf-8"))

    def test_session_start_hook_output(self):
        self.store.add("tester", "Fact A", kind="fact")
        payload = self.pipeline.session_start_hook_output()
        self.assertIn("hookSpecificOutput", payload)
        self.assertIn("Fact A", payload["hookSpecificOutput"]["additionalContext"])

    def test_on_chat_end_writes_summary_and_facts(self):
        transcript = (
            "User: remember: deploy only from main\n"
            "User: prefer concise answers\n"
            "- Always open PR links after pushing\n"
        )
        written = self.pipeline.on_chat_end(
            conversation_id="sess-1", transcript=transcript
        )
        self.assertGreaterEqual(len(written), 2)
        kinds = {m.kind for m in written}
        self.assertIn("summary", kinds)
        contents = " ".join(m.content for m in written)
        self.assertIn("deploy only from main", contents)
        listed = self.store.list_for_user("tester")
        self.assertTrue(any(m.source_conversation == "sess-1" for m in listed))

    def test_on_chat_end_explicit_summary_facts(self):
        written = self.pipeline.on_chat_end(
            conversation_id="sess-2",
            summary="Worked on hooks",
            facts=["Uses SessionStart for inject"],
        )
        self.assertEqual(len(written), 2)
        self.assertEqual(written[0].kind, "summary")
        self.assertEqual(written[1].kind, "fact")

    def test_derive_helpers(self):
        text = "User: hello world\nremember: keep secrets out of logs\n- Prefer UTF-8 outbox"
        self.assertIn("hello world", derive_summary(text))
        facts = derive_facts(text)
        self.assertTrue(any("secrets" in f for f in facts))

    def test_resolve_user_id_env(self):
        old = os.environ.get("GROK_MEMORY_USER")
        os.environ["GROK_MEMORY_USER"] = "simon"
        try:
            self.assertEqual(resolve_user_id(), "simon")
        finally:
            if old is None:
                del os.environ["GROK_MEMORY_USER"]
            else:
                os.environ["GROK_MEMORY_USER"] = old


class TestHookScripts(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "hook.db"
        self.topic = Path(self._tmp.name) / "topic.md"

    def tearDown(self):
        self._tmp.cleanup()

    def _run_hook(self, script: str, payload: dict, env_extra: dict | None = None):
        env = os.environ.copy()
        env["GROK_MEMORY_USER"] = "hookuser"
        # Point store at temp db by monkeypatching via env consumed in future;
        # hooks use default path — isolate HOME instead.
        env["USERPROFILE"] = self._tmp.name
        env["HOME"] = self._tmp.name
        if env_extra:
            env.update(env_extra)
        proc = subprocess.run(
            [sys.executable, str(ROOT / "src" / "hooks" / script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            cwd=str(ROOT),
            check=False,
        )
        return proc

    def test_session_start_script(self):
        # Seed store under temp HOME
        store = MemoryStore(Path(self._tmp.name) / ".grok" / "memory.db")
        store.add("hookuser", "Seed fact", kind="fact")
        proc = self._run_hook(
            "session_start.py",
            {"hookEventName": "session_start", "sessionId": "abc"},
            {"GROK_MEMORY_SYNC_TOPIC": str(self.topic)},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Seed fact", proc.stdout)
        self.assertTrue(self.topic.is_file())

    def test_session_end_script(self):
        transcript = Path(self._tmp.name) / "t.txt"
        transcript.write_text(
            "User: remember: park docs before dispatch\n", encoding="utf-8"
        )
        proc = self._run_hook(
            "session_end.py",
            {
                "sessionId": "end-1",
                "transcriptPath": str(transcript),
            },
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout or "{}")
        self.assertGreaterEqual(data.get("stored", 0), 1)
        store = MemoryStore(Path(self._tmp.name) / ".grok" / "memory.db")
        memories = store.list_for_user("hookuser")
        self.assertTrue(any("park docs" in m.content for m in memories))


if __name__ == "__main__":
    unittest.main()
