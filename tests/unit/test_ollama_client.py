"""Tests for the Ollama client."""

from unittest.mock import MagicMock, patch
import pytest

from server.tools import OllamaClient
from server.base.exceptions import OllamaException, OllamaConnectionException


def _mock_session(get_json=None, post_json=None, get_exc=None, post_exc=None):
    """Build a mock requests.Session with controllable get/post behaviour."""
    session = MagicMock()

    if get_exc is not None:
        session.get.side_effect = get_exc
    else:
        get_resp = MagicMock()
        get_resp.json.return_value = get_json if get_json is not None else {"models": []}
        get_resp.status_code = 200
        get_resp.ok = True
        session.get.return_value = get_resp

    if post_exc is not None:
        session.post.side_effect = post_exc
    else:
        post_resp = MagicMock()
        post_resp.json.return_value = post_json or {}
        post_resp.status_code = 200
        session.post.return_value = post_resp

    return session


class TestOllamaClient:
    """Test cases for OllamaClient (local mode, mocked HTTP session)."""

    def test_initialization_success(self):
        session = _mock_session()
        with patch("server.tools.llm.ollama_client._build_session", return_value=session):
            client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
        assert client.base_url == "http://localhost:11434"
        assert client.model == "qwen3:8b"

    def test_initialization_connection_failure(self):
        import requests

        session = _mock_session(get_exc=requests.exceptions.ConnectionError("refused"))
        with patch("server.tools.llm.ollama_client._build_session", return_value=session):
            with patch("server.tools.llm.ollama_client.config") as cfg:
                cfg.ollama.mode = "local"
                cfg.ollama.base_url = "http://localhost:11434"
                cfg.ollama.model = "qwen3:8b"
                cfg.ollama.timeout = 5
                cfg.ollama.api_key = ""
                with pytest.raises(OllamaConnectionException):
                    OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")

    def test_generate_success(self):
        session = _mock_session(post_json={"response": "Generated text", "eval_count": 20})
        with patch("server.tools.llm.ollama_client._build_session", return_value=session):
            client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
            result = client.generate("test prompt")
        assert "response" in result
        assert result["model"] == "qwen3:8b"
        assert "latency_ms" in result

    def test_generate_failure(self):
        import requests

        session = _mock_session(post_exc=requests.exceptions.RequestException("API error"))
        with patch("server.tools.llm.ollama_client._build_session", return_value=session):
            client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
            with pytest.raises(OllamaException):
                client.generate("test prompt")

    def test_chat_success(self):
        session = _mock_session(
            post_json={"message": {"content": "Chat response"}, "eval_count": 25}
        )
        with patch("server.tools.llm.ollama_client._build_session", return_value=session):
            client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
            result = client.chat([{"role": "user", "content": "Hello"}])
        assert "message" in result
        assert "latency_ms" in result

    def test_structured_generate_success(self):
        session = _mock_session(post_json={"response": '{"name": "test", "age": 30}'})
        with patch("server.tools.llm.ollama_client._build_session", return_value=session):
            client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
            result = client.structured_generate("test prompt")
        assert "parsed_response" in result
        assert result["parsed_response"]["name"] == "test"

    def test_structured_generate_invalid_json(self):
        session = _mock_session(post_json={"response": "not valid json"})
        with patch("server.tools.llm.ollama_client._build_session", return_value=session):
            client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
            with pytest.raises(OllamaException):
                client.structured_generate("test prompt")

    def test_is_model_available(self):
        session = _mock_session(get_json={"models": [{"name": "qwen3:8b"}, {"name": "llama:7b"}]})
        with patch("server.tools.llm.ollama_client._build_session", return_value=session):
            client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
            assert client.is_model_available("qwen3:8b") is True
            assert client.is_model_available("nonexistent:8b") is False
