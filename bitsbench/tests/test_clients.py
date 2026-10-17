"""Exercise the real provider SDK clients against a local fake server (no network, no API key)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from bitsbench.clients import Message

REQUESTS: list[dict] = []


class _Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        REQUESTS.append({"path": self.path, "body": body})
        if self.path.endswith("/v1/messages"):
            self._anthropic_stream()
        else:
            self._openai()

    def _send(self, ctype: str, payload: bytes):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _anthropic_stream(self):
        msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": "fake-model", "content": [],
               "stop_reason": None, "stop_sequence": None,
               "usage": {"input_tokens": 11, "output_tokens": 0, "cache_read_input_tokens": 5}}
        events = [
            ("message_start", {"type": "message_start", "message": msg}),
            ("content_block_start", {"type": "content_block_start", "index": 0,
                                     "content_block": {"type": "thinking", "thinking": "", "signature": ""}}),
            ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                     "delta": {"type": "signature_delta", "signature": "sig123"}}),
            ("content_block_stop", {"type": "content_block_stop", "index": 0}),
            ("content_block_start", {"type": "content_block_start", "index": 1,
                                     "content_block": {"type": "text", "text": ""}}),
            ("content_block_delta", {"type": "content_block_delta", "index": 1,
                                     "delta": {"type": "text_delta", "text": "Trying 7.\nQUERY: 7"}}),
            ("content_block_stop", {"type": "content_block_stop", "index": 1}),
            ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                               "usage": {"output_tokens": 9}}),
            ("message_stop", {"type": "message_stop"}),
        ]
        payload = "".join(f"event: {e}\ndata: {json.dumps(d)}\n\n" for e, d in events).encode()
        self._send("text/event-stream", payload)

    def _openai(self):
        resp = {"id": "c1", "object": "chat.completion", "created": 0, "model": "fake-oai",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": "QUERY: 9"}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 4, "total_tokens": 24,
                          "completion_tokens_details": {"reasoning_tokens": 2}}}
        self._send("application/json", json.dumps(resp).encode())


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_anthropic_client_streams_and_replays_thinking(server, monkeypatch):
    pytest.importorskip("anthropic")
    from bitsbench.clients import AnthropicClient

    monkeypatch.setenv("ANTHROPIC_BASE_URL", server)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    c = AnthropicClient("test-model", effort="high", max_retries=0)
    REQUESTS.clear()
    m1 = c.complete("SYS", [Message("user", "go")])
    assert m1.text == "Trying 7.\nQUERY: 7"
    assert m1.raw[0]["type"] == "thinking" and m1.raw[0]["signature"] == "sig123"
    c.complete("SYS", [Message("user", "go"), m1, Message("user", "next")])
    first, second = REQUESTS[0]["body"], REQUESTS[1]["body"]
    assert first["output_config"] == {"effort": "high"} and first["cache_control"] == {"type": "ephemeral"}
    assert first["stream"] is True and "thinking" not in first
    assert second["messages"][1] == {"role": "assistant", "content": m1.raw}, "assistant content replayed unchanged"
    assert second["messages"][:1] == first["messages"], "history is append-only"
    u = c.usage_snapshot()
    assert u["input_tokens"] == 22 and u["output_tokens"] == 18 and u["cache_read_input_tokens"] == 10


def test_openai_compatible_client(server, monkeypatch):
    pytest.importorskip("openai")
    from bitsbench.clients import make_client

    monkeypatch.setenv("FAKE_KEY", "k")
    c = make_client("compat:fake-oai", base_url=server + "/v1", api_key_env="FAKE_KEY", effort="medium")
    REQUESTS.clear()
    m = c.complete("SYS", [Message("user", "go")])
    assert m.text == "QUERY: 9" and c.name == "compat:fake-oai@medium"
    body = REQUESTS[0]["body"]
    assert body["messages"][0] == {"role": "system", "content": "SYS"} and body["reasoning_effort"] == "medium"
    assert c.usage_snapshot()["reasoning_tokens"] == 2


def test_cached_client_replays(tmp_path):
    from bitsbench.clients import CachedClient, MockClient
    from bitsbench.domains import get_domain
    from bitsbench.episodes import make_episode

    ep = make_episode("dev", "numbers", "L1", 0)
    inner = MockClient(error_rate=0.0)
    c = CachedClient(inner, tmp_path / "c.sqlite")
    c.bind(get_domain("numbers"), ep)
    a = c.complete("S", [Message("user", "hi")])
    c2 = CachedClient(MockClient(seed=99), tmp_path / "c.sqlite")
    c2.bind(get_domain("numbers"), ep)
    b = c2.complete("S", [Message("user", "hi")])
    assert a.text == b.text and c2.usage_snapshot()["cached_calls"] == 1
    c2.bind(get_domain("numbers"), make_episode("dev", "numbers", "L1", 1))
    c2.complete("S", [Message("user", "hi")])
    assert c2.usage_snapshot()["cached_calls"] == 1, "another episode must not reuse the cached sample"
