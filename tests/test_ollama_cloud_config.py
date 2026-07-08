"""Tests for Ollama Cloud configuration support."""

import pytest
import os
from unittest.mock import patch, MagicMock

from server.tools.ollama_client import OllamaClient


class TestOllamaCloudConfiguration:
    """Test Ollama Cloud support in configuration."""

    def test_ollama_config_has_cloud_support(self):
        """Test that OllamaConfig class supports cloud mode."""
        from server.config import OllamaConfig
        # Just verify the attributes exist
        config = OllamaConfig(mode="cloud", api_key="test-key")
        assert hasattr(config, "mode")
        assert hasattr(config, "api_key")
        assert hasattr(config, "base_url")
        assert hasattr(config, "model")

    def test_cloud_mode_attribute(self):
        """Test cloud mode can be set."""
        from server.config import OllamaConfig
        config = OllamaConfig(mode="cloud")
        assert config.mode == "cloud"

    def test_api_key_attribute(self):
        """Test API key can be set."""
        from server.config import OllamaConfig
        config = OllamaConfig(api_key="my-secret-key")
        assert config.api_key == "my-secret-key"


class TestOllamaClientCloudMode:
    """Test OllamaClient with cloud mode."""

    @patch("server.tools.ollama_client.requests.get")
    def test_get_headers_local_mode(self, mock_get):
        """Test that local mode doesn't add auth headers."""
        mock_get.return_value = MagicMock(json=lambda: {"models": []})

        client = OllamaClient(base_url="http://localhost:11434", model="mistral")
        headers = client._get_headers()
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"

    @patch("server.tools.ollama_client.requests.get")
    def test_get_headers_cloud_mode(self, mock_get):
        """Test that cloud mode adds Bearer token auth header."""
        mock_get.return_value = MagicMock(json=lambda: {"models": []})

        client = OllamaClient(
            base_url="https://api.ollama.ai",
            model="mistral",
            api_key="test-key-12345"
        )
        client.mode = "cloud"  # Force cloud mode for testing
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key-12345"

    @patch("server.tools.ollama_client.requests.post")
    @patch("server.tools.ollama_client.requests.get")
    def test_generate_includes_auth_headers_cloud(self, mock_get, mock_post):
        """Test that generate includes auth headers in cloud mode."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "test response",
            "eval_count": 10,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        mock_get.return_value = mock_response

        client = OllamaClient(
            base_url="https://api.ollama.ai",
            model="mistral",
            api_key="test-key-xyz"
        )
        client.mode = "cloud"  # Force cloud mode
        result = client.generate("test prompt")

        # Verify the call included auth headers
        call_args = mock_post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "Authorization" in headers
        assert "test-key-xyz" in headers["Authorization"]

    @patch("server.tools.ollama_client.requests.get")
    def test_cloud_mode_api_key_parameter(self, mock_get):
        """Test that api_key parameter is used when provided."""
        mock_get.return_value = MagicMock(json=lambda: {"models": []})

        client = OllamaClient(
            base_url="https://api.ollama.ai",
            api_key="cloud-key-abc123"
        )
        assert client.api_key == "cloud-key-abc123"


class TestEnvironmentLoading:
    """Test .env file loading in run_server."""

    def test_env_file_example_exists(self):
        """Test that .env.example file exists with proper content."""
        from pathlib import Path
        env_file = Path(".env.example")
        assert env_file.exists(), ".env.example file should exist"

        content = env_file.read_text()
        assert "OLLAMA_MODE" in content
        assert "OLLAMA_KEY" in content
        assert "OLLAMA_BASE_URL" in content
        assert "cloud" in content.lower()
        assert "local" in content.lower()

    def test_env_example_has_both_modes(self):
        """Test that .env.example shows configuration for both modes."""
        from pathlib import Path
        env_file = Path(".env.example")
        content = env_file.read_text()

        # Check for local mode section
        assert "OLLAMA_MODE=local" in content
        assert "http://localhost:11434" in content

        # Check for cloud mode section
        assert "OLLAMA_MODE=cloud" in content
        assert "ollama.ai" in content or "api." in content
