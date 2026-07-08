"""Tests for the Ollama client."""

import json
from unittest.mock import Mock, patch
import pytest

from server.tools.ollama_client import OllamaClient
from server.exceptions import OllamaException, OllamaConnectionException


class TestOllamaClient:
    """Test cases for OllamaClient."""

    @patch("server.tools.ollama_client.requests.get")
    def test_initialization_success(self, mock_get):
        """Test successful initialization."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        client = OllamaClient(
            base_url="http://localhost:11434", model="qwen3:8b"
        )

        assert client.base_url == "http://localhost:11434"
        assert client.model == "qwen3:8b"

    @patch("tools.ollama_client.requests.get")
    def test_initialization_connection_failure(self, mock_get):
        """Test initialization with connection failure."""
        mock_get.side_effect = Exception("Connection refused")

        with pytest.raises(OllamaConnectionException):
            OllamaClient(
                base_url="http://localhost:11434", model="qwen3:8b"
            )

    @patch("tools.ollama_client.requests.post")
    @patch("tools.ollama_client.requests.get")
    def test_generate_success(self, mock_get, mock_post):
        """Test successful text generation."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        mock_post.return_value.json.return_value = {
            "response": "Generated text",
            "eval_base": 10,
            "eval_count": 20,
        }
        mock_post.return_value.status_code = 200

        client = OllamaClient()
        result = client.generate("test prompt")

        assert "response" in result
        assert result["model"] == "qwen3:8b"
        assert "latency_ms" in result

    @patch("tools.ollama_client.requests.post")
    @patch("tools.ollama_client.requests.get")
    def test_generate_failure(self, mock_get, mock_post):
        """Test generation failure."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        mock_post.side_effect = Exception("API error")

        client = OllamaClient()

        with pytest.raises(OllamaException):
            client.generate("test prompt")

    @patch("tools.ollama_client.requests.post")
    @patch("tools.ollama_client.requests.get")
    def test_chat_success(self, mock_get, mock_post):
        """Test successful chat."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        mock_post.return_value.json.return_value = {
            "message": {"content": "Chat response"},
            "prompt_eval_count": 15,
            "eval_count": 25,
        }
        mock_post.return_value.status_code = 200

        client = OllamaClient()
        result = client.chat([{"role": "user", "content": "Hello"}])

        assert "message" in result
        assert "latency_ms" in result

    @patch("tools.ollama_client.requests.post")
    @patch("tools.ollama_client.requests.get")
    def test_structured_generate_success(self, mock_get, mock_post):
        """Test successful structured generation."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        mock_post.return_value.json.return_value = {
            "response": '{"name": "test", "age": 30}',
        }
        mock_post.return_value.status_code = 200

        client = OllamaClient()
        result = client.structured_generate("test prompt")

        assert "parsed_response" in result
        assert result["parsed_response"]["name"] == "test"

    @patch("tools.ollama_client.requests.post")
    @patch("tools.ollama_client.requests.get")
    def test_structured_generate_invalid_json(self, mock_get, mock_post):
        """Test structured generation with invalid JSON."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        mock_post.return_value.json.return_value = {
            "response": "not valid json",
        }
        mock_post.return_value.status_code = 200

        client = OllamaClient()

        with pytest.raises(OllamaException):
            client.structured_generate("test prompt")

    @patch("tools.ollama_client.requests.get")
    def test_is_model_available(self, mock_get):
        """Test model availability check."""
        mock_get.return_value.json.return_value = {
            "models": [{"name": "qwen3:8b"}, {"name": "llama:7b"}]
        }
        mock_get.return_value.status_code = 200

        client = OllamaClient()

        assert client.is_model_available("qwen3:8b") is True
        assert client.is_model_available("nonexistent:8b") is False
