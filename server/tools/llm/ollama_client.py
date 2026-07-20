"""Ollama API client."""

import json
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...config import config
from ...base.exceptions import OllamaConnectionException, OllamaException
from ...base.logger import setup_logger

logger = setup_logger(__name__)


def _build_session() -> requests.Session:
    """Create a pooled session with retry/backoff for transient failures."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class OllamaClient:
    """Client for interacting with the Ollama API."""

    def __init__(self, base_url: str = None, model: str = None, api_key: str = None):
        """Initialize the Ollama client.

        Supports local and cloud modes based on configuration.

        Args:
            base_url: Ollama API base URL
            model: Model name to use
            api_key: API key for cloud mode
        """
        self.base_url = (base_url or config.ollama.base_url).rstrip("/")
        self.model = model or config.ollama.model
        self.timeout = config.ollama.timeout
        self.mode = config.ollama.mode
        self.api_key = api_key or config.ollama.api_key
        self.session = _build_session()

        logger.info(f"Ollama client initialized in {self.mode} mode")
        if self.mode == "cloud":
            # Never log the key itself, only whether one is configured.
            logger.info("Using Ollama Cloud (API key configured: %s)", bool(self.api_key))
        elif self.mode == "local":
            logger.info(f"Using local Ollama at {self.base_url}")

        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify connection to Ollama service (local or cloud)."""
        try:
            headers = {}
            if self.mode == "cloud" and self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = self.session.get(
                f"{self.base_url}/api/tags",
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Successfully connected to Ollama ({self.mode} mode) at {self.base_url}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Cannot connect to Ollama at {self.base_url}: {str(e)}")
            # Don't fail on cloud mode - API might have different connection check
            if self.mode == "local":
                raise OllamaConnectionException(
                    f"Cannot connect to local Ollama at {self.base_url}: {str(e)}"
                )
            else:
                logger.info("Continuing in cloud mode (connection check may not be available)")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests (includes auth for cloud mode)."""
        headers = {"Content-Type": "application/json"}
        if self.mode == "cloud" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

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
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers=self._get_headers(),
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
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers=self._get_headers(),
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
        """Generate structured output (JSON) with retry on parse failure.

        The function appends JSON schema instructions to the prompt.
        If JSON parsing fails, retries with error feedback to the LLM.

        Args:
            prompt: Input prompt
            schema: Optional JSON schema for validation
            **kwargs: Additional parameters

        Returns:
            Dictionary with parsed JSON response and metadata
        """
        if schema:
            schema_str = json.dumps(schema, indent=2)
            base_prompt = (
                f"{prompt}\n\n"
                f"Return ONLY valid JSON matching this schema:\n"
                f"{schema_str}"
            )
        else:
            base_prompt = (
                f"{prompt}\n\n"
                "Return ONLY valid JSON. No other text."
            )

        # Retry up to 2 times on JSON parse failure
        max_retries = 2
        last_error = None

        for attempt in range(max_retries):
            if attempt == 0:
                full_prompt = base_prompt
            else:
                # On retry, include error feedback
                full_prompt = (
                    f"{base_prompt}\n\n"
                    f"PREVIOUS ATTEMPT FAILED with error:\n{last_error}\n\n"
                    "Please fix this and return ONLY valid JSON with proper escaping. "
                    "Ensure all backslashes are properly escaped (use \\\\ for literal backslash)."
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
                if attempt > 0:
                    logger.info(f"Structured generation successful (retry {attempt})")
                else:
                    logger.info("Structured generation successful")
                return result
            except (json.JSONDecodeError, ValueError) as e:
                last_error = str(e)
                logger.warning(
                    f"JSON parse attempt {attempt + 1} failed: {last_error}. "
                    f"Retrying..." if attempt < max_retries - 1 else "Max retries reached."
                )
                if attempt == max_retries - 1:
                    # Last attempt failed
                    logger.error(f"Failed to parse JSON after {max_retries} attempts: {last_error}")
                    raise OllamaException(
                        f"Failed to parse structured response as JSON after {max_retries} attempts: {last_error}"
                    )

        # Defensive: the loop always returns or raises above, but guard against
        # an implicit None return if the retry logic ever changes.
        raise OllamaException(
            f"Structured generation exhausted retries without a result: {last_error}"
        )

    def is_model_available(self, model: str = None) -> bool:
        """Check if a model is available.

        Args:
            model: Model name to check (uses default if not provided)

        Returns:
            True if model is available, False otherwise
        """
        model = model or self.model
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            models = response.json().get("models", [])
            return any(m.get("name", "").startswith(model) for m in models)
        except requests.exceptions.RequestException:
            # Cloud mode may not support /api/tags endpoint
            if self.mode == "cloud":
                logger.info("Cloud mode: Assuming model is available (cannot verify)")
                return True
            return False
