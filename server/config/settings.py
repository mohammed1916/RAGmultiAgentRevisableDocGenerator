"""Application configuration."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file for Cloud Ollama and other config
load_dotenv()


@dataclass
class LangSmithConfig:
    """LangSmith tracing and observability configuration."""

    enabled: bool = os.getenv("LANGSMITH_ENABLED", "false").lower() == "true"
    api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    endpoint: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    project: str = os.getenv("LANGSMITH_PROJECT", "specbot-rag")


@dataclass
class OllamaConfig:
    """Ollama service configuration.

    Supports both local and cloud modes:
    - Local: OLLAMA_MODE=local, OLLAMA_BASE_URL=http://localhost:11434
    - Cloud: OLLAMA_MODE=cloud, OLLAMA_KEY=<api-key>, OLLAMA_BASE_URL=<cloud-url>
    """

    mode: str = os.getenv("OLLAMA_MODE", "local")  # "local" or "cloud"
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    api_key: str = os.getenv("OLLAMA_KEY", "")  # For cloud mode
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "300"))


@dataclass
class AppConfig:
    """Application configuration."""

    ollama: OllamaConfig = None
    langsmith: LangSmithConfig = None
    max_review_iterations: int = 2
    document_output_dir: str = "output"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self):
        if self.ollama is None:
            self.ollama = OllamaConfig()
        if self.langsmith is None:
            self.langsmith = LangSmithConfig()
        os.makedirs(self.document_output_dir, exist_ok=True)


# Global config instance
config = AppConfig()
