"""Application configuration."""

import os
from dataclasses import dataclass


@dataclass
class OllamaConfig:
    """Ollama service configuration."""

    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "300"))


@dataclass
class AppConfig:
    """Application configuration."""

    ollama: OllamaConfig = None
    max_review_iterations: int = 2
    document_output_dir: str = "generated_documents"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self):
        if self.ollama is None:
            self.ollama = OllamaConfig()
        os.makedirs(self.document_output_dir, exist_ok=True)


# Global config instance
config = AppConfig()
