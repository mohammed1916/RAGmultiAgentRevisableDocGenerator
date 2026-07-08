"""Ollama API client."""

import json
import time
from typing import Any, Dict, List, Optional

import requests

from ..config import config
from ..exceptions import OllamaConnectionException, OllamaException
from ..logger import setup_logger

logger = setup_logger(__name__)


class OllamaClient:
    """Client for interacting with the Ollama API."""

    def __init__(self, base_url: str = None, model: str = None):
        """Initialize the Ollama client.

        Args:
            base_url: Ollama API base URL
            model: Model name to use
        """
        self.base_url = base_url or config.ollama.base_url
        self.model = model or config.ollama.model
        self.timeout = config.ollama.timeout
        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify connection to Ollama service."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=5
            )
            response.raise_for_status()
            logger.info(f"Connected to Ollama at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise OllamaConnectionException(
                f"Cannot connect to Ollama at {self.base_url}: {str(e)}"
            )

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using the model.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters for the generate endpoint

        Returns:
            Generation result with response, timing, and token info
        """
        logger.info(f"Generating with prompt length: {len(prompt)}")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            **kwargs,
        }

        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            latency_ms = (time.time() - start_time) * 1000

            result = response.json()
            result["latency_ms"] = latency_ms
            result["model"] = self.model

            logger.info(
                f"Generation completed in {latency_ms:.2f}ms. "
                f"Tokens: {result.get('eval_base', 0)} prompt, "
                f"{result.get('eval_count', 0)} completion"
            )
            return result
        except requests.exceptions.RequestException as e:
            raise OllamaException(f"Generation failed: {str(e)}")

    def chat(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> Dict[str, Any]:
        """Send a chat message to the model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters for the chat endpoint

        Returns:
            Chat result with response, timing, and token info
        """
        logger.info(f"Chat with {len(messages)} messages")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            **kwargs,
        }

        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            latency_ms = (time.time() - start_time) * 1000

            result = response.json()
            result["latency_ms"] = latency_ms
            result["model"] = self.model

            logger.info(
                f"Chat completed in {latency_ms:.2f}ms. "
                f"Tokens: {result.get('prompt_eval_count', 0)} prompt, "
                f"{result.get('eval_count', 0)} completion"
            )
            return result
        except requests.exceptions.RequestException as e:
            raise OllamaException(f"Chat failed: {str(e)}")

    def structured_generate(
        self, prompt: str, schema: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output (JSON).

        The function appends JSON schema instructions to the prompt.

        Args:
            prompt: Input prompt
            schema: Optional JSON schema for validation
            **kwargs: Additional parameters

        Returns:
            Dictionary with parsed JSON response and metadata
        """
        if schema:
            schema_str = json.dumps(schema, indent=2)
            full_prompt = (
                f"{prompt}\n\n"
                f"Return ONLY valid JSON matching this schema:\n"
                f"{schema_str}"
            )
        else:
            full_prompt = (
                f"{prompt}\n\n"
                "Return ONLY valid JSON. No other text."
            )

        result = self.generate(full_prompt, **kwargs)

        try:
            # Extract JSON from response
            response_text = result.get("response", "").strip()

            # Try to find JSON in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)

            result["parsed_response"] = parsed
            logger.info("Structured generation successful")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise OllamaException(
                f"Failed to parse structured response as JSON: {str(e)}"
            )

    def is_model_available(self, model: str = None) -> bool:
        """Check if a model is available locally.

        Args:
            model: Model name to check (uses default if not provided)

        Returns:
            True if model is available, False otherwise
        """
        model = model or self.model
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=5
            )
            response.raise_for_status()
            models = response.json().get("models", [])
            return any(m.get("name", "").startswith(model) for m in models)
        except requests.exceptions.RequestException:
            return False
