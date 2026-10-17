"""Model clients.

Provider SDKs are imported lazily so the benchmark itself only needs numpy.
Anthropic models go through the official ``anthropic`` SDK; anything that
speaks the OpenAI chat-completions protocol (OpenAI, vLLM, OpenRouter,
Together, Gemini's compatibility endpoint, ...) goes through the ``openai`` SDK.

Refusal fallbacks to other models are deliberately not enabled: every reply in
a BITS-Bench run must come from the model named in the results.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class Message:
    role: str                     # "user" | "assistant"
    text: str
    raw: Any = None               # provider-native assistant content, replayed unchanged
    meta: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        d = {"role": self.role, "text": self.text}
        if self.raw is not None:
            d["raw"] = self.raw
        if self.meta:
            d["meta"] = self.meta
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Message":
        return cls(d["role"], d["text"], d.get("raw"), d.get("meta", {}))


class Client(ABC):
    name: str

    def __init__(self) -> None:
        self._usage: dict[str, float] = {}

    @abstractmethod
    def complete(self, system: str, messages: list[Message]) -> Message: ...

    def config(self) -> dict:
        return {"name": self.name}

    def _add_usage(self, **kv: float) -> None:
        for k, v in kv.items():
            if v:
                self._usage[k] = self._usage.get(k, 0) + v

    def usage_snapshot(self, reset: bool = False) -> dict:
        u = dict(self._usage)
        if reset:
            self._usage = {}
        return u


class AnthropicClient(Client):
    def __init__(self, model: str, max_tokens: int = 32000, effort: str | None = None,
                 thinking_display: str | None = None, timeout: float = 900, max_retries: int = 8):
        super().__init__()
        import anthropic  # lazy: only needed for Anthropic models

        self.model, self.max_tokens, self.effort, self.thinking_display = model, max_tokens, effort, thinking_display
        self.name = f"anthropic:{model}" + (f"@{effort}" if effort else "")
        self._client = anthropic.Anthropic(timeout=timeout, max_retries=max_retries)

    def config(self) -> dict:
        return {"name": self.name, "model": self.model, "max_tokens": self.max_tokens, "effort": self.effort,
                "thinking_display": self.thinking_display}

    def complete(self, system: str, messages: list[Message]) -> Message:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [self._to_api(m) for m in messages],
            "extra_body": {"cache_control": {"type": "ephemeral"}},  # automatic prompt caching
        }
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        if self.thinking_display:
            kwargs["thinking"] = {"type": "adaptive", "display": self.thinking_display}
        with self._client.messages.stream(**kwargs) as stream:
            resp = stream.get_final_message()
        text = "".join(b.text for b in resp.content if b.type == "text")
        u = resp.usage
        self._add_usage(input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                        cache_read_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
                        cache_creation_input_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
                        refusals=int(resp.stop_reason == "refusal"),
                        max_tokens_stops=int(resp.stop_reason == "max_tokens"))
        raw = resp.to_dict()["content"]
        return Message("assistant", text, raw=raw, meta={"stop_reason": resp.stop_reason, "model": resp.model})

    @staticmethod
    def _to_api(m: Message) -> dict:
        if m.role == "assistant" and m.raw:
            return {"role": "assistant", "content": m.raw}  # thinking blocks passed back unchanged
        return {"role": m.role, "content": m.text or "(empty reply)"}


class OpenAIClient(Client):
    def __init__(self, model: str, base_url: str | None = None, api_key_env: str = "OPENAI_API_KEY",
                 max_tokens: int | None = None, reasoning_effort: str | None = None,
                 temperature: float | None = None, timeout: float = 900, max_retries: int = 8, label: str = "openai"):
        super().__init__()
        import openai  # lazy: only needed for OpenAI-compatible endpoints

        self.model, self.base_url, self.max_tokens = model, base_url, max_tokens
        self.reasoning_effort, self.temperature = reasoning_effort, temperature
        self.name = f"{label}:{model}" + (f"@{reasoning_effort}" if reasoning_effort else "")
        self._client = openai.OpenAI(base_url=base_url, api_key=os.environ.get(api_key_env),
                                     timeout=timeout, max_retries=max_retries)

    def config(self) -> dict:
        return {"name": self.name, "model": self.model, "base_url": self.base_url, "max_tokens": self.max_tokens,
                "reasoning_effort": self.reasoning_effort, "temperature": self.temperature}

    def complete(self, system: str, messages: list[Message]) -> Message:
        msgs = [{"role": "system", "content": system}] + [{"role": m.role, "content": m.text} for m in messages]
        kwargs: dict[str, Any] = {"model": self.model, "messages": msgs}
        if self.max_tokens:
            kwargs["max_completion_tokens"] = self.max_tokens
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        r = self._client.chat.completions.create(**kwargs)
        choice = r.choices[0]
        text = choice.message.content or ""
        if r.usage:
            details = getattr(r.usage, "completion_tokens_details", None)
            self._add_usage(input_tokens=r.usage.prompt_tokens, output_tokens=r.usage.completion_tokens,
                            reasoning_tokens=getattr(details, "reasoning_tokens", 0) or 0)
        return Message("assistant", text, meta={"finish_reason": choice.finish_reason, "model": r.model})


class MockClient(Client):
    """Offline stand-in that emits valid (random) experiments and predictions.

    Used by the test suite and ``--model mock`` dry runs; it occasionally emits
    malformed replies so the retry paths get exercised.
    """

    def __init__(self, seed: int = 0, error_rate: float = 0.1):
        super().__init__()
        self.name = "mock"
        self.seed, self.error_rate = seed, error_rate

    def bind(self, domain, ep) -> None:
        self.domain, self.ep = domain, ep
        self.rng = np.random.default_rng([ep.seed & 0xFFFFFFFF, self.seed])

    def complete(self, system: str, messages: list[Message]) -> Message:
        last = messages[-1].text
        self._add_usage(input_tokens=len(system) // 4 + sum(len(m.text) for m in messages) // 4, output_tokens=20)
        if self.rng.random() < self.error_rate:
            return Message("assistant", "Hmm, let me think about this.")
        if "PREDICTIONS:" in last:
            ask = next(m.text for m in reversed(messages) if "Predict f(x) for each of these " in m.text)
            n = int(ask.split("Predict f(x) for each of these ")[1].split(" ")[0])
            if self.domain.binary:
                preds = ", ".join("true" if self.rng.random() < 0.5 else "false" for _ in range(n))
            else:
                preds = ", ".join("[]" for _ in range(n))
            rule = "RULE: x0\n" if "RULE:" in ask else ""
            return Message("assistant", f"{rule}PREDICTIONS: [{preds}]")
        x = self.domain.random_query(self.rng)
        return Message("assistant", f"Let me try something.\nQUERY: {self.domain.fmt_input(x)}")


class CachedClient(Client):
    """Wraps a client with an on-disk cache keyed by the full request.

    Re-running an interrupted episode then replays already-paid-for calls for
    free. Each cached reply is still a genuine sample from the model. The key
    includes the episode id: different episodes of a configuration share their
    opening prompt, and must not share the model's sampled reply to it.
    """

    _lock = threading.Lock()

    def __init__(self, inner: Client, path: Path):
        super().__init__()
        self.inner, self.name = inner, inner.name
        self._episode = None
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False, timeout=60)
        with self._lock:
            self._db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
            self._db.commit()

    def bind(self, domain, ep) -> None:
        self._episode = ep.id
        if hasattr(self.inner, "bind"):
            self.inner.bind(domain, ep)

    def config(self) -> dict:
        return self.inner.config()

    def complete(self, system: str, messages: list[Message]) -> Message:
        key = hashlib.sha256(json.dumps([self.inner.config(), self._episode, system, [m.to_json() for m in messages]],
                                        sort_keys=True, default=str).encode()).hexdigest()
        with self._lock:
            row = self._db.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
        if row:
            self._add_usage(cached_calls=1)
            return Message.from_json(json.loads(row[0]))
        msg = self.inner.complete(system, messages)
        for k, v in self.inner.usage_snapshot(reset=True).items():
            self._add_usage(**{k: v})
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (key, json.dumps(msg.to_json())))
            self._db.commit()
        return msg


def make_client(spec: str, *, effort: str | None = None, max_tokens: int | None = None,
                base_url: str | None = None, api_key_env: str | None = None, temperature: float | None = None,
                thinking_display: str | None = None, cache: Path | None = None) -> Client:
    """Build a client from ``provider:model`` (providers: anthropic, openai, compat, mock)."""
    provider, _, model = spec.partition(":")
    if provider == "mock":
        client: Client = MockClient(seed=int(model or 0))
    elif provider == "anthropic":
        client = AnthropicClient(model, max_tokens=max_tokens or 32000, effort=effort, thinking_display=thinking_display)
    elif provider in ("openai", "compat"):
        if provider == "compat" and not base_url:
            raise ValueError("compat:<model> needs --base-url")
        client = OpenAIClient(model, base_url=base_url, api_key_env=api_key_env or "OPENAI_API_KEY",
                              max_tokens=max_tokens, reasoning_effort=effort, temperature=temperature, label=provider)
    else:
        raise ValueError(f"unknown provider in {spec!r}; use anthropic:, openai:, compat: or mock")
    return CachedClient(client, cache) if cache else client

