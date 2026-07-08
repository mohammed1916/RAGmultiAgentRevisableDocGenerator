"""Custom exceptions for the application."""


class DocumentGenerationException(Exception):
    """Base exception for document generation errors."""

    pass


class OllamaException(DocumentGenerationException):
    """Exception raised when Ollama API calls fail."""

    pass


class OllamaConnectionException(OllamaException):
    """Exception raised when unable to connect to Ollama."""

    pass


class AgentException(DocumentGenerationException):
    """Exception raised when an agent fails."""

    pass


class PlannerException(AgentException):
    """Exception raised by the Planner Agent."""

    pass


class WriterException(AgentException):
    """Exception raised by the Writer Agent."""

    pass


class ReviewerException(AgentException):
    """Exception raised by the Reviewer Agent."""

    pass


class DOCXGenerationException(DocumentGenerationException):
    """Exception raised when DOCX generation fails."""

    pass


class ValidationException(DocumentGenerationException):
    """Exception raised for validation errors."""

    pass
