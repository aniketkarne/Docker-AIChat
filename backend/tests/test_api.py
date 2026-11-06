"""Regression tests for the backend API.

No network, no real OpenAI calls: the AI helpers are monkeypatched or fed a
fake client. Run with `python -m pytest` from backend/.
"""
import os
import subprocess
import sys
import types

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    main.sessions.clear()
    monkeypatch.setattr(main, "_client", None, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    yield
    main.sessions.clear()
    monkeypatch.setattr(main, "_client", None, raising=False)


@pytest.fixture()
def client():
    return TestClient(main.app)


class FakeCompletions:
    """Records the kwargs of every create() call, returns a canned reply."""

    def __init__(self, content="FROM scratch"):
        self.calls = []
        self.content = content

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = types.SimpleNamespace(content=self.content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


def fake_client(content="FROM scratch"):
    completions = FakeCompletions(content)
    client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=completions)
    )
    return client, completions


# --- model selection -------------------------------------------------------

def test_default_model_is_current():
    # gpt-4 was shut down 2026-10-23; the default must be a live model.
    assert main.get_model() == "gpt-6-luna"


def test_model_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "my-model")
    assert main.get_model() == "my-model"


def test_ai_optimize_uses_configured_model_and_no_temperature(monkeypatch):
    client, completions = fake_client()
    monkeypatch.setattr(main, "get_client", lambda: client)
    monkeypatch.setenv("OPENAI_MODEL", "my-model")

    main.ai_optimize("FROM node:20")

    assert len(completions.calls) == 1
    assert completions.calls[0]["model"] == "my-model"
    # Current reasoning models reject non-default sampling parameters.
    assert "temperature" not in completions.calls[0]


# --- lazy client / missing key --------------------------------------------

def test_module_imports_without_openai_key():
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    proc = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_optimize_without_key_returns_503_not_crash(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post("/optimize", json={"dockerfile": "FROM node:20"})
    assert resp.status_code == 503
    assert "OPENAI_API_KEY" in resp.json()["detail"]


def test_optimize_missing_dockerfile_is_422(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main, "ai_optimize", lambda raw: calls.append(raw) or "x")
    resp = client.post("/optimize", json={})
    assert resp.status_code == 422
    assert calls == []  # no AI call for an empty request


# --- /suggestions ----------------------------------------------------------

def test_suggestions_unknown_session_404(client, monkeypatch):
    monkeypatch.setattr(main, "ai_optimize", lambda raw: pytest.fail("AI called"))
    resp = client.get("/suggestions", params={"sessionID": "nope"})
    assert resp.status_code == 404


def test_suggestions_calls_ai_exactly_once(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main, "ai_optimize", lambda raw: calls.append(raw) or "A\nB")
    main.sessions["s1"] = {"raw": "FROM node:20"}

    first = client.get("/suggestions", params={"sessionID": "s1"})
    second = client.get("/suggestions", params={"sessionID": "s1"})

    assert first.status_code == 200
    assert first.json()["suggestions"] == ["A", "B"]
    assert second.json()["suggestions"] == ["A", "B"]
    assert calls == ["FROM node:20"]  # computed once, then cached


def test_suggestions_never_sends_empty_dockerfile(client, monkeypatch):
    monkeypatch.setattr(main, "ai_optimize", lambda raw: pytest.fail("AI called"))
    main.sessions["empty"] = {"raw": ""}
    resp = client.get("/suggestions", params={"sessionID": "empty"})
    assert resp.status_code == 422


# --- /chat -----------------------------------------------------------------

def test_chat_history_keeps_user_turns(client, monkeypatch):
    async def fake_ai_chat(prompt):
        return "the answer"

    monkeypatch.setattr(main, "ai_chat", fake_ai_chat)
    main.sessions["s1"] = {"raw": "FROM node:20"}

    resp = client.post(
        "/chat",
        json={"sessionID": "s1", "history": [], "question": "why node:20?"},
    )

    assert resp.status_code == 200
    assert resp.json()["history"] == [
        {"role": "user", "content": "why node:20?"},
        {"role": "assistant", "content": "the answer"},
    ]


def test_chat_invalid_session_still_errors(client):
    resp = client.post("/chat", json={"sessionID": "nope", "question": "hi"})
    assert resp.json() == {"error": "Invalid sessionID"}
